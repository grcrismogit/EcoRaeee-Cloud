"""Configuración de la API (variables de entorno con valores por defecto para desarrollo local)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _cargar_env(ruta: Path) -> None:
    """Lee un archivo .env sencillo (CLAVE=valor) si existe, sin dependencias externas."""
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


_cargar_env(BASE_DIR / ".env")


class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://ecoraee:ecoraee_local@localhost:5432/ecoraee"
    )
    jwt_secret: str = os.getenv("JWT_SECRET", "clave-solo-para-desarrollo-local-cambiar")
    jwt_minutos: int = int(os.getenv("JWT_MINUTOS", "480"))
    cors_origins: list[str] = [
        o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    ]
    # Evidencias: bucket S3 si se indica S3_BUCKET_EVIDENCIAS; si no, carpeta local (Docker)
    storage_dir: Path = Path(os.getenv("STORAGE_DIR", str(BASE_DIR / "storage")))
    s3_bucket: str = os.getenv("S3_BUCKET_EVIDENCIAS", "")
    url_firmada_segundos: int = int(os.getenv("URL_FIRMADA_SEGUNDOS", "300"))
    max_archivo_mb: int = int(os.getenv("MAX_ARCHIVO_MB", "10"))
    # AWS (las credenciales las da el rol IAM de la instancia EC2, nunca van aquí)
    aws_region: str = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
    sns_topic_arn: str = os.getenv("SNS_TOPIC_ARN", "")


settings = Settings()
