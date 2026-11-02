import pytest

from warehouse.dominio.pedido import Pedido
from warehouse.dominio.producto import Producto
from warehouse.generacion.generador import ConfigGeneracion, generar_escenario
from warehouse.generacion.validador_cobertura import validar_cobertura_waves
from warehouse.waves.generador_waves import EstrategiaWaves, generar_waves_con_split


def _escenario(seed=42, n_pedidos=10, max_prod_pedido=3):
    cfg = ConfigGeneracion(
        seed=seed, n_pedidos=n_pedidos, max_productos_por_pedido=max_prod_pedido
    )
    return generar_escenario(cfg)


def test_split_cobertura_exacta():
    esc = _escenario(n_pedidos=10)
    waves, items_por_wave = generar_waves_con_split(
        esc.pedidos,
        esc.warehouse,
        max_pedidos=3,
        max_productos=10,
        max_peso_kg=500.0,
    )
    validar_cobertura_waves(esc.pedidos, items_por_wave)  # no lanza
    # Cada wave tiene al menos 1 item
    for wid, items in items_por_wave.items():
        assert len(items) >= 1


def test_split_pedido_grande_se_parte():
    """Un pedido con más items que max_productos_wave DEBE partirse."""
    esc = _escenario(n_pedidos=1, max_prod_pedido=10)
    waves, items_por_wave = generar_waves_con_split(
        esc.pedidos,
        esc.warehouse,
        max_pedidos=3,
        max_productos=4,
        max_peso_kg=500.0,
    )
    assert len(waves) >= 2
    validar_cobertura_waves(esc.pedidos, items_por_wave)


def test_split_cantidad_de_item():
    """Un item con cantidad > max_productos se parte por unidades."""
    esc = _escenario(n_pedidos=1, max_prod_pedido=1)
    # Forzar cantidad alta en el único item
    esc.pedidos[0].items[0].cantidad = 25
    waves, items_por_wave = generar_waves_con_split(
        esc.pedidos,
        esc.warehouse,
        max_pedidos=1,
        max_productos=10,
        max_peso_kg=1e6,
    )
    assert len(waves) >= 3  # 25 unidades / 10 por wave
    for items in items_por_wave.values():
        assert sum(i.cantidad for i in items) <= 10
    validar_cobertura_waves(esc.pedidos, items_por_wave)


def test_split_pedidos_vacios():
    waves, items_por_wave = generar_waves_con_split(
        [],
        generar_escenario(ConfigGeneracion(seed=1)).warehouse,
        max_pedidos=3,
        max_productos=10,
        max_peso_kg=500.0,
    )
    assert waves == []
    assert items_por_wave == {}


def test_split_peso_unitario_imposible_falla():
    """Si un producto pesa más que max_peso_kg, no se puede generar."""
    esc = _escenario(n_pedidos=1, max_prod_pedido=1)
    # Asegurar que el producto del pedido pese más que el límite
    pid = esc.pedidos[0].items[0].producto_id
    esc.warehouse.productos[pid].peso_kg = 999.0
    with pytest.raises(ValueError, match="(?i)no se pudo"):
        generar_waves_con_split(
            esc.pedidos,
            esc.warehouse,
            max_pedidos=3,
            max_productos=10,
            max_peso_kg=100.0,
        )


def test_split_prioridad_ordena_por_prioridad():
    esc = _escenario(n_pedidos=5, max_prod_pedido=1)
    waves, _ = generar_waves_con_split(
        esc.pedidos,
        esc.warehouse,
        max_pedidos=1,
        max_productos=5,
        max_peso_kg=500.0,
        estrategia=EstrategiaWaves.PRIORIDAD,
    )
    # Primera wave debe tener el pedido más prioritario
    mas_prio = max(esc.pedidos, key=lambda p: (p.prioridad, -int(p.id[3:])))
    assert waves[0].pedidos[0].id == mas_prio.id


def test_split_validador_detecta_faltantes():
    esc = _escenario(n_pedidos=2, max_prod_pedido=1)
    waves, items_por_wave = generar_waves_con_split(
        esc.pedidos,
        esc.warehouse,
        max_pedidos=3,
        max_productos=10,
        max_peso_kg=500.0,
    )
    # Corromper: quitar un item
    primer_wid = next(iter(items_por_wave))
    items_por_wave[primer_wid].pop()
    with pytest.raises(ValueError, match="incompleta"):
        validar_cobertura_waves(esc.pedidos, items_por_wave)


def test_split_validador_detecta_sobrantes():
    esc = _escenario(n_pedidos=1, max_prod_pedido=1)
    waves, items_por_wave = generar_waves_con_split(
        esc.pedidos,
        esc.warehouse,
        max_pedidos=3,
        max_productos=10,
        max_peso_kg=500.0,
    )
    # Duplicar cantidad
    wid = next(iter(items_por_wave))
    items_por_wave[wid][0].cantidad += 5
    with pytest.raises(ValueError, match="excedida"):
        validar_cobertura_waves(esc.pedidos, items_por_wave)
