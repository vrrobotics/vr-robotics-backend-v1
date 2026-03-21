from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Supabase
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str

    # Razorpay
    RAZORPAY_KEY_ID: str
    RAZORPAY_KEY_SECRET: str

    # JWT
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24

    # Email (Brevo SMTP)
    SMTP_HOST: str = "smtp-relay.brevo.com"
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASSWORD: str
    FROM_EMAIL: str = "info@vrroboticsacademy.com"
    VR_ADMIN_EMAIL: str = "md@vrroboticsacademy.com"

    # Frontend
    FRONTEND_URL: str = "https://www.vrroboticsacademy.com"

    class Config:
        env_file = ".env"


settings = Settings()