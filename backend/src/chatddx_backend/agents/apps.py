from django.apps import AppConfig
from django.db import connection
from django.db.models.signals import post_migrate


class AgentsConfig(AppConfig):
    name = "chatddx_backend.agents"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        post_migrate.connect(setup_immutability_triggers, sender=self)


def setup_immutability_triggers(sender, **kwargs):
    from .trail import TrailModel

    shared_function_sql = """
        CREATE OR REPLACE FUNCTION enforce_partial_immutability()
        RETURNS TRIGGER AS $$
        DECLARE
            old_data jsonb;
            new_data jsonb;
        BEGIN
            IF OLD.fingerprint IS NOT NULL AND OLD.fingerprint != '' THEN
                old_data := to_jsonb(OLD) - 'updated_at';
                new_data := to_jsonb(NEW) - 'updated_at';
            IF old_data != new_data THEN
                RAISE EXCEPTION 'Immutable Record Error: Only "updated_at" may be modified on fingerprinted records. Detected changes in: %',
                (SELECT jsonb_object_agg(key, value)
                 FROM jsonb_each(new_data)
                 WHERE old_data->key IS DISTINCT FROM value);
        END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """

    with connection.cursor() as cursor:
        cursor.execute(shared_function_sql)

    for model in sender.get_models():
        if issubclass(model, TrailModel):
            table_name = model._meta.db_table

            trigger_sql = f"""
                DROP TRIGGER IF EXISTS prevent_immutable_updates ON {table_name};
                CREATE TRIGGER prevent_immutable_updates
                BEFORE UPDATE ON {table_name}
                FOR EACH ROW
                EXECUTE FUNCTION enforce_partial_immutability();
            """

            with connection.cursor() as cursor:
                cursor.execute(trigger_sql)
                print(f"Applied immutability trigger to {table_name}")
