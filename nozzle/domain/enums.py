from enum import StrEnum, IntEnum


class SourceType(StrEnum):
    """Тип источника алертов."""
    WAZUH = "wazuh"
    ELASTIC = "elastic"
    GRAYLOG = "graylog"
    SPLUNK = "splunk"
    WEBHOOK = "webhook"


class SourceStatus(StrEnum):
    """Статус подключения к источнику."""
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"


class AlertStatus(StrEnum):
    """Статус алерта в нашей системе."""
    NEW = "new"                   # Только получен, ещё не обработан
    CLUSTERED = "clustered"       # Помещён в кластер
    DISMISSED = "dismissed"       # Аналитик подтвердил: это шум
    ESCALATED = "escalated"       # Аналитик подтвердил: это инцидент


class ClusterStatus(StrEnum):
    """Статус кластера."""
    OPEN = "open"                 # Активный, ждёт внимания
    REVIEWED = "reviewed"         # Просмотрен аналитиком
    DISMISSED = "dismissed"       # Подтверждён как шум
    ESCALATED = "escalated"       # Подтверждён как инцидент


class Decision(StrEnum):
    """Решение аналитика по алерту или кластеру."""
    CONFIRMED_NOISE = "confirmed_noise"
    CONFIRMED_INCIDENT = "confirmed_incident"
    UNGROUPED = "ungrouped"       # Аналитик разгруппировал кластер


class FeedbackSource(StrEnum):
    """Источник обратной связи."""
    EXPLICIT = "explicit"         # Аналитик явно нажал кнопку
    IMPLICIT = "implicit"         # Извлечено из действий (закрыл, эскалировал)


class UserTier(StrEnum):
    """Уровень подписки."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class SeverityLevel(IntEnum):
    """Уровни критичности (совместимы с Wazuh/Elastic)."""
    INFO = 0
    LOW = 3
    MEDIUM = 5
    HIGH = 8
    CRITICAL = 12
    EMERGENCY = 15