"""Pruebas de la integración con AWS (S3 y SNS) usando moto, que simula los
servicios en memoria: no necesitan cuenta de AWS ni internet.

Ejecutar desde la carpeta backend:   python -m pytest -v tests/test_aws.py
"""
import json

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

from app.config import settings
from app.main import app
from app.services import almacenamiento, notificaciones
from scripts import init_db

BUCKET = "ecoraee-evidencias-prueba"


@pytest.fixture(scope="module")
def aws():
    mp = pytest.MonkeyPatch()
    for clave, valor in {"AWS_ACCESS_KEY_ID": "testing", "AWS_SECRET_ACCESS_KEY": "testing",
                         "AWS_SESSION_TOKEN": "testing"}.items():
        mp.setenv(clave, valor)
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=BUCKET)
        sns = boto3.client("sns", region_name="us-east-1")
        topico = sns.create_topic(Name="ecoraee-eventos")["TopicArn"]
        # Una cola SQS suscrita al tópico permite leer lo que se publicó
        sqs = boto3.client("sqs", region_name="us-east-1")
        cola = sqs.create_queue(QueueName="captura")["QueueUrl"]
        arn_cola = sqs.get_queue_attributes(QueueUrl=cola, AttributeNames=["QueueArn"])["Attributes"]["QueueArn"]
        sns.subscribe(TopicArn=topico, Protocol="sqs", Endpoint=arn_cola)

        mp.setattr(settings, "s3_bucket", BUCKET)
        mp.setattr(settings, "sns_topic_arn", topico)
        almacenamiento._s3.cache_clear()
        notificaciones._sns.cache_clear()
        yield {"s3": s3, "sqs": sqs, "cola": cola}
        almacenamiento._s3.cache_clear()
        notificaciones._sns.cache_clear()
    mp.undo()


@pytest.fixture(scope="module")
def client(aws):
    init_db.main()
    with TestClient(app) as c:
        yield c


def _h(client, email):
    r = client.post("/api/auth/login", json={"email": email, "password": "Demo2026!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _mensajes(aws):
    r = aws["sqs"].receive_message(QueueUrl=aws["cola"], MaxNumberOfMessages=10)
    return [json.loads(m["Body"]) for m in r.get("Messages", [])]


def test_salud_informa_s3_y_sns(client):
    datos = client.get("/api/salud").json()
    assert datos["almacenamiento"] == f"s3://{BUCKET}" and datos["notificaciones_sns"] is True


def test_evidencia_en_s3(client, aws):
    h = _h(client, "operador@ecoraee.ec")
    r = client.post("/api/evidencias", data={"tipo_evidencia": "FOTO", "vinculo": "dispositivo", "id_vinculo": "9"},
                    files={"archivo": ("foto ups.png", b"\x89PNG\r\n\x1a\nups", "text/html")}, headers=h)
    assert r.status_code == 201, r.text
    ev = r.json()

    # El objeto está en el bucket, cifrado y con el tipo de contenido de la extensión (no el que dijo el navegador)
    obj = aws["s3"].head_object(Bucket=BUCKET, Key=ev["s3_key"])
    assert obj["ServerSideEncryption"] == "AES256" and obj["ContentType"] == "image/png"

    assert ev["vinculo"] == "Dispositivo RAEE-2026-00009"
    url = client.get("/api/evidencias", headers=h).json()[0]["url"]  # vista previa directa desde S3
    assert BUCKET in url and "X-Amz-Signature" in url and "X-Amz-Expires=300" in url
    assert client.get(f"/api/evidencias/{ev['id_evidencia']}/verificar", headers=h).json()["integra"] is True
    assert client.get(f"/api/evidencias/{ev['id_evidencia']}/archivo", headers=h).content.endswith(b"ups")

    # Si alguien altera el archivo en S3, la verificación lo detecta (RN-07)
    aws["s3"].put_object(Bucket=BUCKET, Key=ev["s3_key"], Body=b"alterado")
    assert client.get(f"/api/evidencias/{ev['id_evidencia']}/verificar", headers=h).json()["integra"] is False

    assert client.delete(f"/api/evidencias/{ev['id_evidencia']}", headers=h).status_code == 204
    assert aws["s3"].list_objects_v2(Bucket=BUCKET).get("KeyCount", 0) == 0


def test_sns_avisa_movimientos(client, aws):
    _mensajes(aws)  # vacía la cola
    h = _h(client, "coordinador@ecoraee.ec")
    # La transferencia 3 (datos sintéticos) está EN_TRANSITO: al recibirla se publica el evento
    r = client.post("/api/transferencias/3/recibir", json={}, headers=h)
    assert r.status_code == 200, r.text
    mensajes = _mensajes(aws)
    assert len(mensajes) == 1
    assert mensajes[0]["Subject"] == "EcoRAEE Cloud · Transferencia #3 recibida"
    assert "RAEE-2026-00005" in mensajes[0]["Message"]
    assert mensajes[0]["MessageAttributes"]["evento"]["Value"] == "TRANSFERENCIA_RECIBIDA"

    d = client.post("/api/destinos", json={"id_dispositivo": 5, "tipo_destino": "DISPOSICION_FINAL"}, headers=h)
    assert d.status_code == 201, d.text
    assert "RAEE-2026-00005 cerró su trazabilidad" in _mensajes(aws)[0]["Subject"]


def test_falla_de_sns_no_rompe_la_operacion(client, aws, monkeypatch):
    monkeypatch.setattr(settings, "sns_topic_arn", "arn:aws:sns:us-east-1:123456789012:no-existe")
    h = _h(client, "coordinador@ecoraee.ec")
    r = client.post("/api/transferencias/4/despachar", headers=h)  # PROGRAMADA en los datos sintéticos
    assert r.status_code == 200 and r.json()["estado"] == "EN_TRANSITO", r.text


def test_error_de_aws_llega_con_cors_y_mensaje_claro(client, aws, monkeypatch):
    # Bucket mal escrito en /ecoraee/S3_BUCKET_EVIDENCIAS: el navegador debe ver el motivo, no un "error de CORS"
    monkeypatch.setattr(settings, "s3_bucket", "bucket-que-no-existe")
    h = {**_h(client, "operador@ecoraee.ec"), "Origin": "http://localhost:5173"}
    r = client.post("/api/evidencias", data={"tipo_evidencia": "FOTO", "vinculo": "dispositivo", "id_vinculo": "9"},
                    files={"archivo": ("foto.png", b"\x89PNG", "image/png")}, headers=h)
    assert r.status_code == 502 and "NoSuchBucket" in r.json()["detail"]
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"
