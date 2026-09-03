import os


class Settings:
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017/weaver")
    SECRET_KEY: str | None = os.getenv("SECRET_KEY")
    JWT_LIFETIME_SECONDS: int = int(os.getenv("JWT_LIFETIME_SECONDS", "3600"))
    REDIS_URL: str | None = os.getenv("REDIS_URL")
    # SMTP / email settings (optional)
    SMTP_HOST: str | None = os.getenv("SMTP_HOST")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str | None = os.getenv("SMTP_USER")
    SMTP_PASSWORD: str | None = os.getenv("SMTP_PASSWORD")
    SMTP_FROM: str | None = os.getenv("SMTP_FROM")
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")

    # Environment mode: 'development' or 'production'. When production, require SECRET_KEY to be set.
    ENV: str = os.getenv("ENV", "development")
    REQUIRE_SECRET_IN_PRODUCTION: bool = os.getenv("REQUIRE_SECRET_IN_PRODUCTION", "true").lower() in ("1", "true", "yes")
    # Security-related settings
    ALLOWED_HOSTS: list[str] = [h for h in os.getenv("ALLOWED_HOSTS", "").split(",") if h]
    CORS_ALLOWED_ORIGINS: list[str] = [h for h in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if h]
    FORCE_HTTPS: bool = os.getenv("FORCE_HTTPS", "false").lower() in ("1", "true", "yes")
    HSTS_MAX_AGE: int = int(os.getenv("HSTS_MAX_AGE", "63072000"))
    HSTS_INCLUDE_SUBDOMAINS: bool = os.getenv("HSTS_INCLUDE_SUBDOMAINS", "true").lower() in ("1", "true", "yes")

    def ensure_secret(self):
        import logging
        import os
        logger = logging.getLogger("weaver.config")
        if not self.SECRET_KEY:
            if self.ENV == "production" and self.REQUIRE_SECRET_IN_PRODUCTION:
                logger.error("SECRET_KEY is required in production. Set SECRET_KEY environment variable.")
                raise RuntimeError("SECRET_KEY is required in production")
            # generate a temporary secret for development. In production set SECRET_KEY env var.
            self.SECRET_KEY = os.urandom(32).hex()
            logger.warning("No SECRET_KEY found in environment — generated a temporary secret. Set SECRET_KEY for production.")

settings = Settings()
