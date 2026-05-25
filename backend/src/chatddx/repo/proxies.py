# src/chatddx/django/repo/admin/proxies.py
from functools import cached_property
from typing import final

import tomli_w

from chatddx.repo.base import BranchProxy
from chatddx.repo.branch_models import (
    AgentBranchModel,
    ConnectionBranchModel,
    OutputTypeBranchModel,
    SamplingParamsBranchModel,
    ToolBranchModel,
    ToolGroupBranchModel,
)


class SuperAgent(BranchProxy, AgentBranchModel):
    @final
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        proxy = True
        app_label = "orm"
        verbose_name = "Super Agent"
        verbose_name_plural = "Super Agents"


class Agent(BranchProxy, AgentBranchModel):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        proxy = True
        app_label = "orm"
        verbose_name = "Agent"
        verbose_name_plural = "Agents"


class Connection(BranchProxy, ConnectionBranchModel):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        proxy = True
        app_label = "orm"
        verbose_name = "Connection"
        verbose_name_plural = "Connections"

    @cached_property
    def profile_toml(self) -> str:
        return tomli_w.dumps(self.target.profile)


class OutputType(BranchProxy, OutputTypeBranchModel):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        proxy = True
        app_label = "orm"
        verbose_name = "Output type"
        verbose_name_plural = "Output types"


class SamplingParams(BranchProxy, SamplingParamsBranchModel):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        proxy = True
        app_label = "orm"
        verbose_name = "Sampling parameters"
        verbose_name_plural = "Sampling parameters"


class ToolGroup(BranchProxy, ToolGroupBranchModel):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        proxy = True
        app_label = "orm"
        verbose_name = "Tool group"
        verbose_name_plural = "Tool groups"


class Tool(BranchProxy, ToolBranchModel):
    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        proxy = True
        app_label = "orm"
        verbose_name = "Tool"
        verbose_name_plural = "Tools"
