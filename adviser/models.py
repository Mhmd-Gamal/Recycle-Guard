from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, serialize_by_alias=True)


class Action(StrictModel):
    kind: str = Field(max_length=40)
    zone: int
    revision: int = Field(ge=0)


class Zone(StrictModel):
    id: int = Field(ge=0, le=3)
    name: str = Field(max_length=80)
    heat: int = Field(ge=-1, le=100)
    people: int = Field(ge=-1, le=4)
    isolated: int = Field(ge=-1, le=1)
    observedAt: int = Field(ge=-1, le=32)
    age: int = Field(ge=-1, le=32)
    source: Literal["recon", "telemetry", "unavailable"]


class Observation(StrictModel):
    schema_version: Literal["recycleguard.observation.v1"] = Field(alias="schema")
    seed: int = Field(ge=-2147483648, le=2147483647)
    tick: int = Field(ge=0, le=32)
    revision: int = Field(ge=0, le=32)
    water: int = Field(ge=0, le=18)
    crews: int = Field(ge=0, le=2)
    horizon: Literal[32]
    damage: int = Field(ge=0)
    scenario: Literal["reliable", "delayed", "dropout"]
    status: Literal["active", "contained", "escalated", "timeout"]
    zones: list[Zone] = Field(min_length=4, max_length=4)

    @model_validator(mode="after")
    def consistent(self):
        if self.revision != self.tick or [z.id for z in self.zones] != [0, 1, 2, 3]:
            raise ValueError("Revision/tick or zone ordering mismatch")
        for z in self.zones:
            if z.source == "unavailable":
                if any(v != -1 for v in (z.heat, z.people, z.isolated, z.age, z.observedAt)):
                    raise ValueError("Unavailable evidence must be explicitly unknown")
            elif z.age != self.tick - z.observedAt or z.observedAt < 0 or min(z.heat, z.people, z.isolated) < 0:
                raise ValueError("Invalid evidence timestamp/value")
        return self


class AdviceRequest(StrictModel):
    observation: Observation
    mode: Literal["scripted", "offline_raw", "offline_checked_permissive", "offline_checked", "llm_raw", "llm_checked"] = "offline_checked"
    exclude: list[Action] = Field(default_factory=list, max_length=24)


class Advice(StrictModel):
    schema_version: Literal["recycleguard.advice.v1"] = Field(default="recycleguard.advice.v1", alias="schema")
    revision: int
    mode: str
    provider: str
    proposal: Action
    recommendation: Action
    intervention: bool
    violations: list[str]
    explanation: str
    evidence: list[str]
    missing: list[str]
    alternatives: list[Action]
    latency_ms: float
    uncertainty: str
    plan: list[str]

