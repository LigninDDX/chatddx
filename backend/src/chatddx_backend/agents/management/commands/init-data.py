from django.core.management.base import BaseCommand
from chatddx_backend.agents.tests import data


class Command(BaseCommand):
    help = "Writes datasets to database"

    def add_arguments(self, parser):
        parser.add_argument(
            "dataset", type=str, help="the name of the dataset to create"
        )

    def handle(self, *args, **options):
        dataset = options.get("dataset")
        getattr(data, str(dataset))()
