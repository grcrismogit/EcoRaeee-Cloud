"""Almacenamiento de evidencias: bucket de Amazon S3 o carpeta local.

Si existe la variable S3_BUCKET_EVIDENCIAS se usa S3; si no, la carpeta
STORAGE_DIR (desarrollo con Docker). Las credenciales de AWS nunca están en el
código: boto3 las toma del rol IAM de la instancia EC2.
"""
import base64
import hashlib
from functools import cache
from pathlib import Path
from typing import Optional

from fastapi import HTTPException

from ..config import settings


@cache
def _s3():
    import boto3
    from botocore.config import Config
    # s3v4 y la región del bucket: necesarios para que las URL prefirmadas sean válidas
    return boto3.client("s3", region_name=settings.aws_region,
                        config=Config(signature_version="s3v4", retries={"max_attempts": 3}))


def usa_s3() -> bool:
    return bool(settings.s3_bucket)


def descripcion() -> str:
    return f"s3://{settings.s3_bucket}" if usa_s3() else "carpeta local"


def _ruta(clave: str) -> Path:
    ruta = (settings.storage_dir / clave).resolve()
    if settings.storage_dir.resolve() not in ruta.parents:
        raise HTTPException(400, "Clave de almacenamiento no válida.")
    return ruta


def guardar(clave: str, contenido: bytes, tipo: Optional[str]) -> None:
    if usa_s3():
        # S3 comprueba el SHA-256 al recibir el archivo y lo guarda cifrado (SSE-S3)
        _s3().put_object(Bucket=settings.s3_bucket, Key=clave, Body=contenido,
                         ContentType=tipo or "application/octet-stream", ServerSideEncryption="AES256",
                         ChecksumSHA256=base64.b64encode(hashlib.sha256(contenido).digest()).decode())
        return
    ruta = _ruta(clave)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(contenido)


def leer(clave: str) -> Optional[bytes]:
    """Contenido del archivo, o None si ya no está en el almacenamiento."""
    if usa_s3():
        try:
            return _s3().get_object(Bucket=settings.s3_bucket, Key=clave)["Body"].read()
        except _s3().exceptions.NoSuchKey:
            return None
    ruta = _ruta(clave)
    return ruta.read_bytes() if ruta.exists() else None


def eliminar(clave: str) -> None:
    if usa_s3():
        _s3().delete_object(Bucket=settings.s3_bucket, Key=clave)
    else:
        _ruta(clave).unlink(missing_ok=True)


def url_temporal(clave: str, nombre: str) -> Optional[str]:
    """URL prefirmada de solo lectura (expira pronto). En modo local no hay URL."""
    if not usa_s3():
        return None
    params = {"Bucket": settings.s3_bucket, "Key": clave, "ResponseContentDisposition": f'inline; filename="{nombre}"'}
    if clave.endswith(".txt"):
        params["ResponseContentType"] = "text/plain; charset=utf-8"
    return _s3().generate_presigned_url("get_object", Params=params, ExpiresIn=settings.url_firmada_segundos)
