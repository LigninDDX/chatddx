from django.db.models import TextChoices


class ProviderType(TextChoices):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"
    VLLM = "vllm"


class ToolType(TextChoices):
    FUNCTION = "function", "Function"
    CODE_INTERPRETER = "code_interpreter", "Code Interpreter"
    FILE_SEARCH = "file_search", "File Search"
    WEB_SEARCH = "web_search", "Web Search"


class ValidationStrategy(TextChoices):
    NOOP = "noop"
    RETRY = "retry"
    INFORM = "inform"
    CRASH = "crash"


class CoercionStrategy(TextChoices):
    PROMPTED = "prompted"
    TOOL = "tool"
    NATIVE = "native"


class Role(TextChoices):
    SYSTEM = "system", "System"
    USER = "user", "User"
    ASSISTANT = "assistant", "Assistant"
    TOOL = "tool", "Tool"
