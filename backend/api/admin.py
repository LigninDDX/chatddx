from api.tasks import ddxtest_task
from django.contrib import admin, messages
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from django.utils.html import format_html
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from . import models

admin.site.unregister(User)
admin.site.unregister(Group)


class AIUserInline(StackedInline):
    model = models.AIUser
    verbose_name_plural = "AI Users"


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    list_display = BaseUserAdmin.list_display + ("get_config_field",)

    def get_config_field(self, obj):
        return obj.aiuser.config if hasattr(obj, "aiuser") else None

    get_config_field.short_description = "config"

    inlines = [AIUserInline]


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


@admin.register(models.PromptHistory)
class PromptHistoryAdmin(ModelAdmin):
    list_display = ["__str__", "config", "user", "prompt", "response"]


@admin.register(models.Diagnosis)
class DiagnosisAdmin(ModelAdmin):
    list_display = [
        "__str__",
        "pattern",
    ]


@admin.register(models.DDXTestCase)
class DDXTestCaseAdmin(ModelAdmin):
    save_as = True
    list_display = ["__str__", "truncated_input", "diagnosis_list", "group_list"]


@admin.register(models.DDXCaseResult)
class DDXCaseResultAdmin(ModelAdmin):
    list_display = [
        "__str__",
        "run",
        "timestamp",
        "chat",
        "response_formated",
        "patterns_formated",
        "ranks_formated",
    ]

    def ranks_formated(self, obj):
        return format_html(obj.ranks().replace("\n", "<br>"))

    ranks_formated.short_description = "Ranks"

    def response_formated(self, obj):
        return format_html(obj.response.replace("\n", "<br>"))

    response_formated.short_description = "Response"

    def patterns_formated(self, obj):
        return format_html(obj.patterns().replace("\n", "<br>"))

    patterns_formated.short_description = "Patterns"


@admin.register(models.DDXTestRun)
class DDXTestRunAdmin(ModelAdmin):
    list_display = ["__str__", "timestamp", "status", "chat", "group"]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change and any(
            key in request.POST for key in ["_save", "_continue", "_addanother"]
        ):
            self.run_ddxtest(obj.pk)

    def run_ddxtest(self, run_id):
        print(f"Running custom function for {run_id}")
        ddxtest_task.delay(run_id)


@admin.register(models.OpenAIMessage)
class OpenAIMessageAdmin(ModelAdmin):
    pass


@admin.register(models.DDXTestGroup)
class DDXTestGroup(ModelAdmin):
    pass


class OpenAIChatMessagesInline(TabularInline):
    model = models.OpenAIChat_messages
    fields = ["openaimessage", "order"]
    extra = 1


@admin.register(models.OpenAIChat)
class OpenAIChatAdmin(ModelAdmin):
    list_display = ["__str__", "model", "messages_formated"]
    inlines = [OpenAIChatMessagesInline]

    def messages_formated(self, obj):
        return format_html("<br>".join([str(m) for m in obj.messages.all()]))

    messages_formated.short_description = "Prompts"


@admin.register(models.OpenAIChatCluster)
class OpenAIChatClusterAdmin(ModelAdmin):
    pass


@admin.register(models.OpenAIMessageRole)
class OpenAIMessageRoleAdmin(ModelAdmin):
    pass


@admin.register(models.OpenAIModel)
class OpenAIModelAdmin(ModelAdmin):
    pass


@admin.register(models.OpenAILogitBias)
class OpenAILogitBiad(ModelAdmin):
    pass
