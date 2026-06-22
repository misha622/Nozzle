class NozzleError(Exception):
    """Базовое исключение Nozzle."""
    def __init__(self, message: str = "An error occurred", detail: dict | None = None):
        self.message = message
        self.detail = detail or {}
        super().__init__(self.message)


class SourceConnectionError(NozzleError):
    """Не удалось подключиться к источнику."""
    def __init__(self, source_name: str, reason: str = ""):
        super().__init__(
            message=f"Failed to connect to source '{source_name}': {reason}",
            detail={"source_name": source_name, "reason": reason},
        )


class SourceAuthError(NozzleError):
    """Ошибка аутентификации в источнике."""
    def __init__(self, source_name: str):
        super().__init__(
            message=f"Authentication failed for source '{source_name}'",
            detail={"source_name": source_name},
        )


class AlertNotFoundError(NozzleError):
    """Алерт не найден."""
    def __init__(self, alert_id: str):
        super().__init__(
            message=f"Alert not found: {alert_id}",
            detail={"alert_id": alert_id},
        )


class ClusterNotFoundError(NozzleError):
    """Кластер не найден."""
    def __init__(self, cluster_id: str):
        super().__init__(
            message=f"Cluster not found: {cluster_id}",
            detail={"cluster_id": cluster_id},
        )


class ConfigurationError(NozzleError):
    """Ошибка конфигурации."""
    pass


class InsufficientDataError(NozzleError):
    """Недостаточно данных для выполнения операции."""
    def __init__(self, operation: str, required: int, available: int):
        super().__init__(
            message=f"Insufficient data for {operation}: need {required}, have {available}",
            detail={"operation": operation, "required": required, "available": available},
        )