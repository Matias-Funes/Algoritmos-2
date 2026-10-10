import pytest

from warehouse.dominio.estado_pedido import EstadoPedido
from warehouse.dominio.item_pedido import ItemPedido
from warehouse.dominio.pedido import Pedido

# --- ItemPedido ---


def test_item_pedido_valido():
    item = ItemPedido(producto_id="P001", cantidad=3)
    assert item.producto_id == "P001"
    assert item.cantidad == 3


def test_item_pedido_cantidad_cero_falla():
    with pytest.raises(ValueError):
        ItemPedido(producto_id="P001", cantidad=0)


def test_item_pedido_cantidad_negativa_falla():
    with pytest.raises(ValueError):
        ItemPedido(producto_id="P001", cantidad=-1)


# --- Pedido: construcción ---


def test_pedido_vacio_por_defecto():
    p = Pedido(id="P01")
    assert p.id == "P01"
    assert p.items == []
    assert p.prioridad == 3
    assert p.estado == EstadoPedido.PENDIENTE


def test_pedido_prioridad_valida_en_rango():
    for prioridad in (1, 2, 3, 4, 5):
        p = Pedido(id="P", prioridad=prioridad)
        assert p.prioridad == prioridad


def test_pedido_prioridad_fuera_de_rango_falla():
    with pytest.raises(ValueError):
        Pedido(id="P", prioridad=0)
    with pytest.raises(ValueError):
        Pedido(id="P", prioridad=6)


def test_pedido_prioridad_negativa_falla():
    with pytest.raises(ValueError):
        Pedido(id="P", prioridad=-1)


# --- Pedido: lista de items aislada entre instancias ---


def test_dos_pedidos_no_comparten_lista_de_items():
    p1 = Pedido(id="P01")
    p2 = Pedido(id="P02")
    p1.agregar_item("A", 1)
    assert p2.items == [], "p2 no debería tener items de p1"
    assert len(p1.items) == 1


# --- Pedido: agregar items ---


def test_agregar_item_nuevo():
    p = Pedido(id="P01")
    p.agregar_item("PROD_D", 2)
    assert len(p.items) == 1
    assert p.items[0].producto_id == "PROD_D"
    assert p.items[0].cantidad == 2


def test_agregar_item_consolida_cantidades():
    p = Pedido(id="P01")
    p.agregar_item("PROD_D", 2)
    p.agregar_item("PROD_D", 3)
    assert len(p.items) == 1
    assert p.items[0].cantidad == 5


def test_agregar_varios_productos_distintos():
    p = Pedido(id="P01")
    p.agregar_item("D", 1)
    p.agregar_item("G", 2)
    p.agregar_item("H", 3)
    assert len(p.items) == 3


# --- Pedido: consultas ---


def test_cantidad_total_productos():
    p = Pedido(id="P01")
    p.agregar_item("D", 1)
    p.agregar_item("G", 2)
    p.agregar_item("H", 3)
    assert p.cantidad_total_productos() == 6


def test_cantidad_total_productos_vacio():
    p = Pedido(id="P01")
    assert p.cantidad_total_productos() == 0


def test_productos_ids_sin_repetidos():
    p = Pedido(id="P01")
    p.agregar_item("D", 1)
    p.agregar_item("D", 5)  # se consolida
    p.agregar_item("G", 2)
    assert p.productos_ids() == {"D", "G"}


def test_tiene_producto():
    p = Pedido(id="P01")
    p.agregar_item("D", 1)
    assert p.tiene_producto("D") is True
    assert p.tiene_producto("X") is False
