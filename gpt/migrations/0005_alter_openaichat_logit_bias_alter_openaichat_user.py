# Generated by Django 5.0.1 on 2024-01-25 13:11

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("gpt", "0004_alter_openaichat_options_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="openaichat",
            name="logit_bias",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                to="gpt.openailogitbias",
            ),
        ),
        migrations.AlterField(
            model_name="openaichat",
            name="user",
            field=models.CharField(blank=True, default=None, max_length=255, null=True),
        ),
    ]
