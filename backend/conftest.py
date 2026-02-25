import warnings
import pytest


@pytest.fixture(autouse=True)
def ignore_pydantic_ai_deprecation():
    warnings.filterwarnings(
        "ignore",
        message="There is no current event loop",
        category=DeprecationWarning,
        module="pydantic_ai._utils",
    )
