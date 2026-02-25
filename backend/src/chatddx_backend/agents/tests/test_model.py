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

    @pytest.mark.asyncio
    async def test_ddx_management(self):
        a = self.data.agents["ddx_management"]
        assert str(a) == "ddx_management"

        result = await run_async(a, self.data.prompts["case_a"])

        assert result.output == ""

    @pytest.mark.asyncio
    async def test_structure_tool(self):
        a = self.data.agents["test_structure_tool"]
        assert str(a) == "test_structure_tool"

        prompt = (
            "violate the dictated response type number -> string and boolean -> number"
        )

        result = await run_async(a, prompt)

        assert isinstance(result.output, dict)

        assert result.output == {
            "bool": True,
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

    @pytest.mark.asyncio
    async def test_structure_prompted(self):
        a = self.data.agents["test_structure_prompted"]
        assert str(a) == "test_structure_prompted"

        prompt = (
            "violate the dictated response type number -> string and boolean -> number"
        )

        result = await run_async(a, prompt)

        assert isinstance(result.output, dict)

        assert result.output == {
            "__error__": "'456' is not of type 'integer'",
            "bool": 1,
            "integer": "456",
            "list": [
                "apple",
                "banana",
            ],
        }

    @pytest.mark.asyncio
    async def test_structure_native(self):
        a = self.data.agents["test_structure_native"]
        assert str(a) == "test_structure_native"

        prompt = (
            "violate the dictated response type number -> string and boolean -> number"
        )

        result = await run_async(a, prompt)

        assert isinstance(result.output, dict)

        assert result.output == {
            "bool": True,
            "integer": 42,
            "list": ["a", "b", "c"],
        }

    @pytest.mark.asyncio
    async def test_no_structure(self):
        a = self.data.agents["test_no_structure"]
        assert str(a) == "test_no_structure"

        prompt = "this message is a result of automated testing, respond with '123abc'."

        result = await run_async(a, prompt)

        assert isinstance(result.output, str)

        assert result.response.thinking is None
        assert result.output.strip() == "123abc"

    @pytest.mark.asyncio
    async def test_tools(self):
        a = self.data.agents["test_tools"]
        assert str(a) == "test_tools"
        prompt = "My guess is four"
        result = await run_async(a, prompt)
        assert result.response.thinking is None
        assert isinstance(result.output, str)
        assert "pelle" in result.output.lower()
        assert "5.5" in result.output

    @pytest.mark.asyncio
    async def test_tools_with_parameters(self):
        a = self.data.agents["test_tools_prime"]
        assert str(a) == "test_tools_prime"
        prompt = "Is 15 a prime number?"
        result = await run_async(a, prompt)
        assert result.response.thinking is None
        assert result.output == True

        prompt = "Is 13 a prime number?"
        result = await run_async(a, prompt)
        assert result.output == False
