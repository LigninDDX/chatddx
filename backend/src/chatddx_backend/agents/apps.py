# type: ignore
from pathlib import Path

from django.apps import AppConfig
from django.db import connection
from django.db.models.signals import post_migrate


class AgentsConfig(AppConfig):
    name = "chatddx_backend.agents"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        post_migrate.connect(setup_immutability_triggers, sender=self)


def setup_immutability_triggers(sender, **_):
    from .trail import TrailModel

    current_dir = Path(__file__).parent
    function_sql_path = current_dir / "sql/immutability_function.sql"
    trigger_sql_path = current_dir / "sql/immutability_trigger.sql"

    shared_function_sql = function_sql_path.read_text()
    trigger_sql_template = trigger_sql_path.read_text()

    with connection.cursor() as cursor:
        cursor.execute(shared_function_sql)

    for model in sender.get_models():
        if issubclass(model, TrailModel):
            table_name = model._meta.db_table

            trigger_sql = trigger_sql_template.format(table_name=table_name)
            with connection.cursor() as cursor:
                cursor.execute(trigger_sql)
                print(f"Applied immutability trigger to {table_name}")
