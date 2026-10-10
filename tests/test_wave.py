import pytest

from warehouse.dominio.estado_pedido import EstadoPedido
from warehouse.dominio.estado_wave import EstadoWave
from warehouse.dominio.pedido import Pedido
from warehouse.dominio.wave import Wave

# --- helpers ---


def pedido(pid: str, prioridad: int = 3, items: dict | None = None) -> Pedido:
    p = Pedido(id=pid, prioridad=prioridad)
    for prod, cant in (items or {}).items():
        p.agregar_item(prod, cant)
    return p


# --- construcción ---


def test_wave_vacia_por_defecto():
    w = Wave(id="W1")
    assert w.id == "W1"
    assert w.pedidos == []
    assert w.estado == EstadoWave.ABIERTA


def test_wave_max_pedidos_invalido_falla():
    with pytest.raises(ValueError):
        Wave(id="W1", max_pedidos=0)
    with pytest.raises(ValueError):
        Wave(id="W1", max_pedidos=-1)


def test_wave_max_productos_invalido_falla():
    with pytest.raises(ValueError):
        Wave(id="W1", max_productos=0)


def test_dos_waves_no_comparten_lista_de_pedidos():
    w1 = Wave(id="W1")
    w2 = Wave(id="W2")
    w1.agregar_pedido(pedido("P01"))
    assert w2.pedidos == []
    assert len(w1.pedidos) == 1


# --- agregar pedidos ---


def test_agregar_pedido_cambia_estado_del_pedido():
    p = pedido("P01")
    w = Wave(id="W1")
    w.agregar_pedido(p)
    assert p.estado == EstadoPedido.EN_WAVE


def test_no_puedo_pasar_max_pedidos():
    w = Wave(id="W1", max_pedidos=2)
    w.agregar_pedido(pedido("P01"))
    w.agregar_pedido(pedido("P02"))
    with pytest.raises(ValueError):
        w.agregar_pedido(pedido("P03"))


def test_no_puedo_pasar_max_productos():
    w = Wave(id="W1", max_pedidos=10, max_productos=5)
    w.agregar_pedido(pedido("P01", items={"A": 3}))
    # agregar uno con 3 productos más pasaría de 5
    with pytest.raises(ValueError):
        w.agregar_pedido(pedido("P02", items={"B": 3}))


def test_agregar_pedido_justo_en_el_limite():
    w = Wave(id="W1", max_pedidos=10, max_productos=5)
    w.agregar_pedido(pedido("P01", items={"A": 3}))
    w.agregar_pedido(pedido("P02", items={"B": 2}))  # 3+2 = 5, ok
    assert w.cantidad_productos() == 5


# --- puede_agregar no muta ---


def test_puede_agregar_no_modifica_nada():
    w = Wave(id="W1", max_pedidos=2)
    p = pedido("P01")
    assert w.puede_agregar(p) is True
    assert w.pedidos == []
    assert p.estado == EstadoPedido.PENDIENTE


def test_puede_agregar_falla_por_capacidad():
    w = Wave(id="W1", max_pedidos=1)
    w.agregar_pedido(pedido("P01"))
    assert w.puede_agregar(pedido("P02")) is False


def test_puede_agregar_falla_si_wave_cerrada():
    w = Wave(id="W1")
    w.cerrar()
    assert w.puede_agregar(pedido("P01")) is False


# --- consultas ---


def test_cantidad_pedidos():
    w = Wave(id="W1")
    w.agregar_pedido(pedido("P01"))
    w.agregar_pedido(pedido("P02"))
    assert w.cantidad_pedidos() == 2


def test_cantidad_productos():
    w = Wave(id="W1")
    w.agregar_pedido(pedido("P01", items={"A": 2, "B": 1}))
    w.agregar_pedido(pedido("P02", items={"C": 3}))
    assert w.cantidad_productos() == 6


def test_prioridad_maxima():
    w = Wave(id="W1")
    w.agregar_pedido(pedido("P01", prioridad=2))
    w.agregar_pedido(pedido("P02", prioridad=5))
    w.agregar_pedido(pedido("P03", prioridad=3))
    assert w.prioridad_maxima() == 5


def test_prioridad_maxima_wave_vacia():
    w = Wave(id="W1")
    assert w.prioridad_maxima() == 0


def test_ubicaciones_requeridas_union_sin_repetidos():
    w = Wave(id="W1")
    w.agregar_pedido(pedido("P01", items={"A": 1, "B": 2}))
    w.agregar_pedido(pedido("P02", items={"B": 1, "C": 1}))
    assert w.ubicaciones_requeridas() == {"A", "B", "C"}


# --- transiciones de estado ---


def test_cerrar_wave_abierta():
    w = Wave(id="W1")
    w.cerrar()
    assert w.estado == EstadoWave.CERRADA


def test_no_se_puede_cerrar_wave_ya_cerrada():
    w = Wave(id="W1")
    w.cerrar()
    with pytest.raises(ValueError):
        w.cerrar()


def test_iniciar_preparacion_marca_pedidos():
    w = Wave(id="W1")
    p1 = pedido("P01")
    p2 = pedido("P02")
    w.agregar_pedido(p1)
    w.agregar_pedido(p2)
    w.cerrar()
    w.iniciar_preparacion()
    assert w.estado == EstadoWave.EN_PREPARACION
    assert p1.estado == EstadoPedido.EN_PREPARACION
    assert p2.estado == EstadoPedido.EN_PREPARACION


def test_no_se_puede_iniciar_preparacion_sin_cerrar():
    w = Wave(id="W1")
    w.agregar_pedido(pedido("P01"))
    with pytest.raises(ValueError):
        w.iniciar_preparacion()


def test_completar_wave_marca_pedidos_preparados():
    w = Wave(id="W1")
    p1 = pedido("P01")
    w.agregar_pedido(p1)
    w.cerrar()
    w.iniciar_preparacion()
    w.completar()
    assert w.estado == EstadoWave.COMPLETADA
    assert p1.estado == EstadoPedido.PREPARADO


def test_no_se_puede_completar_sin_preparar():
    w = Wave(id="W1")
    w.agregar_pedido(pedido("P01"))
    w.cerrar()
    with pytest.raises(ValueError):
        w.completar()
