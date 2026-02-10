from pydantic import BaseModel, Field


class DiagnosisSelection(BaseModel):
    name: str = Field(description="The name of the medical condition")
    confidence: int = Field(description="Ranking or probability score")


class DDXResponse(BaseModel):
    diagnoses: list[DiagnosisSelection]
