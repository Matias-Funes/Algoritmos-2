"""Motor paso a paso para el movimiento y la recolección de pickers.

La clase mantiene el estado temporal de la simulación y coordina los
movimientos en sincronía. Puede ejecutar rutas ya preparadas o planificar
tramos dinámicos entre racks y zonas de despacho.
"""

from __future__ import annotations

import heapq
import sys
from math import floor
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.inventory import Producto
from src.core.picker import Picker

# Un picker bloqueado esta cantidad de ticks, y cuyos bloqueadores tambien estan
# parados, se considera atascado y alguien del grupo cede el paso.
TICKS_ATASCO = 3


class Simulation:
    def __init__(
        self,
        warehouse: Any,
        pickers: list[Any],
        rutas: Any = None,
        productos: Any = None,
        pedidos: Any = None,
        inventario: Any = None,
        asignaciones: dict[str, Any] | None = None,
        cache_distancias: Any = None,
        puntos_despacho: dict[str, list[tuple[int, int]]] | None = None,
        estrategia_recorrido: str = "Vecino más cercano (B)"
    ) -> None:
        self.estrategia_recorrido = estrategia_recorrido
        self.warehouse = warehouse
        self.pickers = [
            self._crear_picker(picker) for picker in pickers
        ]
        self.paso_actual = 0
        self._rutas = {
            picker.id: self._obtener_ruta(
                rutas, picker, indice, len(self.pickers) == 1
            )
            for indice, picker in enumerate(self.pickers)
        }
        self._indices_ruta = {
            picker.id: (
                1
                if self._rutas[picker.id]
                and self._rutas[picker.id][0] == tuple(picker.posicion_actual)
                else 0
            )
            for picker in self.pickers
        }
        self._productos = self._indexar_productos(productos, inventario)
        self._demanda_por_picker: dict[str, dict[str, int]] = {}
        self._demanda_global: dict[str, int] = {}
        self._asignaciones_explicitas = asignaciones is not None
        self._cargar_demanda(pedidos, asignaciones)
        self._demanda_global_inicial = dict(self._demanda_global)
        self._demanda_por_picker_inicial = {
            picker_id: dict(demanda)
            for picker_id, demanda in self._demanda_por_picker.items()
        }
        self._total_productos = sum(self._demanda_global.values()) + sum(
            sum(demanda.values())
            for demanda in self._demanda_por_picker.values()
        )
        self._modo_dinamico = (
            cache_distancias is not None or puntos_despacho is not None
        )
        if self._modo_dinamico and (
            cache_distancias is None or puntos_despacho is None
        ):
            raise ValueError(
                "La navegación dinámica requiere caché de distancias y "
                "puntos de despacho."
            )
        self._cache_distancias = cache_distancias
        self._puntos_despacho = {
            zona_id: list(dict.fromkeys(tuple(punto) for punto in puntos))
            for zona_id, puntos in (puntos_despacho or {}).items()
        }
        self._celdas_recoleccion_cache: dict[
            int, tuple[tuple[int, int], ...]
        ] = {}
        self._ticks_bloqueado = {
            picker.id: 0 for picker in self.pickers
        }
        self.productos_recogidos: list[dict[str, Any]] = []
        self.productos_faltantes: list[dict[str, Any]] = []
        self.descargas: list[dict[str, Any]] = []
        self._cantidad_productos_recogidos = 0
        self._cantidad_productos_despachados = 0
        self.distancia = 0
        self.ultima_altura = 0  # <--- NUEVO: Variable para las métricas
        self._en_ejecucion = False
        self._stock_inicial = {
            producto_id: self._valor(
                producto, "cantidad_disponible", default=None
            )
            for producto_id, producto in self._productos.items()
        }
        self._estado_inicial = {
            picker.id: {
                "posicion": tuple(picker.posicion_actual),
                "carga": picker.carga_actual_kg,
                "items": list(picker.items_transportados),
            }
            for picker in self.pickers
        }
        if self._modo_dinamico:
            if self._total_productos and not self._puntos_despacho:
                raise ValueError(
                    "La simulación necesita al menos un punto de despacho "
                    "accesible para recoger productos."
                )
            self._inicializar_navegacion_dinamica()
        else:
            self._recoger_en_posiciones_actuales()

    @staticmethod
    def _crear_picker(picker: Any) -> Any:
        if not isinstance(picker, dict):
            return picker
        ubicacion = picker["posicion_inicial"]
        if isinstance(ubicacion, dict):
            ubicacion = (ubicacion["x"], ubicacion["y"])

        # Lee la prioridad desde el JSON
        prioridad = picker.get("prioridad", 1)

        return Picker(
            picker.get("id", picker.get("picker_id")),
            tuple(ubicacion),
            picker["capacidad_carga_kg"],
            prioridad=prioridad
        )

    @staticmethod
    def _obtener_ruta(
        rutas: Any, picker: Any, indice: int, es_unico_picker: bool
    ) -> list[tuple[int, int]]:
        if rutas is None:
            ruta = []
        elif isinstance(rutas, dict):
            ruta = rutas.get(picker.id, rutas.get(indice, []))
        elif not rutas:
            ruta = []
        elif rutas and all(
            isinstance(punto, (tuple, list)) and len(punto) == 2
            for punto in rutas
        ):
            ruta = rutas if es_unico_picker or indice == 0 else []
        else:
            ruta = rutas[indice] if indice < len(rutas) else []

        resultado = []
        for punto in ruta:
            if not isinstance(punto, (tuple, list)) or len(punto) != 2:
                raise ValueError(f"Coordenada de ruta inválida: {punto!r}.")
            resultado.append((int(punto[0]), int(punto[1])))
        return resultado

    @staticmethod
    def _indexar_productos(productos: Any, inventario: Any) -> dict[str, Any]:
        if productos is None and inventario is not None:
            if hasattr(inventario, "todos_los_productos"):
                productos = inventario.todos_los_productos()
            elif isinstance(inventario, dict):
                productos = inventario
        if productos is None:
            return {}
        if hasattr(productos, "todos_los_productos"):
            productos = productos.todos_los_productos()
        if isinstance(productos, dict):
            elementos = []
            for producto_id, producto in productos.items():
                elementos.append(
                    producto
                    if not isinstance(producto, dict)
                    else Simulation._crear_producto(producto, producto_id)
                )
        else:
            elementos = [
                Simulation._crear_producto(producto)
                if isinstance(producto, dict)
                else producto
                for producto in productos
            ]
        return {
            str(Simulation._valor(producto, "producto_id", "id")): producto
            for producto in elementos
        }

    @staticmethod
    def _crear_producto(datos: dict[str, Any], producto_id: Any = None) -> Producto:
        ubicacion = datos["ubicacion"]
        if isinstance(ubicacion, dict):
            ubicacion = (
                ubicacion["x"],
                ubicacion["y"],
                ubicacion.get("z", 0),
            )
        return Producto(
            str(datos.get("producto_id", datos.get("id", producto_id))),
            datos.get("nombre", ""),
            datos.get("rack_id", ""),
            tuple(ubicacion),
            datos.get("cantidad_disponible", 0),
            datos.get("peso_kg", 0.0),
        )

    @staticmethod
    def _valor(objeto: Any, *nombres: str, default: Any = None) -> Any:
        for nombre in nombres:
            if isinstance(objeto, dict) and nombre in objeto:
                return objeto[nombre]
            if hasattr(objeto, nombre):
                return getattr(objeto, nombre)
        return default

    @staticmethod
    def _items_de_pedido(pedido: Any) -> list[tuple[str, int]]:
        items = Simulation._valor(pedido, "items", default=[])
        normalizados = []
        for item in items:
            if isinstance(item, dict):
                producto_id = item.get("producto_id", item.get("id"))
                cantidad = item.get("cantidad", 1)
            else:
                producto_id, cantidad = item
            if (
                producto_id is None
                or not isinstance(cantidad, int)
                or isinstance(cantidad, bool)
                or cantidad <= 0
            ):
                raise ValueError(f"Item de pedido inválido: {item!r}.")
            normalizados.append((str(producto_id), cantidad))
        return normalizados

    def _cargar_demanda(self, pedidos: Any, asignaciones: dict[str, Any] | None) -> None:
        if pedidos is not None and asignaciones is None:
            lista_pedidos = getattr(pedidos, "pedidos", pedidos)
            if isinstance(lista_pedidos, dict):
                lista_pedidos = list(lista_pedidos.values())
            for pedido in lista_pedidos:
                for producto_id, cantidad in self._items_de_pedido(pedido):
                    self._demanda_global[producto_id] = (
                        self._demanda_global.get(producto_id, 0) + cantidad
                    )

        if asignaciones is not None:
            for picker_id, asignados in asignaciones.items():
                pedidos_picker = getattr(asignados, "pedidos", asignados)
                if isinstance(pedidos_picker, dict):
                    pedidos_picker = list(pedidos_picker.values())
                demanda: dict[str, int] = {}
                for asignado in pedidos_picker:
                    if isinstance(asignado, dict) and (
                        "producto_id" in asignado or "id" in asignado
                    ):
                        pedido_items = self._items_de_pedido(
                            {"items": [asignado]}
                        )
                    elif isinstance(asignado, (tuple, list)) and len(asignado) == 2:
                        pedido_items = [(str(asignado[0]), asignado[1])]
                    else:
                        pedido_items = self._items_de_pedido(asignado)
                    for producto_id, cantidad in pedido_items:
                        demanda[producto_id] = demanda.get(producto_id, 0) + cantidad
                self._demanda_por_picker[str(picker_id)] = demanda

    def _celda_recoleccion(self, producto: Any) -> tuple[int, int]:
        ubicacion = self._valor(producto, "ubicacion")
        if isinstance(ubicacion, dict):
            x, y = int(ubicacion["x"]), int(ubicacion["y"])
        else:
            x, y = int(ubicacion[0]), int(ubicacion[1])

        if self.warehouse is None or not hasattr(self.warehouse, "grid"):
            return x, y
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if (
                0 <= nx < self.warehouse.ancho_x
                and 0 <= ny < self.warehouse.largo_y
                and self.warehouse.grid[ny][nx].tipo == "PASILLO"
            ):
                return nx, ny
        return x, y

    def _cantidad_pendiente(self, picker: Any, producto_id: str) -> int:
        if self._asignaciones_explicitas:
            return self._demanda_por_picker.get(picker.id, {}).get(producto_id, 0)
        return self._demanda_global.get(producto_id, 0)

    def _reducir_demanda(self, picker: Any, producto_id: str, cantidad: int) -> None:
        demanda = (
            self._demanda_por_picker.setdefault(picker.id, {})
            if self._asignaciones_explicitas
            else self._demanda_global
        )
        restante = demanda.get(producto_id, 0) - cantidad
        if restante > 0:
            demanda[producto_id] = restante
        else:
            demanda.pop(producto_id, None)

    def _recoger_en_posicion(self, picker: Any) -> None:
        posicion = tuple(picker.posicion_actual)
        for producto_id, producto in self._productos.items():
            cantidad = self._cantidad_pendiente(picker, producto_id)
            if not cantidad or self._celda_recoleccion(producto) != posicion:
                continue
            stock = self._valor(producto, "cantidad_disponible", default=None)
            if stock is not None and cantidad > stock:
                raise ValueError(
                    f"Stock insuficiente para '{producto_id}': "
                    f"disponible {stock}, pedido {cantidad}."
                )

            if hasattr(picker, "recoger"):
                picker.recoger(producto, cantidad)
            else:
                peso = float(self._valor(producto, "peso_kg", default=0.0))
                picker.carga_actual_kg = getattr(picker, "carga_actual_kg", 0.0) + (
                    peso * cantidad
                )

            # --- CÁLCULO DE ALTURA (Z) ---
            ubicacion = self._valor(producto, "ubicacion")
            z = int(ubicacion[2]) if len(ubicacion) > 2 else 1
            pasos_por_altura = z * 2

            self.distancia += pasos_por_altura
            self.paso_actual += pasos_por_altura
            self.ultima_altura = z  # <--- NUEVO: Guardamos para la métrica

            picker.tiempo_recoleccion = 5
            picker.info_recoleccion = f"Nivel {z}"
            # ------------------------------

            if stock is not None:
                producto.cantidad_disponible -= cantidad
            self._reducir_demanda(picker, producto_id, cantidad)
            self.productos_recogidos.append(
                {
                    "picker_id": picker.id,
                    "producto_id": producto_id,
                    "cantidad": cantidad,
                }
            )
            self._cantidad_productos_recogidos += cantidad

    def _recoger_en_posiciones_actuales(self) -> None:
        for picker in self.pickers:
            self._recoger_en_posicion(picker)

    def _inicializar_navegacion_dinamica(self) -> None:
        self._tramos_dinamicos: dict[str, list[tuple[int, int]]] = {
            picker.id: [] for picker in self.pickers
        }
        self._objetivos_dinamicos: dict[str, dict[str, Any] | None] = {
            picker.id: None for picker in self.pickers
        }
        self._estado_picker: dict[str, str] = {
            picker.id: "activo" for picker in self.pickers
        }
        self._ticks_bloqueado = {
            picker.id: 0 for picker in self.pickers
        }
        self._ticks_sin_movimiento = 0
        self._rutas = {
            picker.id: [tuple(picker.posicion_actual)]
            for picker in self.pickers
        }
        self._indices_ruta = {picker.id: 0 for picker in self.pickers}

        for picker in self.pickers:
            self._planificar_picker_dinamico(picker)
            picker.tiempo_recoleccion = 0

    def _celdas_recoleccion(self, producto: Any) -> list[tuple[int, int]]:
        cache_key = id(producto)
        if cache_key in self._celdas_recoleccion_cache:
            return list(self._celdas_recoleccion_cache[cache_key])

        ubicacion = self._valor(producto, "ubicacion")
        if isinstance(ubicacion, dict):
            x, y = int(ubicacion["x"]), int(ubicacion["y"])
        else:
            x, y = int(ubicacion[0]), int(ubicacion[1])

        if self.warehouse is None or not hasattr(self.warehouse, "grid"):
            puntos = [(x, y)]
            self._celdas_recoleccion_cache[cache_key] = tuple(puntos)
            return puntos

        puntos = []
        if self.warehouse.grid[y][x].es_transitable():
            puntos.append((x, y))
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if (
                0 <= nx < self.warehouse.ancho_x
                and 0 <= ny < self.warehouse.largo_y
                and self.warehouse.grid[ny][nx].es_transitable()
            ):
                puntos.append((nx, ny))
        puntos = list(dict.fromkeys(puntos))
        self._celdas_recoleccion_cache[cache_key] = tuple(puntos)
        return puntos

    def _registrar_faltante(
        self,
        picker: Any,
        producto_id: str,
        cantidad: int,
        motivo: str,
    ) -> None:
        if cantidad <= 0:
            return
        self.productos_faltantes.append(
            {
                "picker_id": picker.id,
                "producto_id": producto_id,
                "cantidad": cantidad,
                "motivo": motivo,
            }
        )
        self._reducir_demanda(picker, producto_id, cantidad)

    def _ruta_mas_cercana(
        self,
        picker: Any,
        origen: tuple[int, int],
        destinos: list[tuple[int, int]],
        busqueda: tuple[
            tuple[int, int],
            dict[tuple[int, int], float],
            dict[tuple[int, int], tuple[int, int]],
        ] | None = None,
    ) -> tuple[float, tuple[int, int]] | None:
        if busqueda is None:
            busqueda = self._calcular_distancias_con_picker(picker, origen)
        mejor: tuple[float, tuple[int, int]] | None = None
        for destino in destinos:
            if busqueda is None:
                distancia = self._cache_distancias.distancia(origen, destino)
            else:
                distancia = busqueda[1].get(destino, float("inf"))
            if distancia == float("inf"):
                continue
            candidato = (distancia, destino)
            if mejor is None or candidato < mejor:
                mejor = candidato
        return mejor

    def _calcular_distancias_con_picker(
        self,
        picker: Any,
        origen: tuple[int, int] | None = None,
        destinos: set[tuple[int, int]] | None = None,
    ) -> tuple[
        tuple[int, int],
        dict[tuple[int, int], float],
        dict[tuple[int, int], tuple[int, int]],
    ] | None:
        """Calcula una búsqueda desde el picker para todos los destinos."""
        origen = (
            tuple(picker.posicion_actual) if origen is None else tuple(origen)
        )
        grafo = getattr(self._cache_distancias, "_grafo", None)
        if grafo is None:
            return None

        bloqueadas = {
            tuple(otro.posicion_actual)
            for otro in self.pickers
            if otro.id != picker.id
            and self._estado_picker.get(otro.id) != "terminado"
        }
        distancias = {origen: 0.0}
        predecesores: dict[tuple[int, int], tuple[int, int]] = {}
        destinos_pendientes = set(destinos or ())
        destinos_pendientes.difference_update(bloqueadas)
        destinos_pendientes.discard(origen)
        cola = [(0.0, origen)]
        while cola:
            distancia_actual, actual = heapq.heappop(cola)
            if distancia_actual != distancias.get(actual):
                continue
            destinos_pendientes.discard(actual)
            if destinos is not None and not destinos_pendientes:
                break
            for vecino, peso in grafo.get_neighbors(actual).items():
                if vecino in bloqueadas:
                    continue
                nueva_distancia = distancia_actual + peso
                if nueva_distancia < distancias.get(vecino, float("inf")):
                    distancias[vecino] = nueva_distancia
                    predecesores[vecino] = actual
                    heapq.heappush(cola, (nueva_distancia, vecino))
        return origen, distancias, predecesores

    def _camino_desde_busqueda(
        self,
        picker: Any,
        destino: tuple[int, int],
        busqueda: tuple[
            tuple[int, int],
            dict[tuple[int, int], float],
            dict[tuple[int, int], tuple[int, int]],
        ] | None,
    ) -> tuple[float, list[tuple[int, int]]] | None:
        if busqueda is None:
            origen = tuple(picker.posicion_actual)
            distancia = self._cache_distancias.distancia(origen, destino)
            camino = self._cache_distancias.camino(origen, destino)
            return (distancia, camino) if camino else None

        origen, distancias, predecesores = busqueda
        distancia = distancias.get(destino)
        if distancia is None:
            return None
        camino = [destino]
        while camino[-1] != origen:
            camino.append(predecesores[camino[-1]])
        camino.reverse()
        return distancia, camino

    def _camino_con_picker(
        self,
        picker: Any,
        destino: tuple[int, int],
    ) -> tuple[float, list[tuple[int, int]]] | None:
        origen = tuple(picker.posicion_actual)
        busqueda = self._calcular_distancias_con_picker(picker, origen)
        return self._camino_desde_busqueda(picker, destino, busqueda)

    def _establecer_tramo(
        self,
        picker: Any,
        camino: list[tuple[int, int]],
        objetivo: dict[str, Any],
    ) -> None:
        if any(
            abs(origen[0] - destino[0]) + abs(origen[1] - destino[1]) != 1
            for origen, destino in zip(camino, camino[1:])
        ):
            raise ValueError("Las rutas de los pickers no pueden tener diagonales.")
        self._objetivos_dinamicos[picker.id] = objetivo
        self._tramos_dinamicos[picker.id] = camino
        self._indices_ruta[picker.id] = 1
        self._rutas[picker.id].extend(camino[1:])

    @staticmethod
    def _orden_id_picker(picker_id: str) -> tuple[str, int, str]:
        prefijo, separador, sufijo = picker_id.rpartition("_")
        if separador and sufijo.isdigit():
            return prefijo, int(sufijo), picker_id
        return picker_id, -1, picker_id

    def _replanificar_picker_bloqueado(self, picker: Any) -> bool:
        objetivo = self._objetivos_dinamicos.get(picker.id)
        if objetivo is None:
            return False

        if objetivo["tipo"] == "producto":
            destinos = set(
                self._celdas_recoleccion(
                    self._productos[objetivo["producto_id"]]
                )
            )
        elif objetivo["tipo"] == "despacho":
            destinos = {
                destino
                for puntos in self._puntos_despacho.values()
                for destino in puntos
            }
        else:
            return False
        busqueda = self._calcular_distancias_con_picker(
            picker, destinos=destinos
        )
        opciones: list[tuple[float, tuple[int, int], list[tuple[int, int]]]] = []
        if objetivo["tipo"] == "producto":
            producto = self._productos[objetivo["producto_id"]]
            for destino in self._celdas_recoleccion(producto):
                ruta = self._camino_desde_busqueda(
                    picker, destino, busqueda
                )
                if ruta is not None:
                    distancia, camino = ruta
                    opciones.append((distancia, destino, camino))
        elif objetivo["tipo"] == "despacho":
            for zona_id, puntos in self._puntos_despacho.items():
                for destino in puntos:
                    ruta = self._camino_desde_busqueda(
                        picker, destino, busqueda
                    )
                    if ruta is None:
                        continue
                    distancia, camino = ruta
                    prioridad_zona = 0 if zona_id == objetivo["zona_id"] else 1
                    opciones.append(
                        (distancia + prioridad_zona * 1e-6, destino, camino)
                    )

        if not opciones:
            return False

        _, _, camino = min(opciones, key=lambda opcion: (opcion[0], opcion[1]))
        tramo_actual = self._tramos_dinamicos[picker.id]
        indice_actual = self._indices_ruta[picker.id]
        camino_pendiente = tramo_actual[max(indice_actual - 1, 0) :]
        if camino == camino_pendiente:
            return False

        self._rutas[picker.id] = [tuple(picker.posicion_actual)]
        self._establecer_tramo(picker, camino, objetivo)
        return True

    def _ceder_paso(self, picker: Any) -> bool:
        """Intenta destrabar a `picker`: primero busca otra ruta evitando a los
        demás y, si no hay, se corre a una celda vecina libre para dejar pasar."""
        if self._replanificar_picker_bloqueado(picker):
            return True
        grafo = getattr(self._cache_distancias, "_grafo", None)
        if grafo is None:
            return False

        posicion = tuple(picker.posicion_actual)
        ocupadas: set[tuple[int, int]] = set()
        siguientes: set[tuple[int, int]] = set()
        for otro in self.pickers:
            if (
                otro.id == picker.id
                or self._estado_picker[otro.id] == "terminado"
            ):
                continue
            ocupadas.add(tuple(otro.posicion_actual))
            tramo = self._tramos_dinamicos[otro.id]
            indice = self._indices_ruta[otro.id]
            if indice < len(tramo):
                siguientes.add(tramo[indice])

        tramo_propio = self._tramos_dinamicos[picker.id]
        indice_propio = self._indices_ruta[picker.id]
        celda_bloqueada = (
            tramo_propio[indice_propio]
            if indice_propio < len(tramo_propio)
            else None
        )
        libres = [
            vecino
            for vecino in grafo.get_neighbors(posicion)
            if vecino not in ocupadas and vecino != celda_bloqueada
        ]
        if not libres:
            return False
        preferidas = [vecino for vecino in libres if vecino not in siguientes]
        destino = min(preferidas or libres)
        self._rutas[picker.id] = [posicion]
        self._establecer_tramo(picker, [posicion, destino], {"tipo": "ceder"})
        return True

    def _resolver_atascos(
        self,
        bloqueos_por_picker: dict[str, set[str]],
        aceptados: set[str],
        propuestas: dict[str, tuple[int, int]],
    ) -> None:
        """Detecta grupos de pickers que se bloquean entre sí (cruces de frente,
        pickers esperando un punto de despacho ocupado, etc.) y hace que uno
        del grupo, el de menor prioridad, cede el paso."""
        activos = {
            picker.id: picker
            for picker in self.pickers
            if self._estado_picker[picker.id] != "terminado"
        }

        def parado(picker_id: str) -> bool:
            picker = activos.get(picker_id)
            return (
                picker is not None
                and picker_id not in aceptados
                and getattr(picker, "tiempo_recoleccion", 0) <= 0
            )

        def parado_firme(picker_id: str) -> bool:
            return parado(picker_id) and (
                picker_id not in propuestas
                or self._ticks_bloqueado.get(picker_id, 0) >= 2
            )

        padre: dict[str, str] = {}

        def raiz(picker_id: str) -> str:
            padre.setdefault(picker_id, picker_id)
            while padre[picker_id] != picker_id:
                padre[picker_id] = padre[padre[picker_id]]
                picker_id = padre[picker_id]
            return picker_id

        hay_atasco = False
        for picker_id, bloqueadores in bloqueos_por_picker.items():
            if (
                not parado(picker_id)
                or self._ticks_bloqueado.get(picker_id, 0) < TICKS_ATASCO
                or not bloqueadores
                or not all(parado_firme(b) for b in bloqueadores)
            ):
                continue
            hay_atasco = True
            for bloqueador in bloqueadores:
                padre[raiz(picker_id)] = raiz(bloqueador)
        if not hay_atasco:
            return

        grupos: dict[str, list[str]] = {}
        for picker_id in list(padre):
            grupos.setdefault(raiz(picker_id), []).append(picker_id)
        for miembros in grupos.values():
            if len(miembros) < 2:
                continue
            # Cede primero el de menor prioridad; a igualdad, el de id mayor.
            candidatos = sorted(
                (activos[m] for m in miembros if m in activos),
                key=lambda p: (p.prioridad, -self._orden_id_picker(p.id)[1]),
            )
            for picker in candidatos:
                if self._ceder_paso(picker):
                    self._ticks_bloqueado[picker.id] = 0
                    break

    def _planificar_descarga_dinamica(self, picker: Any) -> bool:
        if not self._puntos_despacho:
            raise ValueError(
                f"El picker {picker.id} necesita descargar, pero no hay "
                "puntos de despacho configurados."
            )

        ocupadas = {
            tuple(otro.posicion_actual)
            for otro in self.pickers
            if otro.id != picker.id
            and self._estado_picker.get(otro.id) != "terminado"
        }
        opciones = []
        destinos = {
            punto
            for puntos in self._puntos_despacho.values()
            for punto in puntos
            if punto not in ocupadas
        }
        busqueda = self._calcular_distancias_con_picker(
            picker, destinos=destinos
        )
        hay_punto_alcanzable = False
        puntos_ocupados = 0
        origen = tuple(picker.posicion_actual)
        for zona_id, puntos in self._puntos_despacho.items():
            for punto in puntos:
                if punto in ocupadas:
                    puntos_ocupados += 1
                    continue
                ruta = self._camino_desde_busqueda(
                    picker, punto, busqueda
                )
                if ruta is None:
                    camino = self._cache_distancias.camino(origen, punto)
                    if not camino:
                        continue
                    ruta = (
                        self._cache_distancias.distancia(origen, punto),
                        camino,
                    )
                hay_punto_alcanzable = True
                distancia, camino = ruta
                opciones.append((distancia, zona_id, punto, camino))

        if not opciones:
            cantidad_puntos = sum(
                len(puntos) for puntos in self._puntos_despacho.values()
            )
            if cantidad_puntos and puntos_ocupados == cantidad_puntos:
                return False
            if not hay_punto_alcanzable:
                raise ValueError(
                    f"No hay una ruta desde {origen} hasta una zona de "
                    f"despacho para el picker {picker.id}."
                )
            return False

        _, zona_id, punto, camino = min(
            opciones, key=lambda opcion: (opcion[0], opcion[1], opcion[2])
        )
        self._establecer_tramo(
            picker,
            camino,
            {"tipo": "despacho", "zona_id": zona_id, "punto": punto},
        )
        return True

    def _planificar_picker_dinamico(self, picker: Any) -> None:
        if self._estado_picker[picker.id] == "terminado":
            return
        if self._indices_ruta[picker.id] < len(
            self._tramos_dinamicos[picker.id]
        ):
            return

        objetivo_anterior = self._objetivos_dinamicos[picker.id]
        if objetivo_anterior is not None:
            self._atender_objetivo_dinamico(picker, objetivo_anterior)
            self._objetivos_dinamicos[picker.id] = None
        self._tramos_dinamicos[picker.id] = []
        self._indices_ruta[picker.id] = 0

        while self._estado_picker[picker.id] != "terminado":
            demanda = (
                self._demanda_por_picker.get(picker.id, {})
                if self._asignaciones_explicitas
                else self._demanda_global
            )
            for producto_id, cantidad in list(demanda.items()):
                producto = self._productos.get(producto_id)
                if producto is None:
                    raise ValueError(
                        f"El pedido del picker {picker.id} referencia el "
                        f"producto inexistente '{producto_id}'."
                    )
                stock = self._valor(
                    producto, "cantidad_disponible", default=None
                )
                if stock is not None and stock <= 0:
                    self._registrar_faltante(
                        picker, producto_id, cantidad, "stock_agotado"
                    )

                # ... (el resto del código sigue igual)
            demanda = (
                self._demanda_por_picker.get(picker.id, {})
                if self._asignaciones_explicitas
                else self._demanda_global
            )
            if not demanda:
                if picker.carga_actual_kg > 1e-9:
                    if self._planificar_descarga_dinamica(picker):
                        if len(self._tramos_dinamicos[picker.id]) == 1:
                            objetivo = self._objetivos_dinamicos[picker.id]
                            self._objetivos_dinamicos[picker.id] = None
                            self._atender_objetivo_dinamico(picker, objetivo)
                            continue
                    return
                self._estado_picker[picker.id] = "terminado"
                return

            capacidad_libre = (
                picker.capacidad_carga_kg - picker.carga_actual_kg
            )
            origen = tuple(picker.posicion_actual)
            productos_candidatos = []
            destinos = set()
            inalcanzables = []
            for producto_id, cantidad in demanda.items():
                producto = self._productos[producto_id]
                peso = float(self._valor(producto, "peso_kg", default=0.0))
                if peso > 0:
                    unidades_posibles = floor(
                        (capacidad_libre + 1e-9) / peso
                    )
                    if unidades_posibles <= 0:
                        continue

                puntos = self._celdas_recoleccion(producto)
                productos_candidatos.append((producto_id, puntos))
                destinos.update(puntos)

            busqueda = self._calcular_distancias_con_picker(
                picker, origen, destinos
            )
            opciones: list[
                tuple[float, str, tuple[int, int], bool]
            ] = []
            for producto_id, puntos in productos_candidatos:
                destino_cercano = self._ruta_mas_cercana(
                    picker, origen, puntos, busqueda
                )
                usa_busqueda_dinamica = destino_cercano is not None
                if destino_cercano is None:
                    destinos_alcanzables = [
                        (self._cache_distancias.distancia(origen, punto), punto)
                        for punto in puntos
                    ]
                    destinos_alcanzables = [
                        opcion
                        for opcion in destinos_alcanzables
                        if opcion[0] != float("inf")
                    ]
                    if not destinos_alcanzables:
                        inalcanzables.append(producto_id)
                        continue
                    destino_cercano = min(destinos_alcanzables)
                distancia, punto = destino_cercano
                opciones.append(
                    (
                        distancia,
                        producto_id,
                        punto,
                        usa_busqueda_dinamica,
                    )
                )

            if opciones:
                if self.estrategia_recorrido == "Orden de pedidos (A)":
                    primer_producto = list(demanda.keys())[0]
                    elegido = None
                    for opcion in opciones:
                        _, prod_id, _, _ = opcion
                        if prod_id == primer_producto:
                            elegido = opcion
                            break

                    if elegido is None:
                        elegido = min(opciones, key=lambda opcion: opcion[:2])
                else:
                    elegido = min(opciones, key=lambda opcion: opcion[:2])

                _, producto_id, punto, usa_busqueda_dinamica = elegido
                if usa_busqueda_dinamica:
                    ruta_elegida = self._camino_desde_busqueda(
                        picker, punto, busqueda
                    )
                else:
                    ruta_elegida = self._camino_desde_busqueda(
                        picker, punto, None
                    )
                if ruta_elegida is None:
                    inalcanzables.append(producto_id)
                    continue
                _, camino = ruta_elegida

                objetivo = {"tipo": "producto", "producto_id": producto_id}

                if len(camino) == 1:
                    if tuple(picker.posicion_actual) == camino[0]:
                        self._atender_objetivo_dinamico(picker, objetivo)
                    continue

                self._establecer_tramo(picker, camino, objetivo)
                return

            if picker.carga_actual_kg > 1e-9:
                if self._planificar_descarga_dinamica(picker):
                    camino = self._tramos_dinamicos[picker.id]
                    if len(camino) == 1:
                        objetivo = self._objetivos_dinamicos[picker.id]
                        self._objetivos_dinamicos[picker.id] = None
                        self._atender_objetivo_dinamico(picker, objetivo)
                        continue
                return

            for producto_id, cantidad in list(demanda.items()):
                producto = self._productos[producto_id]
                peso = float(self._valor(producto, "peso_kg", default=0.0))
                motivo = (
                    "capacidad_picker"
                    if peso > picker.capacidad_carga_kg
                    else "sin_ruta"
                    if producto_id in inalcanzables
                    else "capacidad_picker"
                )
                self._registrar_faltante(
                    picker, producto_id, cantidad, motivo
                )

    def _atender_objetivo_dinamico(
        self,
        picker: Any,
        objetivo: dict[str, Any] | None,
    ) -> None:
        if objetivo is None:
            return
        if objetivo["tipo"] == "ceder":
            return
        if objetivo["tipo"] == "producto":
            self._recoger_objetivo_dinamico(
                picker, objetivo["producto_id"]
            )
            return

        items = picker.descargar()
        puerta_id = None
        if self.warehouse is not None:
            zona = self.warehouse.zonas.get(objetivo["zona_id"])
            puerta_id = zona.puerta_id if zona is not None else None
        self.descargas.append(
            {
                "picker_id": picker.id,
                "zona_id": objetivo["zona_id"],
                "puerta_id": puerta_id,
                "paso": self.paso_actual,
                "items": [
                    {"producto_id": producto_id, "cantidad": cantidad}
                    for producto_id, cantidad in items
                ],
            }
        )
        self._cantidad_productos_despachados += sum(
            cantidad for _, cantidad in items
        )

    def _recoger_objetivo_dinamico(
        self,
        picker: Any,
        producto_id: str,
    ) -> None:
        producto = self._productos[producto_id]
        pendiente = self._cantidad_pendiente(picker, producto_id)
        if pendiente <= 0:
            return

        stock = self._valor(producto, "cantidad_disponible", default=None)
        disponible = pendiente if stock is None else min(pendiente, stock)
        peso = float(self._valor(producto, "peso_kg", default=0.0))
        capacidad_libre = max(
            picker.capacidad_carga_kg - picker.carga_actual_kg, 0.0
        )
        unidades_capacidad = (
            disponible
            if peso <= 0
            else floor((capacidad_libre + 1e-9) / peso)
        )
        cantidad = min(disponible, unidades_capacidad)
        if cantidad <= 0:
            return

        picker.recoger(producto, cantidad)

        # --- CÁLCULO DE ALTURA (Z) ---
        ubicacion = self._valor(producto, "ubicacion")
        z = int(ubicacion[2]) if len(ubicacion) > 2 else 1
        pasos_por_altura = z * 2

        self.distancia += pasos_por_altura
        self.paso_actual += pasos_por_altura
        self.ultima_altura = z  # <--- NUEVO: Guardamos para la métrica

        picker.tiempo_recoleccion = 5
        picker.info_recoleccion = f"Nivel {z}"
        # ------------------------------

        if stock is not None:
            producto.cantidad_disponible -= cantidad
        self._reducir_demanda(picker, producto_id, cantidad)
        self.productos_recogidos.append(
            {
                "picker_id": picker.id,
                "producto_id": producto_id,
                "cantidad": cantidad,
            }
        )
        self._cantidad_productos_recogidos += cantidad

    def avanzar_paso(self) -> bool:
        propuestas: dict[str, tuple[int, int]] = {}
        habia_pausa = False

        if self._modo_dinamico:
            for picker in self.pickers:
                if getattr(picker, "tiempo_recoleccion", 0) > 0:
                    continue
                self._planificar_picker_dinamico(picker)

        for picker in self.pickers:
            if getattr(picker, "tiempo_recoleccion", 0) > 0:
                picker.tiempo_recoleccion -= 1
                if picker.tiempo_recoleccion == 0:
                    picker.info_recoleccion = ""
                habia_pausa = True
                continue

            if self._modo_dinamico:
                tramo = self._tramos_dinamicos[picker.id]
                indice = self._indices_ruta[picker.id]
                if indice < len(tramo):
                    propuestas[picker.id] = tramo[indice]
            else:
                ruta = self._rutas[picker.id]
                indice = self._indices_ruta[picker.id]
                if indice < len(ruta):
                    propuestas[picker.id] = ruta[indice]

        if not propuestas:
            if habia_pausa:
                self.paso_actual += 1
                self._en_ejecucion = True
                return True

            if not self._modo_dinamico or all(
                estado == "terminado"
                for estado in self._estado_picker.values()
            ):
                self._en_ejecucion = False
                return False
            self.paso_actual += 1
            self._ticks_sin_movimiento += 1
            if self._ticks_sin_movimiento > max(10, len(self.pickers) * 10):
                raise RuntimeError(
                    "Los pickers no pueden avanzar: todos los puntos de "
                    "despacho alcanzables están ocupados."
                )
            self._en_ejecucion = True
            return True

        self.paso_actual += 1
        destinos: dict[tuple[int, int], list[Any]] = {}
        for picker in self.pickers:
            if picker.id in propuestas:
                destinos.setdefault(propuestas[picker.id], []).append(picker)

        aceptados: set[str] = set()
        bloqueos_por_picker: dict[str, set[str]] = {}
        for pickers_destino in destinos.values():
            ganador = min(
                pickers_destino,
                key=lambda picker: (
                    -picker.prioridad,
                    str(picker.id),
                ),
            )
            aceptados.add(ganador.id)
            for picker in pickers_destino:
                if picker.id != ganador.id:
                    bloqueos_por_picker.setdefault(picker.id, set()).add(
                        ganador.id
                    )

        if self._modo_dinamico:
            picker_por_zona: dict[str, str] = {}
            for picker in self.pickers:
                objetivo = self._objetivos_dinamicos[picker.id]
                if (
                    picker.id not in aceptados
                    or objetivo is None
                    or objetivo["tipo"] != "despacho"
                    or propuestas[picker.id] != objetivo["punto"]
                ):
                    continue
                zona_id = objetivo["zona_id"]
                if zona_id in picker_por_zona:
                    aceptados.remove(picker.id)
                    bloqueos_por_picker.setdefault(picker.id, set()).add(
                        picker_por_zona[zona_id]
                    )
                else:
                    picker_por_zona[zona_id] = picker.id

        cambio = True
        while cambio:
            cambio = False
            posiciones_ocupadas = {
                tuple(picker.posicion_actual): picker.id
                for picker in self.pickers
                if picker.id not in aceptados
                and (
                    not self._modo_dinamico
                    or self._estado_picker[picker.id] != "terminado"
                )
            }
            for picker in self.pickers:
                if picker.id not in aceptados:
                    continue
                ocupante = posiciones_ocupadas.get(propuestas[picker.id])
                if ocupante is not None:
                    bloqueos_por_picker.setdefault(picker.id, set()).add(
                        ocupante
                    )
                    aceptados.remove(picker.id)
                    cambio = True

        for indice, picker in enumerate(self.pickers):
            if picker.id not in aceptados:
                continue
            for otro in self.pickers[indice + 1 :]:
                if (
                    otro.id in aceptados
                    and propuestas[picker.id] == tuple(otro.posicion_actual)
                    and propuestas[otro.id] == tuple(picker.posicion_actual)
                ):
                    bloqueos_por_picker.setdefault(picker.id, set()).add(otro.id)
                    bloqueos_por_picker.setdefault(otro.id, set()).add(picker.id)
                    aceptados.remove(picker.id)
                    aceptados.remove(otro.id)

        for picker in self.pickers:
            if picker.id not in aceptados:
                continue
            destino = propuestas[picker.id]
            anterior = tuple(picker.posicion_actual)
            picker.mover_a(destino)
            self._indices_ruta[picker.id] += 1
            self.distancia += abs(destino[0] - anterior[0]) + abs(
                destino[1] - anterior[1]
            )
            if not self._modo_dinamico:
                self._recoger_en_posicion(picker)

        if self._modo_dinamico:
            for picker in self.pickers:
                bloqueadores = bloqueos_por_picker.get(picker.id, set())
                if not bloqueadores:
                    self._ticks_bloqueado[picker.id] = 0
                    continue
                self._ticks_bloqueado[picker.id] += 1
                espera = self._ticks_bloqueado[picker.id]
                es_picker_mayor = all(
                    self._orden_id_picker(picker.id)
                    > self._orden_id_picker(bloqueador_id)
                    for bloqueador_id in bloqueadores
                )
                if (
                    espera >= 2
                    and (espera - 2) % 5 == 0
                    and es_picker_mayor
                ):
                    self._replanificar_picker_bloqueado(picker)

            self._resolver_atascos(bloqueos_por_picker, aceptados, propuestas)

            if aceptados:
                self._ticks_sin_movimiento = 0
            else:
                self._ticks_sin_movimiento += 1
                if self._ticks_sin_movimiento > max(10, len(self.pickers) * 10):
                    raise RuntimeError(
                        "Los pickers llevan más de un tick bloqueados. "
                        "No se encontró una ruta alternativa. Revisá la "
                        "circulación y los puntos de despacho."
                    )

            for picker in self.pickers:
                if (
                    picker.id not in aceptados
                    or self._indices_ruta[picker.id]
                    < len(self._tramos_dinamicos[picker.id])
                ):
                    continue
                objetivo = self._objetivos_dinamicos[picker.id]
                self._objetivos_dinamicos[picker.id] = None
                self._tramos_dinamicos[picker.id] = []
                self._indices_ruta[picker.id] = 0
                self._atender_objetivo_dinamico(picker, objetivo)

            for picker in self.pickers:
                self._planificar_picker_dinamico(picker)

        quedan_pasos = (
            any(estado != "terminado" for estado in self._estado_picker.values())
            if self._modo_dinamico
            else any(
                self._indices_ruta[picker.id] < len(self._rutas[picker.id])
                for picker in self.pickers
            )
        )
        self._en_ejecucion = quedan_pasos
        return quedan_pasos

    def get_estado(self) -> dict[str, Any]:
        return {
            "paso_actual": self.paso_actual,
            "pickers": [
                {
                    "id": picker.id,
                    "x": picker.posicion_actual[0],
                    "y": picker.posicion_actual[1],
                    "carga_actual_kg": picker.carga_actual_kg,
                    "items_transportados": [
                        {"producto_id": producto_id, "cantidad": cantidad}
                        for producto_id, cantidad in picker.items_transportados
                    ],
                    "productos_transportados": sum(
                        cantidad
                        for _, cantidad in picker.items_transportados
                    ),
                    "productos_objetivo": sum(
                        self._demanda_por_picker_inicial.get(
                            picker.id, {}
                        ).values()
                    )
                    if self._asignaciones_explicitas
                    else sum(self._demanda_global_inicial.values()),
                    "activo": (
                        not self._modo_dinamico
                        or self._estado_picker[picker.id] != "terminado"
                    ),
                    "recolectando": getattr(picker, "tiempo_recoleccion", 0) > 0,
                    "info_recoleccion": getattr(picker, "info_recoleccion", "")
                }
                for picker in self.pickers
            ],
            "rutas": [
                list(
                    (self._tramos_dinamicos[picker.id] if self._modo_dinamico else self._rutas[picker.id])[
                        max(0, self._indices_ruta[picker.id] - 1):
                    ]
                )
                for picker in self.pickers
            ],
            "productos_recogidos": self._cantidad_productos_recogidos,
            "total_productos": self._total_productos,
            "distancia": self.distancia,

            # Le pasamos a la UI los pedidos que se están procesando actualmente
            "ultima_altura": self.ultima_altura,  # <--- NUEVO: Métrica de altura

            "pedidos_actuales": (
                self._demanda_por_picker
                if self._asignaciones_explicitas
                else self._demanda_global
            ),

            "recolecciones": [dict(item) for item in self.productos_recogidos],
            "faltantes": [dict(item) for item in self.productos_faltantes],
            "productos_despachados": self._cantidad_productos_despachados,
            "descargas": [
                {**descarga, "items": [dict(item) for item in descarga["items"]]}
                for descarga in self.descargas
            ],
        }

    def iniciar(self) -> None:
        self._en_ejecucion = True

    def pausar(self) -> None:
        self._en_ejecucion = False

    def continuar(self) -> None:
        """Reanuda la simulación desde donde se pausó."""
        self._en_ejecucion = True

    def resetear(self) -> None:
        for picker in self.pickers:
            inicial = self._estado_inicial[picker.id]
            picker.mover_a(inicial["posicion"])
            picker.items_transportados = list(inicial["items"])
            picker.carga_actual_kg = inicial["carga"]
            picker.tiempo_recoleccion = 0

        self._indices_ruta = {
            picker.id: (
                1
                if self._rutas[picker.id]
                and self._rutas[picker.id][0]
                == tuple(picker.posicion_actual)
                else 0
            )
            for picker in self.pickers
        }
        self.paso_actual = 0
        self.distancia = 0
        self.ultima_altura = 0  # <--- NUEVO: Reiniciar altura
        self.productos_recogidos.clear()
        self.productos_faltantes.clear()
        self.descargas.clear()
        self._cantidad_productos_recogidos = 0
        self._cantidad_productos_despachados = 0
        self._en_ejecucion = False
        self._demanda_global = dict(self._demanda_global_inicial)
        self._demanda_por_picker = {
            picker_id: dict(demanda)
            for picker_id, demanda in self._demanda_por_picker_inicial.items()
        }
        for producto_id, stock in self._stock_inicial.items():
            if stock is not None:
                self._productos[producto_id].cantidad_disponible = stock
        if self._modo_dinamico:
            self._inicializar_navegacion_dinamica()
        else:
            self._recoger_en_posiciones_actuales()