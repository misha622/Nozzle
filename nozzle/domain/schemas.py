from datetime import datetime
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, IPvAnyAddress
from nozzle.domain.enums import (
    AlertStatus, ClusterStatus, Decision, FeedbackSource,
    SourceType, SeverityLevel, UserTier
)


# ============================================================
# Raw — что приходит от источника
# ============================================================

class RawAlert(BaseModel):
    """Сырой алерт от источника до нормализации."""
    external_id: str = Field(..., description="ID алерта во внешней системе")
    source_type: SourceType
    source_id: UUID = Field(..., description="ID источника в нашей системе")
    raw_payload: dict = Field(..., description="Полный JSON от источника")
    received_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================
# Normalized — единый формат внутри системы
# ============================================================

class NormalizedAlert(BaseModel):
    """Нормализованный алерт — основной объект ядра."""
    id: UUID = Field(default_factory=uuid4)
    external_id: str
    source_type: SourceType
    source_id: UUID

    rule_id: str
    rule_name: str | None = None
    severity: int = 0

    agent_name: str | None = None
    agent_id: str | None = None
    source_ip: IPvAnyAddress | None = None
    source_hostname: str | None = None
    destination_ip: IPvAnyAddress | None = None

    description: str = ""
    full_log: str | None = None
    raw_json: dict = Field(default_factory=dict)

    status: AlertStatus = AlertStatus.NEW
    cluster_id: UUID | None = None

    received_at: datetime = Field(default_factory=datetime.utcnow)
    normalized_at: datetime = Field(default_factory=datetime.utcnow)

    extra_data: dict = Field(default_factory=dict)

    class Config:
        use_enum_values = True


# ============================================================
# Clustering output
# ============================================================

class ClusterCandidate(BaseModel):
    """Результат работы стратегии кластеризации."""
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str
    strategy: str                          # Имя стратегии, создавшей кластер
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    alert_ids: list[UUID]
    alert_count: int = 0
    representative_alert_id: UUID | None = None  # Самый характерный алерт
    extra_data: dict = Field(default_factory=dict)

    def model_post_init(self, __context):
        if self.alert_count == 0:
            self.alert_count = len(self.alert_ids)


# ============================================================
# API Request / Response
# ============================================================

class AlertResponse(BaseModel):
    """API-ответ: один алерт."""
    id: UUID
    external_id: str
    source_type: SourceType
    rule_id: str
    rule_name: str | None
    severity: int
    agent_name: str | None
    source_ip: str | None
    description: str
    status: AlertStatus
    cluster_id: UUID | None
    received_at: datetime

    class Config:
        from_attributes = True


class AlertListResponse(BaseModel):
    """API-ответ: список алертов."""
    total: int
    page: int
    page_size: int
    items: list[AlertResponse]


class ClusterResponse(BaseModel):
    """API-ответ: один кластер."""
    id: UUID
    name: str
    description: str
    strategy: str
    confidence: float
    alert_count: int
    status: ClusterStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClusterDetailResponse(ClusterResponse):
    """API-ответ: кластер с вложенными алертами."""
    alerts: list[AlertResponse]


class FeedbackRequest(BaseModel):
    """API-запрос: отправить обратную связь."""
    alert_id: UUID | None = None
    cluster_id: UUID | None = None
    decision: Decision
    comment: str | None = None


class FeedbackResponse(BaseModel):
    """API-ответ: запись обратной связи."""
    id: UUID
    alert_id: UUID | None
    cluster_id: UUID | None
    decision: Decision
    source: FeedbackSource
    created_at: datetime

    class Config:
        from_attributes = True


class StatsDashboard(BaseModel):
    """API-ответ: данные для дашборда."""
    total_alerts_24h: int
    total_clusters_24h: int
    alerts_saved_pct: float        # Процент схлопнутых алертов
    top_noisy_rules: list[dict]     # [{rule_id, rule_name, count}]
    false_positive_rate: float
    avg_cluster_confidence: float
    incidents_missed: int = 0      # Реальных инцидентов пропущено


class SourceConfig(BaseModel):
    """Конфигурация источника."""
    name: str
    type: SourceType
    config: dict = Field(default_factory=dict)


class SourceResponse(BaseModel):
    """API-ответ: источник."""
    id: UUID
    name: str
    type: SourceType
    status: str
    last_polled_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    """API-ответ: пользователь."""
    id: UUID
    email: str
    tier: UserTier
    alert_limit_daily: int
    created_at: datetime

    class Config:
        from_attributes = True