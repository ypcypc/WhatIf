### 总览：一次完整「点击 → 阅读 → 回复 → 下一段」循环

```
玩家输入          ⟶  前端 UI（React）
                       ⟶  Anchor Service（FastAPI 路由）
                             ⟶  原文＋锚点
                       ⟶  LLM Service（FastAPI 路由）
                             ⟶  ChatGPT-4.1-mini
                             ⟶  结构化脚本 + 状态变更
                       ⟶  前端逐句渲染
                       ⟶  玩家回复
«重复»
```

---

## 1. 前端（React）——**单轮交互的责任分割**

| 阶段        | 前端动作                                                      | 何时解锁输入                | 何时锁定输入                          |
| --------- | --------------------------------------------------------- | --------------------- | ------------------------------- |
| **加载脚本**  | 调用 *Anchor → LLM*，拿到 `script` 数组                          | 脚本返回 **并** 渲染完毕时      | 发起请求后立即                         |
| **展示**    | 用“打字机”或淡入动画逐句吐出 `narration` / `chat`                      | 每句渲染完即可继续下一句          | 整段脚本全部吐完前不响应 Enter              |
| **进入交互**  | 遇到 `interaction`，在文本框中放入 `defaultReply` 作为半透明 placeholder | `interaction` 渲染完毕即解锁 | 用户按 **Enter** 提交；UI 显示用户回复后立刻锁定 |
| **触发下一轮** | 把 `session_id`、`player_reply` 发给 Anchor Service           | ——                    | 同上                              |

> **前端状态保存**：除 `session_id` 外，不额外存历史；只保留 “本轮脚本 + 正在显示的段落索引” 等 UI 状态。
> **并发控制**：页面维护一个 `isBusy` 布尔值；只要处于网络请求中或脚本尚未渲染完成，就拦截 Enter、点击、滚轮等。

---

## 2. Anchor Service——**文本拼接策略**

1. 根据 `chapterId` 与 `anchorIndex` 计算：

   * `startIdx = prevAnchorPos + 1`（若无上一锚点则 0）
   * `endIdx   = currAnchorPos`
2. 读取章节段落列表，切片 `[startIdx : endIdx]` 形成「原文片段」。
3. 取 `currAnchorPos` 处的 **锚点文本**，拼在原文片段之后。
4. 若 `currAnchorPos` 是本章最后一个锚点，可附带章节尾部文本，方便下一轮过渡。
5. 返回给前端一个字段 `context`, 其内容顺序恒为：

   ```
   原文片段
   ——分隔符（可选）
   锚点文本
   ——分隔符（可选）
   （尾部原文）
   ```

> **检索介质**：段落可以来自平铺的 JSON 数组、SQLite、甚至向量库；关键是能 O(1) 地定位段落索引。
> **幂等性**：同一 `chapterId` + `anchorIndex` 调用多次返回一致，便于重放与测试。

---

## 3. LLM Service——**Prompt 组装细节**

| 片段顺序 | 内容                                       | 说明                                                                        |
| ---- | ---------------------------------------- | ------------------------------------------------------------------------- |
| ①    | `summary:` 长期摘要                          | 出自快照；快照应该大概在原文的字数的 1 / 3 左右                                               |
| ②    | `recent:` 最近 5 轮（锚点 ± 原文 ± 玩家回复 ± AI 脚本） | 从快照 `recent` 直接序列化                                                        |
| ③    | `state:` JSON 格式的全局变量                    | 包含 `deviation`、`affinity`、`flags`、`variables`                             |
| ④    | `context:` 原文＋锚点 （由 Anchor Service 提供）   | 确保原文在前，锚点在后                                                               |
| ⑤    | `player_reply:` 玩家刚输入的文本                 | 空串表示章节开头或自动剧情                                                             |
| ⑥    | 指令栅栏                                     | 清晰告诉模型：输出 **JSON**，字段 `type, text, speakerId, defaultReply, stateDelta` 等 |

### 偏离度（`deviation`）控制逻辑

* `deviation < 0.05` → 直接复制小说原句；`stateDelta.deviation = 0`.
* `0.05 ≤ deviation ≤ 0.3` → 轻微改编，主线一致；`stateDelta.deviation` 微增减。
* `> 0.3` → 允许自由发挥，但**必须**在输出里暗示收束：`stateDelta.deviation` 至多回落 0.1\~0.2。
* 后端在拿到 `stateDelta` 后与原值相加裁剪到 \[0, 1]，再写回快照。

> **Token 预算**：把 ①+② 压缩 ≤ 800 tokens；④ 控制在 600 tokens 左右；指令 + ③ + ⑤ 约 200 tokens；可在 4k-context 内运行。
> **OpenAI 调用**：使用 `tool_choice = "auto"`，让模型走函数调用返回结构化 JSON；并把温度随着 `deviation` 增大而线性提高（如 0.3 → 0.9）。

---

## 4. 数据持久化

| 文件              | 写入时机                  | 作用                            |
| --------------- | --------------------- | ----------------------------- |
| `events.jsonl`  | 每轮结束，把玩家事件与 AI 事件各写一行 | 完整审计                          |
| `snapshot.json` | 同时覆盖写入                | 保存 `<summary, recent, state>` |
| （可选）向量库         | 超过 N 段被摘要的文本转成向量      | Anchor 复合检索                   |

* 当 `recent` > 5 时，取最早 2\~3 条做摘要；摘要调用与脚本生成同一个模型，但用低温度和总结指令。
* `summary` 字数上限 2 k 中文字符；溢出时再压缩一次。

---

## 5. 运行与部署要点

| 层面          | 建议                                                                                              |
| ----------- | ----------------------------------------------------------------------------------------------- |
| **FastAPI** | 开 `uvicorn` 多 worker；LLM 调用放协程；文件 I/O 用 `aiofiles`；对 OpenAI 调用加 `tenacity` 重试与速率限额。             |
| **队列**      | 若担心 LLM 延时，可将生成任务入 Redis/-RQ；前端轮询或 WebSocket 拉流。                                                |
| **前端**      | Create-React-App / Vite；用 `react-query` 或 SWR 处理请求状态；全局 `AppContext` 存 `session_id` 与 `isBusy`。 |
| **CI/CD**   | 前端 Netlify/Vercel；后端 Docker + Gunicorn + UvicornWorkers；配置 `OPENAI_API_KEY` `DATA_DIR` 等环境变量。   |
| **版本回溯**    | 事件流即事实真相；任何调试可重放 `events.jsonl`。                                                                |
| **测试**      | 单元测试：Anchor 边界条件、Prompt 拼接、偏离度裁剪；集成测试：模拟三轮互动确保文件正确更新。                                           |

---

### 关键点回顾

1. **Anchor Service 负责“锚点间剪裁”**，LLM Service 负责“记忆拼接＋偏离度策略”。
2. **前端永不保存大段历史**——只看脚本、只交互、只控节奏。
3. **偏离度单向缓冲**——跑偏可慢慢拉回，绝不瞬移。
4. **所有状态写回快照**，文件就是数据库；向量库只是加速检索。

按此思路落地，就可以在 React-FastAPI 框架下实现既忠实原著又可互动的轻小说 / Galgame 体验。祝项目顺利！
