import pytest

from chatddx.core.choices import ToolChoices
from chatddx.core.models import IdentityModel
from chatddx.repo import proxies
from chatddx.repo.base import BaseFormDataOut, TrailSchema
from chatddx.repo.branch_models import ToolBranchModel
from chatddx.repo.form_data_in import ToolFormDataIn
from chatddx.repo.loaders.branches import get_branch_model
from chatddx.repo.main import Repo


def test_type_pipeline():
    tool = Repo("tool", TrailSchema).model_validate(
        {
            "command": "cmd",
            "type": ToolChoices.FUNCTION,
        }
    )
    assert tool.command == "cmd"

    assert Repo("tool", BaseFormDataOut).model_validate


@pytest.mark.django_db
def test_branch():
    IdentityModel.objects.get_or_create(name="alex")
    data = {
        "name": "tool",
        "command": "cmd",
        "type": ToolChoices.FUNCTION,
    }
    form_data = ToolFormDataIn.model_validate(data)
    tool = get_branch_model("tool", "alex", form_data)
    tool.save()
    ToolBranchModel.objects.get(name="tool")
    assert isinstance(tool, proxies.Tool)
    tool = get_branch_model("tool", "alex", form_data)
    assert isinstance(tool, proxies.Tool)
