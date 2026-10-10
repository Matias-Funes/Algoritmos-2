import pytest

from warehouse.dominio.posicion import Posicion
from warehouse.dominio.producto import Producto
from warehouse.dominio.tipo_nodo import TipoNodo
from warehouse.warehouse.warehouse import Warehouse


def _warehouse_10x10() -> Warehouse:
    w = Warehouse(10, 10)
    w.construir_grafo({(x, y) for x in range(10) for y in range(10)})
    return w


def test_grilla_10x10_tiene_100_nodos():
    w = _warehouse_10x10()
    assert len(w.grafo) == 100


def test_nodo_0_es_la_esquina():
    w = _warehouse_10x10()
    assert w.grafo.nodo(0).posicion == Posicion(0, 0)


def test_esquina_tiene_2_vecinos():
    w = _warehouse_10x10()
    assert len(w.grafo.vecinos(0)) == 2


def test_borde_tiene_3_vecinos():
    w = _warehouse_10x10()
    # (5, 0) está en el borde inferior
    nid = w._nodo_por_xy[(5, 0)]
    assert len(w.grafo.vecinos(nid)) == 3


def test_interior_tiene_4_vecinos():
    w = _warehouse_10x10()
    nid = w._nodo_por_xy[(5, 5)]
    assert len(w.grafo.vecinos(nid)) == 4


def test_no_hay_aristas_duplicadas():
    w = _warehouse_10x10()
    nid = w._nodo_por_xy[(5, 5)]
    destinos = [a.destino for a in w.grafo.vecinos(nid)]
    assert len(destinos) == len(set(destinos))


def test_conectar_grilla_incompleta():
    """Si solo hay dos celdas contiguas, deben quedar conectadas."""
    w = Warehouse(10, 10)
    w.construir_grafo({(0, 0), (1, 0)})
    assert len(w.grafo) == 2
    assert len(w.grafo.vecinos(0)) == 1
    assert len(w.grafo.vecinos(1)) == 1


def test_zona_despacho_sobre_pasillo_promueve_el_tipo():
    w = Warehouse(5, 5)
    w.construir_grafo({(x, y) for x in range(5) for y in range(5)})

    w.agregar_zona_despacho("A", (1, 1), (3, 3))

    # El centro de la zona (2, 2) es el nodo representativo
    nid = w.zonas["A"].nodo_representativo
    assert w.grafo.nodo(nid).tipo == TipoNodo.DESPACHO


def test_rack_no_crea_nodo_en_el_grafo():
    w = Warehouse(5, 5)
    w.construir_grafo({(0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (2, 1)})
    n_antes = len(w.grafo)
    w.agregar_rack("R001", 2, 2)  # celda que no era transitable
    assert len(w.grafo) == n_antes
    assert (2, 2) not in w._nodo_por_xy


def test_rack_sobre_celda_transitable_falla():
    w = Warehouse(5, 5)
    w.construir_grafo({(0, 0), (1, 0), (2, 0)})
    with pytest.raises(ValueError, match="choca"):
        w.agregar_rack("R001", 1, 0)


def test_dos_racks_en_la_misma_celda_falla():
    w = Warehouse(5, 5)
    w.construir_grafo({(0, 0), (1, 0), (2, 0)})
    w.agregar_rack("R001", 2, 2)
    with pytest.raises(ValueError, match="Ya hay un rack"):
        w.agregar_rack("R002", 2, 2)


def test_producto_sin_pasillo_adyacente_falla():
    w = Warehouse(5, 5)
    w.construir_grafo({(0, 0)})  # una sola celda transitable
    w.agregar_rack("R001", 4, 4)  # rack lejos de todo
    p = Producto(id="P001", nombre="X", rack_id="R001", z=1, stock=1)
    with pytest.raises(ValueError, match="pasillo adyacente"):
        w.agregar_producto(p)


def test_picking_es_vecino_horizontal_del_rack():
    w = Warehouse(5, 5)
    transitables = {(x, y) for x in range(5) for y in range(5) if (x, y) != (2, 2)}
    w.construir_grafo(transitables)
    w.agregar_rack("R001", 2, 2)
    p = Producto(id="P001", nombre="X", rack_id="R001", z=1, stock=1)
    w.agregar_producto(p)

    nodo = w.grafo.nodo(p.nodo_picking)
    assert abs(nodo.posicion.x - 2) == 1
    assert nodo.posicion.y == 2


def test_rack_sin_pasillo_horizontal_no_tiene_picking():
    """Un rack cuyo único vecino es vertical NO puede tener picking."""
    w = Warehouse(5, 5)
    transitables = {(2, 0), (2, 1), (2, 3), (2, 4)}  # columna vertical
    w.construir_grafo(transitables)
    w.agregar_rack("R001", 2, 2)  # vecinos (2,1) y (2,3)
    p = Producto(id="P001", nombre="X", rack_id="R001", z=1, stock=1)
    import pytest

    with pytest.raises(ValueError, match="pasillo adyacente"):
        w.agregar_producto(p)


def test_picking_es_determinista():
    """Con múltiples pasillos adyacentes, el elegido debe ser siempre el mismo."""
    w1 = Warehouse(5, 5)
    w2 = Warehouse(5, 5)
    transitables = {(x, y) for x in range(5) for y in range(5) if (x, y) != (2, 2)}
    for w in (w1, w2):
        w.construir_grafo(transitables)
        w.agregar_rack("R001", 2, 2)
        w.agregar_producto(
            Producto(id="P001", nombre="X", rack_id="R001", z=1, stock=1)
        )
    assert w1.productos["P001"].nodo_picking == w2.productos["P001"].nodo_picking
