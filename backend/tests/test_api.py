import pytest
from chatddx_backend.api import models


def test_hello():
    assert True


@pytest.mark.skip(reason="pghistory not implemented yet")
@pytest.mark.django_db
def test_pghistory():
    diagnosis = models.Diagnosis.objects.create(name="name", pattern="pattern")
    diagnosis_perm = diagnosis.events.order_by("-pgh_id")[0]
    assert diagnosis.events.data == 0
    assert diagnosis.pk == 1

    diagnosis_snapshots = models.DiagnosisSnapshot.objects.all()
    assert len(diagnosis_snapshots) == 1

    diagnosis.name = "new name"
    diagnosis.pattern = "new pattern"
    diagnosis.save()

    assert diagnosis_perm.pk == 1
    assert diagnosis_perm.name == "name"

    diagnosis_reverted = diagnosis_perm.revert()
    assert diagnosis_reverted.serialize()["pk"] == 1

    assert diagnosis.pk == 2


@pytest.mark.django_db
def test_serialize():
    _ = models.OpenAIMessageRole.objects.create(name="system")
    role_user = models.OpenAIMessageRole.objects.create(name="user")
    endpoint = "https://mockgpt.wiremockapi.cloud/v1"
    api_key = "sk-6yb1w7imqh88304chm0ldnq0hgtpjr0z"

    test_message = models.OpenAIMessage.objects.create(
        content="hello",
        role=role_user,
    )

    model = models.OpenAIModel.objects.create(name="gpt-4")

    chat = models.OpenAIChat.objects.create(
        endpoint=endpoint,
        api_key=api_key,
        model=model,
    )
    chat.messages.set([test_message])

    _ = models.OpenAIChatCluster.objects.create(
        identifier="test",
        diagnoses=chat,
        examinations=chat,
        details=chat,
    )
    cluster: models.OpenAIChatCluster | None = models.OpenAIChatCluster.objects.get(
        identifier="test"
    )
    assert cluster.identifier == "test"
