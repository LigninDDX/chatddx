import pytest


@pytest.fixture(scope="module")
def django_db_setup(django_test_environment, django_db_blocker):  # type: ignore
    with django_db_blocker.unblock():  # type: ignore
        yield
