from django.db.models import TextChoices


class ProviderChoices(TextChoices):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"
    VLLM = "vllm"


class ToolChoices(TextChoices):
    FUNCTION = "function", "Function"
    CODE_INTERPRETER = "code_interpreter", "Code Interpreter"
    FILE_SEARCH = "file_search", "File Search"
    WEB_SEARCH = "web_search", "Web Search"


class ValidationChoices(TextChoices):
    NOOP = "noop"
    RETRY = "retry"
    INFORM = "inform"
    CRASH = "crash"


class CoercionChoices(TextChoices):
    PROMPTED = "prompted"
    TOOL = "tool"
    NATIVE = "native"


class RoleChoices(TextChoices):
    SYSTEM = "system", "System"
    USER = "user", "User"
    ASSISTANT = "assistant", "Assistant"
    TOOL = "tool", "Tool"
