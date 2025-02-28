from chatddx_backend.api import ddxtest, models
from chatddx_backend.api.tasks import ddxtest_task
from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.safestring import mark_safe
from unfold.admin import ModelAdmin, StackedInline, TabularInline

# from django.contrib.admin import ModelAdmin, StackedInline, TabularInline
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

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


class DiagnosisForm(forms.ModelForm):
    def clean_pattern(self):
        value = self.cleaned_data["pattern"]
        try:
            eval(ddxtest.render_pattern(""), {"s": ""})
        except Exception as e:
            raise ValidationError(f"Invalid pattern: {e}")

        return value

    class Meta:
        model = models.Diagnosis
        fields = "__all__"


@admin.register(models.Diagnosis)
class DiagnosisAdmin(admin.ModelAdmin):
    # form = DiagnosisForm
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
        return mark_safe(obj.ranks().replace("\n", "<br>"))

    ranks_formated.short_description = "Ranks"

    def response_formated(self, obj):
        return mark_safe(obj.response.replace("\n", "<br>"))

    response_formated.short_description = "Response"

    def patterns_formated(self, obj):
        return mark_safe(obj.patterns().replace("\n", "<br>"))

    patterns_formated.short_description = "Patterns"


@admin.register(models.DDXTestRun)
class DDXTestRunAdmin(ModelAdmin):
    list_display = ["__str__", "timestamp", "status", "chat", "group"]
    exclude = ("status", "snapshot")

    def has_change_permission(self, request, obj=None):
        if obj:
            return False
        return super().has_change_permission(request, obj)

    def save_model(self, request, obj, form, change):
        cases = obj.group.ddxtestcase_set.all()
        obj.snapshot = {
            "chat": obj.chat.serialize(),
            "group": [case.serialize() for case in cases],
        }
        super().save_model(request, obj, form, change)
        transaction.on_commit(lambda: ddxtest_task.delay(obj.pk))


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
        return mark_safe("<br>".join([str(m) for m in obj.messages.all()]))

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
