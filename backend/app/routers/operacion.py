"""Procesos de trazabilidad: lotes, dispositivos, solicitudes de recolección,
recepciones, evaluaciones técnicas y destino final."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..crud import crear_router_crud, obtener_o_404
from ..database import get_db
from ..models import (DestinoFinal, DetalleTransferencia, Dispositivo, EvaluacionTecnica, Evidencia,
                      HistorialEstado, Lote, Recepcion, SolicitudRecoleccion, Transferencia, Usuario)
from ..schemas import (DestinoCrear, DestinoOut, DispositivoIn, DispositivoOut, EvaluacionCrear, EvaluacionEditar,
                       EvaluacionOut, EvidenciaOut, HistorialOut, LoteDetalleOut, LoteIn, LoteOut, RecepcionCrear,
                       RecepcionEditar, RecepcionOut, SolicitudCrear, SolicitudEditar, SolicitudOut, TransferenciaOut)
from ..security import asignar_actor, usuario_actual
from ..services.notificaciones import notificar


def _solo_propios(usuario: Usuario, id_generador: int) -> None:
    """Un GENERADOR solo gestiona sus propios lotes."""
    if usuario.rol_codigo == "GENERADOR" and id_generador != usuario.id_usuario:
        raise HTTPException(403, "Solo puede gestionar los lotes que usted registró.")


# --------------------------------------------------------------------- lotes
def _crear_lote(datos, usuario, db):
    return asignar_actor(datos, "id_generador", usuario, "generador del lote")


def _editar_lote(obj, datos, usuario, db):
    _solo_propios(usuario, obj.id_generador)
    if usuario.rol_codigo != "ADMIN" or not datos.get("id_generador"):
        datos["id_generador"] = obj.id_generador
    return datos


lotes = crear_router_crud(
    prefijo="/lotes", etiqueta="Lotes", nombre="Lote", modelo=Lote,
    esquema_crear=LoteIn, esquema_salida=LoteOut, roles_escritura=("GENERADOR",),
    orden=Lote.id_lote.desc(),
    filtros={"estado": (Lote.estado, str), "id_generador": (Lote.id_generador, int)},
    busqueda=[Lote.codigo_lote, Lote.descripcion],
    antes_de_crear=_crear_lote, antes_de_actualizar=_editar_lote,
    antes_de_eliminar=lambda obj, u, db: _solo_propios(u, obj.id_generador),
)


@lotes.get("/{id_}/detalle", response_model=LoteDetalleOut, summary="Lote con sus dispositivos")
def detalle_lote(id_: int, db: Session = Depends(get_db), _: Usuario = Depends(usuario_actual)):
    return obtener_o_404(db, Lote, id_, "Lote")


# --------------------------------------------------------------------- dispositivos
def _crear_dispositivo(datos, usuario, db):
    lote = obtener_o_404(db, Lote, datos["id_lote"], "Lote")
    _solo_propios(usuario, lote.id_generador)
    return datos


def _editar_dispositivo(obj, datos, usuario, db):
    _solo_propios(usuario, obj.lote.id_generador)
    if datos["id_lote"] != obj.id_lote:
        nuevo = obtener_o_404(db, Lote, datos["id_lote"], "Lote")
        _solo_propios(usuario, nuevo.id_generador)
    return datos


dispositivos = crear_router_crud(
    prefijo="/dispositivos", etiqueta="Dispositivos", nombre="Dispositivo", modelo=Dispositivo,
    esquema_crear=DispositivoIn, esquema_salida=DispositivoOut, roles_escritura=("GENERADOR",),
    orden=Dispositivo.id_dispositivo,
    filtros={
        "estado": (Dispositivo.estado_actual, str), "id_centro": (Dispositivo.id_centro_actual, int),
        "id_categoria": (Dispositivo.id_categoria, int), "id_lote": (Dispositivo.id_lote, int),
        "clasificacion": (Dispositivo.clasificacion, str),
    },
    busqueda=[Dispositivo.codigo_unico, Dispositivo.modelo, Dispositivo.numero_serie],
    antes_de_crear=_crear_dispositivo, antes_de_actualizar=_editar_dispositivo,
    antes_de_eliminar=lambda obj, u, db: _solo_propios(u, obj.lote.id_generador),
)


def _trazabilidad(db: Session, d: Dispositivo) -> dict:
    """Reúne todo el recorrido del dispositivo: de dónde vino, por dónde pasó y dónde terminó."""
    solicitud_ids = select(SolicitudRecoleccion.id_solicitud).where(SolicitudRecoleccion.id_lote == d.id_lote)
    recepcion = db.scalars(select(Recepcion).where(Recepcion.id_solicitud.in_(solicitud_ids))).first()
    historial = db.scalars(select(HistorialEstado).where(HistorialEstado.id_dispositivo == d.id_dispositivo)
                           .order_by(HistorialEstado.nro_cambio)).all()
    evaluaciones = db.scalars(select(EvaluacionTecnica).where(EvaluacionTecnica.id_dispositivo == d.id_dispositivo)
                              .order_by(EvaluacionTecnica.fecha_evaluacion)).all()
    transferencias = db.scalars(select(Transferencia).join(DetalleTransferencia)
                                .where(DetalleTransferencia.id_dispositivo == d.id_dispositivo)
                                .order_by(Transferencia.fecha_salida)).unique().all()
    destino = db.scalars(select(DestinoFinal).where(DestinoFinal.id_dispositivo == d.id_dispositivo)).first()
    condiciones = [Evidencia.id_dispositivo == d.id_dispositivo]
    if evaluaciones:
        condiciones.append(Evidencia.id_evaluacion.in_([e.id_evaluacion for e in evaluaciones]))
    if transferencias:
        condiciones.append(Evidencia.id_transferencia.in_([t.id_transferencia for t in transferencias]))
    if destino:
        condiciones.append(Evidencia.id_destino_final == destino.id_destino_final)
    evidencias = db.scalars(select(Evidencia).where(or_(*condiciones)).order_by(Evidencia.fecha_carga)).all()
    return {
        "dispositivo": DispositivoOut.model_validate(d),
        "lote": LoteOut.model_validate(d.lote),
        "recepcion": RecepcionOut.model_validate(recepcion) if recepcion else None,
        "historial": [HistorialOut.model_validate(h) for h in historial],
        "evaluaciones": [EvaluacionOut.model_validate(e) for e in evaluaciones],
        "transferencias": [TransferenciaOut.model_validate(t) for t in transferencias],
        "destino_final": DestinoOut.model_validate(destino) if destino else None,
        "evidencias": [EvidenciaOut.model_validate(e) for e in evidencias],
    }


@dispositivos.get("/{id_}/trazabilidad", summary="Trazabilidad completa de un dispositivo")
def trazabilidad_por_id(id_: int, db: Session = Depends(get_db), _: Usuario = Depends(usuario_actual)):
    return _trazabilidad(db, obtener_o_404(db, Dispositivo, id_, "Dispositivo"))


trazabilidad = APIRouter(prefix="/trazabilidad", tags=["Dispositivos"])


@trazabilidad.get("/{codigo}", summary="Buscar la trazabilidad por código único (RAEE-AAAA-NNNNN)")
def trazabilidad_por_codigo(codigo: str, db: Session = Depends(get_db), _: Usuario = Depends(usuario_actual)):
    d = db.scalars(select(Dispositivo).where(Dispositivo.codigo_unico == codigo.strip().upper())).first()
    if d is None:
        raise HTTPException(404, f"No existe un dispositivo con el código {codigo}.")
    return _trazabilidad(db, d)


# --------------------------------------------------------------------- solicitudes
def _crear_solicitud(datos, usuario, db):
    datos = asignar_actor(datos, "id_solicitante", usuario, "solicitante")
    lote = obtener_o_404(db, Lote, datos["id_lote"], "Lote")
    _solo_propios(usuario, lote.id_generador)
    datos["estado"] = "PROGRAMADA" if datos.get("fecha_programada") else "PENDIENTE"
    return datos


solicitudes = crear_router_crud(
    prefijo="/solicitudes", etiqueta="Recolección", nombre="Solicitud", modelo=SolicitudRecoleccion,
    esquema_crear=SolicitudCrear, esquema_editar=SolicitudEditar, esquema_salida=SolicitudOut,
    roles_escritura=("GENERADOR", "COORDINADOR_LOGISTICO"), orden=SolicitudRecoleccion.id_solicitud.desc(),
    filtros={"estado": (SolicitudRecoleccion.estado, str), "id_lote": (SolicitudRecoleccion.id_lote, int),
             "id_centro_destino": (SolicitudRecoleccion.id_centro_destino, int)},
    antes_de_crear=_crear_solicitud,
)


# --------------------------------------------------------------------- recepciones
def _crear_recepcion(datos, usuario, db):
    datos = asignar_actor(datos, "id_operador", usuario, "operador que recibe")
    solicitud = obtener_o_404(db, SolicitudRecoleccion, datos["id_solicitud"], "Solicitud")
    datos["id_centro"] = solicitud.id_centro_destino  # se recibe en el centro de la solicitud
    return datos


def _avisar_recepcion(r):
    notificar("LOTE_RECIBIDO", f"Lote {r.codigo_lote} recibido",
              f"El lote {r.codigo_lote} llegó a {r.centro_nombre} ({r.peso_recibido_kg} kg). "
              f"Recibió: {r.operador_nombre}.")


recepciones = crear_router_crud(
    prefijo="/recepciones", etiqueta="Recolección", nombre="Recepción", modelo=Recepcion,
    esquema_crear=RecepcionCrear, esquema_editar=RecepcionEditar, esquema_salida=RecepcionOut,
    roles_escritura=("OPERADOR_CENTRO",), orden=Recepcion.id_recepcion.desc(),
    filtros={"id_centro": (Recepcion.id_centro, int)},
    antes_de_crear=_crear_recepcion, permitir_eliminar=False,  # forma parte de la trazabilidad
    despues_de_crear=_avisar_recepcion,
)


# --------------------------------------------------------------------- evaluaciones
evaluaciones = crear_router_crud(
    prefijo="/evaluaciones", etiqueta="Evaluaciones", nombre="Evaluación", modelo=EvaluacionTecnica,
    esquema_crear=EvaluacionCrear, esquema_editar=EvaluacionEditar, esquema_salida=EvaluacionOut,
    roles_escritura=("TECNICO_EVALUADOR",), orden=EvaluacionTecnica.fecha_evaluacion.desc(),
    filtros={"id_dispositivo": (EvaluacionTecnica.id_dispositivo, int),
             "clasificacion": (EvaluacionTecnica.clasificacion, str),
             "id_tecnico": (EvaluacionTecnica.id_tecnico, int)},
    antes_de_crear=lambda d, u, db: asignar_actor(d, "id_tecnico", u, "técnico evaluador"),
)


# --------------------------------------------------------------------- destino final
def _crear_destino(datos, usuario, db):
    datos = asignar_actor(datos, "id_usuario_confirma", usuario, "usuario que confirma")
    d = obtener_o_404(db, Dispositivo, datos["id_dispositivo"], "Dispositivo")
    if d.id_centro_actual is None:
        raise HTTPException(409, f"El dispositivo {d.codigo_unico} todavía no está en ningún centro.")
    datos["id_centro"] = d.id_centro_actual  # el cierre ocurre donde está el equipo
    if datos["tipo_destino"] != "DONACION":
        datos["id_org_beneficiaria"] = datos.get("id_org_beneficiaria")
    return datos


def _avisar_destino(d):
    beneficiaria = f" Beneficiaria: {d.org_beneficiaria_nombre}." if d.org_beneficiaria_nombre else ""
    notificar("DESTINO_FINAL", f"{d.codigo_unico} cerró su trazabilidad",
              f"El dispositivo {d.codigo_unico} quedó CERRADO con destino {d.tipo_destino} en {d.centro_nombre}."
              f"{beneficiaria} Confirmó: {d.usuario_confirma_nombre}.")


destinos = crear_router_crud(
    prefijo="/destinos", etiqueta="Destino final", nombre="Destino final", modelo=DestinoFinal,
    esquema_crear=DestinoCrear, esquema_salida=DestinoOut,
    roles_escritura=("COORDINADOR_LOGISTICO", "OPERADOR_CENTRO"), orden=DestinoFinal.fecha_confirmacion.desc(),
    filtros={"tipo_destino": (DestinoFinal.tipo_destino, str), "id_centro": (DestinoFinal.id_centro, int)},
    antes_de_crear=_crear_destino, permitir_editar=False, permitir_eliminar=False,  # RN-08: cierre definitivo
    despues_de_crear=_avisar_destino,
)


# --------------------------------------------------------------------- historial
historial = APIRouter(prefix="/historial", tags=["Dispositivos"])


@historial.get("", response_model=list[HistorialOut], summary="Últimos cambios de estado")
def ultimos_cambios(limite: int = 20, id_dispositivo: Optional[int] = None,
                    db: Session = Depends(get_db), _: Usuario = Depends(usuario_actual)):
    consulta = select(HistorialEstado).order_by(HistorialEstado.fecha_cambio.desc(), HistorialEstado.nro_cambio.desc())
    if id_dispositivo:
        consulta = consulta.where(HistorialEstado.id_dispositivo == id_dispositivo)
    return db.scalars(consulta.limit(min(max(limite, 1), 200))).all()


routers = [lotes, dispositivos, trazabilidad, solicitudes, recepciones, evaluaciones, destinos, historial]
