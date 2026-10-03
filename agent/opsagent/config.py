import os


class Settings:
    """Environment-driven settings, read at call time so tests can override."""

    @property
    def kubectl_bin(self) -> str:
        return os.getenv("KUBECTL_BIN", "kubectl")

    @property
    def log_tail_lines(self) -> int:
        return int(os.getenv("LOG_TAIL_LINES", "100"))

    @property
    def kubectl_timeout(self) -> float:
        return float(os.getenv("KUBECTL_TIMEOUT_SECONDS", "15"))

    @property
    def webhook_token(self) -> str:
        return os.getenv("WEBHOOK_TOKEN", "")

    @property
    def anthropic_api_key(self) -> str:
        return os.getenv("ANTHROPIC_API_KEY", "")

    @property
    def llm_model(self) -> str:
        return os.getenv("LLM_MODEL", "claude-sonnet-5-5")

    @property
    def slack_webhook_url(self) -> str:
        return os.getenv("SLACK_WEBHOOK_URL", "")


settings = Settings()
