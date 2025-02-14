from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.core.management import call_command
from django.shortcuts import redirect
from django.urls import path

from . import models


class PromptHistoryAdmin(admin.ModelAdmin):
    list_display = ["timestamp", "config", "user", "prompt", "response"]


class DDXTestAdmin(admin.ModelAdmin):
    save_as = True
    list_display = ["name", "truncated_input", "expect", "chat_list", "group_list"]
    change_list_template = "admin/api/DDXTest/change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("run-ddxtests/", self.run_command, name="run_ddxtests"),
        ]
        return custom_urls + urls

    def run_command(self, request):
        arg = request.GET.get("arg", None)
        if arg:
            call_command("ddxtest", arg)
            self.message_user(
                request, f"Command executed with argument: {arg}", messages.SUCCESS
            )
        else:
            self.message_user(request, "No argument selected!", messages.ERROR)

        self.message_user(request, "Command executed successfully", messages.SUCCESS)
        return redirect(request.META.get("HTTP_REFERER", "admin:index"))

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["test_groups"] = models.DDXTestGroup.objects.all()
        return super().changelist_view(request, extra_context=extra_context)


class DDXTestResultAdmin(admin.ModelAdmin):
    list_display = [
        "run",
        "timestamp",
        "test",
        "chat",
        "expect",
        "output",
        "expect_pos",
    ]


class DDXTestRunAdmin(admin.ModelAdmin):
    list_display = ["timestamp", "group"]


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
admin.site.register(models.DDXTestRun, DDXTestRunAdmin)
admin.site.register(models.DDXTestGroup)
admin.site.register(models.PromptHistory, PromptHistoryAdmin)
