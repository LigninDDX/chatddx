# src/chatddx_backend/agents/apps.py
# type: ignore
from pathlib import Path

from django.apps import AppConfig
from django.db import connection
from django.db.models.signals import post_migrate


class AgentsConfig(AppConfig):
    name = "chatddx_backend.agents"
    verbose_name = "Agent configuration"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        post_migrate.connect(install_trail_triggers, sender=self)


def install_trail_triggers(sender, **kwargs):
    from django.db import connections

    from .trail import TrailModel

    functions_tpl = (Path(__file__).parent / "sql/trail_functions.sql").read_text()
    triggers_tpl = (Path(__file__).parent / "sql/trail_triggers.sql").read_text()

    connection = connections[kwargs.get("using", "default")]

    for model in sender.get_models():
        if issubclass(model, TrailModel):
            context = get_model_context(model)

            functions_sql = functions_tpl.format(**context)
            triggers_sql = triggers_tpl.format(**context)

            with connection.cursor() as cursor:
                cursor.execute(functions_sql)
                cursor.execute(triggers_sql)
                print(f"Applied immutability trigger to {context['table_name']}")


def get_model_context(model):
    table_name = model._meta.db_table

    columns = [
        f.column
        for f in model._meta.fields
        if f.name not in ["id", "trail", "trail_id", "fingerprint"]
    ]
    cols_str = ", ".join(f'"{col}"' for col in columns)
    vals_str = ", ".join(f'NEW."{col}"' for col in columns)

    return {
        "table_name": table_name,
        "columns": cols_str,
        "parameters": vals_str,
    }
