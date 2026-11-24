"""Transferencias entre centros: PROGRAMADA → EN_TRANSITO → CERRADA (o CANCELADA).

Despachar y recibir se ejecutan con procedimientos almacenados para que
dispositivos, inventario y transferencia cambien en una sola transacción (RN-06).
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..crud import obtener_o_404
from ..database import get_db
from ..models import AristaRed, DetalleTransferencia, Dispositivo, NodoRed, Transferencia, Usuario
from ..schemas import (AristaOut, DispositivoOut, RecibirIn, TransferenciaCrear, TransferenciaDetalleOut, TransferenciaEditar,
                       TransferenciaOut)
from ..security import asignar_actor, requiere_rol, usuario_actual
from ..services.notificaciones import notificar

router = APIRouter(prefix="/transferencias", tags=["Transferencias"])
coordinador = requiere_rol("COORDINADOR_LOGISTICO")
receptor = requiere_rol("COORDINADOR_LOGISTICO", "OPERADOR_CENTRO")


def _codigos(t: Transferencia) -> str:
    return ", ".join(d.codigo_unico for d in t.dispositivos)


@router.get("", response_model=list[TransferenciaOut], summary="Listar transferencias")
def listar(estado: Optional[str] = None, id_centro: Optional[int] = None,
           db: Session = Depends(get_db), _: Usuario = Depends(usuario_actual)):
    consulta = select(Transferencia).order_by(Transferencia.id_transferencia.desc())
    if estado:
        consulta = consulta.where(Transferencia.estado.in_(estado.split(",")))
    if id_centro:
        consulta = consulta.where((Transferencia.id_centro_origen == id_centro) | (Transferencia.id_centro_destino == id_centro))
    return db.scalars(consulta).unique().all()


@router.get("/rutas", response_model=list[AristaOut], summary="Aristas que unen dos centros (rutas posibles)")
def rutas(origen: int, destino: int, db: Session = Depends(get_db), _: Usuario = Depends(usuario_actual)):
    o = select(NodoRed.id_nodo).where(NodoRed.id_centro == origen)
    d = select(NodoRed.id_nodo).where(NodoRed.id_centro == destino)
    consulta = select(AristaRed).where(AristaRed.id_nodo_origen.in_(o), AristaRed.id_nodo_destino.in_(d))
    return db.scalars(consulta).unique().all()


@router.get("/disponibles", response_model=list[DispositivoOut],
            summary="Dispositivos de un centro que pueden incluirse en una transferencia")
def disponibles(origen: int, transferencia: Optional[int] = None, db: Session = Depends(get_db),
                _: Usuario = Depends(usuario_actual)):
    ocupados = (select(DetalleTransferencia.id_dispositivo).join(Transferencia)
                .where(Transferencia.estado.in_(["PROGRAMADA", "EN_TRANSITO"])))
    if transferencia:  # al editar, los equipos de esta misma transferencia siguen disponibles
        ocupados = ocupados.where(Transferencia.id_transferencia != transferencia)
    consulta = (select(Dispositivo)
                .where(Dispositivo.id_centro_actual == origen,
                       Dispositivo.estado_actual.in_(["RECIBIDO", "EVALUADO", "TRANSFERIDO"]),
                       Dispositivo.id_dispositivo.not_in(ocupados))
                .order_by(Dispositivo.id_dispositivo))
    return db.scalars(consulta).unique().all()


@router.get("/{id_}", response_model=TransferenciaDetalleOut, summary="Transferencia con sus dispositivos")
def obtener(id_: int, db: Session = Depends(get_db), _: Usuario = Depends(usuario_actual)):
    return obtener_o_404(db, Transferencia, id_, "Transferencia")


@router.post("", response_model=TransferenciaDetalleOut, status_code=201, summary="Programar transferencia")
def crear(datos: TransferenciaCrear, db: Session = Depends(get_db), usuario: Usuario = Depends(coordinador)):
    valores = asignar_actor(datos.model_dump(exclude={"dispositivos"}), "id_coordinador", usuario, "coordinador logístico")
    t = Transferencia(**valores)
    db.add(t)
    db.flush()  # obtiene el id sin confirmar todavía
    for id_dispositivo in datos.dispositivos:
        db.add(DetalleTransferencia(id_transferencia=t.id_transferencia, id_dispositivo=id_dispositivo))
        db.flush()  # cada equipo pasa por el trigger RN-05 (capacidad de la arista)
    db.commit()     # todo o nada
    db.refresh(t)
    return t


@router.put("/{id_}", response_model=TransferenciaDetalleOut, summary="Editar transferencia PROGRAMADA")
def actualizar(id_: int, datos: TransferenciaEditar, db: Session = Depends(get_db),
               _: Usuario = Depends(coordinador)):
    t = obtener_o_404(db, Transferencia, id_, "Transferencia")
    if t.estado != "PROGRAMADA":
        raise HTTPException(409, f"Solo se editan transferencias PROGRAMADAS (esta está {t.estado}).")
    if datos.id_centro_destino == t.id_centro_origen:
        raise HTTPException(422, "El centro de destino debe ser distinto del de origen.")
    actuales = {d.id_dispositivo for d in t.detalles}
    nuevos = set(datos.dispositivos)
    # 1) quitar los que salen, 2) cambiar cabecera (ruta), 3) agregar los nuevos
    for det in list(t.detalles):
        if det.id_dispositivo not in nuevos:
            db.delete(det)
    db.flush()
    t.id_centro_destino = datos.id_centro_destino
    t.id_arista = datos.id_arista
    t.fecha_salida = datos.fecha_salida
    db.flush()
    for id_dispositivo in sorted(nuevos - actuales):
        db.add(DetalleTransferencia(id_transferencia=t.id_transferencia, id_dispositivo=id_dispositivo))
        db.flush()
    db.commit()
    db.refresh(t)
    return t


@router.post("/{id_}/despachar", response_model=TransferenciaDetalleOut, summary="Despachar (sale del centro)")
def despachar(id_: int, db: Session = Depends(get_db), _: Usuario = Depends(coordinador)):
    obtener_o_404(db, Transferencia, id_, "Transferencia")
    db.execute(text("CALL sp_despachar_transferencia(:id)"), {"id": id_})
    db.commit()
    t = db.get(Transferencia, id_)
    notificar("TRANSFERENCIA_DESPACHADA", f"Transferencia #{id_} en tránsito",
              f"La transferencia #{id_} salió de {t.centro_origen_nombre} hacia {t.centro_destino_nombre} "
              f"con {t.num_dispositivos} dispositivo(s): {_codigos(t)}.")
    return t


@router.post("/{id_}/recibir", response_model=TransferenciaDetalleOut, summary="Recibir en el centro destino (RN-03, RN-06)")
def recibir(id_: int, datos: RecibirIn, db: Session = Depends(get_db), usuario: Usuario = Depends(receptor)):
    obtener_o_404(db, Transferencia, id_, "Transferencia")
    # El ADMIN indica quién recibe; operadores y coordinadores firman en su propio nombre
    responsable = datos.id_responsable if usuario.rol_codigo == "ADMIN" else usuario.id_usuario
    if not responsable:
        raise HTTPException(422, "Seleccione el responsable que recibe la transferencia.")
    db.execute(text("CALL sp_recibir_transferencia(:id, :resp)"), {"id": id_, "resp": responsable})
    db.commit()
    t = db.get(Transferencia, id_)
    notificar("TRANSFERENCIA_RECIBIDA", f"Transferencia #{id_} recibida",
              f"La transferencia #{id_} llegó a {t.centro_destino_nombre} y quedó CERRADA. "
              f"Recibió: {t.responsable_nombre}. Dispositivos: {_codigos(t)}.")
    return t


@router.post("/{id_}/cancelar", response_model=TransferenciaDetalleOut, summary="Cancelar transferencia PROGRAMADA")
def cancelar(id_: int, db: Session = Depends(get_db), _: Usuario = Depends(coordinador)):
    t = obtener_o_404(db, Transferencia, id_, "Transferencia")
    t.estado = "CANCELADA"  # el trigger solo permite PROGRAMADA → CANCELADA
    db.commit()
    db.refresh(t)
    return t


@router.delete("/{id_}", status_code=204, summary="Eliminar transferencia PROGRAMADA o CANCELADA")
def eliminar(id_: int, db: Session = Depends(get_db), _: Usuario = Depends(coordinador)):
    t = obtener_o_404(db, Transferencia, id_, "Transferencia")
    db.delete(t)
    db.commit()
    return Response(status_code=204)
