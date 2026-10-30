"""Punto de entrada que integra los módulos del Wave Picking System."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Callable

from src.algorithms.pathfinding import (
    CacheDistancias,
    estrategia_A,
    estrategia_B,
    obtener_puntos_de_interes,
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
                datos["id"],
                tuple(posicion),
                datos["capacidad_carga_kg"],
            )
        )
    return pickers


def _validar_stock_pedidos(
    pedidos: list[Orden],
    inventario: GestorInventario,
) -> None:
    """Rechaza escenarios cuya demanda total supera el stock disponible."""
    demanda_por_producto: dict[str, int] = {}
    for pedido in pedidos:
        for producto_id, cantidad in pedido.items:
            demanda_por_producto[producto_id] = (
                demanda_por_producto.get(producto_id, 0) + cantidad
            )

    faltantes = []
    for producto_id, demanda in demanda_por_producto.items():
        producto = inventario.obtener_producto(producto_id)
        if demanda > producto.cantidad_disponible:
            faltantes.append(
                f"{producto_id}: se piden {demanda}, "
                f"hay {producto.cantidad_disponible}"
            )
    if faltantes:
        detalle = "; ".join(faltantes)
        raise ValueError(
            "El escenario tiene pedidos que superan el stock disponible: "
            f"{detalle}."
        )


def _crear_waves(
    pedidos: list[Orden],
    pickers: list[Picker],
    inventario: GestorInventario,
    configuracion: dict[str, Any],
) -> tuple[list[Wave], dict[str, list[Orden]], dict[str, list[Wave]]]:
    """Distribuye pedidos en waves que respetan capacidades y picker asignado.

    Cada orden se asigna al picker con menor carga en su wave actual que pueda
    transportarla. Al llenarse una wave, ese picker puede recibir otra para un
    viaje posterior; la carga se reinicia entre viajes.
    """
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

    for pedido in pedidos:
        peso_pedido = pedido.peso_total(inventario)
        candidatos = sorted(
            pickers,
            key=lambda picker: (carga_wave_actual[picker.id], picker.id),
        )
        asignado = False

        for picker in candidatos:
            wave = wave_actual.get(picker.id)
            if wave is None or not wave.puede_aceptar(pedido, inventario):
                nueva_wave = Wave(
                    wave_id=f"WAVE_{siguiente_wave_id:03d}",
                    capacidad_max_pedidos=max_pedidos,
                    capacidad_max_productos=max_productos,
                    peso_max_kg=picker.capacidad_carga_kg,
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
                f"El pedido {pedido.orden_id} excede la capacidad de carga "
                "de todos los pickers o los límites de una wave."
            )

    return waves, pedidos_por_picker, waves_por_picker


def _calcular_ruta_picker(
    picker: Picker,
    waves: list[Wave],
    grafo: Any,
    warehouse: Any,
    inventario: GestorInventario,
    cache: CacheDistancias,
    estrategia: Callable[..., dict[str, Any]],
    volver_a_inicio: bool = False,
) -> list[tuple[int, int]]:
    """Construye la ruta de un picker, incluyendo el trayecto inicial.

    Las estrategias del proyecto calculan el orden/camino entre ubicaciones de
    productos, empezando en el primer producto de la wave. Esta función agrega
    el tramo desde la posición inicial (o la última wave) hasta ese primer
    producto y concatena las rutas de todas las waves asignadas.
    """
    ruta_completa: list[tuple[int, int]] = []
    posicion_inicial = tuple(picker.posicion_actual)
    posicion_actual = posicion_inicial

    for wave in waves:
        if volver_a_inicio:
            posicion_actual = posicion_inicial
        puntos = obtener_puntos_de_interes(wave, warehouse, inventario)
        if not puntos:
            continue

        tramo_inicial = cache.camino(posicion_actual, puntos[0])
        if not tramo_inicial:
            raise ValueError(
                f"No hay camino desde {posicion_actual} hasta el primer "
                f"punto de recolección {puntos[0]} del picker {picker.id}."
            )

        resultado_estrategia = estrategia(
            grafo, wave, warehouse, inventario, cache
        )
        tramo_estrategia = resultado_estrategia["ruta"]
        if not tramo_estrategia and len(set(puntos)) == 1:
            # Las estrategias no necesitan buscar un tramo entre productos si
            # una wave solo visita una ubicación distinta.
            tramo_estrategia = [puntos[0]]
        if any(punto not in tramo_estrategia for punto in puntos):
            raise ValueError(
                f"La estrategia no pudo incluir todos los puntos de "
                f"recolección de la wave {wave.id}."
            )

        if tramo_estrategia and tramo_inicial[-1] == tramo_estrategia[0]:
            tramo_inicial.extend(tramo_estrategia[1:])
        else:
            tramo_inicial.extend(tramo_estrategia)

        if ruta_completa and ruta_completa[-1] == tramo_inicial[0]:
            ruta_completa.extend(tramo_inicial[1:])
        else:
            ruta_completa.extend(tramo_inicial)
        posicion_actual = ruta_completa[-1]

        if volver_a_inicio:
            regreso = cache.camino(posicion_actual, posicion_inicial)
            if not regreso:
                raise ValueError(
                    f"No hay camino de regreso a la posición inicial "
                    f"{posicion_inicial} del picker {picker.id}."
                )
            ruta_completa.extend(regreso[1:])
            posicion_actual = posicion_inicial

    return ruta_completa


def _crear_fases_simulacion(
    pickers: list[Picker],
    waves_por_picker: dict[str, list[Wave]],
    grafo: Any,
    warehouse: Any,
    inventario: GestorInventario,
    cache: CacheDistancias,
) -> list[dict[str, Any]]:
    """Agrupa por turno las waves y rutas que ejecutarán todos los pickers.

    Cada ruta comienza y termina en la posición inicial del picker, que actúa
    como punto de entrega antes de que comience su siguiente wave.
    """
    fases = []

    cantidad_turnos = max(
        (len(waves_por_picker[picker.id]) for picker in pickers),
        default=0,
    )
    for indice_turno in range(cantidad_turnos):
        rutas = {}
        asignaciones = {}
        for picker in pickers:
            waves_picker = waves_por_picker[picker.id]
            if indice_turno >= len(waves_picker):
                continue
            wave = waves_picker[indice_turno]
            ruta_a = _calcular_ruta_picker(
                picker,
                [wave],
                grafo,
                warehouse,
                inventario,
                cache,
                estrategia_A,
                volver_a_inicio=True,
            )
            ruta_b = _calcular_ruta_picker(
                picker,
                [wave],
                grafo,
                warehouse,
                inventario,
                cache,
                estrategia_B,
                volver_a_inicio=True,
            )
            estrategia_elegida = "A" if len(ruta_a) <= len(ruta_b) else "B"
            ruta = ruta_a if estrategia_elegida == "A" else ruta_b
            print(
                f"   {picker.id}, {wave.id}: "
                f"A={max(len(ruta_a) - 1, 0)} pasos, "
                f"B={max(len(ruta_b) - 1, 0)} pasos; "
                f"se usa {estrategia_elegida}"
            )
            rutas[picker.id] = ruta
            asignaciones[picker.id] = wave.pedidos
        fases.append({"rutas": rutas, "asignaciones": asignaciones})

    # También permite abrir escenarios sin pedidos: la ventana mostrará el
    # almacén y la simulación finalizará sin movimientos.
    return fases or [{"rutas": {}, "asignaciones": {}}]


class _SimulationTk:
    """Ejecuta en paralelo los viajes de cada turno dentro de Tk."""

    def __init__(
        self,
        warehouse: Any,
        pickers: list[Picker],
        productos: list[Producto],
        fases: list[dict[str, Any]],
        intervalo_ms: int = 250,
    ) -> None:
        self.warehouse = warehouse
        self.pickers = pickers
        self.productos = productos
        self.fases = fases
        self.intervalo_ms = intervalo_ms
        self.fase_actual = 0
        self._root = None
        self._actualizar_interfaz: Callable[[], None] | None = None
        self._after_id = None
        self._en_ejecucion = False
        self._fase_completada = False
        self._productos_recogidos_acumulados = 0
        self._total_productos = sum(
            cantidad
            for fase in fases
            for pedidos_fase in fase["asignaciones"].values()
            for pedido in pedidos_fase
            for _, cantidad in pedido.items
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
        """Crea un motor común con las rutas del turno para toda la flota."""
        fase = self.fases[indice]
        return Simulation(
            warehouse=self.warehouse,
            pickers=self.pickers,
            rutas=fase["rutas"],
            productos=self.productos,
            asignaciones=fase["asignaciones"],
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
        recogidos_en_fase = (
            0
            if self._fase_completada
            else estado["productos_recogidos"]
        )
        estado["productos_recogidos"] = (
            self._productos_recogidos_acumulados + recogidos_en_fase
        )
        estado["total_productos"] = self._total_productos
        estado["wave_actual"] = self.fase_actual + 1
        estado["waves_totales"] = len(self.fases)
        # La interfaz muestra a toda la flota, incluso a quienes ya terminaron
        # su ruta del turno actual.
        estado["pickers"] = [
            {
                "id": picker.id,
                "x": picker.posicion_actual[0],
                "y": picker.posicion_actual[1],
                "carga_actual_kg": picker.carga_actual_kg,
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

        self._productos_recogidos_acumulados += self._simulacion_actual.get_estado()[
            "productos_recogidos"
        ]
        self._fase_completada = True
        self._descargar_pickers_de_fase()
        siguiente_fase = self.fase_actual + 1
        if siguiente_fase >= len(self.fases):
            self._en_ejecucion = False
            return False

        self.fase_actual = siguiente_fase
        self._simulacion_actual = self._crear_simulacion_fase(self.fase_actual)
        self._fase_completada = False
        return True

    def _descargar_pickers_de_fase(self) -> None:
        """Descarga los pickers que terminaron la wave recién completada."""
        for picker_id in self.fases[self.fase_actual]["asignaciones"]:
            picker = next(
                picker for picker in self.pickers if picker.id == picker_id
            )
            picker.descargar()

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
    """Muestra los escenarios JSON disponibles y devuelve el elegido.

    La lista se vuelve a consultar cada vez que se ejecuta el programa, así
    cualquier escenario nuevo agregado a data/scenarios aparece sin modificar
    el código. También se acepta escribir el nombre o la ruta de otro JSON.
    """
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

    print("5. Calculando estrategias de recorrido A y B por wave")
    cache = CacheDistancias(grafo)
    fases = _crear_fases_simulacion(
        pickers, waves_por_picker, grafo, warehouse, inventario, cache
    )

    print(
        f"6. Iniciando motor de simulación: {len(waves)} waves "
        f"en {len(fases)} fases de viaje"
    )
    simulacion = _SimulationTk(
        warehouse=warehouse,
        pickers=pickers,
        productos=productos,
        fases=fases,
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
