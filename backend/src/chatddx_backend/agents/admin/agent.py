from functools import cached_property

from chatddx_backend.agents.models import (
    AgentModel,
    ConnectionModel,
    OutputTypeModel,
    SamplingParamsModel,
    ToolGroupModel,
)
from chatddx_backend.agents.schemas import (
    AgentSpec,
    ConnectionSpec,
    OutputTypeSpec,
    SamplingParamsSpec,
    ToolGroupSpec,
)


class Agent(AgentModel):
    Spec = AgentSpec

    class Meta:  # type: ignore
        proxy = True
        verbose_name = "Agent"
        verbose_name_plural = "Agents"

    def __str__(self):
        return self.name

    @cached_property
    def spec(self):
        return self.Spec.model_validate(self)


class Connection(ConnectionModel):
    Spec = ConnectionSpec

    class Meta:  # type: ignore
        proxy = True
        verbose_name = "Connection"
        verbose_name_plural = "Connections"

    def __str__(self):
        return self.name

    @cached_property
    def spec(self):
        return self.Spec.model_validate(self)


class OutputType(OutputTypeModel):
    Spec = OutputTypeSpec

    class Meta:  # type: ignore
        proxy = True
        verbose_name = "Output Type"
        verbose_name_plural = "Output Types"

    def __str__(self):
        return self.name

    @cached_property
    def spec(self):
        return self.Spec.model_validate(self)


class SamplingParams(SamplingParamsModel):
    Spec = SamplingParamsSpec

    class Meta:  # type: ignore
        proxy = True
        verbose_name = "Sampling Params"
        verbose_name_plural = "Sampling Params"

    def __str__(self):
        return self.name

    @cached_property
    def spec(self):
        return self.Spec.model_validate(self)


class ToolGroup(ToolGroupModel):
    Spec = ToolGroupSpec

    class Meta:  # type: ignore
        proxy = True
        verbose_name = "Tool Group"
        verbose_name_plural = "Tool Groups"

    def __str__(self):
        return self.name

    @cached_property
    def spec(self):
        return self.Spec.model_validate(self)
