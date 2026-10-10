import math

import pytest

from warehouse.algoritmos.caminos import camino_mas_corto, dijkstra, distancia
from warehouse.dominio.posicion import Posicion
from warehouse.dominio.tipo_nodo import TipoNodo
from warehouse.estructuras.grafo import Grafo
from warehouse.warehouse.warehouse import Warehouse


def _grilla(n: int) -> Warehouse:
    w = Warehouse(n, n)
    w.construir_grafo({(x, y) for x in range(n) for y in range(n)})
    return w


def test_dijkstra_distancias_en_grilla():
    w = _grilla(3)
    dist, _ = dijkstra(w.grafo, 0)  # esquina (0,0)
    # A (2,2) son 4 pasos Manhattan
    destino = w._nodo_por_xy[(2, 2)]
    assert dist[destino] == 4


def test_dijkstra_predecesores_reconstruyen_camino():
    w = _grilla(3)
    dist, pred = dijkstra(w.grafo, 0)
    destino = w._nodo_por_xy[(2, 2)]
    camino = []
    actual = destino
    while actual is not None:
        camino.append(actual)
        actual = pred[actual]
    camino.reverse()
    assert camino[0] == 0
    assert camino[-1] == destino
    assert len(camino) == 5  # 4 aristas, 5 nodos


def test_camino_mas_corto_simple():
    w = _grilla(3)
    camino, dist = camino_mas_corto(
        w.grafo, w._nodo_por_xy[(0, 0)], w._nodo_por_xy[(2, 0)]
    )
    assert dist == 2
    assert len(camino) == 3


def test_camino_mas_corto_mismo_nodo():
    w = _grilla(3)
    n = w._nodo_por_xy[(1, 1)]
    camino, dist = camino_mas_corto(w.grafo, n, n)
    assert camino == [n]
    assert dist == 0


def test_distancia_sin_camino():
    w = Warehouse(5, 5)
    w.construir_grafo({(0, 0), (4, 4)})
    n0 = w._nodo_por_xy[(0, 0)]
    n1 = w._nodo_por_xy[(4, 4)]
    assert distancia(w.grafo, n0, n1) == math.inf


def test_camino_sin_camino_devuelve_vacio():
    w = Warehouse(5, 5)
    w.construir_grafo({(0, 0), (4, 4)})
    n0 = w._nodo_por_xy[(0, 0)]
    n1 = w._nodo_por_xy[(4, 4)]
    camino, dist = camino_mas_corto(w.grafo, n0, n1)
    assert camino == []
    assert dist == math.inf


def test_dijkstra_con_pesos_distintos():
    """Con pesos distintos, el camino no es simplemente el más corto en aristas."""
    g = Grafo()
    a = g.agregar_nodo(Posicion(0, 0), TipoNodo.PASILLO)
    b = g.agregar_nodo(Posicion(1, 0), TipoNodo.PASILLO)
    c = g.agregar_nodo(Posicion(2, 0), TipoNodo.PASILLO)

    # Camino directo a->c con peso 10, indirecto a->b->c con peso 2+2=4
    g.agregar_arista(a, c, peso=10.0)
    g.agregar_arista(a, b, peso=2.0)
    g.agregar_arista(b, c, peso=2.0)

    camino, dist = camino_mas_corto(g, a, c)
    assert dist == 4
    assert camino == [a, b, c]


def test_dijkstra_origen_inexistente():
    w = _grilla(3)
    with pytest.raises(KeyError):
        dijkstra(w.grafo, 9999)
