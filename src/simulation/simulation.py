"""Motor paso a paso para el movimiento y la recolección de pickers.

La clase mantiene el estado temporal de la simulación: posición de cada picker,
cuánto avanzó su ruta, demanda todavía pendiente, productos recolectados y
distancia recorrida. No calcula rutas; recibe las rutas ya preparadas y aplica
cada movimiento en sincronía para poder resolver colisiones entre pickers.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    # Si este archivo se ejecuta directamente, Python agrega a sys.path la
    # carpeta src/simulation, no la raíz del repositorio. Agregamos esa raíz
    # para que los imports absolutos del proyecto también funcionen en ese caso.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.core.inventory import Producto
from src.core.picker import Picker


class Simulation:
    """Coordina rutas, colisiones y recolección durante una simulación.

    Cada ruta es una secuencia de coordenadas (x, y). En cada tick se calcula
    primero el movimiento pretendido de todos los pickers y luego se decide qué
    movimientos son compatibles. Así la decisión no depende de mover a uno y
    cambiar el estado antes de evaluar a los demás.

    Args:
        warehouse: Mapa del almacén; se usa para encontrar el pasillo contiguo
            desde el cual se accede a una ubicación de producto.
        pickers: Pickers ya construidos o diccionarios con sus datos iniciales.
        rutas: Rutas por id, por índice de picker o una única ruta plana.
        productos: Productos como objetos, diccionarios o colección de inventario.
        pedidos: Pedidos que definen la demanda si no se indican asignaciones.
        inventario: Inventario alternativo para obtener los productos.
        asignaciones: Demanda asignada por id de picker. Cuando se proporciona,
            la recolección se limita a la asignación individual.
    """

    def __init__(
        self,
        warehouse: Any,
        pickers: list[Any],
        rutas: Any = None,
        productos: Any = None,
        pedidos: Any = None,
        inventario: Any = None,
        asignaciones: dict[str, Any] | None = None,
    ) -> None:
        # Normalizar los pickers antes de usar sus identificadores y posiciones.
        self.warehouse = warehouse
        self.pickers = [
            self._crear_picker(picker) for picker in pickers
        ]
        # paso_actual cuenta ticks globales. Cada picker tiene además un índice
        # independiente porque puede esperar y avanzar menos que los demás.
        self.paso_actual = 0
        self._rutas = {
            picker.id: self._obtener_ruta(
                rutas, picker, indice, len(self.pickers) == 1
            )
            for indice, picker in enumerate(self.pickers)
        }
        # Si la ruta incluye la posición de partida como primer nodo, ese nodo ya
        # está ocupado y no requiere un movimiento; por eso se empieza en 1.
        self._indices_ruta = {
            picker.id: (
                1
                if self._rutas[picker.id]
                and self._rutas[picker.id][0] == tuple(picker.posicion_actual)
                else 0
            )
            for picker in self.pickers
        }
        # Las búsquedas frecuentes se hacen por id de producto, no recorriendo
        # repetidamente una lista o consultando distintas formas de inventario.
        self._productos = self._indexar_productos(productos, inventario)
        self._demanda_por_picker: dict[str, dict[str, int]] = {}
        self._demanda_global: dict[str, int] = {}
        self._asignaciones_explicitas = asignaciones is not None
        self._cargar_demanda(pedidos, asignaciones)
        # Copias separadas permiten que resetear() restaure la demanda aun
        # después de que las cantidades pendientes hayan sido consumidas.
        self._demanda_global_inicial = dict(self._demanda_global)
        self._demanda_por_picker_inicial = {
            picker_id: dict(demanda)
            for picker_id, demanda in self._demanda_por_picker.items()
        }
        self._total_productos = sum(self._demanda_global.values()) + sum(
            sum(demanda.values())
            for demanda in self._demanda_por_picker.values()
        )
        # Registro de eventos de recolección y métricas que consulta la interfaz.
        self.productos_recogidos: list[dict[str, Any]] = []
        self.distancia = 0
        self._en_ejecucion = False
        # Guardar el stock y estado iniciales para devolver el modelo a su
        # condición original cuando el usuario presione reiniciar.
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
        # Si un picker ya empieza sobre un punto de recolección, recoger también
        # en el estado inicial, sin exigir un movimiento previo.
        self._recoger_en_posiciones_actuales()

    @staticmethod
    def _crear_picker(picker: Any) -> Any:
        """Convierte la representación de escenario en un objeto Picker.

        Los objetos Picker ya existentes se reutilizan. Los diccionarios de
        escenarios usan coordenadas con claves x/y, mientras que Picker recibe
        una tupla; esta función adapta ese formato al constructor de la clase.
        """
        if not isinstance(picker, dict):
            return picker
        ubicacion = picker["posicion_inicial"]
        if isinstance(ubicacion, dict):
            ubicacion = (ubicacion["x"], ubicacion["y"])
        return Picker(
            picker.get("id", picker.get("picker_id")),
            tuple(ubicacion),
            picker["capacidad_carga_kg"],
        )

    @staticmethod
    def _obtener_ruta(
        rutas: Any, picker: Any, indice: int, es_unico_picker: bool
    ) -> list[tuple[int, int]]:
        """Obtiene y valida la ruta de un picker en los formatos aceptados.

        Se admite un diccionario indexado por id (o índice), una lista de rutas
        por picker y una sola lista plana de coordenadas para una simulación de
        un picker. La salida siempre es una lista de tuplas de enteros.
        """
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

        # Validar la forma de cada nodo y normalizar listas JSON a tuplas.
        resultado = []
        for punto in ruta:
            if not isinstance(punto, (tuple, list)) or len(punto) != 2:
                raise ValueError(f"Coordenada de ruta inválida: {punto!r}.")
            resultado.append((int(punto[0]), int(punto[1])))
        return resultado

    @staticmethod
    def _indexar_productos(productos: Any, inventario: Any) -> dict[str, Any]:
        """Construye un índice producto_id -> producto desde distintas fuentes.

        Si no se pasó la lista de productos, se intenta leer del inventario.
        Los datos crudos en forma de diccionario se convierten a Producto para
        que Picker.recoger() reciba el tipo de objeto que espera.
        """
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
                # El id puede estar en la clave del diccionario y no dentro del
                # objeto serializado, por eso se pasa como valor de respaldo.
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
        """Adapta un producto serializado al modelo Producto del proyecto."""
        ubicacion = datos["ubicacion"]
        if isinstance(ubicacion, dict):
            # Los JSON describen la ubicación con x/y/z; el modelo almacena
            # esas coordenadas como una tupla.
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
        """Lee el primer atributo disponible, tanto de objetos como de dicts.

        Esta pequeña adaptación permite aceptar los objetos del dominio y los
        diccionarios crudos que devuelve el cargador de escenarios.
        """
        for nombre in nombres:
            if isinstance(objeto, dict) and nombre in objeto:
                return objeto[nombre]
            if hasattr(objeto, nombre):
                return getattr(objeto, nombre)
        return default

    @staticmethod
    def _items_de_pedido(pedido: Any) -> list[tuple[str, int]]:
        """Devuelve los items de un pedido en el formato (id, cantidad).

        Cada item puede ser un par como usa Orden o un diccionario como aparece
        en el JSON. Se rechazan ids vacíos y cantidades que no sean enteros
        positivos para no introducir una demanda inválida en la simulación.
        """
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
        """Prepara las cantidades que la simulación debe recolectar.

        Sin asignaciones, toda la demanda se comparte como demanda global.
        Con asignaciones explícitas, se guarda por picker para impedir que un
        picker recoja los productos asignados a otro.
        """
        if pedidos is not None and asignaciones is None:
            # Wave expone sus órdenes en .pedidos; también se admite una lista
            # normal o un diccionario indexado por id.
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
                    # Una asignación puede ser un item individual, una tupla
                    # (producto_id, cantidad) o un pedido completo.
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
        """Calcula dónde se para el picker para acceder a un producto.

        La coordenada del producto suele estar dentro de un rack. Si hay
        almacén, se busca una celda PASILLO ortogonal adyacente y se devuelve
        esa coordenada transitable. Sin mapa se usa directamente la ubicación
        del producto, útil para escenarios simplificados o pruebas.
        """
        ubicacion = self._valor(producto, "ubicacion")
        if isinstance(ubicacion, dict):
            x, y = int(ubicacion["x"]), int(ubicacion["y"])
        else:
            x, y = int(ubicacion[0]), int(ubicacion[1])

        if self.warehouse is None or not hasattr(self.warehouse, "grid"):
            return x, y
        # Revisar primero derecha, izquierda, arriba y abajo; el primer pasillo
        # encontrado es el punto de acceso elegido para la recolección.
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
        """Consulta cuántas unidades de un producto le faltan por recoger."""
        if self._asignaciones_explicitas:
            return self._demanda_por_picker.get(picker.id, {}).get(producto_id, 0)
        return self._demanda_global.get(producto_id, 0)

    def _reducir_demanda(self, picker: Any, producto_id: str, cantidad: int) -> None:
        """Resta de la demanda las unidades recogidas y elimina ceros."""
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
        """Recolecta los productos pendientes accesibles desde la posición actual.

        Antes de recoger se valida que el producto exista y que haya stock. El
        picker valida a su vez que su capacidad de carga sea suficiente. Solo
        después de una recolección exitosa se descuenta stock/demanda y se
        registra el evento, evitando contabilizar una operación fallida.
        """
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
                # Picker.recoger actualiza su carga y los items transportados.
                picker.recoger(producto, cantidad)
            else:
                # Permite usar pickers ficticios en pruebas, siempre que
                # implementen al menos los atributos básicos de estado.
                peso = float(self._valor(producto, "peso_kg", default=0.0))
                picker.carga_actual_kg = getattr(picker, "carga_actual_kg", 0.0) + (
                    peso * cantidad
                )
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

    def _recoger_en_posiciones_actuales(self) -> None:
        """Evalúa las posiciones iniciales de todos los pickers."""
        for picker in self.pickers:
            self._recoger_en_posicion(picker)

    def avanzar_paso(self) -> bool:
        """Avanza un tick y devuelve si quedan movimientos pendientes.

        El procesamiento tiene varias fases:
        1. Recolectar los movimientos pretendidos sin mover a nadie.
        2. Resolver destinos compartidos dando prioridad al orden de pickers.
        3. Cancelar movimientos hacia pickers que esperan y cruces de posiciones.
        4. Aplicar los movimientos aprobados, medir distancia y recoger productos.

        El índice de ruta solo avanza cuando el picker se mueve. Si espera, el
        mismo nodo queda pendiente para el próximo tick. El retorno es False si
        no queda ningún movimiento por realizar.
        """
        # Mapa picker_id -> destino solicitado en el tick actual. No contiene
        # pickers que ya completaron sus rutas.
        propuestas: dict[str, tuple[int, int]] = {}
        for picker in self.pickers:
            ruta = self._rutas[picker.id]
            indice = self._indices_ruta[picker.id]
            if indice < len(ruta):
                propuestas[picker.id] = ruta[indice]

        if not propuestas:
            self._en_ejecucion = False
            return False

        # Un tick transcurre si había al menos un movimiento por intentar,
        # incluso si una colisión termina haciendo esperar a todos.
        self.paso_actual += 1
        # Agrupar por destino para detectar simultáneamente las solicitudes
        # conflictivas; así todos los pickers compiten en el mismo tick.
        destinos: dict[tuple[int, int], list[Any]] = {}
        for picker in self.pickers:
            if picker.id in propuestas:
                destinos.setdefault(propuestas[picker.id], []).append(picker)

        aceptados: set[str] = set()
        for pickers_destino in destinos.values():
            # La lista recibida define la prioridad principal. El id sirve
            # como criterio estable en caso de igualdad de posición en lista.
            ganador = min(
                pickers_destino,
                key=lambda picker: (
                    self.pickers.index(picker),
                    str(picker.id),
                ),
            )
            aceptados.add(ganador.id)

        # Si un picker no ganó, se queda en su posición. Ningún otro picker
        # puede entrar en esa celda; la iteración se repite porque cancelar un
        # movimiento puede dejar bloqueado a un picker adicional detrás de él.
        cambio = True
        while cambio:
            cambio = False
            posiciones_ocupadas = {
                tuple(picker.posicion_actual): picker.id
                for picker in self.pickers
                if picker.id not in aceptados
            }
            for picker in self.pickers:
                if picker.id not in aceptados:
                    continue
                ocupante = posiciones_ocupadas.get(propuestas[picker.id])
                if ocupante is not None:
                    aceptados.remove(picker.id)
                    cambio = True

        # También se impide que dos pickers se crucen en un solo tick mediante
        # el intercambio directo de sus celdas actuales.
        for indice, picker in enumerate(self.pickers):
            if picker.id not in aceptados:
                continue
            for otro in self.pickers[indice + 1 :]:
                if (
                    otro.id in aceptados
                    and propuestas[picker.id] == tuple(otro.posicion_actual)
                    and propuestas[otro.id] == tuple(picker.posicion_actual)
                ):
                    aceptados.remove(picker.id)
                    aceptados.remove(otro.id)

        # Aplicar únicamente los movimientos ya validados. Al modificar posición
        # e índice aquí, un picker rechazado conserva exactamente su paso.
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
            self._recoger_en_posicion(picker)

        # Aún puede haber trabajo aunque un picker haya terminado; por ejemplo,
        # si otro tuvo que esperar y conserva un nodo pendiente en su ruta.
        quedan_pasos = any(
            self._indices_ruta[picker.id] < len(self._rutas[picker.id])
            for picker in self.pickers
        )
        self._en_ejecucion = quedan_pasos
        return quedan_pasos

    def get_estado(self) -> dict[str, Any]:
        """Devuelve una instantánea del estado actual.

        La UI espera x/y/id para dibujar pickers; además se ofrecen carga,
        paso, rutas, cantidad recogida, total solicitado, distancia acumulada
        y el detalle de cada recolección. Se crean listas/dicts nuevos para que
        el consumidor no altere directamente las estructuras internas.
        """
        return {
            "paso_actual": self.paso_actual,
            "pickers": [
                {
                    "id": picker.id,
                    "x": picker.posicion_actual[0],
                    "y": picker.posicion_actual[1],
                    "carga_actual_kg": picker.carga_actual_kg,
                }
                for picker in self.pickers
            ],
            "rutas": [list(self._rutas[picker.id]) for picker in self.pickers],
            "productos_recogidos": sum(
                item["cantidad"] for item in self.productos_recogidos
            ),
            "total_productos": self._total_productos,
            "distancia": self.distancia,
            "recolecciones": [dict(item) for item in self.productos_recogidos],
        }

    def iniciar(self) -> None:
        """Marca la simulación como activa para un controlador externo."""
        self._en_ejecucion = True

    def pausar(self) -> None:
        """Marca la simulación como pausada sin modificar su estado."""
        self._en_ejecucion = False

    def resetear(self) -> None:
        """Restaura la simulación al estado inicial.

        Se restauran posiciones/cargas de los pickers, los índices de ruta,
        contadores, demanda pendiente y stock. Al final se vuelve a procesar
        cualquier recolección que corresponda a una posición inicial.
        """
        # Restaurar primero cada picker para que las rutas vuelvan a comenzar
        # desde la misma ubicación que tenían al construir la simulación.
        for picker in self.pickers:
            inicial = self._estado_inicial[picker.id]
            picker.mover_a(inicial["posicion"])
            picker.items_transportados = list(inicial["items"])
            picker.carga_actual_kg = inicial["carga"]
        # Si la ruta empieza con la posición inicial, se salta de nuevo ese
        # primer nodo ya ocupado; en otro caso se vuelve al índice cero.
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
        self.productos_recogidos.clear()
        self._en_ejecucion = False
        # Las cantidades iniciales se guardaron como copias en el constructor,
        # porque las estructuras activas se modifican durante la recolección.
        self._demanda_global = dict(self._demanda_global_inicial)
        self._demanda_por_picker = {
            picker_id: dict(demanda)
            for picker_id, demanda in self._demanda_por_picker_inicial.items()
        }
        for producto_id, stock in self._stock_inicial.items():
            if stock is not None:
                self._productos[producto_id].cantidad_disponible = stock
        self._recoger_en_posiciones_actuales()


if __name__ == "__main__":
    # Prueba ejecutable independiente: ambos pickers intentan ir a (1, 0) en
    # el primer tick. PK_01 tiene prioridad por aparecer primero en la lista;
    # PK_02 espera, y en los ticks posteriores continúa su ruta pendiente.
    desde_a = Picker("PK_01", (0, 0), 10)
    desde_b = Picker("PK_02", (2, 0), 10)
    simulacion = Simulation(
        warehouse=None,
        pickers=[desde_a, desde_b],
        rutas={
            "PK_01": [(0, 0), (1, 0), (1, 1), (2, 1)],
            "PK_02": [(2, 0), (1, 0), (0, 0)],
        },
    )
    # Mostrar hasta tres ticks y detenerse antes si todas las rutas terminan.
    for _ in range(3):
        quedan = simulacion.avanzar_paso()
        print(f"Paso {simulacion.paso_actual}: {simulacion.get_estado()['pickers']}")
        if not quedan:
            break