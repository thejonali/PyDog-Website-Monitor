class AppError(RuntimeError):
    def __init__(self, message, code="application_error", details=None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


class ConfigurationError(AppError):
    def __init__(self, message, details=None):
        super().__init__(message, code="configuration_error", details=details)


class MonitorError(AppError):
    def __init__(self, message, details=None):
        super().__init__(message, code="monitor_error", details=details)
