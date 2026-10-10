from typing import Optional

from warehouse.dominio.posicion import Posicion
from warehouse.dominio.producto import Producto
from warehouse.dominio.puerta import Puerta
from warehouse.dominio.rack import Rack
from warehouse.dominio.tipo_nodo import TipoNodo
from warehouse.dominio.zona import ZonaDespacho
from warehouse.estructuras.grafo import Grafo


class Warehouse:
    def __init__(self, ancho: int, alto: int) -> None:
        self.ancho = ancho
        self.alto = alto

        self.grafo = Grafo()
        self.productos: dict[str, Producto] = {}
        self.racks: dict[str, Rack] = {}
        self.zonas: dict[str, ZonaDespacho] = {}
        self.puertas: dict[str, Puerta] = {}

        self._nodo_por_xy: dict[tuple[int, int], int] = {}
        self._racks_ocupados: set[tuple[int, int]] = set()

    # --- helpers de construcción ---
    def _nodo_en(
        self, x: int, y: int, tipo: TipoNodo, producto_id: Optional[str] = None
    ) -> int:
        key = (x, y)
        if key in self._nodo_por_xy:
            nid = self._nodo_por_xy[key]
            nodo = self.grafo.nodo(nid)
            # Promover PASILLO → tipo más específico (DESPACHO, PUERTA)
            if nodo.tipo == TipoNodo.PASILLO and tipo != TipoNodo.PASILLO:
                nodo.tipo = tipo
                if producto_id is not None:
                    nodo.producto_id = producto_id
            return nid
        nid = self.grafo.agregar_nodo(Posicion(x, y), tipo, producto_id)
        self._nodo_por_xy[key] = nid
        return nid

    def _conectar_vecinos(self) -> None:
        for (x, y), nid in self._nodo_por_xy.items():
            for dx, dy in ((1, 0), (0, 1)):
                vecino = self._nodo_por_xy.get((x + dx, y + dy))
                if vecino is not None:
                    self.grafo.agregar_arista(nid, vecino, peso=1.0)

    # --- construcción del grafo ---
    def construir_grafo(self, celdas_transitables: set[tuple[int, int]]) -> None:
        """Crea nodos PASILLO para cada (x, y) y conecta vecinos.
        Las celdas de racks NO deben estar acá."""
        for x, y in sorted(celdas_transitables):
            self._nodo_en(x, y, TipoNodo.PASILLO)
        self._conectar_vecinos()

    # --- racks ---
    def agregar_rack(self, rack_id: str, x: int, y: int) -> None:
        """Registra un rack como obstáculo físico. NO crea nodo en el grafo.
        La celda del rack no debe ser transitable."""
        if (x, y) in self._nodo_por_xy:
            raise ValueError(
                f"El rack {rack_id} en ({x}, {y}) choca con una celda transitable"
            )
        if (x, y) in self._racks_ocupados:
            raise ValueError(f"Ya hay un rack en ({x}, {y})")
        self.racks[rack_id] = Rack(rack_id, x, y)
        self._racks_ocupados.add((x, y))

    def _nodo_picking_de_rack(self, rack: Rack) -> Optional[int]:
        """Un rack se alcanza solo desde un pasillo vertical (mismo y, distinto x).
        Solo se consideran vecinos horizontales."""
        for dx in (-1, 1):
            vecino = self._nodo_por_xy.get((rack.x + dx, rack.y))
            if vecino is not None:
                return vecino
        return None

    # --- productos ---
    def agregar_producto(self, producto: Producto) -> None:
        if producto.rack_id not in self.racks:
            raise ValueError(
                f"El producto {producto.id} referencia rack inexistente: {producto.rack_id}"
            )
        rack = self.racks[producto.rack_id]
        nodo = self._nodo_picking_de_rack(rack)
        if nodo is None:
            raise ValueError(
                f"El rack {rack.id} en ({rack.x}, {rack.y}) no tiene pasillo adyacente"
            )
        producto.nodo_picking = nodo
        self.productos[producto.id] = producto

    # --- zonas y puertas ---
    def agregar_zona_despacho(
        self, zona_id: str, p1: tuple[int, int], p2: tuple[int, int]
    ) -> int:
        cx = (p1[0] + p2[0]) // 2
        cy = (p1[1] + p2[1]) // 2
        nid = self._nodo_en(cx, cy, TipoNodo.DESPACHO)
        self.zonas[zona_id] = ZonaDespacho(zona_id, p1, p2, nid)
        return nid

    def agregar_puerta(self, puerta_id: str, x: int, y: int, tipo: str) -> int:
        nid = self._nodo_en(x, y, TipoNodo.PUERTA)
        self.puertas[puerta_id] = Puerta(puerta_id, Posicion(x, y), tipo, nid)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            vecino = self._nodo_por_xy.get((x + dx, y + dy))
            if vecino is not None:
                self.grafo.agregar_arista(nid, vecino, peso=1.0)
        return nid
