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


    # --- remediation (opens rollback PRs; never merges anything) ---
    @property
    def remediation_enabled(self) -> bool:
        return os.getenv("REMEDIATION_ENABLED", "false").lower() == "true"

    @property
    def remediation_mode(self) -> str:
        """dry-run (default): only report what would be done. pr: actually open the PR."""
        return os.getenv("REMEDIATION_MODE", "dry-run").lower()

    @property
    def github_token(self) -> str:
        return os.getenv("GITHUB_TOKEN", "")

    @property
    def github_repo(self) -> str:
        return os.getenv("GITHUB_REPO", "PawasGavande/ops-agent-sre")

    @property
    def base_branch(self) -> str:
        return os.getenv("GITHUB_BASE_BRANCH", "main")

    @property
    def remediation_namespaces(self) -> list[str]:
        raw = os.getenv("REMEDIATION_NAMESPACES", "opsagent-demo")
        return [n.strip() for n in raw.split(",") if n.strip()]

    @property
    def manifest_path_template(self) -> str:
        return os.getenv("MANIFEST_PATH_TEMPLATE", "k8s/base/{app}.yaml")


settings = Settings()
