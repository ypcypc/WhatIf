from dataclasses import dataclass

from core.models import PhaseType


@dataclass(frozen=True)
class PhaseConfig:
    system_prompt_file: str
    input_template_file: str
    config_name: str


PHASE_CONFIGS: dict[PhaseType, PhaseConfig] = {
    PhaseType.SETUP: PhaseConfig(
        system_prompt_file="setup_system.txt",
        input_template_file="setup_input.txt",
        config_name="setup_orchestrator",
    ),
    PhaseType.CONFRONTATION: PhaseConfig(
        system_prompt_file="confrontation_system.txt",
        input_template_file="confrontation_input.txt",
        config_name="confrontation_orchestrator",
    ),
    PhaseType.RESOLUTION: PhaseConfig(
        system_prompt_file="resolution_system.txt",
        input_template_file="resolution_input.txt",
        config_name="resolution_orchestrator",
    ),
}
