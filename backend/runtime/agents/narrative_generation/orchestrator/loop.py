import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable

import json_repair
from pydantic import ValidationError

from core.llm import LLMClient
from runtime.agents.models import (
    ToolCall,
    ToolCallsOutput,
    ToolResult,
)
from runtime.game_logger import glog


@dataclass
class LoopConfig:
    model: str
    temperature: float
    thinking_budget: int | None
    config_name: str
    max_rounds: int = 5
    extra_params: dict = field(default_factory=dict)
    api_base: str | None = None
    api_key_env: str | None = None


@dataclass
class LoopResult:
    tool_results: dict[str, ToolResult] = field(default_factory=dict)
    orchestrator_meta: dict = field(default_factory=dict)


def run_tool_loop(
    llm: LLMClient,
    system_prompt: str,
    user_input: str,
    loop_config: LoopConfig,
    tool_handler: Callable[[ToolCall], ToolResult],
) -> LoopResult:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]
    all_tool_results: dict[str, ToolResult] = {}

    for round_num in range(loop_config.max_rounds):
        response_text = _call_llm(llm, messages, loop_config)
        parsed = _parse_response(response_text)

        if isinstance(parsed, ToolCallsOutput):
            glog.log("AGENT_EXEC", {
                "agent": loop_config.config_name,
                "step": "tool_loop_round",
                "round": round_num + 1,
                "tool_calls": [tc.name for tc in parsed.tool_calls],
            })
        else:
            glog.log("AGENT_EXEC", {
                "agent": loop_config.config_name,
                "step": "ready_for_writer",
                "round": round_num + 1,
            })

        if isinstance(parsed, ToolCallsOutput) and parsed.tool_calls:
            results = _execute_tool_calls_parallel(parsed.tool_calls, tool_handler)
            for r in results:
                all_tool_results[r.tool_name] = r
            if "request_bridge" in all_tool_results or "deviation_release" in all_tool_results:
                return LoopResult(tool_results=all_tool_results, orchestrator_meta={})
            _append_tool_results(messages, response_text, results)
            continue

        meta = parsed if isinstance(parsed, dict) else {}
        return LoopResult(tool_results=all_tool_results, orchestrator_meta=meta)

    return LoopResult(tool_results=all_tool_results, orchestrator_meta={})


def _call_llm(
    llm: LLMClient,
    messages: list[dict],
    loop_config: LoopConfig,
) -> str:
    prompt_parts = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        if role == "system":
            prompt_parts.append(content)
        elif role == "user":
            prompt_parts.append(f"\n--- User Input ---\n{content}")
        elif role == "assistant":
            prompt_parts.append(f"\n--- Previous Response ---\n{content}")
        elif role == "tool_result":
            prompt_parts.append(f"\n--- Tool Results ---\n{content}")

    prompt = "\n".join(prompt_parts)
    return llm.generate(
        prompt=prompt,
        model=loop_config.model,
        temperature=loop_config.temperature,
        thinking_budget=loop_config.thinking_budget,
        extra_params=loop_config.extra_params or None,
        api_base=loop_config.api_base,
        api_key_env=loop_config.api_key_env,
    )


def _parse_response(response_text: str) -> ToolCallsOutput | dict:
    text = response_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        glog.log("ORCHESTRATOR_JSON_REPAIR", {
            "response_preview": text[:200],
        })
        try:
            repaired = json_repair.repair_json(text)
            data = json.loads(repaired)
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Invalid JSON from LLM: {e}\nResponse: {text[:500]}")

    if "tool_calls" in data and data["tool_calls"]:
        normalized_calls = []
        for call in data["tool_calls"]:
            if "arguments" not in call:
                name = call.get("name")
                arguments = {k: v for k, v in call.items() if k != "name"}
                normalized_calls.append({"name": name, "arguments": arguments})
            else:
                normalized_calls.append(call)
        data["tool_calls"] = normalized_calls

        try:
            return ToolCallsOutput.model_validate(data)
        except ValidationError as e:
            raise ValueError(f"Invalid tool_calls format: {e}")

    if "ready_for_writer" in data or "narrative" in data:
        return data

    raise ValueError(f"Response missing tool_calls or ready_for_writer: {list(data.keys())}")


def _append_tool_results(
    messages: list[dict],
    assistant_response: str,
    tool_results: list[ToolResult],
) -> None:
    messages.append({"role": "assistant", "content": assistant_response})
    parts = ["<tool_results>"]
    for result in tool_results:
        parts.append(f'<result tool="{result.tool_name}">')
        parts.append(result.content)
        parts.append("</result>")
    parts.append("</tool_results>")
    messages.append({"role": "tool_result", "content": "\n".join(parts)})


def _execute_tool_calls_parallel(
    tool_calls: list[ToolCall],
    tool_handler: Callable[[ToolCall], ToolResult],
) -> list[ToolResult]:
    if len(tool_calls) <= 1:
        return [tool_handler(tc) for tc in tool_calls]

    with ThreadPoolExecutor(
        max_workers=len(tool_calls),
        thread_name_prefix="toolloop",
    ) as pool:
        futures = [pool.submit(tool_handler, tc) for tc in tool_calls]
        return [f.result() for f in futures]
