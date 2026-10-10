from pathlib import Path

import pytest

from warehouse.dominio.tipo_nodo import TipoNodo
from warehouse.io.cargador_json import ErrorDeCarga, cargar_escenario

RUTA_CHICO = Path(__file__).parent.parent / "data" / "escenarios" / "chico.json"


@pytest.fixture
def escenario_chico():
    return cargar_escenario(RUTA_CHICO)


# --- carga feliz ---


def test_carga_nombre(escenario_chico):
    assert escenario_chico.nombre == "chico"


def test_warehouse_dimensiones(escenario_chico):
    assert escenario_chico.warehouse.ancho == 6
    assert escenario_chico.warehouse.alto == 4


def test_grafo_tiene_20_nodos(escenario_chico):
    # 6*4 - 4 racks = 20 celdas transitables
    assert len(escenario_chico.warehouse.grafo) == 20


def test_racks_no_estan_en_el_grafo(escenario_chico):
    w = escenario_chico.warehouse
    for rack in w.racks.values():
        assert (rack.x, rack.y) not in w._nodo_por_xy


def test_picking_es_un_pasillo_adyacente(escenario_chico):
    w = escenario_chico.warehouse
    for prod in w.productos.values():
        assert prod.nodo_picking >= 0
        nodo = w.grafo.nodo(prod.nodo_picking)
        assert nodo.tipo == TipoNodo.PASILLO

        rack = w.racks[prod.rack_id]
        dy = abs(nodo.posicion.y - rack.y)
        dx = abs(nodo.posicion.x - rack.x)
        assert (dx, dy) == (
            1,
            0,
        ), f"El picking de {prod.id} no es un pasillo horizontal adyacente"


def test_picking_de_p001_no_es_la_celda_del_rack(escenario_chico):
    w = escenario_chico.warehouse
    p001 = w.productos["P001"]
    r001 = w.racks["R001"]
    assert (r001.x, r001.y) not in w._nodo_por_xy
    nodo_picking = w.grafo.nodo(p001.nodo_picking)
    assert (nodo_picking.posicion.x, nodo_picking.posicion.y) != (r001.x, r001.y)


def test_racks_cargados(escenario_chico):
    assert set(escenario_chico.warehouse.racks.keys()) == {
        "R001",
        "R002",
        "R003",
        "R004",
    }


def test_productos_cargados(escenario_chico):
    prods = escenario_chico.warehouse.productos
    assert set(prods.keys()) == {"P001", "P002", "P003", "P004"}
    assert prods["P001"].nombre == "Caja chica"
    assert prods["P001"].stock == 20
    assert prods["P003"].z == 2


def test_zona_despacho_cargada(escenario_chico):
    assert "A" in escenario_chico.warehouse.zonas
    zona = escenario_chico.warehouse.zonas["A"]
    assert zona.p1 == (0, 0)
    assert zona.p2 == (1, 0)


def test_puerta_cargada(escenario_chico):
    assert "D1" in escenario_chico.warehouse.puertas
    p = escenario_chico.warehouse.puertas["D1"]
    assert p.tipo == "OUTBOUND"


def test_pedidos_cargados(escenario_chico):
    ids = [p.id for p in escenario_chico.pedidos]
    assert ids == ["PED01", "PED02"]
    assert escenario_chico.pedidos[0].prioridad == 5
    assert escenario_chico.pedidos[1].prioridad == 3


def test_items_de_pedido(escenario_chico):
    ped = escenario_chico.pedidos[0]
    assert ped.cantidad_total_productos() == 3
    assert ped.productos_ids() == {"P001", "P004"}


def test_wave_config(escenario_chico):
    cfg = escenario_chico.wave_config
    assert cfg.max_pedidos == 3
    assert cfg.max_productos == 20


# --- errores ---


def test_archivo_inexistente():
    with pytest.raises(ErrorDeCarga):
        cargar_escenario("/ruta/que/no/existe.json")


def test_json_invalido(tmp_path):
    f = tmp_path / "mal.json"
    f.write_text("{no es json", encoding="utf-8")
    with pytest.raises(ErrorDeCarga):
        cargar_escenario(f)


def test_falta_campo_obligatorio(tmp_path):
    f = tmp_path / "sin_pedidos.json"
    f.write_text('{"version":"1.0","warehouse":{},"productos":[]}', encoding="utf-8")
    with pytest.raises(ErrorDeCarga, match="pedidos"):
        cargar_escenario(f)


def _escribir_json(tmp_path, data: dict) -> Path:
    import json

    f = tmp_path / "esc.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    return f


def test_producto_referencia_rack_inexistente(tmp_path):
    data = {
        "version": "1.0",
        "warehouse": {
            "ancho": 3,
            "alto": 3,
            "celdas_transitables": [
                [0, 0],
                [1, 0],
                [2, 0],
                [0, 1],
                [1, 1],
                [2, 1],
                [0, 2],
                [1, 2],
                [2, 2],
            ],
            "racks": [],
        },
        "productos": [
            {"id": "P001", "nombre": "X", "rack_id": "NO_EXISTE", "z": 1, "stock": 1}
        ],
        "pedidos": [],
    }
    f = _escribir_json(tmp_path, data)
    with pytest.raises(ErrorDeCarga, match="NO_EXISTE"):
        cargar_escenario(f)


def test_pedido_referencia_producto_inexistente(tmp_path):
    data = {
        "version": "1.0",
        "warehouse": {
            "ancho": 3,
            "alto": 3,
            "celdas_transitables": [
                [0, 0],
                [1, 0],
                [2, 0],
                [0, 1],
                [2, 1],  # (1,1) es rack, no transitable
                [0, 2],
                [1, 2],
                [2, 2],
            ],
            "racks": [{"id": "R001", "x": 1, "y": 1}],
        },
        "productos": [
            {"id": "P001", "nombre": "X", "rack_id": "R001", "z": 1, "stock": 1}
        ],
        "pedidos": [
            {
                "id": "PED01",
                "prioridad": 3,
                "items": [{"producto_id": "NO_EXISTE", "cantidad": 1}],
            }
        ],
    }
    f = _escribir_json(tmp_path, data)
    with pytest.raises(ErrorDeCarga, match="NO_EXISTE"):
        cargar_escenario(f)


def test_celda_fuera_de_rango(tmp_path):
    data = {
        "version": "1.0",
        "warehouse": {
            "ancho": 3,
            "alto": 3,
            "celdas_transitables": [[99, 99]],
            "racks": [],
        },
        "productos": [],
        "pedidos": [],
    }
    f = _escribir_json(tmp_path, data)
    with pytest.raises(ErrorDeCarga, match="fuera de rango"):
        cargar_escenario(f)


def test_rack_sobre_celda_transitable_falla(tmp_path):
    data = {
        "version": "1.0",
        "warehouse": {
            "ancho": 3,
            "alto": 3,
            "celdas_transitables": [
                [0, 0],
                [1, 0],
                [2, 0],
                [0, 1],
                [1, 1],
                [2, 1],  # (1,1) está en transitables
                [0, 2],
                [1, 2],
                [2, 2],
            ],
            "racks": [{"id": "R001", "x": 1, "y": 1}],
        },
        "productos": [],
        "pedidos": [],
    }
    f = _escribir_json(tmp_path, data)
    with pytest.raises(ErrorDeCarga, match="choca"):
        cargar_escenario(f)
