from collections import defaultdict
from pathlib import Path

import pytest
from django.urls import reverse

from chatddx_backend.agents.admin import proxies
from chatddx_backend.agents.admin.schemas import TemplateData
from chatddx_backend.agents.models import IdentityModel
from chatddx_backend.agents.models.loader import create_form_data
from chatddx_backend.agents.schemas import TrailRegistry

parameters = [
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
    add_url = reverse("admin:agents_outputtype_add")
    some_key, *rest = data.keys()

    post_data = data[some_key].model_dump(mode="json", exclude_none=True)

    assert isinstance(post_data["definition"], str)
    post_data["definition"] = "asdf=1"

    response = admin_client.post(
        add_url,
        data=post_data,
        follow=True,
    )

    (message,) = [str(m) for m in response.context["messages"]]
    assert "added successfully" in message


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
