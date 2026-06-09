from django.db.models import OuterRef, QuerySet, Subquery

from chatddx.history.proxies import Message
from chatddx.repo.proxies import Agent


def qs_messages(qs: QuerySet[Message], owner_name: str):
    agent_branch = Agent.objects.filter(
        target=OuterRef("agent"),
        owner__name=owner_name,
    ).order_by("-timestamp")

    qs = qs.annotate(
        agent_branch_id=Subquery(agent_branch.values("id")[:1]),
        agent_branch_name=Subquery(agent_branch.values("name")[:1]),
    )

    return qs.order_by("timestamp")
