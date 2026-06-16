"""Custom exceptions for the AI Assistant."""


class AIAssistantError(Exception):
    """Base exception for all AI Assistant errors."""

    pass


class ToolError(AIAssistantError):
    """Exception raised when a tool execution fails."""

    def __init__(self, tool_name: str, message: str, cause: Exception = None):
        self.tool_name = tool_name
        self.message = message
        self.cause = cause
        super().__init__(f"[{tool_name}] {message}")


class OfflineError(ToolError):
    """Exception raised when a tool is offline or unavailable."""

    pass


class LLMError(AIAssistantError):
    """Exception raised when LLM service fails."""

    def __init__(self, message: str, provider: str = None, cause: Exception = None):
        self.message = message
        self.provider = provider
        self.cause = cause
        provider_str = f" ({provider})" if provider else ""
        super().__init__(f"LLM error{provider_str}: {message}")


class LLMTimeoutError(LLMError):
    """Exception raised when LLM request times out."""

    pass


class ContextError(AIAssistantError):
    """Exception raised when context/memory management fails."""

    pass


class IntentAnalysisError(AIAssistantError):
    """Exception raised when intent analysis fails."""

    pass


class ValidationError(AIAssistantError):
    """Exception raised when validation fails."""

    pass


class ConfigurationError(AIAssistantError):
    """Exception raised when configuration is invalid."""

    pass
