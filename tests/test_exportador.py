import json
from pathlib import Path

import pytest

from warehouse.generacion.generador import ConfigGeneracion, generar_escenario
from warehouse.io.cargador_json import cargar_escenario
from warehouse.io.exportador import escenario_a_dict, exportar_escenario


def test_exportar_escenario_crea_archivo(tmp_path):
    esc = generar_escenario(ConfigGeneracion(seed=42))
    out = tmp_path / "salida.json"
    exportar_escenario(esc, out)
    assert out.exists()


def test_dict_tiene_campos_esperados():
    esc = generar_escenario(ConfigGeneracion(seed=42))
    d = escenario_a_dict(esc)
    for campo in (
        "version",
        "nombre",
        "warehouse",
        "productos",
        "pedidos",
        "wave_config",
    ):
        assert campo in d
    for campo in ("ancho", "alto", "celdas_transitables", "racks"):
        assert campo in d["warehouse"]


def test_round_trip_generador_exportador_cargador(tmp_path):
    """Generar → exportar → cargar debe dar el mismo escenario."""
    esc_original = generar_escenario(ConfigGeneracion(seed=42, n_pedidos=5))
    out = tmp_path / "esc.json"
    exportar_escenario(esc_original, out)

    esc_cargado = cargar_escenario(out)

    # Dimensiones
    assert esc_cargado.warehouse.ancho == esc_original.warehouse.ancho
    assert esc_cargado.warehouse.alto == esc_original.warehouse.alto

    # Racks
    assert set(esc_cargado.warehouse.racks.keys()) == set(
        esc_original.warehouse.racks.keys()
    )

    # Productos
    assert set(esc_cargado.warehouse.productos.keys()) == set(
        esc_original.warehouse.productos.keys()
    )
    for pid in esc_original.warehouse.productos:
        p1 = esc_original.warehouse.productos[pid]
        p2 = esc_cargado.warehouse.productos[pid]
        assert p1.nombre == p2.nombre
        assert p1.rack_id == p2.rack_id
        assert p1.z == p2.z
        assert p1.stock == p2.stock

    # Pedidos
    assert len(esc_cargado.pedidos) == len(esc_original.pedidos)
    for p1, p2 in zip(esc_original.pedidos, esc_cargado.pedidos):
        assert p1.id == p2.id
        assert p1.prioridad == p2.prioridad
        assert p1.productos_ids() == p2.productos_ids()


def test_round_trip_mantiene_nodos_de_picking(tmp_path):
    """Los nodos de picking deben apuntar al mismo lugar tras round-trip."""
    esc_original = generar_escenario(ConfigGeneracion(seed=42))
    out = tmp_path / "esc.json"
    exportar_escenario(esc_original, out)

    esc_cargado = cargar_escenario(out)

    for pid, prod in esc_original.warehouse.productos.items():
        orig_nodo = prod.nodo_picking
        nuevo_nodo = esc_cargado.warehouse.productos[pid].nodo_picking

        pos_orig = esc_original.warehouse.grafo.nodo(orig_nodo).posicion
        pos_nuevo = esc_cargado.warehouse.grafo.nodo(nuevo_nodo).posicion
        assert pos_orig == pos_nuevo


def test_exportar_escenario_chico(tmp_path):
    """El chico.json cargado se puede exportar y recargar."""
    ruta = Path(__file__).parent.parent / "data" / "escenarios" / "chico.json"
    esc = cargar_escenario(ruta)
    out = tmp_path / "chico_re.json"
    exportar_escenario(esc, out)
    esc2 = cargar_escenario(out)
    assert set(esc2.warehouse.productos.keys()) == set(esc.warehouse.productos.keys())


def test_exportar_incluye_seed(tmp_path):
    """La seed de generación se preserva tras round-trip."""
    esc = generar_escenario(ConfigGeneracion(seed=42))
    out = tmp_path / "esc.json"
    exportar_escenario(esc, out)

    esc2 = cargar_escenario(out)
    assert esc2.seed == 42


def test_exportar_sin_seed(tmp_path):
    """Un escenario sin seed se exporta con seed=None."""
    esc = generar_escenario(ConfigGeneracion(seed=None))
    out = tmp_path / "esc.json"
    exportar_escenario(esc, out)

    esc2 = cargar_escenario(out)
    assert esc2.seed is None


def test_round_trip_con_waves_y_resultados(tmp_path):
    """Guardar y cargar un escenario con waves y resultados."""
    from warehouse.algoritmos.recorridos import recorrer_wave
    from warehouse.waves.generador_waves import EstrategiaWaves, generar_waves

    esc = generar_escenario(ConfigGeneracion(seed=42, n_pedidos=10))
    waves = generar_waves(
        esc.pedidos,
        esc.warehouse,
        max_pedidos=3,
        max_productos=20,
        estrategia=EstrategiaWaves.PRIORIDAD_Y_CERCANIA,
    )
    esc.waves = waves
    esc.resultados = {
        w.id: recorrer_wave(w, esc.warehouse, estrategia="vecino_mas_cercano")
        for w in waves
    }

    out = tmp_path / "esc.json"
    exportar_escenario(esc, out)
    esc2 = cargar_escenario(out)

    # Verificar waves
    assert len(esc2.waves) == len(esc.waves)
    assert {w.id for w in esc2.waves} == {w.id for w in esc.waves}
    for w1, w2 in zip(esc.waves, esc2.waves):
        assert w1.id == w2.id
        assert w1.estado == w2.estado
        assert {p.id for p in w1.pedidos} == {p.id for p in w2.pedidos}

    # Verificar resultados
    assert set(esc2.resultados.keys()) == set(esc.resultados.keys())
    for wid, r1 in esc.resultados.items():
        r2 = esc2.resultados[wid]
        assert r1.estrategia == r2.estrategia
        assert r1.camino_completo == r2.camino_completo
        assert r1.orden_paradas == r2.orden_paradas
        assert r1.distancia_total == r2.distancia_total
        assert r1.indices_de_paradas == r2.indices_de_paradas


def test_cargar_sin_waves_ni_resultados(tmp_path):
    """Un JSON sin waves ni resultados se carga como escenario fresco."""
    esc = generar_escenario(ConfigGeneracion(seed=42))
    out = tmp_path / "esc.json"
    exportar_escenario(esc, out)
    esc2 = cargar_escenario(out)
    assert esc2.waves == []
    assert esc2.resultados == {}


def test_exportar_incluye_sesion(tmp_path):
    """La sesión de simulación se preserva tras round-trip."""
    from warehouse.warehouse.escenario import Sesion

    esc = generar_escenario(ConfigGeneracion(seed=42, n_pedidos=10))
    esc.sesion = Sesion(
        wave_actual=2,
        indice_actual=15,
        estrategia_recorrido="orden_pedidos",
    )

    out = tmp_path / "esc.json"
    exportar_escenario(esc, out)
    esc2 = cargar_escenario(out)

    assert esc2.sesion is not None
    assert esc2.sesion.wave_actual == 2
    assert esc2.sesion.indice_actual == 15
    assert esc2.sesion.estrategia_recorrido == "orden_pedidos"


def test_exportar_sin_sesion(tmp_path):
    """Sin sesión, el JSON guarda null y al cargar queda None."""
    esc = generar_escenario(ConfigGeneracion(seed=42))
    esc.sesion = None

    out = tmp_path / "esc.json"
    exportar_escenario(esc, out)
    esc2 = cargar_escenario(out)

    assert esc2.sesion is None
