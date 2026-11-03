from __future__ import annotations

import copy
import math
import random
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from warehouse.algoritmos.distancias import CacheDistancias
from warehouse.dominio.picker import Picker
from warehouse.dominio.tipo_nodo import TipoNodo
from warehouse.dominio.wave import Wave
from warehouse.warehouse.warehouse import Warehouse
from warehouse.waves.generador_waves import ItemWave

if TYPE_CHECKING:
    from warehouse.dominio.producto import Producto
    from warehouse.dominio.zona import ZonaDespacho


@dataclass
class Tarea:
    producto_id: str
    cantidad: int
    nodo_picking: int
    pedido_id: str = ""
    wave_id: str = ""
    completada: bool = False
    asignada_a: str | None = None


@dataclass
class EstadoPicker:
    picker: Picker
    nodo_actual: int
    camino_actual: list[int] = field(default_factory=list)
    tarea_actual: Tarea | None = None
    zona_objetivo: "ZonaDespacho" | None = None
    # Fases: BUSCANDO_TAREA, YENDO_A_ITEM, RECOGIENDO, YENDO_A_DESPACHO, ENTRANDO_A_ZONA, DESCARGANDO, SALIENDO_DE_ZONA, YENDO_A_FINAL, TERMINADO
    fase: str = "BUSCANDO_TAREA"
    carga_kg: float = 0.0
    productos_recogidos: set[str] = field(default_factory=set)
    espera_restante: int = 0
    bloqueos_consecutivos: int = 0
    wave_actual: str | None = None


@dataclass
class SimulacionDinamica:
    pickers: dict[str, EstadoPicker]
    tareas_pendientes: list[Tarea]
    productos_totales: set[str]
    nodo_a_productos: dict[int, list[str]]
    cantidad_pedida: dict[str, int]
    cache: CacheDistancias
    warehouse: Warehouse
    paso_actual: int = 0
    zonas_despacho: dict[int, "ZonaDespacho"] = field(default_factory=dict)
    peso_en_zona: dict[str, float] = field(default_factory=dict)
    cajas_en_zona: dict[int, int] = field(default_factory=dict)
    productos_entregados: set[str] = field(default_factory=set)
    distancia_total: float = 0.0
    aristas_recorridas: int = 0
    nodos_visitados: int = 0
    tiempo_ejecucion: float = 0.0
    # --- 3a: tracking de waves ---
    waves: dict[str, Wave] = field(default_factory=dict)
    tareas_por_wave: dict[str, list[Tarea]] = field(default_factory=dict)
    waves_pendientes: list[str] = field(default_factory=list)
    waves_activas: set[str] = field(default_factory=set)
    waves_completadas: set[str] = field(default_factory=set)
    distancia_por_wave: dict[str, float] = field(default_factory=dict)
    max_pickers_por_wave: int = 3
    items_por_picker: int = 5
    total_items_recogidos: int = 0
    total_viajes: int = 0

    def copiar_estado(self) -> "SimulacionDinamica":
        """Hace un snapshot rápido del estado actual para poder retroceder."""
        estado_mutable = {
            "pickers": self.pickers,
            "tareas_pendientes": self.tareas_pendientes,
            "peso_en_zona": self.peso_en_zona,
            "cajas_en_zona": self.cajas_en_zona,
            "productos_entregados": self.productos_entregados,
            "distancia_por_wave": self.distancia_por_wave,
        }
        copia = copy.deepcopy(estado_mutable)

        return SimulacionDinamica(
            pickers=copia["pickers"],
            tareas_pendientes=copia["tareas_pendientes"],
            productos_totales=self.productos_totales,
            nodo_a_productos=self.nodo_a_productos,
            cantidad_pedida=self.cantidad_pedida,
            cache=self.cache,
            warehouse=self.warehouse,
            paso_actual=self.paso_actual,
            zonas_despacho=self.zonas_despacho,
            peso_en_zona=copia["peso_en_zona"],
            cajas_en_zona=copia["cajas_en_zona"],
            productos_entregados=copia["productos_entregados"],
            distancia_total=self.distancia_total,
            aristas_recorridas=self.aristas_recorridas,
            nodos_visitados=self.nodos_visitados,
            tiempo_ejecucion=self.tiempo_ejecucion,
            waves=self.waves,
            tareas_por_wave=self.tareas_por_wave,
            waves_pendientes=self.waves_pendientes,
            waves_completadas=set(self.waves_completadas),
            distancia_por_wave=copia["distancia_por_wave"],
            max_pickers_por_wave=self.max_pickers_por_wave,
            items_por_picker=self.items_por_picker,
            total_items_recogidos=self.total_items_recogidos,
            total_viajes=self.total_viajes,
        )

    @classmethod
    def desde_waves(
        cls,
        waves: list[Wave],
        pickers: list[Picker],
        warehouse: Warehouse,
        posiciones_aleatorias: bool = False,
        items_por_wave: dict[str, list] | None = None,
    ) -> "SimulacionDinamica":

        cache = CacheDistancias(warehouse.grafo)

        tareas_por_wave: dict[str, list[Tarea]] = {}
        productos_totales: set[str] = set()
        cantidad_pedida: dict[str, int] = {}
        nodo_a_productos: dict[int, list[str]] = {}

        for wave in waves:
            wave_items: list[ItemWave]
            if items_por_wave and wave.id in items_por_wave:
                wave_items = items_por_wave[wave.id]
            else:
                # Legacy: sintetizar desde wave.pedidos
                wave_items = []
                for pedido in wave.pedidos:
                    for item in pedido.items:
                        wave_items.append(ItemWave(pedido.id, item.producto_id, item.cantidad))

            tareas: list[Tarea] = []
            for iw in wave_items:
                prod = warehouse.productos[iw.producto_id]
                tareas.append(Tarea(
                    producto_id=iw.producto_id,
                    cantidad=iw.cantidad,
                    nodo_picking=prod.nodo_picking,
                    pedido_id=iw.pedido_id,
                    wave_id=wave.id,
                ))
                productos_totales.add(iw.producto_id)
                cantidad_pedida[iw.producto_id] = (
                    cantidad_pedida.get(iw.producto_id, 0) + iw.cantidad
                )
                nodo_a_productos.setdefault(prod.nodo_picking, []).append(iw.producto_id)

            tareas_por_wave[wave.id] = tareas

        # --- Zonas de despacho ---
        zonas_dict = {}
        peso_en_zona = {}
        for z in warehouse.zonas.values():
            peso_en_zona[z.id] = 0.0
            for x in range(z.p1[0], z.p2[0] + 1):
                for y in range(z.p1[1], z.p2[1] + 1):
                    nid = warehouse._nodo_por_xy.get((x, y))
                    if nid is not None:
                        zonas_dict[nid] = z

        # --- Nodos de pasillo para arranque aleatorio ---
        nodos_pasillo = [
            nid for nid, nodo in warehouse.grafo._nodos.items()
            if nodo.tipo == TipoNodo.PASILLO
        ]
        if posiciones_aleatorias:
            random.shuffle(nodos_pasillo)

        # --- Pickers ---
        estado_pickers = {}
        for i, base_picker in enumerate(pickers):
            picker = copy.deepcopy(base_picker)
            if posiciones_aleatorias and i < len(nodos_pasillo):
                nodo_inicio = nodos_pasillo[i]
            else:
                nodo_inicio = warehouse._nodo_por_xy.get(base_picker.posicion_inicial)
                if nodo_inicio is None:
                    nodo_inicio = next(iter(warehouse._nodo_por_xy.values()))
            estado_pickers[picker.id] = EstadoPicker(
                picker=picker,
                nodo_actual=nodo_inicio,
                wave_actual=None,
            )

        # --- Orden de waves pendientes: prioridad desc, luego FIFO por id ---
        waves_dict = {w.id: w for w in waves}
        waves_pendientes = sorted(
            waves_dict.keys(),
            key=lambda wid: (
                -max((p.prioridad for p in waves_dict[wid].pedidos), default=0),
                wid,
            ),
        )

        return cls(
            pickers=estado_pickers,
            tareas_pendientes=[t for ts in tareas_por_wave.values() for t in ts],
            productos_totales=productos_totales,
            nodo_a_productos=nodo_a_productos,
            cantidad_pedida=cantidad_pedida,
            cache=cache,
            warehouse=warehouse,
            zonas_despacho=zonas_dict,
            peso_en_zona=peso_en_zona,
            waves=waves_dict,
            tareas_por_wave=tareas_por_wave,
            waves_pendientes=list(waves_pendientes),
            waves_activas=set(),
            distancia_por_wave={w.id: 0.0 for w in waves},
        )

    @property
    def completada(self) -> bool:
        return (
            all(ep.fase == "TERMINADO" for ep in self.pickers.values())
            and len(self.waves_completadas) == len(self.waves)
        )

    @property
    def productos_pendientes(self) -> set[str]:
        recogidos = set()
        for ep in self.pickers.values():
            recogidos.update(ep.productos_recogidos)
        return self.productos_totales - recogidos

    def _camino_rodeando_zonas(self, start_nid: int, end_nid: int) -> list[int]:
        """Calcula una ruta que evita atravesar cualquier celda de zona de despacho."""
        from collections import deque
        queue = deque([(start_nid, [start_nid])])
        visited = {start_nid}

        while queue:
            current, path = queue.popleft()
            if current == end_nid:
                return path

            for a in self.warehouse.grafo.vecinos(current):
                vecino = a.destino
                if vecino in visited:
                    continue
                if self.zonas_despacho.get(vecino) is not None:
                    continue

                visited.add(vecino)
                queue.append((vecino, path + [vecino]))

        return [start_nid, end_nid]

    def _camino_corto_por_zonas(self, start_nid: int, end_nid: int) -> list[int]:
        """BFS estándar SIN evitar zonas. Último recurso para desbloquear
        pickers en corredores sin ruta alternativa."""
        from collections import deque
        queue = deque([(start_nid, [start_nid])])
        visited = {start_nid}
        while queue:
            current, path = queue.popleft()
            if current == end_nid:
                return path
            for a in self.warehouse.grafo.vecinos(current):
                vecino = a.destino
                if vecino in visited:
                    continue
                visited.add(vecino)
                queue.append((vecino, path + [vecino]))
        return [start_nid, end_nid]

    def _romper_swaps(
        self,
        propuestas: dict[str, int],
        bloqueados: set[str],
        ocupadas_ahora: dict[int, str],
    ) -> None:
        """Rompe deadlocks de swap mutuo: PK_A quiere ir a la celda de PK_B
        y PK_B quiere ir a la celda de PK_A.
        """
        FASE_ENTREGA = ("YENDO_A_DESPACHO", "ENTRANDO_A_ZONA", "DESCARGANDO", "SALIENDO_DE_ZONA")

        for pid, ep in list(self.pickers.items()):
            if pid not in bloqueados:
                continue

            mi_dst = propuestas.get(pid)
            if mi_dst is None:
                continue

            # Buscar swap partner
            partner_pid = None
            for other_pid, other_ep in self.pickers.items():
                if other_pid == pid or other_pid not in bloqueados:
                    continue
                if (
                    propuestas.get(other_pid) == ep.nodo_actual
                    and mi_dst == other_ep.nodo_actual
                ):
                    partner_pid = other_pid
                    break

            if partner_pid is None:
                continue

            partner_ep = self.pickers[partner_pid]

            # Usamos variables booleanas explícitas para evitar NameError
            yo_en_entrega = ep.fase in FASE_ENTREGA
            partner_en_entrega = partner_ep.fase in FASE_ENTREGA

            if yo_en_entrega and partner_en_entrega:
                continue  # Ninguno puede ceder
            elif not yo_en_entrega and partner_en_entrega:
                pass  # Yo cedo
            elif yo_en_entrega and not partner_en_entrega:
                continue  # El otro cede
            else:
                # Ambos pueden ceder: el de mayor ID cede (menor prioridad)
                if pid < partner_pid:
                    continue

            ep.bloqueos_consecutivos += 1
            if ep.bloqueos_consecutivos < 3:
                continue
            ep.bloqueos_consecutivos = 0

            ocupadas = set(ocupadas_ahora.keys())

            # Destinos a evitar: propuestas de OTROS pickers (incluyendo el partner)
            destinos_ajenos = set()
            for p in propuestas:
                if p != pid:
                    destinos_ajenos.add(propuestas[p])
            destinos_ajenos.add(partner_ep.nodo_actual)

            vecinos = [a.destino for a in self.warehouse.grafo.vecinos(ep.nodo_actual)]

            def _candidato(v: int, permitir_zona: bool) -> bool:
                if v in ocupadas or v in destinos_ajenos:
                    return False
                if self.warehouse.grafo.nodo(v).tipo == TipoNodo.PUERTA:
                    return False
                if not permitir_zona and self.zonas_despacho.get(v) is not None:
                    return False
                return True

            libres = [v for v in vecinos if _candidato(v, permitir_zona=False)]
            if not libres:
                libres = [v for v in vecinos if _candidato(v, permitir_zona=True)]
            if not libres:
                continue

            viejo = ep.nodo_actual
            nuevo = libres[0]
            ep.nodo_actual = nuevo
            self.aristas_recorridas += 1
            self.distancia_total += 1.0
            self.nodos_visitados += 1
            if ep.wave_actual is not None:
                self.distancia_por_wave[ep.wave_actual] += 1.0

            ocupadas_ahora.pop(viejo, None)
            ocupadas_ahora[nuevo] = pid

            # Recalcular camino al target de la fase actual
            target: int | None = None
            if ep.fase == "YENDO_A_ITEM" and ep.tarea_actual:
                target = ep.tarea_actual.nodo_picking
            elif ep.fase == "YENDO_A_DESPACHO" and ep.zona_objetivo:
                target = self._nodo_entrega_zona(ep.zona_objetivo)
            elif ep.fase in ("ENTRANDO_A_ZONA", "SALIENDO_DE_ZONA") and ep.camino_actual:
                target = ep.camino_actual[-1]

            if target is not None:
                ep.camino_actual = self._camino_corto_por_zonas(ep.nodo_actual, target)

            # El partner ya no está en swap: desbloquearlo este tick
            bloqueados.discard(partner_pid)
            # Yo ya me moví: no aplicar movimiento estándar
            propuestas.pop(pid, None)
            bloqueados.discard(pid)

    def _mover_ociosos_que_estorban(
        self,
        propuestas: dict[str, int],
        ocupadas_ahora: dict[int, str],
    ) -> None:
        """Mueve pickers ociosos que estén bloqueando activamente a otros."""
        if not propuestas:
            return

        destinos_activos = {
            d
            for pid, d in propuestas.items()
            if self.pickers[pid].wave_actual is not None
            or self.pickers[pid].fase != "BUSCANDO_TAREA"
        }

        for pid, ep in self.pickers.items():
            if ep.wave_actual is not None or ep.fase != "BUSCANDO_TAREA":
                continue

            nodo_tipo = self.warehouse.grafo.nodo(ep.nodo_actual).tipo
            en_puerta_o_zona = (
                nodo_tipo == TipoNodo.PUERTA
                or ep.nodo_actual in self.zonas_despacho
            )
            bloquea_a_otro = ep.nodo_actual in destinos_activos
            if not (en_puerta_o_zona or bloquea_a_otro):
                continue

            ocupadas = set(ocupadas_ahora.keys())
            vecinos = [a.destino for a in self.warehouse.grafo.vecinos(ep.nodo_actual)]

            def _candidato(v: int, permitir_zona: bool) -> bool:
                if v in ocupadas or v in destinos_activos:
                    return False
                if self.warehouse.grafo.nodo(v).tipo == TipoNodo.PUERTA:
                    return False
                if not permitir_zona and self.zonas_despacho.get(v) is not None:
                    return False
                return True

            libres = [v for v in vecinos if _candidato(v, permitir_zona=False)]
            if not libres:
                libres = [v for v in vecinos if _candidato(v, permitir_zona=True)]
            if not libres:
                continue

            viejo = ep.nodo_actual
            nuevo = libres[0]
            ep.nodo_actual = nuevo
            self.aristas_recorridas += 1
            self.distancia_total += 1.0
            self.nodos_visitados += 1

            ocupadas_ahora.pop(viejo, None)
            ocupadas_ahora[nuevo] = pid

    def _es_celda_segura_para_caja(self, zona, target_nid, nodo_puerta) -> bool:
        """Verifica si colocar una caja en target_nid no bloquea el paso hacia las demás celdas libres."""
        from collections import deque
        temp_cajas = self.cajas_en_zona.copy()
        temp_cajas[target_nid] = temp_cajas.get(target_nid, 0) + 1

        empty_cells = set()
        for x in range(zona.p1[0], zona.p2[0] + 1):
            for y in range(zona.p1[1], zona.p2[1] + 1):
                nid = self.warehouse._nodo_por_xy.get((x, y))
                if nid and temp_cajas.get(nid, 0) == 0:
                    empty_cells.add(nid)

        if not empty_cells:
            return True

        queue = deque([nodo_puerta])
        visited = {nodo_puerta}
        reached = 0

        while queue:
            current = queue.popleft()
            if current in empty_cells:
                reached += 1

            for a in self.warehouse.grafo.vecinos(current):
                vecino = a.destino
                if vecino in visited:
                    continue
                if self.zonas_despacho.get(vecino) != zona:
                    continue
                if temp_cajas.get(vecino, 0) > 0:
                    continue
                visited.add(vecino)
                queue.append(vecino)

        return reached == len(empty_cells)

    def _path_a_celda_libre(self, zona, nodo_puerta) -> list[int] | None:
        """Camino desde la puerta a una celda de la zona libre de pickers y cajas."""
        from collections import deque
        ocupados_por_otros = {
            p.nodo_actual for p in self.pickers.values() if p.nodo_actual != nodo_puerta
        }
        queue = deque([(nodo_puerta, [nodo_puerta])])
        visited = {nodo_puerta}
        while queue:
            current, path = queue.popleft()
            if (
                current != nodo_puerta
                and self.zonas_despacho.get(current) is zona
                and current not in ocupados_por_otros
                and self.cajas_en_zona.get(current, 0) == 0  # <-- Verifica que no haya caja
            ):
                # Verifica que dejar la caja ahí no bloquee la salida
                if self._es_celda_segura_para_caja(zona, current, nodo_puerta):
                    return path
            for a in self.warehouse.grafo.vecinos(current):
                vecino = a.destino
                if vecino in visited:
                    continue
                if self.zonas_despacho.get(vecino) != zona:
                    continue
                visited.add(vecino)
                queue.append((vecino, path + [vecino]))
        return None


    def _path_desde_zona_a_puerta(self, zona, nodo_actual, nodo_puerta) -> list[int]:
        from collections import deque
        queue = deque([(nodo_actual, [nodo_actual])])
        visited = {nodo_actual}
        while queue:
            current, path = queue.popleft()
            if current == nodo_puerta:
                return path
            for a in self.warehouse.grafo.vecinos(current):
                vecino = a.destino
                if vecino in visited:
                    continue
                if self.zonas_despacho.get(vecino) != zona and vecino != nodo_puerta:
                    continue
                # Evita pisar las cajas al salir
                if self.cajas_en_zona.get(vecino, 0) > 0:  # <-- Verifica que no haya caja
                    continue
                visited.add(vecino)
                queue.append((vecino, path + [vecino]))
        return [nodo_actual]

    def _zona_mas_cercana(self, ep: EstadoPicker) -> "ZonaDespacho" | None:
        mejor_zona = None
        mejor_dist = float("inf")
        zona_llena_cercana = None
        dist_llena = float("inf")

        for zona in self.warehouse.zonas.values():
            nodo_destino = self._nodo_entrega_zona(zona)
            d = self.cache.distancia(ep.nodo_actual, nodo_destino)
            if self.peso_en_zona[zona.id] + ep.carga_kg <= zona.peso_max_kg:
                if d < mejor_dist:
                    mejor_dist = d
                    mejor_zona = zona
            else:
                if d < dist_llena:
                    dist_llena = d
                    zona_llena_cercana = zona

        return mejor_zona if mejor_zona else zona_llena_cercana

    def _nodo_entrega_zona(self, zona) -> int:
        puerta = self.warehouse.puertas.get(zona.puerta_id)
        return puerta.nodo if puerta else zona.nodo_representativo

    def _buscar_nodo_final_exterior(self, ep: EstadoPicker) -> int | None:
        """Busca un pasillo alejado de la puerta y prioriza los cercanos al centro."""
        from collections import deque
        queue = deque([(ep.nodo_actual, 0)])
        visited = {ep.nodo_actual}

        center_x = self.warehouse.ancho // 2
        center_y = self.warehouse.alto // 2

        ocupadas = {p.nodo_actual for p in self.pickers.values()}

        mejor_nodo = None
        mejor_dist_centro = float("inf")

        while queue:
            current, dist = queue.popleft()
            n_curr = self.warehouse.grafo.nodo(current)

            if dist >= 3 and n_curr.tipo == TipoNodo.PASILLO and self.zonas_despacho.get(current) is None:
                if current not in ocupadas:
                    d_centro = abs(n_curr.posicion.x - center_x) + abs(n_curr.posicion.y - center_y)
                    if d_centro < mejor_dist_centro:
                        mejor_dist_centro = d_centro
                        mejor_nodo = current

            if dist < 10:
                for a in self.warehouse.grafo.vecinos(current):
                    v = a.destino
                    if v not in visited and self.zonas_despacho.get(v) is None:
                        visited.add(v)
                        queue.append((v, dist + 1))

        return mejor_nodo if mejor_nodo else ep.nodo_actual

    # ---------- 3b: gestión de waves ----------

    def _pickers_en_wave(self, w_id: str) -> int:
        return sum(1 for ep in self.pickers.values() if ep.wave_actual == w_id)

    def _cap_wave(self, w_id: str) -> int:
        """Decisión 1=B: cap por workload total (suma de cantidades)."""
        # Sumamos la cantidad total de productos a recoger en esta wave
        total_items = sum(t.cantidad for t in self.tareas_por_wave.get(w_id, []))

        # Ahora calculamos el cap en base al total de items
        cap_por_carga = max(1, math.ceil(total_items / self.items_por_picker))
        return min(cap_por_carga, self.max_pickers_por_wave)

    def _wave_sort_key(self, w_id: str) -> tuple[int, str]:
        """Decisión 2=B: prioridad desc, luego FIFO por id."""
        w = self.waves[w_id]
        max_prio = max((p.prioridad for p in w.pedidos), default=0)
        return (-max_prio, w_id)

    def _asignar_picker_a_wave(self, ep: EstadoPicker) -> bool:
        """Bindea ep a la mejor wave disponible."""
        # 1) PRIORIDAD 1: Intentar unirse a una wave ACTIVA que tenga capacidad
        for w_id in sorted(self.waves_activas, key=self._wave_sort_key):
            if self._pickers_en_wave(w_id) >= self._cap_wave(w_id):
                continue
            hay_libres = any(
                not t.completada and t.asignada_a is None
                for t in self.tareas_por_wave[w_id]
            )
            if hay_libres:
                ep.wave_actual = w_id
                return True

        # 2) PRIORIDAD 2: Si no pudo unirse a ninguna, arrancar una wave pendiente
        for w_id in sorted(self.waves_pendientes, key=self._wave_sort_key):
            if self._pickers_en_wave(w_id) < self._cap_wave(w_id):
                ep.wave_actual = w_id
                self.waves_pendientes.remove(w_id)
                self.waves_activas.add(w_id)
                return True

        return False

    def _reclamar_tarea_de_wave(self, ep: EstadoPicker) -> Tarea | None:
        """Reclama la tarea más cercana de la wave actual que quepa en la capacidad."""
        if ep.wave_actual is None:
            return None
        mejor: Tarea | None = None
        mejor_dist = float("inf")
        for t in self.tareas_por_wave[ep.wave_actual]:
            if t.completada or t.asignada_a is not None:
                continue
            peso_unit = self.warehouse.productos[t.producto_id].peso_kg
            if ep.carga_kg + peso_unit > ep.picker.capacidad_carga_kg:
                continue
            d = self.cache.distancia(ep.nodo_actual, t.nodo_picking)
            if d < mejor_dist:
                mejor_dist = d
                mejor = t
        if mejor is not None:
            mejor.asignada_a = ep.picker.id
        return mejor

    def _liberar_picker(self, ep: EstadoPicker) -> None:
        """Suelta la wave actual. La marca completada si corresponde."""
        w_id = ep.wave_actual
        if w_id is None:
            return
        ep.wave_actual = None
        todas_ok = all(
            t.completada for t in self.tareas_por_wave.get(w_id, [])
        )
        sin_pickers = not any(
            p.wave_actual == w_id for p in self.pickers.values()
        )
        if todas_ok and sin_pickers:
            self.waves_activas.discard(w_id)
            self.waves_completadas.add(w_id)

    def _hay_trabajo_global(self) -> bool:
        """True si queda alguna wave pendiente, activa, o algún picker con carga."""
        if self.waves_pendientes:
            return True
        if self.waves_activas:
            return True
        if any(ep.carga_kg > 0 for ep in self.pickers.values()):
            return True
        return False

    def avanzar(self) -> bool:
        if self.completada:
            return False

        t_inicio_tick = time.perf_counter()
        self.paso_actual += 1

        for pid, ep in self.pickers.items():
            if ep.espera_restante > 0 or ep.fase in ("TERMINADO", "RECOGIENDO", "DESCARGANDO"):
                continue

            if ep.fase == "BUSCANDO_TAREA":
                # (1) Sin wave → intentar bindear
                if ep.wave_actual is None:
                    if not self._asignar_picker_a_wave(ep):
                        if not self._hay_trabajo_global():
                            ep.fase = "TERMINADO"
                            ep.camino_actual = []
                        else:
                            ep.espera_restante = 1
                        continue

                # (2) Intentar reclamar tarea de la wave actual
                tarea = self._reclamar_tarea_de_wave(ep)
                if tarea is not None:
                    ep.tarea_actual = tarea
                    ep.camino_actual = self._camino_rodeando_zonas(
                        ep.nodo_actual, tarea.nodo_picking
                    )
                    ep.fase = "YENDO_A_ITEM"
                    continue

                # (3) Sin tarea reclamable pero con carga → entregar
                if ep.carga_kg > 0:
                    zona = self._zona_mas_cercana(ep)
                    if zona is not None:
                        ep.zona_objetivo = zona
                        nodo_entrega = self._nodo_entrega_zona(zona)
                        ep.camino_actual = self._camino_rodeando_zonas(ep.nodo_actual, nodo_entrega)
                        ep.fase = "YENDO_A_DESPACHO"
                    else:
                        ep.espera_restante = 1
                    continue

                # (4) Sin carga y sin reclamables → soltar la wave
                self._liberar_picker(ep)
                ep.espera_restante = 1
                continue

            if ep.fase in ("YENDO_A_ITEM", "YENDO_A_DESPACHO", "ENTRANDO_A_ZONA", "SALIENDO_DE_ZONA", "YENDO_A_FINAL"):
                if len(ep.camino_actual) <= 1:
                    if ep.fase == "YENDO_A_ITEM" and ep.tarea_actual:
                        prod = self.warehouse.productos[ep.tarea_actual.producto_id]
                        ep.espera_restante = prod.z
                        ep.fase = "RECOGIENDO"

                    elif ep.fase == "YENDO_A_DESPACHO":
                        if ep.zona_objetivo:
                            camino_adentro = self._path_a_celda_libre(ep.zona_objetivo, ep.nodo_actual)
                            if camino_adentro:
                                ep.camino_actual = camino_adentro
                                ep.fase = "ENTRANDO_A_ZONA"
                            else:
                                ep.espera_restante = 1
                        else:
                            ep.fase = "BUSCANDO_TAREA"
                            ep.camino_actual = []

                    elif ep.fase == "ENTRANDO_A_ZONA":
                        ep.espera_restante = 2
                        ep.fase = "DESCARGANDO"

                    elif ep.fase == "SALIENDO_DE_ZONA":
                        ep.fase = "BUSCANDO_TAREA"
                        ep.camino_actual = []
                        ep.zona_objetivo = None
                        ep.espera_restante = 1

                    elif ep.fase == "YENDO_A_FINAL":
                        ep.fase = "TERMINADO"
                        ep.camino_actual = []

        propuestas = {}
        for pid, ep in self.pickers.items():
            if ep.fase in ("BUSCANDO_TAREA", "RECOGIENDO", "DESCARGANDO", "TERMINADO") or ep.espera_restante > 0:
                continue
            if len(ep.camino_actual) > 1:
                propuestas[pid] = ep.camino_actual[1]

        ocupadas_ahora = {ep.nodo_actual: pid for pid, ep in self.pickers.items() if ep.fase != "TERMINADO"}
        bloqueados = set()

        # 1. Mover ociosos que estorban
        self._mover_ociosos_que_estorban(propuestas, ocupadas_ahora)

        # 2. Detectar colisiones
        destinos = {}
        for pid, dst in propuestas.items():
            destinos.setdefault(dst, []).append(pid)
        for dst, pids in destinos.items():
            if len(pids) > 1:
                pids.sort()
                bloqueados.update(pids[1:])

        for pid, dst in propuestas.items():
            if dst in ocupadas_ahora and ocupadas_ahora[dst] not in propuestas:
                bloqueados.add(pid)

        for pid, dst in propuestas.items():
            origen = self.pickers[pid].nodo_actual
            for other_pid, other_dst in propuestas.items():
                if (pid != other_pid and other_dst == origen and propuestas[other_pid] == origen and self.pickers[other_pid].nodo_actual == dst):
                    fase_a = self.pickers[pid].fase
                    fase_b = self.pickers[other_pid].fase

                    if fase_a == "SALIENDO_DE_ZONA" and fase_b in ("YENDO_A_DESPACHO", "ENTRANDO_A_ZONA"):
                        bloqueados.add(other_pid)
                    elif fase_b == "SALIENDO_DE_ZONA" and fase_a in ("YENDO_A_DESPACHO", "ENTRANDO_A_ZONA"):
                        bloqueados.add(pid)
                    else:
                        bloqueados.add(pid)
                        bloqueados.add(other_pid)

        # 3. Romper swaps (AHORA SÍ, con bloqueados lleno)
        self._romper_swaps(propuestas, bloqueados, ocupadas_ahora)

        # 4. Aplicar movimientos
        for pid, ep in self.pickers.items():
            if ep.espera_restante > 0:
                ep.espera_restante -= 1
                if ep.espera_restante == 0:
                    if ep.fase == "RECOGIENDO" and ep.tarea_actual:
                        prod = self.warehouse.productos[ep.tarea_actual.producto_id]
                        peso_disponible = ep.picker.capacidad_carga_kg - ep.carga_kg
                        max_unidades = int(peso_disponible // prod.peso_kg)
                        cant_real = min(ep.tarea_actual.cantidad, max_unidades)
                        if cant_real > 0:
                            ep.carga_kg += prod.peso_kg * cant_real
                            ep.productos_recogidos.add(ep.tarea_actual.producto_id)
                            ep.tarea_actual.cantidad -= cant_real
                            # Sumamos las unidades físicas reales recogidas
                            self.total_items_recogidos += cant_real
                            if ep.tarea_actual.cantidad > 0:
                                ep.tarea_actual.asignada_a = None
                            else:
                                ep.tarea_actual.completada = True
                        ep.tarea_actual = None
                        ep.fase = "BUSCANDO_TAREA"

                    elif ep.fase == "DESCARGANDO":
                        zona = self.zonas_despacho.get(ep.nodo_actual)
                        if zona:
                            self.peso_en_zona[zona.id] += ep.carga_kg
                            self.cajas_en_zona[ep.nodo_actual] = self.cajas_en_zona.get(ep.nodo_actual, 0) + 1
                            self.productos_entregados.update(ep.productos_recogidos)
                            self.total_viajes += 1
                            puerta_nodo = self._nodo_entrega_zona(zona)
                            ep.camino_actual = self._path_desde_zona_a_puerta(zona, ep.nodo_actual, puerta_nodo)
                            ep.fase = "SALIENDO_DE_ZONA"
                        else:
                            ep.fase = "BUSCANDO_TAREA"
                        ep.carga_kg = 0.0

                continue

            if pid in propuestas and pid not in bloqueados:
                ep.bloqueos_consecutivos = 0
                ep.nodo_actual = propuestas[pid]
                ep.camino_actual.pop(0)

                self.aristas_recorridas += 1
                self.distancia_total += 1.0
                self.nodos_visitados += 1
                if ep.wave_actual is not None:
                    self.distancia_por_wave[ep.wave_actual] += 1.0

            elif pid in bloqueados:
                ep.bloqueos_consecutivos += 1

        self.tiempo_ejecucion += time.perf_counter() - t_inicio_tick
        return True

