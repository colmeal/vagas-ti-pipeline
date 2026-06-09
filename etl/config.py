"""
config.py — Configurações centralizadas via variáveis de ambiente.
Padrão idêntico ao config.py das aulas (etl_docker_python).
"""
import os


class Settings:
    # Banco de dados
    db_host: str     = os.getenv("DB_HOST", "localhost")
    db_port: int     = int(os.getenv("DB_PORT", "5432"))
    db_name: str     = os.getenv("DB_NAME", "vagas_db")
    db_user: str     = os.getenv("DB_USER", "vagas_user")
    db_password: str = os.getenv("DB_PASSWORD", "vagas_pass")

    # Remotive API
    remotive_url: str    = os.getenv("REMOTIVE_URL", "https://remotive.com/api/remote-jobs")
    remotive_category: str = os.getenv("REMOTIVE_CATEGORY", "software-dev")
    remotive_limit: int  = int(os.getenv("REMOTIVE_LIMIT", "100"))

    # Caminhos de dados
    csv_path: str        = os.getenv("CSV_PATH", "/opt/airflow/data/job_postings.csv")
    json_path: str       = os.getenv("JSON_PATH", "/opt/airflow/data/stacks_map.json")

    @property
    def db_url(self) -> str:
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
