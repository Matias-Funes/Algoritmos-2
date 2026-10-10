import pytest

from warehouse.generacion.generador import (
    ConfigGeneracion,
    _calcular_ancho,
    _patron_columnas,
    generar_escenario,
)
from warehouse.generacion.validador import validar_escenario


def test_ancho_calculado():
    cfg = ConfigGeneracion(n_bloques_racks=4, ancho_pasillo=1, ancho_bloque_racks=2)
    assert _calcular_ancho(cfg) == 13


def test_patron_columnas():
    cfg = ConfigGeneracion(n_bloques_racks=2, ancho_pasillo=1, ancho_bloque_racks=2)
    assert _patron_columnas(cfg) == ["P", "R", "R", "P", "R", "R", "P"]


def test_generacion_default_es_valida():
    cfg = ConfigGeneracion(seed=42)
    esc = generar_escenario(cfg)
    validar_escenario(esc)  # no debe lanzar


def test_geometria_default():
    cfg = ConfigGeneracion(seed=42)
    esc = generar_escenario(cfg)
    w = esc.warehouse
    assert w.ancho == 13
    assert w.alto == 8
    # 8 columnas R * 6 filas intermedias = 48 racks
    assert len(w.racks) == 48


def test_productos_generados():
    cfg = ConfigGeneracion(seed=42, productos_por_rack=2)
    esc = generar_escenario(cfg)
    assert len(esc.warehouse.productos) == 48 * 2


def test_pedidos_generados():
    cfg = ConfigGeneracion(seed=42, n_pedidos=7, max_productos_por_pedido=3)
    esc = generar_escenario(cfg)
    assert len(esc.pedidos) == 7
    for ped in esc.pedidos:
        assert 1 <= len(ped.items) <= 3


def test_reproducibilidad_con_mismo_seed():
    cfg1 = ConfigGeneracion(seed=123)
    cfg2 = ConfigGeneracion(seed=123)
    e1 = generar_escenario(cfg1)
    e2 = generar_escenario(cfg2)

    assert e1.warehouse.ancho == e2.warehouse.ancho
    assert set(e1.warehouse.racks.keys()) == set(e2.warehouse.racks.keys())
    assert set(e1.warehouse.productos.keys()) == set(e2.warehouse.productos.keys())

    for pid in e1.warehouse.productos:
        p1 = e1.warehouse.productos[pid]
        p2 = e2.warehouse.productos[pid]
        assert p1.stock == p2.stock
        assert p1.rack_id == p2.rack_id
        assert p1.z == p2.z

    for ped1, ped2 in zip(e1.pedidos, e2.pedidos):
        assert ped1.prioridad == ped2.prioridad
        assert ped1.productos_ids() == ped2.productos_ids()


def test_seeds_distintos_dan_escenarios_distintos():
    e1 = generar_escenario(ConfigGeneracion(seed=1))
    e2 = generar_escenario(ConfigGeneracion(seed=2))
    # Al menos las prioridades deberían diferir en algún pedido
    prioridades_1 = [p.prioridad for p in e1.pedidos]
    prioridades_2 = [p.prioridad for p in e2.pedidos]
    assert prioridades_1 != prioridades_2


def test_todos_los_racks_tienen_pasillo_horizontal():
    cfg = ConfigGeneracion(seed=42)
    esc = generar_escenario(cfg)
    w = esc.warehouse
    for rack in w.racks.values():
        assert (rack.x - 1, rack.y) in w._nodo_por_xy or (
            rack.x + 1,
            rack.y,
        ) in w._nodo_por_xy


def test_config_invalida_falla():
    with pytest.raises(ValueError):
        ConfigGeneracion(n_bloques_racks=0)
    with pytest.raises(ValueError):
        ConfigGeneracion(alto=2)
    with pytest.raises(ValueError):
        ConfigGeneracion(stock_min=100, stock_max=10)
