import pytest
from django.contrib.contenttypes.models import ContentType


@pytest.fixture(scope="session")
def django_db_setup(django_test_environment, django_db_blocker):  # type: ignore
    with django_db_blocker.unblock():  # type: ignore
        from django.test.utils import setup_databases

        with django_db_blocker.unblock():  # type: ignore
            setup_databases(
                verbosity=0,
                interactive=False,
                keepdb=False,
            )
        yield


@pytest.fixture(autouse=True)
def clear_content_type_cache():
    ContentType.objects.clear_cache()
    yield
