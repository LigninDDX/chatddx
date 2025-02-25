from chatddx_backend.api import models
from django.test import TestCase


def test_hello():
    assert True


class APITestCase(TestCase):
    def setUp(self):
        role_system = models.OpenAIMessageRole.objects.create(name="system")
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

        models.OpenAIChatCluster.objects.create(
            identifier="test",
            diagnoses=chat,
            examinations=chat,
            details=chat,
        )

    def test_serialize(self):
        cluster = models.OpenAIChatCluster.objects.get(identifier="test")
