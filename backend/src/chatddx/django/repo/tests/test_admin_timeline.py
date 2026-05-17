# src/chatddx/django/repo/tests/test_admin_timeline.py
from collections import defaultdict
from pathlib import Path

import pytest
from django.db.models import Q
from django.urls import reverse

from chatddx.django.repo.admin import proxies
from chatddx.django.repo.admin.base import qs_super_agent
from chatddx.django.repo.admin.schemas import (
    TemplateData,
    dict_to_toml,
    parse_toml_or_dict,
)
from chatddx.django.repo.models import AgentModel, ConnectionModel, IdentityModel
from chatddx.django.repo.models.history import AgentBranchModel, ToolBranchModel
from chatddx.django.repo.models.loader import create_form_data
from chatddx.django.repo.schemas import TrailRegistry

parameters = [
    (
        "agent",
        "instructions",
        proxies.Agent,
        lambda i: f"instruction {i}",
    ),
    (
        "tool_group",
        "instructions",
        proxies.ToolGroup,
        lambda i: f"instruction {i}",
    ),
    (
        "output_type",
        "definition",
        proxies.OutputType,
        lambda i: {"value": i},
    ),
    (
        "connection",
        "model",
        proxies.Connection,
        lambda i: f"model {i}",
    ),
    (
        "sampling_params",
        "seed",
        proxies.SamplingParams,
        lambda i: i,
    ),
    (
        "tool",
        "command",
        proxies.Tool,
        lambda i: f"cmd_{i}",
    ),
]


@pytest.fixture
def registry():
    return TrailRegistry.from_file(
        Path(__file__).parent / "registry/test-registry.toml"
    )


@pytest.fixture
def owner(admin_user):
    owner, created = IdentityModel.objects.get_or_create(name=admin_user.username)
    return owner


@pytest.fixture
def template_data(owner: IdentityModel, registry: TrailRegistry):
    form_data = defaultdict(dict)

    for kind, data in registry:
        for name, schema in data.items():
            branch_id, data = create_form_data(schema, name, owner.pk, key="name")
            form_data[kind][str(branch_id)] = data

    return TemplateData(**form_data)


@pytest.mark.django_db
def test_super_agent(template_data, owner, admin_client):

    post_data_nested = {
        "agent_": template_data.agent["some-agent"].model_dump(
            mode="json", exclude_none=True
        ),
        "connection_": template_data.connection["some-connection"].model_dump(
            mode="json", exclude_none=True
        ),
        "sampling_params_": template_data.sampling_params[
            "some-sampling_params"
        ].model_dump(mode="json", exclude_none=True),
        "tool_group_": template_data.tool_group["some-tool_group"].model_dump(
            mode="json", exclude_none=True
        ),
        "output_type_": template_data.output_type["some-output_type"].model_dump(
            mode="json", exclude_none=True
        ),
    }
    post_data = {
        f"{outer}{inner}": value
        for outer, inner_dict in post_data_nested.items()
        for inner, value in inner_dict.items()
    }

    existing = AgentBranchModel.objects.filter(
        owner__name=owner.name,
        name="some-agent",
    )

    assert existing.count() == 1

    response = admin_client.post(
        reverse("admin:agents_superagent_add"),
        data=post_data,
        follow=True,
    )
    assert response.status_code == 200
    if "adminform" in response.context:
        assert response.context["adminform"].form.errors == ""

    existing = AgentBranchModel.objects.filter(
        owner__name=owner.name,
        name="some-agent",
    )

    assert existing.count() == 1

    response = admin_client.post(
        reverse("admin:agents_superagent_change", args=[existing.first().pk]),
        data=post_data,
        follow=True,
    )
    assert response.status_code == 200
    if "adminform" in response.context:
        assert response.context["adminform"].form.errors == ""

    existing = AgentBranchModel.objects.filter(
        owner__name=owner.name,
        name="some-agent",
    )

    assert existing.count() == 1

    assert existing.first().target.output_type.definition["type"] == "object"

    output_type_def = parse_toml_or_dict(post_data["output_type_definition"])

    assert output_type_def is not None
    assert output_type_def["type"] == "object"
    assert output_type_def["properties"]["age"]["minimum"] == 0

    post_data["output_type_definition"] = dict_to_toml(output_type_def)

    response = admin_client.post(
        reverse("admin:agents_superagent_change", args=[existing.first().pk]),
        data=post_data,
        follow=True,
    )
    assert response.status_code == 200
    if "adminform" in response.context:
        assert response.context["adminform"].form.errors == ""

    existing = AgentBranchModel.objects.filter(
        owner__name=owner.name,
        name="some-agent",
    )

    assert existing.count() == 1

    output_type_def["properties"]["age"]["minimum"] = 1
    post_data["output_type_definition"] = dict_to_toml(output_type_def)

    response = admin_client.post(
        reverse("admin:agents_superagent_change", args=[existing.first().pk]),
        data=post_data,
        follow=True,
    )
    assert response.status_code == 200
    if "adminform" in response.context:
        assert response.context["adminform"].form.errors == ""

    existing = AgentBranchModel.objects.filter(
        owner__name=owner.name,
        name="some-agent",
    )

    assert existing.count() == 2

    post_data["output_type_definition"] = "asdf"
    response = admin_client.post(
        reverse("admin:agents_superagent_change", args=[existing.first().pk]),
        data=post_data,
        follow=True,
    )
    assert response.status_code == 200
    if "adminform" in response.context:
        assert (
            "Expected '='"
            in response.context["adminform"].form.errors["output_type_definition"][0]
        )


@pytest.mark.django_db
def test_append(template_data, owner, admin_client):
    data = template_data.tool
    some_key = "some-tool"

    post_data = data[some_key].model_dump(mode="json", exclude_none=True)

    assert isinstance(post_data["command"], str)
    assert post_data["command"] == "some-tool"
    assert post_data["id"] is not None

    existing = ToolBranchModel.objects.filter(
        owner__name=owner.name,
        name=some_key,
    )

    assert existing.count() == 1

    post_data["command"] = "some-command"

    response = admin_client.post(
        reverse("admin:agents_tool_change", args=[existing.first().pk]),
        data=post_data,
        follow=True,
    )
    assert response.status_code == 200
    if "adminform" in response.context:
        assert response.context["adminform"].form.errors == ""

    (message,) = [str(m) for m in response.context["messages"]]
    assert "changed successfully" in message

    versions = ToolBranchModel.objects.filter(
        owner__name=owner.name,
        name=some_key,
    ).count()

    assert versions == 2

    response = admin_client.post(
        reverse("admin:agents_tool_delete", args=[existing.first().pk]),
        data={"post": "yes"},
        follow=True,
    )

    existing = ToolBranchModel.objects.filter(
        owner__name=owner.name,
        name=some_key,
    )

    assert existing.count() == 1

    response = admin_client.post(
        reverse("admin:agents_tool_delete", args=[existing.first().pk]),
        data={"post": "yes"},
        follow=True,
    )
    assert existing.count() == 0


@pytest.mark.django_db
def test_view(template_data, owner, admin_client):
    versions = list(
        AgentBranchModel.objects.filter(
            owner_id=owner.pk,
            name="some-agent",
        ).order_by("timestamp")
    )

    v2_url = reverse("admin:agents_agent_change", args=[versions[0].pk])
    response = admin_client.get(v2_url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_ownership(template_data, owner):
    connection_fields = [field.name for field in ConnectionModel._meta.fields]

    agent_trails = AgentModel.objects.filter(
        branches__owner__name=owner.name
    ).distinct()
    assert len(agent_trails) == 4

    all_owned_connections = (
        ConnectionModel.objects.filter(
            Q(agentmodel__branches__owner__name=owner.name)
            | Q(branches__owner__name=owner.name)
        )
        .values(*connection_fields, "branches__name")
        .distinct()
    )
    assert all_owned_connections[0]["branches__name"] == "some-connection"
    assert len(all_owned_connections) == 2

    agent_connections = ConnectionModel.objects.filter(
        agentmodel__branches__owner__name=owner.name
    ).distinct()
    assert len(agent_connections) == 2

    new_owner = IdentityModel.objects.create(name="alex")
    some_agent = AgentBranchModel.objects.filter(name="some-agent").first()
    some_agent.owner_id = new_owner.pk
    some_agent.save()

    (some_agent_trail,) = AgentModel.objects.filter(
        branches__owner__name="alex"
    ).distinct()
    assert some_agent_trail is not None
    assert some_agent_trail.pk == some_agent.target.pk

    agent_trails = AgentModel.objects.filter(
        branches__owner__name=owner.name
    ).distinct()
    assert len(agent_trails) == 3

    agent_connections = ConnectionModel.objects.filter(
        agentmodel__branches__owner__name=owner.name
    ).distinct()
    assert len(agent_connections) == 1

    all_owned_connections = ConnectionModel.objects.filter(
        Q(agentmodel__branches__owner__name=owner.name)
        | Q(branches__owner__name=owner.name)
    ).distinct()
    assert len(all_owned_connections) == 2


@pytest.mark.django_db
def test_sampling_params(template_data):
    data = template_data.sampling_params

    template_dict = template_data.model_dump(mode="json", exclude_none=True)
    dict_data = template_dict["sampling_params"]

    assert list(data.keys()) == [
        "some-sampling_params",
        "sampling_params-1",
        "sampling_params-2",
    ]
    assert data["some-sampling_params"].stop_sequences is None
    assert data["sampling_params-1"].stop_sequences == ["\\n\\n", "END"]
    assert data["sampling_params-2"].stop_sequences == ["END"]

    dict1 = data["some-sampling_params"].model_dump(mode="json", exclude_none=True)
    dict2 = data["sampling_params-1"].model_dump(mode="json", exclude_none=True)
    dict3 = data["sampling_params-2"].model_dump(mode="json", exclude_none=True)

    assert "stop_sequences" not in dict1
    assert dict2["stop_sequences"] == "\\n\\n\nEND"
    assert dict3["stop_sequences"] == "END"

    assert "stop_sequences" not in dict_data["some-sampling_params"]
    assert dict_data["sampling_params-1"]["stop_sequences"] == "\\n\\n\nEND"
    assert dict_data["sampling_params-2"]["stop_sequences"] == "END"


@pytest.mark.django_db
def test_output_type(template_data, admin_client):
    data = template_data.output_type
    some_key, *rest = data.keys()

    post_data = data[some_key].model_dump(mode="json", exclude_none=True)

    assert isinstance(post_data["definition"], str)
    post_data["definition"] = "asdf=1"

    response = admin_client.post(
        reverse("admin:agents_outputtype_add"),
        data=post_data,
        follow=True,
    )

    (message,) = [str(m) for m in response.context["messages"]]
    assert "added successfully" in message


@pytest.mark.django_db
def test_tool_group(template_data, admin_client):
    data = template_data.tool_group
    add_url = reverse("admin:agents_toolgroup_add")
    some_key = "tool_group-1"

    post_data = data[some_key].model_dump(mode="json", exclude_none=True)

    assert isinstance(post_data["instructions"], str)
    assert post_data["instructions"] == "use these tools"
    assert len(post_data["tools"]) == 3

    response = admin_client.post(
        add_url,
        data=post_data,
        follow=True,
    )
    assert response.status_code == 200
    assert "adminform" not in response.context

    (message,) = [str(m) for m in response.context["messages"]]
    assert "up to date" in message


@pytest.mark.django_db
def test_agent_qs(template_data, owner):
    qs = proxies.Agent.objects.filter(name="some-agent", owner_id=owner.pk)
    agent = qs_super_agent(qs, owner.name).first()
    assert agent is not None
    assert agent.connection_id is not None


@pytest.mark.django_db
def test_agent(template_data, admin_client):
    data = template_data.agent
    some_key = "some-agent"

    post_data = data[some_key].model_dump(mode="json", exclude_none=True)

    assert isinstance(post_data["instructions"], str)
    assert post_data["instructions"] == "some instructions"
    assert post_data["id"] is not None
    assert post_data["connection_id"] is not None

    assert (
        AgentBranchModel.objects.get(pk=post_data["id"]).target.instructions
        == "some instructions"
    )

    response = admin_client.post(
        reverse("admin:agents_agent_add"),
        data=post_data,
        follow=True,
    )
    assert response.status_code == 200
    if "adminform" in response.context:
        assert response.context["adminform"].form.errors == ""

    (message,) = [str(m) for m in response.context["messages"]]
    assert "up to date" in message


@pytest.mark.django_db
@pytest.mark.parametrize("test_model, test_field, model_class, mutator", parameters)
def test_idempotent_save_prevents_duplicates(
    admin_client,
    template_data,
    owner,
    test_model,
    test_field,
    model_class,
    mutator,
):
    data = getattr(template_data, test_model)
    admin_name = test_model.replace("_", "")

    add_url = reverse(f"admin:agents_{admin_name}_add")

    some_key, *rest = data.keys()

    response = admin_client.post(
        add_url,
        data=data[some_key].model_dump(mode="json", exclude_none=True),
        follow=True,
    )

    (message,) = [str(m) for m in response.context["messages"]]
    assert "up to date" in message

    response = admin_client.post(
        add_url,
        data=data[some_key].model_dump(mode="json", exclude_none=True),
        follow=True,
    )

    (message,) = [str(m) for m in response.context["messages"]]
    assert "up to date" in message

    timeline = model_class.objects.filter(owner_id=owner.pk, name=some_key)
    assert len(timeline) == 1


@pytest.mark.django_db
@pytest.mark.parametrize("test_model, test_field, model_class, mutator", parameters)
def test_name_change_creates_new_branch(
    admin_client,
    template_data,
    owner,
    test_model,
    test_field,
    model_class,
    mutator,
):
    data = getattr(template_data, test_model)
    admin_name = test_model.replace("_", "")

    add_url = reverse(f"admin:agents_{admin_name}_add")

    some_key, another_key, *rest = data.keys()

    data[some_key].name = another_key

    admin_client.post(
        add_url,
        data=data[some_key].model_dump(mode="json", exclude_none=True),
        follow=True,
    )
    timeline = model_class.objects.filter(owner_id=owner.pk, name=some_key)
    assert len(timeline) == 1

    timeline = model_class.objects.filter(owner_id=owner.pk, name=another_key)
    assert len(timeline) == 2


@pytest.mark.django_db
@pytest.mark.parametrize("test_model, test_field, model_class, mutator", parameters)
def test_pager_context_navigation(
    admin_client,
    template_data,
    owner,
    test_model,
    test_field,
    model_class,
    mutator,
):
    data = getattr(template_data, test_model)
    admin_name = test_model.replace("_", "")

    add_url = reverse(f"admin:agents_{admin_name}_add")

    some_key, another_key, *rest = data.keys()

    for i in range(3):
        setattr(data[some_key], test_field, mutator(i))
        admin_client.post(
            add_url,
            data=data[some_key].model_dump(mode="json", exclude_none=True),
            follow=True,
        )

    versions = list(
        model_class.objects.filter(
            owner_id=owner.pk,
            name=some_key,
        ).order_by("timestamp")
    )

    v2_url = reverse(f"admin:agents_{admin_name}_change", args=[versions[1].pk])
    response = admin_client.get(v2_url)
    assert response.status_code == 200
    assert "prev_" in response.context
    assert "next_" in response.context
    assert response.context["version_info"]["current"] == 2
    assert response.context["version_info"]["total"] == 4

    v1_url = reverse(f"admin:agents_{admin_name}_change", args=[versions[0].pk])
    response = admin_client.get(v1_url)
    assert response.status_code == 200
    assert "next_" in response.context
    assert response.context["version_info"]["current"] == 1
    assert response.context["version_info"]["total"] == 4

    v4_url = reverse(f"admin:agents_{admin_name}_change", args=[versions[3].pk])
    response = admin_client.get(v4_url)
    assert response.status_code == 200
    assert "prev_" in response.context
    assert response.context["version_info"]["current"] == 4
    assert response.context["version_info"]["total"] == 4
