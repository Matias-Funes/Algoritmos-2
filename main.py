"""Punto de entrada que integra los módulos del Wave Picking System."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Callable

from src.algorithms.pathfinding import (
    CacheDistancias,
)
from src.core.graph_builder import construir_grafo
from src.core.inventory import GestorInventario, Producto
from src.core.order import Orden
from src.core.picker import Picker
from src.core.wave import Wave
from src.io.scenario_loader import cargar_escenario
from src.simulation.simulation import Simulation
from src.ui.visualization import Ventana


def _crear_productos(datos_productos: list[dict[str, Any]]) -> list[Producto]:
    """Convierte los productos crudos del JSON en objetos del dominio."""
    productos = []
    for datos in datos_productos:
        ubicacion = datos["ubicacion"]
        if isinstance(ubicacion, dict):
            ubicacion = (
                ubicacion["x"],
                ubicacion["y"],
                ubicacion.get("z", 0),
            )
        productos.append(
            Producto(
                datos["id"],
                datos["nombre"],
                datos["rack_id"],
                tuple(ubicacion),
                datos["cantidad_disponible"],
                datos["peso_kg"],
            )
        )
    return productos


def _crear_pedidos(
    datos_pedidos: list[dict[str, Any]],
) -> list[Orden]:
    """Convierte los pedidos crudos a Orden con items (id, cantidad)."""
    return [
        Orden(
            orden_id=datos["id"],
            prioridad=datos["prioridad"],
            estado=datos.get("estado", "PENDIENTE"),
            items=[
                (item["producto_id"], item["cantidad"])
                for item in datos["items"]
            ],
        )
        for datos in datos_pedidos
    ]


def _crear_pickers(datos_pickers: list[dict[str, Any]]) -> list[Picker]:
    """Convierte posiciones x/y del escenario a los Picker del dominio."""
    pickers = []
    for datos in datos_pickers:
        posicion = datos["posicion_inicial"]
        if isinstance(posicion, dict):
            posicion = (posicion["x"], posicion["y"])
        pickers.append(
            Picker(
                picker_id=datos["id"],
                posicion_inicial=tuple(posicion),
                capacidad_carga_kg=datos["capacidad_carga_kg"],
                prioridad=datos.get("prioridad", 1), # Lee la prioridad del JSON
            )
        )
    return pickers


def _validar_stock_pedidos(
    pedidos: list[Orden],
    inventario: GestorInventario,
) -> None:
    """Valida referencias y avisa cuando la demanda supera el stock inicial."""
    demanda_por_producto: dict[str, int] = {}
    for pedido in pedidos:
        for producto_id, cantidad in pedido.items:
            demanda_por_producto[producto_id] = (
                demanda_por_producto.get(producto_id, 0) + cantidad
            )

    for producto_id, demanda in demanda_por_producto.items():
        producto = inventario.obtener_producto(producto_id)
        if demanda > producto.cantidad_disponible:
            print(
                f"   Aviso: {producto_id}: se piden {demanda}, "
                f"hay {producto.cantidad_disponible}; se preparará lo "
                "disponible y se registrará el faltante."
            )


def _crear_waves(
    pedidos: list[Orden],
    pickers: list[Picker],
    inventario: GestorInventario,
    configuracion: dict[str, Any],
) -> tuple[list[Wave], dict[str, list[Orden]], dict[str, list[Wave]]]:
    """Distribuye pedidos en waves sin limitar su peso a la carga del picker."""
    max_pedidos = configuracion.get("wave_max_pedidos", len(pedidos) or 1)
    max_productos = configuracion.get("wave_max_productos", 1)
    if (
        not isinstance(max_pedidos, int)
        or isinstance(max_pedidos, bool)
        or max_pedidos <= 0
    ):
        raise ValueError("wave_max_pedidos debe ser un entero positivo.")
    if (
        not isinstance(max_productos, int)
        or isinstance(max_productos, bool)
        or max_productos <= 0
    ):
        raise ValueError("wave_max_productos debe ser un entero positivo.")
    if pedidos and not pickers:
        raise ValueError("No se pueden procesar pedidos sin pickers.")

    waves: list[Wave] = []
    pedidos_por_picker = {picker.id: [] for picker in pickers}
    waves_por_picker = {picker.id: [] for picker in pickers}
    carga_wave_actual = {picker.id: 0.0 for picker in pickers}
    wave_actual: dict[str, Wave] = {}
    siguiente_wave_id = 1
    peso_max_wave = sum(pedido.peso_total(inventario) for pedido in pedidos)

    for pedido in pedidos:
        peso_pedido = pedido.peso_total(inventario)
        
        # Priorizamos a los pickers con mayor prioridad al asignar waves
        candidatos = sorted(
            pickers,
            key=lambda picker: (-picker.prioridad, carga_wave_actual[picker.id], picker.id),
        )
        candidatos = [
            picker
            for picker in candidatos
            if all(
                inventario.obtener_producto(producto_id).peso_kg
                <= picker.capacidad_carga_kg
                for producto_id, _ in pedido.items
            )
        ]
        if not candidatos:
            raise ValueError(
                f"Ningún picker puede transportar una unidad de cada "
                f"producto del pedido {pedido.orden_id}."
            )
        asignado = False

        for picker in candidatos:
            wave = wave_actual.get(picker.id)
            if wave is None or not wave.puede_aceptar(pedido, inventario):
                nueva_wave = Wave(
                    wave_id=f"WAVE_{siguiente_wave_id:03d}",
                    capacidad_max_pedidos=max_pedidos,
                    capacidad_max_productos=max_productos,
                    peso_max_kg=peso_max_wave,
                )
                if not nueva_wave.puede_aceptar(pedido, inventario):
                    continue
                wave = nueva_wave
                siguiente_wave_id += 1
                wave_actual[picker.id] = wave
                carga_wave_actual[picker.id] = 0.0
                waves.append(wave)
                waves_por_picker[picker.id].append(wave)

            if wave.agregar_pedido(pedido, inventario):
                pedidos_por_picker[picker.id].append(pedido)
                carga_wave_actual[picker.id] += peso_pedido
                asignado = True
                break

        if not asignado:
            raise ValueError(
                f"El pedido {pedido.orden_id} excede los límites de "
                "pedidos/productos configurados para una wave."
            )

    return waves, pedidos_por_picker, waves_por_picker


def _crear_fases_simulacion(
    pickers: list[Picker],
    waves_por_picker: dict[str, list[Wave]],
) -> list[dict[str, Any]]:
    """Agrupa el trabajo de cada wave por turno para ejecutar pickers juntos."""
    fases = []

    cantidad_turnos = max(
        (len(waves_por_picker[picker.id]) for picker in pickers),
        default=0,
    )
    for indice_turno in range(cantidad_turnos):
        asignaciones = {}
        for picker in pickers:
            waves_picker = waves_por_picker[picker.id]
            if indice_turno >= len(waves_picker):
                continue
            wave = waves_picker[indice_turno]
            asignaciones[picker.id] = wave.pedidos
        fases.append({"asignaciones": asignaciones})

    return fases or [{"asignaciones": {}}]


def _obtener_puntos_despacho(
    warehouse: Any,
    grafo: Any,
) -> dict[str, list[tuple[int, int]]]:
    """Busca celdas transitables adyacentes a zonas vinculadas a salida."""
    puntos_por_zona = {}
    for zona in warehouse.zonas.values():
        puerta = warehouse.puertas.get(zona.puerta_id)
        if puerta is None or puerta.tipo not in ("OUTBOUND", "AMBOS"):
            continue

        puntos = set()
        for x, y in zona.celdas():
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                vecino = (x + dx, y + dy)
                if vecino in grafo.adj:
                    puntos.add(vecino)
        if puntos:
            puntos_por_zona[zona.id] = sorted(puntos)

    return puntos_por_zona


class _SimulationTk:
    """Coordina fases y presenta viajes dinámicos al bucle de Tk."""

    def __init__(
        self,
        warehouse: Any,
        pickers: list[Picker],
        productos: list[Producto],
        fases: list[dict[str, Any]],
        cache_distancias: CacheDistancias,
        puntos_despacho: dict[str, list[tuple[int, int]]],
        intervalo_ms: int = 250,
    ) -> None:
        self.warehouse = warehouse
        self.pickers = pickers
        self.productos = productos
        self.fases = fases
        self.cache_distancias = cache_distancias
        self.puntos_despacho = puntos_despacho
        self.intervalo_ms = intervalo_ms
        self.fase_actual = 0
        self._root = None
        self._actualizar_interfaz: Callable[[], None] | None = None
        self._after_id = None
        self._en_ejecucion = False
        self._fase_completada = False
        self._productos_recogidos_acumulados = 0
        self._distancia_acumulada = 0
        self._faltantes_acumulados: list[dict[str, Any]] = []
        self._descargas_acumuladas: list[dict[str, Any]] = []
        self._total_productos = sum(
            cantidad
            for fase in fases
            for pedidos_fase in fase["asignaciones"].values()
            for pedido in pedidos_fase
            for _, cantidad in pedido.items
        )
        self._productos_objetivo_por_picker = {
            picker.id: 0 for picker in pickers
        }
        for fase in fases:
            for picker_id, pedidos_picker in fase["asignaciones"].items():
                self._productos_objetivo_por_picker[picker_id] = (
                    self._productos_objetivo_por_picker.get(picker_id, 0)
                    + sum(
                        cantidad
                        for pedido in pedidos_picker
                        for _, cantidad in pedido.items
                    )
                )
        self._estado_inicial_pickers = {
            picker.id: {
                "posicion": tuple(picker.posicion_actual),
                "carga": picker.carga_actual_kg,
                "items": list(picker.items_transportados),
            }
            for picker in pickers
        }
        self._stock_inicial = {
            producto.producto_id: producto.cantidad_disponible
            for producto in productos
        }
        self._simulacion_actual = self._crear_simulacion_fase(0)

    def _crear_simulacion_fase(self, indice: int) -> Simulation:
        """Crea un motor común que planifica el trabajo de toda la flota."""
        fase = self.fases[indice]
        return Simulation(
            warehouse=self.warehouse,
            pickers=self.pickers,
            productos=self.productos,
            asignaciones=fase["asignaciones"],
            cache_distancias=self.cache_distancias,
            puntos_despacho=self.puntos_despacho,
        )

    def vincular_interfaz(
        self, root: Any, actualizar_interfaz: Callable[[], None]
    ) -> None:
        """Registra la ventana que recibirá cada actualización de estado."""
        self._root = root
        self._actualizar_interfaz = actualizar_interfaz

    def get_estado(self) -> dict[str, Any]:
        """Devuelve el estado del turno activo y de toda la flota."""
        estado = self._simulacion_actual.get_estado()
        faltantes_actuales = estado["faltantes"]
        descargas_actuales = estado["descargas"]
        recogidos_en_fase = (
            0
            if self._fase_completada
            else estado["productos_recogidos"]
        )
        estado["productos_recogidos"] = (
            self._productos_recogidos_acumulados + recogidos_en_fase
        )
        distancia_en_fase = (
            0 if self._fase_completada else estado["distancia"]
        )
        estado["distancia"] = self._distancia_acumulada + distancia_en_fase
        estado["total_productos"] = self._total_productos
        estado["wave_actual"] = self.fase_actual + 1
        estado["waves_totales"] = len(self.fases)
        estado["faltantes"] = list(self._faltantes_acumulados)
        estado["descargas"] = list(self._descargas_acumuladas)
        if not self._fase_completada:
            estado["faltantes"].extend(faltantes_actuales)
            estado["descargas"].extend(descargas_actuales)
        estado["productos_despachados"] = sum(
            item["cantidad"]
            for descarga in estado["descargas"]
            for item in descarga["items"]
        )
        estado_pickers = {
            picker["id"]: picker for picker in estado["pickers"]
        }
        
        # Acá se arma el diccionario que lee la UI. 
        estado["pickers"] = [
            {
                "id": picker.id,
                "x": picker.posicion_actual[0],
                "y": picker.posicion_actual[1],
                "carga_actual_kg": picker.carga_actual_kg,
                "items_transportados": [
                    dict(item)
                    for item in estado_pickers.get(picker.id, {}).get(
                        "items_transportados", []
                    )
                ],
                "productos_transportados": estado_pickers.get(
                    picker.id, {}
                ).get("productos_transportados", 0),
                "productos_objetivo": self._productos_objetivo_por_picker.get(
                    picker.id, 0
                ),
                "activo": estado_pickers.get(picker.id, {}).get(
                    "activo", False
                ),
                # --- ACÁ ESTÁ LA LÍNEA MÁGICA QUE FALTABA ---
                "recolectando": estado_pickers.get(picker.id, {}).get(
                    "recolectando", False
                )
            }
            for picker in self.pickers
        ]
        return estado

    def avanzar_paso(self) -> bool:
        """Avanza el viaje actual o prepara el próximo al completar la wave."""
        if self._fase_completada:
            return False
        if self._simulacion_actual.avanzar_paso():
            return True

        estado_fase = self._simulacion_actual.get_estado()
        self._productos_recogidos_acumulados += estado_fase["productos_recogidos"]
        self._distancia_acumulada += estado_fase["distancia"]
        self._faltantes_acumulados.extend(estado_fase["faltantes"])
        self._descargas_acumuladas.extend(estado_fase["descargas"])
        for faltante in estado_fase["faltantes"]:
            print(
                f"   Faltante {faltante['producto_id']}: "
                f"{faltante['cantidad']} unidades "
                f"({faltante['motivo']}, picker {faltante['picker_id']})"
            )
        self._fase_completada = True
        siguiente_fase = self.fase_actual + 1
        if siguiente_fase >= len(self.fases):
            self._en_ejecucion = False
            return False

        self.fase_actual = siguiente_fase
        self._simulacion_actual = self._crear_simulacion_fase(self.fase_actual)
        self._fase_completada = False
        return True

    def iniciar(self) -> None:
        """Inicia la animación programando ticks sin bloquear Tkinter."""
        if self._root is None or self._actualizar_interfaz is None:
            raise RuntimeError("La simulación debe vincularse a una ventana antes.")
        if self._en_ejecucion:
            return
        self._en_ejecucion = True
        self._programar_paso(0)

    def pausar(self) -> None:
        """Pausa la animación y cancela el callback pendiente, si existe."""
        self._en_ejecucion = False
        if self._after_id is not None and self._root is not None:
            self._root.after_cancel(self._after_id)
            self._after_id = None

    def resetear(self) -> None:
        """Restaura el estado inicial de todos los viajes y del inventario."""
        self.pausar()
        for picker in self.pickers:
            inicial = self._estado_inicial_pickers[picker.id]
            picker.mover_a(inicial["posicion"])
            picker.carga_actual_kg = inicial["carga"]
            picker.items_transportados = list(inicial["items"])
        for producto in self.productos:
            producto.cantidad_disponible = self._stock_inicial[
                producto.producto_id
            ]
        self.fase_actual = 0
        self._fase_completada = False
        self._productos_recogidos_acumulados = 0
        self._distancia_acumulada = 0
        self._faltantes_acumulados.clear()
        self._descargas_acumuladas.clear()
        self._simulacion_actual = self._crear_simulacion_fase(0)
        if self._actualizar_interfaz is not None:
            self._actualizar_interfaz()

    def _programar_paso(self, demora_ms: int) -> None:
        self._after_id = self._root.after(demora_ms, self._avanzar_automaticamente)

    def _avanzar_automaticamente(self) -> None:
        """Ejecuta un tick y vuelve a programarse solo mientras haya ruta."""
        self._after_id = None
        if not self._en_ejecucion:
            return

        quedan_pasos = self.avanzar_paso()
        if self._actualizar_interfaz is not None:
            self._actualizar_interfaz()

        if quedan_pasos and self._en_ejecucion:
            self._programar_paso(self.intervalo_ms)
        else:
            self._en_ejecucion = False


def _seleccionar_escenario(raiz_proyecto: Path) -> Path:
    """Muestra los escenarios JSON disponibles y devuelve el elegido."""
    carpeta_escenarios = raiz_proyecto / "data" / "scenarios"
    escenarios = sorted(
        carpeta_escenarios.glob("*.json"),
        key=lambda ruta: ruta.name.casefold(),
    )
    if not escenarios:
        raise FileNotFoundError(
            f"No hay escenarios .json en {carpeta_escenarios}."
        )

    print("\nEscenarios disponibles:")
    for indice, ruta in enumerate(escenarios, start=1):
        print(f"  {indice}. {ruta.name}")
    print("También puedes escribir una ruta a un archivo JSON.")

    while True:
        seleccion = input(
            f"Elige un escenario [1-{len(escenarios)}] "
            "(Enter para el primero): "
        ).strip()
        if not seleccion:
            return escenarios[0]

        try:
            indice = int(seleccion)
        except ValueError:
            ruta_escrita = Path(seleccion)
            if ruta_escrita.name == seleccion:
                coincidencias = [
                    ruta
                    for ruta in escenarios
                    if ruta.name.casefold() == seleccion.casefold()
                ]
                if coincidencias:
                    return coincidencias[0]
            if not ruta_escrita.is_absolute():
                ruta_escrita = raiz_proyecto / ruta_escrita
            if ruta_escrita.is_file() and ruta_escrita.suffix.casefold() == ".json":
                return ruta_escrita
            print("No se encontró un escenario JSON con ese nombre o ruta.")
            continue

        if 1 <= indice <= len(escenarios):
            return escenarios[indice - 1]
        print(f"Selecciona un número entre 1 y {len(escenarios)}.")


def main() -> None:
    """Ejecuta la integración completa y abre la interfaz de Tkinter."""
    raiz_proyecto = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Wave Picking System")
    parser.add_argument(
        "escenario",
        nargs="?",
        help=(
            "Ruta a un escenario JSON. Si se omite, se muestra la lista "
            "de escenarios disponibles."
        ),
    )
    argumentos = parser.parse_args()
    if argumentos.escenario:
        ruta_escenario = Path(argumentos.escenario)
        if not ruta_escenario.is_absolute():
            ruta_escenario = raiz_proyecto / ruta_escenario
    else:
        ruta_escenario = _seleccionar_escenario(raiz_proyecto)

    print("=== Wave Picking System ===")
    print(f"1. Cargando escenario: {ruta_escenario}")
    warehouse, productos_raw, pedidos_raw, pickers_raw, configuracion = (
        cargar_escenario(str(ruta_escenario))
    )

    print("2. Creando inventario, pedidos y pickers")
    productos = _crear_productos(productos_raw)
    inventario = GestorInventario()
    for producto in productos:
        inventario.agregar_producto(producto)
    pedidos = _crear_pedidos(pedidos_raw)
    pickers = _crear_pickers(pickers_raw)
    _validar_stock_pedidos(pedidos, inventario)

    print("3. Construyendo grafo de circulación")
    grafo = construir_grafo(warehouse)
    if grafo.node_count() == 0:
        raise ValueError("El almacén no contiene celdas transitables.")

    print("4. Generando waves y asignándolas a los pickers")
    waves, _, waves_por_picker = _crear_waves(
        pedidos, pickers, inventario, configuracion
    )
    print(f"   Waves generadas: {len(waves)}")

    print("5. Preparando rutas dinámicas y zonas de despacho")
    cache = CacheDistancias(grafo)
    puntos_despacho = _obtener_puntos_despacho(warehouse, grafo)
    if waves and not puntos_despacho:
        raise ValueError(
            "No hay zonas de despacho accesibles asociadas a una puerta "
            "de salida."
        )
    fases = _crear_fases_simulacion(pickers, waves_por_picker)

    print(
        f"6. Iniciando motor de simulación: {len(waves)} waves "
        f"en {len(fases)} fases de viaje"
    )
    simulacion = _SimulationTk(
        warehouse=warehouse,
        pickers=pickers,
        productos=productos,
        fases=fases,
        cache_distancias=cache,
        puntos_despacho=puntos_despacho,
    )

    print("7. Abriendo visualización Tkinter")
    ventana = Ventana(warehouse, tamano_celda=16)
    simulacion.vincular_interfaz(
        ventana.root, ventana.actualizar_desde_simulacion
    )
    ventana.set_simulacion(simulacion)
    ventana.actualizar_desde_simulacion()
    ventana.iniciar()


if __name__ == "__main__":
    main()