# src/chatddx/repo/shufflers/main.py
from collections import defaultdict
from pathlib import Path
from typing import Any, get_args

from django.db.models import (
    F,
    ForeignKey,
    OneToOneField,
    OuterRef,
    QuerySet,
    Subquery,
)

from chatddx.core.django_fields import RelatedArrayField
from chatddx.core.models import IdentityModel
from chatddx.registry.main import parse_registry
from chatddx.repo.base import (
    BaseFormDataOut,
    BranchModel,
    BranchSpec,
    TrailModel,
    TrailSchema,
    TrailSpec,
)
from chatddx.repo.form_data_out import TemplateData
from chatddx.repo.main import BundleName, Repo
from chatddx.repo.trail_schemas import TrailRegistry
from chatddx.utils import ListOf, OneOf, make_async, one_or_list_of

agent_relations: list[BundleName] = [
    "connection",
    "sampling_params",
    "output_type",
    "tool_group",
]


def ensure_identity(name: str) -> IdentityModel:
    owner, _ = IdentityModel.objects.get_or_create(name=name)
    return owner


ensure_identity_async = make_async(ensure_identity)


def qs_super_agent[T: TrailModel](qs: QuerySet[T], owner_name: str):
    def subquery(owner_name: str, model: str, column: str):
        branch_model_cls = Repo(model, BranchModel)

        return branch_model_cls.objects.filter(
            target=OuterRef(f"target__{model}"),
            owner__name=owner_name,
        ).values(column)[:1]

    branch_annotations = {
        f"{model}_{field}": Subquery(subquery(owner_name, model, field))
        for field in ("name", "id")
        for model in agent_relations
    }
    return qs.select_related(
        *[f"target__{model}" for model in agent_relations]
    ).annotate(**branch_annotations)


def qs_owned_trails[T: TrailModel](qs: QuerySet[T], owner_name: str) -> QuerySet[T]:
    return qs.filter(branches__owner__name=owner_name).annotate(
        branch_name=F("branches__name")
    )


def qs_canon[T: BranchModel](qs: QuerySet[T], owner_name: str) -> QuerySet[T]:
    return qs_owned(qs, owner_name).distinct("owner_id", "name")


def qs_owned[T: BranchModel](qs: QuerySet[T], owner_name: str) -> QuerySet[T]:
    return qs.filter(owner__name=owner_name).order_by("owner_id", "name", "-timestamp")


def dump_trail_registry(registry_path: Path, owner_name: str):
    registry = parse_registry(
        path=registry_path,
        schema=TrailRegistry,
    )

    dumped_registry: dict[str, dict[int, BranchModel]] = {}

    for bundle_name, record in registry:
        dumped_registry[bundle_name] = {}

        for branch_name, schema in record.items():
            branch_model, _ = dump_branch(
                bundle_name=bundle_name,
                branch_name=branch_name,
                owner_name=owner_name,
                trail_schema=schema,
            )

            dumped_registry[bundle_name][branch_model.pk] = branch_model

    return dumped_registry


def load_template_data(owner_name: str):
    payload: dict[BundleName, dict[str, BaseFormDataOut]] = defaultdict(dict)
    for bundle in get_args(BundleName):
        payload[bundle] = {
            str(branch.id): branch
            for branch in load_branches(
                bundle,
                owner_name,
                Repo(bundle, BaseFormDataOut),
            )
        }

    return TemplateData.model_validate(payload)


dump_trail_registry_async = make_async(dump_trail_registry)


def load_branches[T: BaseFormDataOut | BranchSpec](  # pyright: ignore[reportMissingTypeArgument]
    bundle_name: str,
    owner_name: str,
    as_schema: type[T],
) -> list[T]:
    branch_model_cls = Repo(bundle_name, BranchModel)

    qs = qs_canon(
        branch_model_cls.objects.all(),
        owner_name,
    )

    return [
        as_schema.model_validate(
            resolve_related_array_fields(branch.target),
            context={"name": branch.name},
        )
        for branch in qs
    ]


def load_branch[T: BaseFormDataOut | BranchSpec](  # pyright: ignore[reportMissingTypeArgument]
    bundle_name: str,
    branch_name: str,
    owner_name: str,
    as_schema: type[T],
) -> T:
    branch_model_cls = Repo(bundle_name, BranchModel)
    qs = qs_canon(
        branch_model_cls.objects.filter(name=branch_name),
        owner_name,
    )

    if (branch := qs.first()) is None:
        raise ValueError(f"Branch '{bundle_name}.{branch_name}' not found.")

    branch.target = resolve_related_array_fields(branch.target)

    return as_schema.model_validate(branch)  # pyright: ignore[reportUnknownVariableType]


load_branch_async = make_async(load_branch)


def dump_branch(
    bundle_name: str,
    branch_name: str,
    owner_name: str,
    trail_schema: TrailSchema,
) -> tuple[BranchModel, bool]:
    branch_model_cls = Repo(bundle_name, BranchModel)
    trail_model_cls = Repo(bundle_name, TrailModel)

    owner = ensure_identity(owner_name)

    canon = qs_canon(
        branch_model_cls.objects.filter(name=branch_name),
        owner.name,
    ).first()

    if canon and trail_schema.fingerprint == canon.target.fingerprint:
        return canon, False

    trail_model = dump_trail(trail_model_cls, trail_schema)

    branch_instance = branch_model_cls(
        target_id=trail_model.pk,
        owner=owner,
        name=branch_name,
    )

    branch_instance.save()

    return branch_instance, True


dump_branch_async = make_async(dump_branch)


def load_trail[T: TrailSpec](
    bundle_name: str,
    fingerprint: str,
    as_schema: type[T],
):
    trail_model_cls = Repo(bundle_name, TrailModel)
    trail_model = trail_model_cls.objects.get(fingerprint=fingerprint)

    trail_model = resolve_related_array_fields(trail_model)

    return as_schema.model_validate(trail_model)


load_trail_async = make_async(load_trail)


def load_form_data(
    trail_schema: TrailSchema,
    name: str,
) -> BaseFormDataOut:

    form_data_cls = Repo(trail_schema, BaseFormDataOut)

    return form_data_cls.model_validate(
        trail_schema,
        context={"name": name},
    )


def dump_trail[T: TrailModel](
    model_cls: type[T],
    schema: TrailSchema,
) -> T:
    new_values: dict[str, Any] = {}

    for field_name, field_value in schema:
        field = model_cls._meta.get_field(field_name)
        associated_model = (
            getattr(field, "associated_model", None) or field.related_model
        )

        match one_or_list_of(TrailSchema, field_value):
            case OneOf(value) if associated_model:
                new_values[field_name + "_id"] = dump_trail(
                    associated_model,
                    value,
                ).pk

            case ListOf(values) if associated_model:
                new_values[field_name] = [
                    dump_trail(
                        associated_model,
                        value,
                    ).pk
                    for value in values
                ]

            case _:
                new_values[field_name] = field_value

    model, _ = model_cls.objects.get_or_create(
        fingerprint=schema.fingerprint,
        defaults=new_values,
    )

    return model


dump_trail_async = make_async(dump_trail)


def resolve_related_array_fields(model: TrailModel):
    for field in model._meta.concrete_fields:
        if isinstance(field, RelatedArrayField):
            value = getattr(model, field.name)

            if not value:
                setattr(model, field.name, [])
                continue

            queryset = field.associated_model.objects.filter(pk__in=value)
            resolved_value = list(queryset)

            for obj in resolved_value:
                _ = resolve_related_array_fields(obj)

            setattr(model, field.name, resolved_value)

        elif isinstance(field, (ForeignKey, OneToOneField)):
            associated_model = getattr(model, field.name, None)
            if associated_model is not None:
                _ = resolve_related_array_fields(associated_model)

    return model


resolve_related_array_fields_async = make_async(resolve_related_array_fields)
