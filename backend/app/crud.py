"""Fábrica de routers CRUD reutilizable.

Cada módulo declara su modelo, sus esquemas y quién puede escribir; esta
función genera los cinco endpoints REST: listar, obtener, crear, actualizar
y eliminar. Los ganchos (antes_de_crear, antes_de_actualizar, ...) permiten
aplicar reglas propias de cada módulo.
"""
from typing import Any, Callable, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .database import get_db
from .models import Usuario
from .security import requiere_rol, usuario_actual


def obtener_o_404(db: Session, modelo, id_: Any, nombre: str):
    obj = db.get(modelo, id_)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{nombre} {id_} no existe.")
    return obj


def crear_router_crud(
    *,
    prefijo: str,
    etiqueta: str,
    nombre: str,
    modelo,
    esquema_crear,
    esquema_salida,
    esquema_editar=None,
    roles_escritura: tuple[str, ...] = (),
    orden=None,
    filtros: Optional[dict[str, tuple[Any, Callable]]] = None,
    busqueda: Optional[list] = None,
    antes_de_crear: Optional[Callable[[dict, Usuario, Session], dict]] = None,
    antes_de_actualizar: Optional[Callable[[Any, dict, Usuario, Session], dict]] = None,
    antes_de_eliminar: Optional[Callable[[Any, Usuario, Session], None]] = None,
    despues_de_crear: Optional[Callable[[Any], None]] = None,
    permitir_editar: bool = True,
    permitir_eliminar: bool = True,
) -> APIRouter:
    router = APIRouter(prefix=prefijo, tags=[etiqueta])
    esquema_editar = esquema_editar or esquema_crear
    filtros = filtros or {}
    escritor = requiere_rol(*roles_escritura)

    @router.get("", response_model=list[esquema_salida], summary=f"Listar {etiqueta.lower()}")
    def listar(request: Request, q: Optional[str] = None, db: Session = Depends(get_db),
               _: Usuario = Depends(usuario_actual)):
        consulta = select(modelo)
        for parametro, valor in request.query_params.items():
            if parametro in filtros and valor != "":
                columna, convertir = filtros[parametro]
                try:
                    valores = [convertir(v) for v in valor.split(",")]
                except ValueError:
                    raise HTTPException(422, f"El filtro '{parametro}' no es válido.")
                consulta = consulta.where(columna.in_(valores))
        if q and busqueda:
            patron = f"%{q.strip()}%"
            consulta = consulta.where(or_(*[c.ilike(patron) for c in busqueda]))
        if orden is not None:
            consulta = consulta.order_by(*orden) if isinstance(orden, (list, tuple)) else consulta.order_by(orden)
        return db.scalars(consulta).unique().all()

    @router.get("/{id_}", response_model=esquema_salida, summary=f"Obtener {nombre.lower()}")
    def obtener(id_: int, db: Session = Depends(get_db), _: Usuario = Depends(usuario_actual)):
        return obtener_o_404(db, modelo, id_, nombre)

    @router.post("", response_model=esquema_salida, status_code=201, summary=f"Crear {nombre.lower()}")
    def crear(datos: esquema_crear, db: Session = Depends(get_db), usuario: Usuario = Depends(escritor)):
        valores = datos.model_dump()
        if antes_de_crear:
            valores = antes_de_crear(valores, usuario, db)
        obj = modelo(**valores)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        if despues_de_crear:
            despues_de_crear(obj)  # p. ej., notificar por SNS cuando ya quedó guardado
        return obj

    if permitir_editar:
        @router.put("/{id_}", response_model=esquema_salida, summary=f"Actualizar {nombre.lower()}")
        def actualizar(id_: int, datos: esquema_editar, db: Session = Depends(get_db),
                       usuario: Usuario = Depends(escritor)):
            obj = obtener_o_404(db, modelo, id_, nombre)
            valores = datos.model_dump(exclude_unset=False)
            if antes_de_actualizar:
                valores = antes_de_actualizar(obj, valores, usuario, db)
            for campo, valor in valores.items():
                setattr(obj, campo, valor)
            db.commit()
            db.refresh(obj)
            return obj

    if permitir_eliminar:
        @router.delete("/{id_}", status_code=204, summary=f"Eliminar {nombre.lower()}")
        def eliminar(id_: int, db: Session = Depends(get_db), usuario: Usuario = Depends(escritor)):
            obj = obtener_o_404(db, modelo, id_, nombre)
            if antes_de_eliminar:
                antes_de_eliminar(obj, usuario, db)
            db.delete(obj)
            db.commit()
            return Response(status_code=204)

    return router
