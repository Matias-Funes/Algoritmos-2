import pytest

from warehouse.algoritmos.busqueda import bfs_alcanzables
from warehouse.warehouse.warehouse import Warehouse


def _grilla(n: int) -> Warehouse:
    w = Warehouse(n, n)
    w.construir_grafo({(x, y) for x in range(n) for y in range(n)})
    return w


def test_bfs_alcanza_toda_la_grilla():
    w = _grilla(3)
    assert len(bfs_alcanzables(w.grafo, 0)) == 9


def test_bfs_desde_una_esquina_alcanza_la_opuesta():
    w = _grilla(4)
    esquina_inf = w._nodo_por_xy[(0, 0)]
    esquina_sup = w._nodo_por_xy[(3, 3)]
    assert esquina_sup in bfs_alcanzables(w.grafo, esquina_inf)


def test_bfs_en_nodo_aislado():
    w = Warehouse(5, 5)
    w.construir_grafo({(0, 0), (4, 4)})  # no adyacentes
    n0 = w._nodo_por_xy[(0, 0)]
    n1 = w._nodo_por_xy[(4, 4)]
    assert bfs_alcanzables(w.grafo, n0) == {n0}
    assert bfs_alcanzables(w.grafo, n1) == {n1}


def test_bfs_no_atraviesa_huecos():
    # Grilla 3x3 con el centro bloqueado (no está en transitables)
    w = Warehouse(3, 3)
    transitables = {(x, y) for x in range(3) for y in range(3) if (x, y) != (1, 1)}
    w.construir_grafo(transitables)

    n00 = w._nodo_por_xy[(0, 0)]
    n22 = w._nodo_por_xy[(2, 2)]
    # El centro bloqueado no impide rodear, así que igual se alcanzan
    # pero BFS no debe incluir (1,1) porque no está en el grafo
    alcanzables = bfs_alcanzables(w.grafo, n00)
    assert n22 in alcanzables
    assert (1, 1) not in w._nodo_por_xy


def test_bfs_origen_inexistente():
    w = _grilla(3)
    with pytest.raises(KeyError):
        bfs_alcanzables(w.grafo, 9999)
