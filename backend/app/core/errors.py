class AppError(Exception):
    def __init__(
        self, message: str, error_type: str = "app_error", status_code: int = 500
    ):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.status_code = status_code


class LLMProviderError(AppError):
    def __init__(self, message: str):
        super().__init__(message, error_type="llm_error", status_code=503)


class SessionNotFoundError(AppError):
    def __init__(self, session_id: str):
        super().__init__(
            f"Session not found: {session_id}", error_type="not_found", status_code=404
        )
