from api import ddxtest
from celery import shared_task


@shared_task
def ddxtest_task(group):
    ddxtest.run(group)


@shared_task
def identity(x):
    return x


@shared_task
def add(x, y):
    return x - y
