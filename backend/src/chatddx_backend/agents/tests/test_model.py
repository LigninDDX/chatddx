# pyright: reportUnusedParameter=false
import pytest

from chatddx_backend.agents.runtime import run_async
from chatddx_backend.agents.tests.data import create_set_a


@pytest.mark.django_db
class TestAgentSuite:
    @pytest.fixture(scope="class", autouse=True)
    def create_data(self, django_db_setup, django_db_blocker):
        with django_db_blocker.unblock():
            TestAgentSuite.data = create_set_a()

    def test_connection(self):
        assert (
            str(self.data.connections["gemma3_4b"])
            == "gemma3:4b@ollama (http://pelle.km:11434/v1)"
        )

    def test_config(self):
        assert self.data.configs["deterministic"].seed == 0

    @pytest.mark.asyncio
    async def test_ddx_management(self):
        a = self.data.agents["ddx_management"]
        assert str(a) == "ddx management"

        result = await run_async(a, self.data.prompts["case_a"])

        assert result.output == ""

    @pytest.mark.asyncio
    async def test_deterministic_type_check(self):
        a = self.data.agents["deterministic_type_check"]
        assert str(a) == "deterministic type check"

        prompt = (
            "violate the dictated response type number -> string and boolean -> number"
        )

        result = await run_async(a, prompt)

        result.output["error"] = result.validation_error

        assert result.output == {
            "bool": True,
            "error": None,
            "integer": 42,
            "list": [
                "violate",
                "the",
                "dictated",
                "response",
                "type",
                "number",
                "->",
                "string",
                "and",
                "boolean",
                "->",
                "number",
            ],
        }
