"""Notificaciones de eventos RAEE con Amazon SNS (opcional).

Si no existe SNS_TOPIC_ARN no se envía nada. Un fallo de SNS solo se registra
en el log: la operación ya quedó guardada y no debe revertirse por un correo.
"""
import logging
from functools import cache

from ..config import settings

log = logging.getLogger("ecoraee.sns")


@cache
def _sns():
    import boto3
    from botocore.config import Config
    return boto3.client("sns", region_name=settings.aws_region,
                        config=Config(connect_timeout=2, read_timeout=3, retries={"max_attempts": 2}))


def notificar(evento: str, asunto: str, mensaje: str) -> None:
    if not settings.sns_topic_arn:
        return
    try:
        _sns().publish(
            TopicArn=settings.sns_topic_arn,
            Subject=f"EcoRAEE Cloud · {asunto}"[:100],  # SNS admite asuntos de hasta 100 caracteres
            Message=mensaje,
            # permite que cada suscriptor filtre por tipo de evento
            MessageAttributes={"evento": {"DataType": "String", "StringValue": evento}},
        )
        log.info("SNS: evento %s publicado", evento)
    except Exception:
        log.exception("SNS: no se pudo publicar el evento %s", evento)
