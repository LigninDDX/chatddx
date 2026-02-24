from pydantic import BaseModel, Field
from enum import Enum


class SelfReport(BaseModel):
    age: int
    name: str
    kind: str
    purpose: str


class Likelyhood(str, Enum):
    HIGH = "High"
    MODERATE = "Moderate"
    LOW = "Low"
    REMOTE = "Remote"


class UrgencyLevel(str, Enum):
    RESUSCITATIVE = "Immediate Life Threat"
    EMERGENT = "Emergent"
    URGENT = "Urgent"
    STABLE = "Stable"
    ROUTINE = "Routine"


class WorkupPriority(str, Enum):
    STAT = "STAT"
    EXPEDITED = "Expedited"
    ROUTINE = "Routine"


class DDXWorkup(BaseModel):
    test_name: str = Field(
        description="(eg. 'CBC/CRP', 'Chest X-ray', 'Point-of-care Ultrasound').",
    )
    priority: WorkupPriority


class DDXDiagnose(BaseModel):
    diagnosis: str = Field(
        description="The formal medical name of the condition.",
    )
    clinical_rationale: str = Field(
        description="The specific findings from the patient's history or exam that support this diagnosis."
    )
    key_negatives: str | None = Field(
        None,
        description="Absence of specific findings that might argue against this diagnosis (eg. 'No fever' makes pneumonia less likely).",
    )
    urgency: UrgencyLevel
    likelyhood: Likelyhood


class DDXManagement(BaseModel):
    possible_diagnoses: list[DDXDiagnose] = Field(
        description="Prioritized differential diagnoses."
    )
    workup: list[DDXWorkup] = Field(
        description="Diagnostic steps",
    )
    warnings: list[str] = Field(
        description="Red Flags or life-threatening findings (eg. 'Hemodynamic instability', 'Signs of peritonitis').",
    )
    empiric_therapy: list[str] = Field(
        description="Interventions to be started concurrently (eg. 'IV Fluids 1L', 'Broad-spectrum antibiotics', 'Oxygen 2L/min').",
    )
    disposition: list[str] = Field(
        description="Primary destination and contingency plans (eg. 'Admit to Cardiology', 'Consult Cardiothoracic Surgery')."
    )
