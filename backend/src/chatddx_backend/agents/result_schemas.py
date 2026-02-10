from pydantic import BaseModel, Field


class MathAnswer(BaseModel):
    """Math problem solution with reasoning"""

    answer: int
    reasoning: str = Field(description="Step-by-step explanation")


class CodeGeneration(BaseModel):
    """Generated code with metadata"""

    code: str
    language: str
    explanation: str
    tests: list[str] = Field(default_factory=list)


class SentimentAnalysis(BaseModel):
    """Sentiment analysis result"""

    sentiment: str  # positive, negative, neutral
    confidence: float
    reasoning: str


class UserProfile(BaseModel):
    user: str
    profile: str


SCHEMA_REGISTRY = {
    "math_answer": MathAnswer,
    "code_generation": CodeGeneration,
    "sentiment_analysis": SentimentAnalysis,
    "user_profile": UserProfile,
}


def get_schema_choices():
    """For Django choices"""
    return
