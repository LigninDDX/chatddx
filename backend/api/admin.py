from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from . import models


class PromptHistoryAdmin(admin.ModelAdmin):
    list_display = ["timestamp", "config", "user", "prompt", "response"]


class DDXTestAdmin(admin.ModelAdmin):
    save_as = True
    list_display = ["name", "truncated_input", "expect", "chat_list", "group_list"]


class DDXTestResultAdmin(admin.ModelAdmin):
    list_display = ["run", "test", "chat", "expect", "output", "expect_pos"]


class AIUserInline(admin.StackedInline):
    model = models.AIUser
    verbose_name_plural = "AI Users"


class UserAdmin(BaseUserAdmin):
    list_display = BaseUserAdmin.list_display + ("get_config_field",)

    def get_config_field(self, obj):
        return obj.aiuser.config if hasattr(obj, "aiuser") else None

    get_config_field.short_description = "config"

    inlines = [AIUserInline]


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(models.OpenAIChatCluster)
admin.site.register(models.OpenAIChat)
admin.site.register(models.OpenAIMessage)
admin.site.register(models.OpenAIMessageRole)
admin.site.register(models.OpenAIModel)
admin.site.register(models.OpenAILogitBias)
admin.site.register(models.DDXTest, DDXTestAdmin)
admin.site.register(models.DDXTestResult, DDXTestResultAdmin)
admin.site.register(models.DDXTestRun)
admin.site.register(models.DDXTestGroup)
admin.site.register(models.PromptHistory, PromptHistoryAdmin)
