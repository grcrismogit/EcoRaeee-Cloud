"""Flujo máximo con el algoritmo de Edmonds-Karp (Ford-Fulkerson con BFS).

Entrada: aristas dirigidas (id, origen, destino, capacidad), un nodo fuente s
y un nodo sumidero t. Salida: valor del flujo máximo, flujo por arista y las
aristas del corte mínimo (teorema flujo máximo = corte mínimo).
"""
from collections import deque
from dataclasses import dataclass


@dataclass
class _Arco:
    destino: int
    capacidad: float
    flujo: float
    reverso: "_Arco | None" = None
    id_arista: int | None = None  # None en los arcos residuales de retroceso

    @property
    def residual(self) -> float:
        return self.capacidad - self.flujo


def flujo_maximo(aristas: list[tuple[int, int, int, float]], fuente: int, sumidero: int) -> dict:
    grafo: dict[int, list[_Arco]] = {}
    originales: list[_Arco] = []
    for id_arista, u, v, cap in aristas:
        ida = _Arco(v, float(cap), 0.0, id_arista=id_arista)
        vuelta = _Arco(u, 0.0, 0.0)
        ida.reverso, vuelta.reverso = vuelta, ida
        grafo.setdefault(u, []).append(ida)
        grafo.setdefault(v, []).append(vuelta)
        originales.append(ida)
    grafo.setdefault(fuente, [])
    grafo.setdefault(sumidero, [])

    total = 0.0
    iteraciones = 0
    while True:
        # BFS: camino aumentante más corto en número de aristas
        previo: dict[int, _Arco] = {}
        cola = deque([fuente])
        visitados = {fuente}
        while cola and sumidero not in visitados:
            u = cola.popleft()
            for arco in grafo[u]:
                if arco.residual > 1e-9 and arco.destino not in visitados:
                    visitados.add(arco.destino)
                    previo[arco.destino] = arco
                    cola.append(arco.destino)
        if sumidero not in visitados:
            break
        # cuello de botella del camino
        cuello, v = float("inf"), sumidero
        while v != fuente:
            arco = previo[v]
            cuello = min(cuello, arco.residual)
            v = arco.reverso.destino
        # aumentar el flujo a lo largo del camino
        v = sumidero
        while v != fuente:
            arco = previo[v]
            arco.flujo += cuello
            arco.reverso.flujo -= cuello
            v = arco.reverso.destino
        total += cuello
        iteraciones += 1

    # Corte mínimo: nodos alcanzables desde s en el grafo residual final
    alcanzables, cola = {fuente}, deque([fuente])
    while cola:
        u = cola.popleft()
        for arco in grafo[u]:
            if arco.residual > 1e-9 and arco.destino not in alcanzables:
                alcanzables.add(arco.destino)
                cola.append(arco.destino)

    resultado = []
    for arco in originales:
        origen = arco.reverso.destino
        resultado.append({
            "id_arista": arco.id_arista,
            "flujo": round(arco.flujo, 2),
            "saturada": abs(arco.capacidad - arco.flujo) < 1e-9,
            "en_corte_minimo": origen in alcanzables and arco.destino not in alcanzables,
        })
    return {"flujo_maximo": round(total, 2), "aristas": resultado, "iteraciones": iteraciones,
            "conjunto_s": sorted(alcanzables)}
