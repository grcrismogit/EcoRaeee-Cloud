"""Red de traslados (Matemáticas Discretas): escenarios, nodos, aristas y flujo máximo."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..crud import crear_router_crud, obtener_o_404
from ..database import get_db
from ..models import AristaRed, EscenarioRed, FlujoArista, NodoRed, ResultadoFlujo, Usuario
from ..schemas import (AristaIn, AristaOut, EscenarioIn, EscenarioOut, NodoIn, NodoOut, ResultadoOut)
from ..security import requiere_rol, usuario_actual
from ..services.flujo_maximo import flujo_maximo

ROLES_RED = ("COORDINADOR_LOGISTICO",)

escenarios = crear_router_crud(
    prefijo="/escenarios", etiqueta="Red y flujo máximo", nombre="Escenario", modelo=EscenarioRed,
    esquema_crear=EscenarioIn, esquema_salida=EscenarioOut, roles_escritura=ROLES_RED,
    orden=EscenarioRed.id_escenario,
)


def _nodo_mismo_escenario(datos, usuario, db):
    obtener_o_404(db, EscenarioRed, datos["id_escenario"], "Escenario")
    return datos


nodos = crear_router_crud(
    prefijo="/nodos", etiqueta="Red y flujo máximo", nombre="Nodo", modelo=NodoRed,
    esquema_crear=NodoIn, esquema_salida=NodoOut, roles_escritura=ROLES_RED, orden=NodoRed.id_nodo,
    filtros={"id_escenario": (NodoRed.id_escenario, int)}, antes_de_crear=_nodo_mismo_escenario,
)

aristas = crear_router_crud(
    prefijo="/aristas", etiqueta="Red y flujo máximo", nombre="Arista", modelo=AristaRed,
    esquema_crear=AristaIn, esquema_salida=AristaOut, roles_escritura=ROLES_RED, orden=AristaRed.id_arista,
    filtros={"id_escenario": (AristaRed.id_escenario, int)},
)


@escenarios.post("/{id_}/flujo-maximo", response_model=ResultadoOut, status_code=201,
                 summary="Calcular flujo máximo (Edmonds-Karp) y guardar el resultado")
def calcular_flujo(id_: int, db: Session = Depends(get_db), usuario: Usuario = Depends(requiere_rol(*ROLES_RED))):
    escenario = obtener_o_404(db, EscenarioRed, id_, "Escenario")
    lista_nodos = db.scalars(select(NodoRed).where(NodoRed.id_escenario == id_)).all()
    fuentes = [n for n in lista_nodos if n.tipo_nodo == "FUENTE"]
    sumideros = [n for n in lista_nodos if n.tipo_nodo == "SUMIDERO"]
    if len(fuentes) != 1 or len(sumideros) != 1:
        raise HTTPException(422, f"El escenario «{escenario.nombre}» necesita exactamente un nodo FUENTE y un nodo SUMIDERO.")
    lista_aristas = db.scalars(select(AristaRed).where(AristaRed.id_escenario == id_)).unique().all()
    if not lista_aristas:
        raise HTTPException(422, "El escenario no tiene aristas.")

    calculo = flujo_maximo(
        [(a.id_arista, a.id_nodo_origen, a.id_nodo_destino, float(a.capacidad)) for a in lista_aristas],
        fuentes[0].id_nodo, sumideros[0].id_nodo,
    )
    resultado = ResultadoFlujo(id_escenario=id_, algoritmo="Edmonds-Karp",
                               flujo_maximo=calculo["flujo_maximo"], id_ejecutor=usuario.id_usuario)
    db.add(resultado)
    db.flush()
    for a in calculo["aristas"]:
        db.add(FlujoArista(id_resultado=resultado.id_resultado, **a))
    db.commit()
    db.refresh(resultado)
    return resultado


@escenarios.get("/{id_}/resultados", response_model=list[ResultadoOut], summary="Historial de cálculos de flujo")
def resultados(id_: int, db: Session = Depends(get_db), _: Usuario = Depends(usuario_actual)):
    return db.scalars(select(ResultadoFlujo).where(ResultadoFlujo.id_escenario == id_)
                      .order_by(ResultadoFlujo.fecha_ejecucion.desc())).unique().all()


routers = [escenarios, nodos, aristas]
