"""Evidencias (fotos, actas, informes, certificados).

Los archivos se guardan en el bucket privado de Amazon S3 (o en una carpeta
local cuando se trabaja con Docker); en la base solo se registra la clave y el
hash SHA-256 (RN-07). Para verlos se entregan URL prefirmadas que expiran.
"""
import hashlib
import logging
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..crud import obtener_o_404
from ..database import get_db
from ..models import DestinoFinal, Dispositivo, EvaluacionTecnica, Evidencia, Transferencia, Usuario
from ..schemas import EvidenciaOut, TipoEvidencia
from ..security import requiere_rol, usuario_actual
from ..services import almacenamiento

log = logging.getLogger("ecoraee")
router = APIRouter(prefix="/evidencias", tags=["Evidencias"])
cargador = requiere_rol("GENERADOR", "OPERADOR_CENTRO", "TECNICO_EVALUADOR", "COORDINADOR_LOGISTICO")

# El tipo de contenido sale de la extensión permitida, no de lo que declara el navegador
EXTENSIONES = {".pdf": "application/pdf", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
               ".png": "image/png", ".txt": "text/plain; charset=utf-8"}
VINCULOS = {
    "dispositivo": ("id_dispositivo", Dispositivo, "Dispositivo"),
    "evaluacion": ("id_evaluacion", EvaluacionTecnica, "Evaluación"),
    "transferencia": ("id_transferencia", Transferencia, "Transferencia"),
    "destino_final": ("id_destino_final", DestinoFinal, "Destino final"),
}


@router.get("", response_model=list[EvidenciaOut], summary="Listar evidencias")
def listar(id_dispositivo: Optional[int] = None, tipo_evidencia: Optional[str] = None,
           db: Session = Depends(get_db), _: Usuario = Depends(usuario_actual)):
    consulta = select(Evidencia).order_by(Evidencia.fecha_carga.desc())
    if id_dispositivo:
        consulta = consulta.where(Evidencia.id_dispositivo == id_dispositivo)
    if tipo_evidencia:
        consulta = consulta.where(Evidencia.tipo_evidencia == tipo_evidencia)
    return db.scalars(consulta).all()


@router.post("", response_model=EvidenciaOut, status_code=201, summary="Subir evidencia (multipart/form-data)")
def subir(  # def (no async): FastAPI la ejecuta en un hilo y la subida a S3 no bloquea la API
    tipo_evidencia: TipoEvidencia = Form(...),
    vinculo: Literal["dispositivo", "evaluacion", "transferencia", "destino_final"] = Form(...),
    id_vinculo: int = Form(..., gt=0),
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(cargador),
):
    campo, modelo, nombre = VINCULOS[vinculo]
    obtener_o_404(db, modelo, id_vinculo, nombre)

    extension = Path(archivo.filename or "").suffix.lower()
    if extension not in EXTENSIONES:
        raise HTTPException(422, f"Tipo de archivo no permitido. Use: {', '.join(sorted(EXTENSIONES))}.")
    limite = settings.max_archivo_mb * 1024 * 1024
    contenido = archivo.file.read(limite + 1)  # nunca se lee a memoria más que el máximo permitido
    if not contenido:
        raise HTTPException(422, "El archivo está vacío.")
    if len(contenido) > limite:
        raise HTTPException(413, f"El archivo supera el máximo de {settings.max_archivo_mb} MB.")

    base = re.sub(r"[^A-Za-z0-9_\-]+", "-", Path(archivo.filename).stem).strip("-")[:60] or "evidencia"
    ahora = datetime.now()
    s3_key = f"evidencias/{ahora:%Y/%m}/{uuid.uuid4().hex[:8]}-{base}{extension}"
    almacenamiento.guardar(s3_key, contenido, EXTENSIONES[extension])

    evidencia = Evidencia(tipo_evidencia=tipo_evidencia, s3_key=s3_key,
                          hash_sha256=hashlib.sha256(contenido).hexdigest(),
                          id_usuario_carga=usuario.id_usuario, **{campo: id_vinculo})
    db.add(evidencia)
    try:
        db.commit()
    except Exception:
        almacenamiento.eliminar(s3_key)  # no dejar archivos huérfanos si la base rechaza el registro
        raise
    db.refresh(evidencia)
    return evidencia


@router.get("/{id_}/archivo", summary="Descargar el archivo de la evidencia")
def descargar(id_: int, db: Session = Depends(get_db), _: Usuario = Depends(usuario_actual)):
    evidencia = obtener_o_404(db, Evidencia, id_, "Evidencia")
    contenido = almacenamiento.leer(evidencia.s3_key)
    if contenido is None:
        raise HTTPException(404, f"El archivo no se encuentra en {almacenamiento.descripcion()}.")
    return Response(contenido, media_type="application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{evidencia.nombre_archivo}"'})


@router.get("/{id_}/verificar", summary="Verificar integridad (compara el hash SHA-256)")
def verificar(id_: int, db: Session = Depends(get_db), _: Usuario = Depends(usuario_actual)):
    evidencia = obtener_o_404(db, Evidencia, id_, "Evidencia")
    contenido = almacenamiento.leer(evidencia.s3_key)
    if contenido is None:
        return {"integra": False, "mensaje": f"El archivo no está en {almacenamiento.descripcion()}."}
    actual = hashlib.sha256(contenido).hexdigest()
    integra = actual == evidencia.hash_sha256
    return {"integra": integra, "hash_registrado": evidencia.hash_sha256, "hash_actual": actual,
            "mensaje": "El archivo no ha sido alterado." if integra else "¡El archivo fue modificado después de su carga!"}


@router.delete("/{id_}", status_code=204, summary="Eliminar evidencia")
def eliminar(id_: int, db: Session = Depends(get_db), usuario: Usuario = Depends(cargador)):
    evidencia = obtener_o_404(db, Evidencia, id_, "Evidencia")
    if usuario.rol_codigo != "ADMIN" and evidencia.id_usuario_carga != usuario.id_usuario:
        raise HTTPException(403, "Solo quien cargó la evidencia (o un administrador) puede eliminarla.")
    clave = evidencia.s3_key
    db.delete(evidencia)
    db.commit()
    try:
        almacenamiento.eliminar(clave)
    except Exception:  # el registro ya no existe; el archivo queda como versión antigua en S3
        log.exception("No se pudo borrar %s del almacenamiento", clave)
    return Response(status_code=204)
