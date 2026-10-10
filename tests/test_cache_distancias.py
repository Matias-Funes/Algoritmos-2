import math

from warehouse.algoritmos.distancias import CacheDistancias
from warehouse.warehouse.warehouse import Warehouse


def _grilla(n: int) -> Warehouse:
    w = Warehouse(n, n)
    w.construir_grafo({(x, y) for x in range(n) for y in range(n)})
    return w


def test_distancia_simple():
    w = _grilla(3)
    cache = CacheDistancias(w.grafo)
    a = w._nodo_por_xy[(0, 0)]
    b = w._nodo_por_xy[(2, 2)]
    assert cache.distancia(a, b) == 4


def test_distancia_simetrica():
    w = _grilla(3)
    cache = CacheDistancias(w.grafo)
    a = w._nodo_por_xy[(0, 0)]
    b = w._nodo_por_xy[(2, 2)]
    assert cache.distancia(a, b) == cache.distancia(b, a)


def test_camino_correcto():
    w = _grilla(3)
    cache = CacheDistancias(w.grafo)
    a = w._nodo_por_xy[(0, 0)]
    b = w._nodo_por_xy[(2, 0)]
    camino = cache.camino(a, b)
    assert camino[0] == a
    assert camino[-1] == b
    assert len(camino) == 3


def test_cache_reutiliza_dijkstra():
    w = _grilla(5)
    cache = CacheDistancias(w.grafo)
    a = w._nodo_por_xy[(0, 0)]
    cache.distancia(a, w._nodo_por_xy[(0, 4)])
    cache.distancia(a, w._nodo_por_xy[(4, 0)])
    cache.distancia(a, w._nodo_por_xy[(4, 4)])
    assert len(cache._cache) == 1  # solo un Dijkstra


def test_sin_camino():
    w = Warehouse(5, 5)
    w.construir_grafo({(0, 0), (4, 4)})
    cache = CacheDistancias(w.grafo)
    n0 = w._nodo_por_xy[(0, 0)]
    n1 = w._nodo_por_xy[(4, 4)]
    assert cache.distancia(n0, n1) == math.inf
    assert cache.camino(n0, n1) == []
