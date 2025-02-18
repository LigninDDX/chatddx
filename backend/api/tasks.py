import logging

from api import ddxtest
from api.models import DDXTestRun
from celery import chord, shared_task

logger = logging.getLogger(__name__)


@shared_task
def ddxtest_task(run_id):
    chat, cases = ddxtest.load_env(run_id)
    task_group = [ddxtest_case_task.s(run_id, chat, case) for case in cases]

    DDXTestRun.objects.filter(pk=run_id).update(status=DDXTestRun.Status.STARTED)

    chord_task = chord(task_group)(
        ddxtest_completed.s(run_id, chat["pk"]).on_error(
            ddxtest_failed.s(run_id, chat["pk"])
        )
    )

    return chord_task.id


@shared_task
def ddxtest_case_task(run_id, chat, case):
    if DDXTestRun.objects.get(pk=run_id).status == DDXTestRun.Status.CANCELLED:
        msg = f"Task belonging to {run_id} is cancelled."
        logger.warning(msg)
        return msg

    return ddxtest.run_case(run_id, chat, case)


@shared_task
def ddxtest_completed(results, run_id, chat_pk):
    msg = f"Test run {run_id} completed ({len(results)} cases)"
    logger.info(msg)
    ddxtest.invalidate_client_cache(chat_pk)
    DDXTestRun.objects.filter(pk=run_id).update(status=DDXTestRun.Status.COMPLETED)
    return msg


@shared_task
def ddxtest_failed(request, exc, traceback, run_id, chat_pk):
    msg = f"Test run {run_id} failed"
    logger.error(msg)
    logger.error(request)
    logger.error(exc)
    logger.error(traceback)
    ddxtest.invalidate_client_cache(chat_pk)
    DDXTestRun.objects.filter(pk=run_id).update(status=DDXTestRun.Status.FAILED)
    return msg
