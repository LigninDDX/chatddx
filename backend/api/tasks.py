from api import ddxtest
from celery import group, shared_task


@shared_task
def ddxtest_task(group_name, chat_identifier):
    run_id, chat, cases = ddxtest.load_env(group_name, chat_identifier)

    task_group = group([ddxtest_case_task.s(run_id, chat, case) for case in cases])

    group_result = task_group.apply_async()

    return group_result


@shared_task
def ddxtest_case_task(run_id, chat, case):
    return ddxtest.run_case(run_id, chat, case)
