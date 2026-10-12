import json
from pathlib import Path

from warehouse.dominio.item_pedido import ItemPedido
from warehouse.dominio.pedido import Pedido
from warehouse.dominio.producto import Producto
from warehouse.warehouse.escenario import Escenario, WaveConfig
from warehouse.warehouse.warehouse import Warehouse


class ErrorDeCarga(Exception):
    """Error al cargar un escenario desde JSON."""


# --- validaciones ---


def _validar_raiz(data: dict) -> None:
    for campo in ("version", "warehouse", "productos", "pedidos"):
        if campo not in data:
            raise ErrorDeCarga(f"Falta campo obligatorio: '{campo}'")


def _validar_warehouse(data_wh: dict, ancho: int, alto: int) -> None:
    for campo in ("ancho", "alto", "celdas_transitables", "racks"):
        if campo not in data_wh:
            raise ErrorDeCarga(f"Falta campo '{campo}' en warehouse")
    for celda in data_wh["celdas_transitables"]:
        if not (isinstance(celda, list) and len(celda) == 2):
            raise ErrorDeCarga(f"Celda inválida: {celda}")
        x, y = celda
        if not (0 <= x < ancho and 0 <= y < alto):
            raise ErrorDeCarga(f"Celda fuera de rango: {celda}")


# --- construcción ---


def _construir_warehouse(data_wh: dict) -> Warehouse:
    ancho = data_wh["ancho"]
    alto = data_wh["alto"]
    _validar_warehouse(data_wh, ancho, alto)

    w = Warehouse(ancho, alto)

    celdas = {(int(x), int(y)) for x, y in data_wh["celdas_transitables"]}
    w.construir_grafo(celdas)

    for r in data_wh["racks"]:
        try:
            w.agregar_rack(
                r["id"], int(r["x"]), int(r["y"]), niveles=int(r.get("niveles", 4))
            )
        except ValueError as e:
            raise ErrorDeCarga(str(e)) from e

    for z in data_wh.get("zonas_despacho", []):
        w.agregar_zona_despacho(z["id"], tuple(z["p1"]), tuple(z["p2"]))

    for p in data_wh.get("puertas", []):
        w.agregar_puerta(p["id"], int(p["x"]), int(p["y"]), p["tipo"])

    return w


def _construir_productos(data: list[dict], w: Warehouse) -> None:
    for p in data:
        for campo in ("id", "nombre", "rack_id", "z", "stock"):
            if campo not in p:
                raise ErrorDeCarga(f"Producto sin campo '{campo}': {p}")
        if p["id"] in w.productos:
            raise ErrorDeCarga(f"Producto duplicado: {p['id']}")
        producto = Producto(
            id=p["id"],
            nombre=p["nombre"],
            rack_id=p["rack_id"],
            z=int(p["z"]),
            stock=int(p["stock"]),
        )
        try:
            w.agregar_producto(producto)
        except ValueError as e:
            raise ErrorDeCarga(str(e)) from e


def _construir_pedidos(data: list[dict], w: Warehouse) -> list[Pedido]:
    pedidos: list[Pedido] = []
    for p in data:
        for campo in ("id", "prioridad", "items"):
            if campo not in p:
                raise ErrorDeCarga(f"Pedido sin campo '{campo}': {p}")
        pedido = Pedido(id=p["id"], prioridad=int(p["prioridad"]))
        for item in p["items"]:
            prod_id = item["producto_id"]
            if prod_id not in w.productos:
                raise ErrorDeCarga(
                    f"Pedido {p['id']} referencia producto inexistente: {prod_id}"
                )
            pedido.items.append(
                ItemPedido(producto_id=prod_id, cantidad=int(item["cantidad"]))
            )
        pedidos.append(pedido)
    return pedidos


# --- API pública ---


def cargar_escenario(path: str | Path) -> Escenario:
    path = Path(path)
    if not path.exists():
        raise ErrorDeCarga(f"No existe el archivo: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ErrorDeCarga(f"JSON inválido: {e}") from e

    _validar_raiz(data)

    w = _construir_warehouse(data["warehouse"])
    _construir_productos(data["productos"], w)
    pedidos = _construir_pedidos(data["pedidos"], w)

    cfg = data.get("wave_config", {})
    wave_config = WaveConfig(
        max_pedidos=int(cfg.get("max_pedidos", 3)),
        max_productos=int(cfg.get("max_productos", 20)),
    )

    return Escenario(
        nombre=data.get("nombre", path.stem),
        warehouse=w,
        pedidos=pedidos,
        wave_config=wave_config,
        seed=data.get("seed"),
    )
