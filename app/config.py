from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./reconciliation.db"
    app_name: str = "OXXO Reconciliation Service"
    api_v1_prefix: str = "/api/v1"
    stuck_pending_threshold_hours: int = 72
    stuck_pending_high_threshold_hours: int = 120
    amount_mismatch_tolerance: float = 0.01
    amount_mismatch_medium_threshold: float = 0.05
    amount_mismatch_high_threshold: float = 0.10


settings = Settings()
