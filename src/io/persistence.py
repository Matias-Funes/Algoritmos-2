"""Serialización de escenarios en el formato que consume scenario_loader."""

from __future__ import annotations

import copy
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def _leer(objeto: Any, atributo: str, alternativa: str | None = None) -> Any:
    if isinstance(objeto, dict):
        if atributo in objeto:
            return objeto[atributo]
        if alternativa is not None and alternativa in objeto:
            return objeto[alternativa]
    if hasattr(objeto, atributo):
        return getattr(objeto, atributo)
    if alternativa is not None and hasattr(objeto, alternativa):
        return getattr(objeto, alternativa)
    raise ValueError(f"No se puede serializar: falta '{atributo}'.")


def _coordenadas(ubicacion: Any, incluir_altura: bool = False) -> dict[str, int]:
    if isinstance(ubicacion, dict):
        coordenadas = {
            "x": int(ubicacion["x"]),
            "y": int(ubicacion["y"]),
        }
        if incluir_altura:
            coordenadas["z"] = int(ubicacion.get("z", 0))
        return coordenadas

    if not isinstance(ubicacion, (tuple, list)) or len(ubicacion) < 2:
        raise ValueError(f"Ubicación inválida para serializar: {ubicacion!r}.")
    coordenadas = {"x": int(ubicacion[0]), "y": int(ubicacion[1])}
    if incluir_altura:
        coordenadas["z"] = int(ubicacion[2]) if len(ubicacion) > 2 else 0
    return coordenadas


def _serializar_warehouse(warehouse: Any) -> dict[str, Any]:
    return {
        "dimensiones": {
            "ancho_x": warehouse.ancho_x,
            "largo_y": warehouse.largo_y,
        },
        "puertas": [
            {
                "id": puerta.id,
                "tipo": puerta.tipo,
                "ubicacion": {"x": puerta.x, "y": puerta.y},
            }
            for puerta in warehouse.puertas.values()
        ],
        "zonas_despacho": [
            {
                "id": zona.id,
                "puerta_id": zona.puerta_id,
                "ubicacion": {"x": zona.x, "y": zona.y},
                "ancho": zona.ancho,
                "alto": zona.alto,
                "peso_max_kg": zona.peso_max_kg,
            }
            for zona in warehouse.zonas.values()
        ],
        "racks": [
            {
                "id": rack.id,
                "ubicacion": {"x": rack.x, "y": rack.y},
                "ancho": rack.ancho,
                "alto": rack.alto,
            }
            for rack in warehouse.racks.values()
        ],
        "pasillos": [
            {
                "id": pasillo.id,
                "ubicacion": {"x": pasillo.x, "y": pasillo.y},
                "ancho": pasillo.ancho,
                "alto": pasillo.alto,
                "sentido": pasillo.sentido,
            }
            for pasillo in warehouse.pasillos.values()
        ],
    }


def _serializar_producto(producto: Any) -> dict[str, Any]:
    if isinstance(producto, dict):
        return copy.deepcopy(producto)
    return {
        "id": _leer(producto, "producto_id", "id"),
        "nombre": _leer(producto, "nombre"),
        "rack_id": _leer(producto, "rack_id"),
        "ubicacion": _coordenadas(
            _leer(producto, "ubicacion"), incluir_altura=True
        ),
        "cantidad_disponible": _leer(producto, "cantidad_disponible"),
        "peso_kg": _leer(producto, "peso_kg"),
    }


def _serializar_pedido(pedido: Any) -> dict[str, Any]:
    if isinstance(pedido, dict):
        return copy.deepcopy(pedido)

    items = _leer(pedido, "items")
    return {
        "id": _leer(pedido, "orden_id", "id"),
        "prioridad": _leer(pedido, "prioridad"),
        "estado": _leer(pedido, "estado"),
        "items": [
            {"producto_id": producto_id, "cantidad": cantidad}
            for producto_id, cantidad in items
        ],
    }


def _serializar_picker(picker: Any) -> dict[str, Any]:
    if isinstance(picker, dict):
        datos = copy.deepcopy(picker)
        for campo in (
            "posicion_actual",
            "carga_actual_kg",
            "items_transportados",
        ):
            datos.pop(campo, None)
        if "posicion_inicial" in datos:
            datos["posicion_inicial"] = _coordenadas(
                datos["posicion_inicial"]
            )
        return datos

    return {
        "id": _leer(picker, "id"),
        "posicion_inicial": _coordenadas(
            _leer(picker, "posicion_inicial")
        ),
        "capacidad_carga_kg": _leer(picker, "capacidad_carga_kg"),
    }


def crear_datos_escenario(
    warehouse: Any,
    productos: list[Any],
    pedidos: list[Any],
    pickers: list[Any],
    configuracion: dict[str, Any],
) -> dict[str, Any]:
    """Construye una copia JSON-serializable con el esquema del cargador.

    Acepta tanto registros crudos como los modelos de dominio. No incluye
    posiciones actuales, asignaciones ni métricas de una simulación en curso;
    esos datos pertenecen al formato separado de una partida guardada.
    """
    return {
        "warehouse": _serializar_warehouse(warehouse),
        "pickers": [_serializar_picker(picker) for picker in pickers],
        "productos": [_serializar_producto(producto) for producto in productos],
        "pedidos": [_serializar_pedido(pedido) for pedido in pedidos],
        "configuracion": copy.deepcopy(configuracion),
    }


def guardar_escenario(
    ruta_json: str | os.PathLike[str],
    warehouse: Any,
    productos_raw: list[Any],
    pedidos_raw: list[Any],
    pickers_raw: list[Any],
    config: dict[str, Any],
) -> None:
    """Guarda un escenario compatible con ``cargar_escenario``.

    La escritura se realiza primero en un temporal de la misma carpeta y se
    reemplaza el destino al terminar, para evitar dejar JSON truncados.
    """
    ruta = Path(ruta_json)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    datos = crear_datos_escenario(
        warehouse,
        productos_raw,
        pedidos_raw,
        pickers_raw,
        config,
    )

    temporal: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=ruta.parent,
            suffix=".tmp",
            delete=False,
        ) as archivo:
            temporal = archivo.name
            json.dump(datos, archivo, indent=2, ensure_ascii=False)
            archivo.write("\n")
        os.replace(temporal, ruta)
    finally:
        if temporal is not None and os.path.exists(temporal):
            os.unlink(temporal)

    print(f"Escenario guardado exitosamente en {ruta}")
