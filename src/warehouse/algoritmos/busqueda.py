from collections import deque

from warehouse.estructuras.grafo import Grafo


def bfs_alcanzables(grafo: Grafo, origen: int) -> set[int]:
    """BFS desde un nodo. Devuelve el conjunto de nodos alcanzables (incluye origen)."""
    if not grafo.contiene(origen):
        raise KeyError(f"Nodo {origen} no existe en el grafo")

    visitados: set[int] = {origen}
    cola: deque[int] = deque([origen])

    while cola:
        actual = cola.popleft()
        for arista in grafo.vecinos(actual):
            if arista.destino not in visitados:
                visitados.add(arista.destino)
                cola.append(arista.destino)

    return visitados
