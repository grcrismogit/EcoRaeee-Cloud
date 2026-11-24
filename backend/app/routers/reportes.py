"""Tablero, inventario, auditoría y estado del sistema."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import Auditoria, Inventario, Usuario
from ..schemas import AuditoriaOut, HistorialOut, InventarioOut
from ..security import requiere_rol, usuario_actual
from ..services import almacenamiento
from .operacion import ultimos_cambios

router = APIRouter(tags=["Reportes"])

ORDEN_ESTADOS = ["REGISTRADO", "RECIBIDO", "EVALUADO", "EN_TRANSITO", "TRANSFERIDO", "CERRADO"]
ORDEN_CLASIF = ["REUTILIZABLE", "REPARABLE", "RECICLABLE", "NO_RECUPERABLE", "SIN_EVALUAR"]


@router.get("/salud", summary="Estado de la API y de la conexión con PostgreSQL (sin autenticación)")
def salud(db: Session = Depends(get_db)):
    fila = db.execute(text("""
        SELECT version() AS version, current_database() AS base, current_schema() AS esquema,
               (SELECT count(*) FROM information_schema.tables
                 WHERE table_schema = 'ecoraee' AND table_type = 'BASE TABLE') AS tablas,
               COALESCE((SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()), false) AS ssl
    """)).mappings().one()
    # Datos de la arquitectura para el tablero (sin exponer endpoints ni credenciales)
    en_rds = (db.get_bind().url.host or "").endswith(".rds.amazonaws.com")
    return {"api": "ok", "base_datos": "conectada", "postgres": fila["version"].split(",")[0],
            "base": fila["base"], "esquema": fila["esquema"], "tablas": fila["tablas"],
            "motor": "Amazon RDS" if en_rds else "PostgreSQL local", "ssl": fila["ssl"],
            "almacenamiento": almacenamiento.descripcion(), "region": settings.aws_region if en_rds else None,
            "notificaciones_sns": bool(settings.sns_topic_arn),
            "hora_servidor": datetime.now(timezone.utc).isoformat()}


@router.get("/dashboard", summary="Indicadores para el tablero de inicio")
def dashboard(db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    totales = db.execute(text("""
        SELECT (SELECT count(*) FROM dispositivo)                                        AS dispositivos,
               (SELECT COALESCE(sum(peso_kg), 0) FROM dispositivo)                        AS kg_total,
               (SELECT count(*) FROM dispositivo WHERE estado_actual = 'CERRADO')         AS cerrados,
               (SELECT COALESCE(sum(d.peso_kg), 0) FROM dispositivo d
                  JOIN destino_final f ON f.id_dispositivo = d.id_dispositivo
                 WHERE f.tipo_destino <> 'DISPOSICION_FINAL')                             AS kg_recuperados,
               (SELECT count(*) FROM lote)                                                AS lotes,
               (SELECT count(*) FROM centro WHERE activo)                                 AS centros,
               (SELECT count(*) FROM transferencia WHERE estado IN ('PROGRAMADA','EN_TRANSITO')) AS transferencias_activas,
               (SELECT count(*) FROM solicitud_recoleccion WHERE estado IN ('PENDIENTE','PROGRAMADA')) AS solicitudes_pendientes,
               (SELECT count(*) FROM dispositivo WHERE estado_actual IN ('RECIBIDO','TRANSFERIDO')) AS por_evaluar
    """)).mappings().one()
    estados = dict(db.execute(text("SELECT estado_actual, count(*) FROM dispositivo GROUP BY 1")).all())
    clasif = dict(db.execute(text("SELECT COALESCE(clasificacion, 'SIN_EVALUAR'), count(*) FROM dispositivo GROUP BY 1")).all())
    destinos = db.execute(text("SELECT tipo_destino, count(*) AS cantidad FROM destino_final GROUP BY 1 ORDER BY 2 DESC")).mappings().all()
    ocupacion = db.execute(text("SELECT * FROM v_ocupacion_centro ORDER BY id_centro")).mappings().all()
    return {
        "totales": {k: float(v) if k.startswith("kg") else v for k, v in totales.items()},
        "por_estado": [{"estado": e, "cantidad": estados.get(e, 0)} for e in ORDEN_ESTADOS],
        "por_clasificacion": [{"clasificacion": c, "cantidad": clasif.get(c, 0)} for c in ORDEN_CLASIF],
        "por_destino": [dict(r) for r in destinos],
        "ocupacion_centros": [{**dict(r), "capacidad_kg": float(r["capacidad_kg"]), "peso_kg": float(r["peso_kg"]),
                               "ocupacion_pct": float(r["ocupacion_pct"])} for r in ocupacion],
        "ultimos_movimientos": [HistorialOut.model_validate(h) for h in ultimos_cambios(8, None, db, usuario)],
    }


@router.get("/inventario", response_model=list[InventarioOut], summary="Existencias por centro y categoría (RN-06)")
def inventario(id_centro: Optional[int] = None, db: Session = Depends(get_db), _: Usuario = Depends(usuario_actual)):
    consulta = select(Inventario).where(Inventario.cantidad_unidades > 0).order_by(Inventario.id_centro, Inventario.id_categoria)
    if id_centro:
        consulta = consulta.where(Inventario.id_centro == id_centro)
    return db.scalars(consulta).all()


@router.get("/auditoria", response_model=list[AuditoriaOut], summary="Bitácora de auditoría (solo ADMIN)")
def auditoria(tabla: Optional[str] = None, operacion: Optional[str] = None, id_registro: Optional[int] = None,
              limite: int = 100, db: Session = Depends(get_db), _: Usuario = Depends(requiere_rol())):
    consulta = select(Auditoria).order_by(Auditoria.id_auditoria.desc()).limit(min(max(limite, 1), 500))
    if tabla:
        consulta = consulta.where(Auditoria.tabla == tabla)
    if operacion:
        consulta = consulta.where(Auditoria.operacion == operacion)
    if id_registro:
        consulta = consulta.where(Auditoria.id_registro == id_registro)
    return db.scalars(consulta).all()
