# Contrato de interfaces — Sistema de Wave Picking

**Proyecto:** Algoritmos y Estructuras de Datos II
**Versión:** 1.0
**Estado:** Propuesta en español para acordar con el equipo

Este documento define los nombres y las firmas que deben usar los módulos para
poder integrarse. Los nombres de archivos y paquetes existentes se mantienen.
Las interfaces marcadas como propuestas todavía no están implementadas; cada
responsable debe confirmar este contrato antes de programarlas.

## Acuerdos de integración

1. Los nombres públicos y las firmas de este documento son el punto de
   encuentro entre módulos. No cambiar una firma sin avisar al equipo y
   actualizar este documento.
2. Cada integrante modifica los archivos que tiene asignados. Para integrar o
   modificar el trabajo de otra persona, coordinarlo primero.
3. Las coordenadas se expresan como `(x, y)`. En la grilla se accede como
   `grilla[y][x]`.
4. Los identificadores son cadenas (`str`). Las cantidades y dimensiones son
   enteros; los pesos y distancias pueden ser números decimales.
5. Las excepciones documentadas forman parte de la interfaz: no reemplazarlas
   por valores de éxito predeterminados.

## Modelo y carga de datos — Etapa 1

### `src/core/cell.py`

```python
VACIA: str
PASILLO: str
RACK: str
PUERTA: str
DESPACHO: str

N: str
S: str
E: str
O: str
AMBOS: str

class Celda:
    def __init__(self, x: int, y: int) -> None: ...
    x: int
    y: int
    tipo: str
    sentido: str
    ref_id: str | None
    def es_transitable(self) -> bool: ...
    def es_adyacente_a_transitable(self) -> bool: ...
    def __repr__(self) -> str: ...

class Rectangulo:
    def __init__(
        self, elemento_id: str, x: int, y: int, ancho: int, alto: int
    ) -> None: ...
    id: str
    x: int
    y: int
    ancho: int
    alto: int
    def celdas(self) -> list[tuple[int, int]]: ...
    def contiene(self, x: int, y: int) -> bool: ...

class Rack(Rectangulo):
    def __init__(
        self, rack_id: str, x: int, y: int, ancho: int, alto: int
    ) -> None: ...
    # Regla: ancho == 2 o alto == 2.

class Pasillo(Rectangulo):
    def __init__(
        self, pasillo_id: str, x: int, y: int, ancho: int, alto: int,
        sentido: str
    ) -> None: ...
    # sentido: N, S, E, O o AMBOS.

class Puerta:
    def __init__(
        self, puerta_id: str, tipo: str, x: int, y: int
    ) -> None: ...
    # tipo: INBOUND, OUTBOUND o AMBOS; debe ubicarse en el borde.

class ZonaDespacho(Rectangulo):
    def __init__(
        self, zona_id: str, puerta_id: str, x: int, y: int,
        ancho: int, alto: int, peso_max_kg: float
    ) -> None: ...
```

### `src/core/warehouse.py`

```python
class Warehouse:
    def __init__(self, ancho_x: int, largo_y: int) -> None: ...
    ancho_x: int
    largo_y: int
    grilla: list[list[Celda]]  # grilla[y][x]
    racks: dict[str, Rack]
    pasillos: dict[str, Pasillo]
    puertas: dict[str, Puerta]
    zonas: dict[str, ZonaDespacho]

    def agregar_rack(self, rack: Rack) -> None: ...
    def agregar_pasillo(self, pasillo: Pasillo) -> None: ...
    def agregar_puerta(self, puerta: Puerta) -> None: ...
    def agregar_zona_despacho(self, zona: ZonaDespacho) -> None: ...
    def rellenar_pasillos_implicitos(self) -> None: ...
    def imprimir_ascii(self) -> None: ...
```

`rellenar_pasillos_implicitos` convierte las celdas vacías en pasillos
transitables de sentido `AMBOS`.

### `src/core/inventory.py`

Estas son las interfaces que ya existen en el código. Se documentan con sus
nombres actuales para evitar romper el módulo durante la integración.

```python
class Producto:
    def __init__(
        self, producto_id: str, nombre: str, rack_id: str,
        ubicacion: tuple, cantidad_disponible: int = 0, peso_kg: float = 0.0
    ) -> None: ...
    producto_id: str
    nombre: str
    rack_id: str
    ubicacion: tuple  # (x, y, z)
    cantidad_disponible: int
    peso_kg: float
    def para_diccionario(self) -> dict: ...
    @staticmethod
    def del_diccionario(datos: dict) -> "Producto": ...

class HashTable:
    def __init__(self, capacidad: int = 16) -> None: ...
    def insertarHT(self, clave, valor) -> None: ...
    def buscarHT(self, clave): ...       # KeyError si no existe.
    def obtenerHT(self, clave, default=None): ...
    def eliminarHT(self, clave) -> None: ...  # KeyError si no existe.
    def contieneHT(self, clave) -> bool: ...
    def factorDeCarga(self) -> float: ...
    def __len__(self) -> int: ...

class GestorInventario:
    def __init__(self) -> None: ...
    def agregar_producto(self, producto: Producto) -> None: ...
    def obtener_producto(self, producto_id: str) -> Producto: ...
    def eliminar_producto(self, producto_id: str) -> Producto: ...
    def tiene_producto(self, producto_id: str) -> bool: ...
    def reservar_stock(self, producto_id: str, cantidad: int) -> bool: ...
    def actualizar_stock(self, producto_id: str, delta: int) -> int: ...
    def obtener_ubicacion(self, producto_id: str) -> tuple: ...
    def todos_los_productos(self) -> list[Producto]: ...
    def __len__(self) -> int: ...
```

`agregar_producto` lanza `ValueError` si el identificador ya existe.
`reservar_stock` lanza `ValueError` si la cantidad es inválida o no hay stock
suficiente. Las búsquedas y eliminaciones lanzan `KeyError` si el producto no
existe.

### `src/core/order.py`

```python
PENDIENTE: str
EN_WAVE: str
EN_PREPARACION: str
PREPARADO: str

class Orden:
    def __init__(
        self, orden_id: str, prioridad: int,
        items: list[tuple[str, int]], estado: str = PENDIENTE
    ) -> None: ...
    orden_id: str
    prioridad: int  # de 1 a 5
    estado: str
    items: list[tuple[str, int]]  # (producto_id, cantidad)
    def peso_total(self, inventario: GestorInventario) -> float: ...
    def cambiar_estado(self, nuevo_estado: str) -> None: ...
    def esta_pendiente(self) -> bool: ...
    def to_dict(self) -> dict: ...
    @staticmethod
    def del_dict(datos: dict) -> "Orden": ...
```

### `src/core/wave.py`

```python
class Wave:
    def __init__(
        self, wave_id: str, capacidad_max_pedidos: int,
        capacidad_max_productos: int, peso_max_kg: float
    ) -> None: ...
    id: str
    pedidos: list[Orden]
    capacidad_max_pedidos: int
    capacidad_max_productos: int
    peso_max_kg: float
    recorrido_A: list[int] | None
    recorrido_B: list[int] | None
    def peso_total(self, inventario: GestorInventario) -> float: ...
    def cantidad_productos(self) -> int: ...
    def puede_aceptar(
        self, orden: Orden, inventario: GestorInventario
    ) -> bool: ...
    def agregar_pedido(
        self, orden: Orden, inventario: GestorInventario
    ) -> bool: ...
    def __len__(self) -> int: ...
```

### `src/core/picker.py`

```python
class Picker:
    def __init__(
        self, preparador_id: str, posicion_inicial: tuple,
        capacidad_carga_kg: float
    ) -> None: ...
    id: str
    posicion_inicial: tuple  # (x, y)
    posicion_actual: tuple
    capacidad_carga_kg: float
    carga_actual_kg: float
    items_transportados: list[tuple[str, int]]
    def puede_recoger(self, producto: Producto, cantidad: int) -> bool: ...
    def recoger(self, producto: Producto, cantidad: int) -> None: ...
    def mover_a(self, nueva_posicion: tuple) -> None: ...
    def para_diccionario(self) -> dict: ...
    @staticmethod
    def del_diccionario(datos: dict) -> "Picker": ...
```

### `src/io/scenario_loader.py`

```python
def cargar_escenario(ruta_json: str) -> tuple[
    Warehouse, list[dict], list[dict], list[dict], dict
]: ...
```

Devuelve `(almacen, productos_raw, pedidos_raw, preparadores_raw, config)`.
`config` contiene `wave_max_pedidos` y `wave_max_productos`. Lanza
`FileNotFoundError` si no existe el archivo y `ValueError` si el JSON no es
válido.

## Grafos y recorridos — Etapa 2

### `src/core/graph_builder.py`

```python
class Grafo:
    def __init__(self) -> None: ...
    def agregar_nodo(self, nodo_id: int, datos=None) -> None: ...
    def agregar_arista(self, origen: int, destino: int, peso: float) -> None: ...
    def obtener_vecinos(self, nodo_id: int) -> dict[int, float]: ...
    def tiene_nodo(self, nodo_id: int) -> bool: ...
    def cantidad_nodos(self) -> int: ...
    def cantidad_aristas(self) -> int: ...

def construir_grafo(warehouse: Warehouse) -> Grafo: ...
```

El grafo contiene nodos para las celdas de pasillo y aristas dirigidas para
conexiones permitidas por el sentido del pasillo. Cada movimiento adyacente
pesa `1`.

### `src/algorithms/pathfinding.py`

```python
def dijkstra(
    grafo: Grafo, origen: int, destino: int | None = None
) -> tuple: ...

def matriz_distancias(grafo: Grafo, nodos: list[int]) -> dict: ...

def estrategia_A(
    grafo: Grafo, wave: Wave, warehouse: Warehouse,
    inventario: GestorInventario
) -> list[int]: ...

def estrategia_B(
    grafo: Grafo, wave: Wave, warehouse: Warehouse,
    inventario: GestorInventario
) -> list[int]: ...
```

`dijkstra` devuelve `(distancias, predecesores)` sin destino, o
`(distancia, camino)` cuando se especifica un destino. La estrategia A sigue
el orden de los pedidos; la B elige el siguiente vecino más cercano.

## Generación de waves — Etapa 3

### `src/algorithms/wave_manager.py`

```python
def generar_waves(
    ordenes: list[Orden], inventario: GestorInventario,
    warehouse: Warehouse, config: dict
) -> list[Wave]: ...

def ordenar_por_prioridad(ordenes: list[Orden]) -> list[Orden]: ...
```

La generación toma órdenes pendientes en prioridad descendente, inicia cada
wave con la orden más prioritaria y agrega órdenes cercanas mientras se
respeten las capacidades máximas de pedidos, unidades y peso.
La cercanía se calcula con distancia Manhattan entre ubicaciones de productos.
El límite de peso de una wave es el menor peso máximo entre las zonas de despacho.

## Simulación e interfaz — Etapa 4

### `src/simulation/simulation.py`

```python
INACTIVA: str
CORRIENDO: str
PAUSADA: str
TERMINADA: str

class Simulacion:
    def __init__(
        self, warehouse: Warehouse, inventario: GestorInventario,
        waves: list[Wave], pickers: list[Picker], grafo: Grafo
    ) -> None: ...
    warehouse: Warehouse
    inventario: GestorInventario
    waves: list[Wave]
    pickers: list[Picker]
    grafo: Grafo
    estado: str
    paso: int
    def iniciar(self) -> None: ...
    def pausar(self) -> None: ...
    def reanudar(self) -> None: ...
    def resetear(self) -> None: ...
    def avanzar_paso(self) -> None: ...
    def obtener_estado(self) -> dict: ...
```

`obtener_estado` devuelve un diccionario con `estado`, `paso`, `pickers`,
`wave_actual` e `items_recogidos`.

### `src/ui/visualization.py`

```python
class Ventana:
    def __init__(self, simulacion: Simulacion) -> None: ...
    def dibujar_almacen(self) -> None: ...
    def dibujar_preparadores(self) -> None: ...
    def dibujar_recorrido(self, ola_id: str) -> None: ...
    def actualizar(self) -> None: ...
    def iniciar(self) -> None: ...
```

### `main.py`

```python
def main() -> None: ...
```

El punto de entrada carga el escenario, construye las entidades e inventario,
construye el grafo, genera las olas, calcula los recorridos e inicia la
simulación y la ventana.

## Correspondencia con `CONTATRO.md`

El archivo `CONTATRO.md` contiene la versión anterior del contrato, con varios
nombres en inglés. Para evitar dos fuentes contradictorias, el equipo debe
confirmar esta versión en español y considerar este documento como la versión
vigente antes de implementar las interfaces que aún faltan. Los nombres del
módulo de inventario se mantienen tal como están escritos en el código actual.