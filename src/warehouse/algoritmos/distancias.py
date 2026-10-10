from warehouse.algoritmos.caminos import dijkstra
from warehouse.estructuras.grafo import Grafo


class CacheDistancias:
    """Cachea distancias y predecesores desde cada origen consultado.
    La primera consulta desde un origen corre Dijkstra; las siguientes son O(1)."""

    def __init__(self, grafo: Grafo) -> None:
        self._grafo = grafo
        self._cache: dict[int, dict[int, float]] = {}
        self._predecesores: dict[int, dict[int, int | None]] = {}

    def _asegurar_origen(self, origen: int) -> None:
        if origen not in self._cache:
            dist, pred = dijkstra(self._grafo, origen)
            self._cache[origen] = dist
            self._predecesores[origen] = pred

    def distancia(self, u: int, v: int) -> float:
        self._asegurar_origen(u)
        return self._cache[u].get(v, float("inf"))

    def camino(self, u: int, v: int) -> list[int]:
        self._asegurar_origen(u)
        if v not in self._cache[u]:
            return []
        camino: list[int] = []
        actual: int | None = v
        while actual is not None:
            camino.append(actual)
            actual = self._predecesores[u][actual]
        camino.reverse()
        return camino
