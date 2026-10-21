# Contrato de Interfaces — Sistema de Wave Picking

**Proyecto**: Sistema de Wave Picking (UNCUYO — Algoritmos y Estructuras de Datos 2)
**Versión**: 1.0
**Fecha**: [COMPLETAR]
**Estado**: CONGELADO — no cambiar sin avisar al equipo

---

## Reglas del contrato

1. Cada módulo **expone** las clases y funciones listadas acá.
2. **Solo el dueño del módulo** modifica sus archivos.
3. Si alguien necesita cambiar una firma, **avisa al grupo primero** y se actualiza este archivo.
4. Los tipos entre paréntesis son **orientativos** (Python no los valida).
5. Los imports entre módulos deben respetar las flechas del diagrama:

---

## ETAPA 1 — Modelo físico y carga

### `src/core/cell.py` — dueño: [A]

**Constantes de módulo**:
```python
# Tipos de celda
VACIA, PASILLO, RACK, PUERTA, DESPACHO   # strings

# Sentidos de pasillo
N, S, E, O, AMBOS                        # strings
class Cell:
    def __init__(self, x: int, y: int)

    # Atributos públicos
    x        : int          # coordenada x
    y        : int          # coordenada y
    tipo     : str          # VACIA | PASILLO | RACK | PUERTA | DESPACHO
    sentido  : str          # N | S | E | O | AMBOS (solo aplica si tipo==PASILLO)
    ref_id   : str | None   # id del elemento padre (rack_id, puerta_id, etc.)

    # Métodos
    def es_transitable(self) -> bool
        """True si el picker puede pararse acá (solo PASILLO)."""

    def es_adyacente_a_transitable(self) -> bool
        """True si es RACK, PUERTA o DESPACHO."""

    def __repr__(self) -> str

    class Rectangulo:
    def __init__(self, elem_id: str, x: int, y: int, ancho: int, alto: int)

    id     : str
    x      : int
    y      : int
    ancho  : int
    alto   : int

    def celdas(self) -> list[tuple[int, int]]
        """Lista de (x, y) del rectángulo."""

    def contiene(self, x: int, y: int) -> bool

    class Rack(Rectangulo):
    def __init__(self, rack_id, x, y, ancho, alto)
    # Regla: ancho == 2  O  alto == 2

class Pasillo(Rectangulo):
    def __init__(self, pas_id, x, y, ancho, alto, sentido)
    # sentido: "N" | "S" | "E" | "O" | "AMBOS"

class Puerta:
    def __init__(self, puerta_id, tipo, x, y)
    # tipo: "INBOUND" | "OUTBOUND" | "AMBOS"
    # Regla: (x, y) sobre el borde del warehouse

class ZonaDespacho(Rectangulo):
    def __init__(self, zona_id, puerta_id, x, y, ancho, alto, peso_max_kg)

    class Warehouse:
    def __init__(self, ancho_x: int, largo_y: int)

    ancho_x  : int
    largo_y  : int
    grid     : list[list[Cell]]        # grid[y][x] -> Cell
    racks    : dict[str, Rack]
    pasillos : dict[str, Pasillo]
    puertas  : dict[str, Puerta]
    zonas    : dict[str, ZonaDespacho]

    def add_rack(self, rack: Rack) -> None
    def add_pasillo(self, pasillo: Pasillo) -> None
    def add_puerta(self, puerta: Puerta) -> None
    def add_zona_despacho(self, zona: ZonaDespacho) -> None

    def rellenar_pasillos_implicitos(self) -> None
        """Celdas VACIAS → PASILLO con sentido AMBOS."""

    def print_ascii(self) -> None
        """Imprime el warehouse por consola (debug)."""

        def cargar_escenario(ruta_json: str) -> tuple:
    """
    Lee un archivo JSON y devuelve:
        (warehouse, productos_raw, pedidos_raw, pickers_raw, config)

    warehouse     : Warehouse ya construido
    productos_raw : list[dict]  (crudos del JSON)
    pedidos_raw   : list[dict]
    pickers_raw   : list[dict]
    config        : dict {wave_max_pedidos, wave_max_productos}

    Lanza FileNotFoundError si la ruta no existe.
    Lanza ValueError si el JSON es inválido.
    """

    class Product:
    def __init__(self, product_id, name, location, stock=0, peso_kg=0.0)

    product_id : str          # ej: "P001"
    name       : str          # ej: "Monitor 27"
    location   : tuple        # (x, y, z)  — z = altura del estante
    stock      : int
    peso_kg    : float

    def to_dict(self) -> dict
    @staticmethod
    def from_dict(d: dict) -> "Product"

    class HashTable:
    def __init__(self, capacity: int = 16)

    def insert(self, key, value) -> None
    def search(self, key) -> value               # KeyError si no existe
    def get(self, key, default=None) -> value
    def delete(self, key) -> None                # KeyError si no existe
    def contains(self, key) -> bool
    def load_factor(self) -> float
    def __len__(self) -> int

    class InventoryManager:
    def __init__(self)

    def add_product(self, product: Product) -> None
    def get_product(self, product_id: str) -> Product
    def remove_product(self, product_id: str) -> None
    def has_product(self, product_id: str) -> bool
    def reserve_stock(self, product_id: str, quantity: int) -> bool
    def update_stock(self, product_id: str, delta: int) -> int
    def get_location(self, product_id: str) -> tuple
    def all_products(self) -> iterator[Product]
    def __len__(self) -> int

    # Constantes de estado
PENDIENTE       = "PENDIENTE"
EN_WAVE         = "EN_WAVE"
EN_PREPARACION  = "EN_PREPARACION"
PREPARADO       = "PREPARADO"

class Order:
    def __init__(self, order_id, prioridad, items, estado=PENDIENTE)

    id          : str                    # ej: "PED_01"
    prioridad   : int                    # 1 a 5
    estado      : str                    # PENDIENTE | EN_WAVE | EN_PREPARACION | PREPARADO
    items       : list[tuple[str, int]]  # [(producto_id, cantidad), ...]

    def peso_total(self, inventory: InventoryManager) -> float
    def cambiar_estado(self, nuevo_estado: str) -> None
    def esta_pendiente(self) -> bool
    def to_dict(self) -> dict
    @staticmethod
    def from_dict(d: dict) -> "Order"

    class Wave:
    def __init__(self, wave_id,
                 capacidad_max_pedidos, capacidad_max_productos, peso_max_kg)

    id                      : str
    pedidos                 : list[Order]
    capacidad_max_pedidos   : int
    capacidad_max_productos : int
    peso_max_kg             : float
    recorrido_A             : list | None   # se llena en Etapa 2
    recorrido_B             : list | None   # se llena en Etapa 2

    def peso_total(self, inventory) -> float
    def cantidad_productos(self) -> int
    def puede_aceptar(self, order: Order, inventory) -> bool
    def agregar_pedido(self, order: Order, inventory) -> bool
    def __len__(self) -> int

    class Picker:
    def __init__(self, picker_id, posicion_inicial, capacidad_carga_kg)

    id                  : str
    posicion_inicial    : tuple          # (x, y)
    posicion_actual     : tuple
    capacidad_carga_kg  : float
    carga_actual_kg     : float          # inicia en 0
    items_transportados : list           # [(producto_id, cantidad), ...]

    def puede_recoger(self, product: Product, cantidad: int) -> bool
    def recoger(self, product: Product, cantidad: int) -> None
    def mover_a(self, nueva_posicion: tuple) -> None
    def to_dict(self) -> dict
    @staticmethod
    def from_dict(d: dict) -> "Picker"

    #ETAPA 2: -------------------------------------------------------------------------------

    class Graph:
    def __init__(self)

    def add_node(self, node_id, data=None) -> None
    def add_edge(self, u, v, weight: float) -> None      # dirigida u -> v
    def get_neighbors(self, u) -> dict[int, float]        # {v: peso}
    def has_node(self, node_id) -> bool
    def node_count(self) -> int
    def edge_count(self) -> int

    def construir_grafo(warehouse: Warehouse) -> Graph:
    """
    Recorre la grilla y crea:
      - Un nodo por cada celda PASILLO.
      - Una arista dirigida por cada conexión válida respetando sentidos.
    Peso de cada arista = 1 (distancia unitaria).
    """

    def dijkstra(graph: Graph, origen: int, destino: int = None) -> tuple:
    """
    Si destino es None:
        devuelve (distancias, predecesores)
    Si destino no es None:
        devuelve (distancia, [camino de nodos])
    Complejidad: O((V + E) log V)
    """

def matriz_distancias(graph: Graph, nodos: list) -> dict:
    """
    {nodo_origen: {nodo_destino: distancia}}
    Corre dijkstra una vez por cada nodo de la lista.
    """

def estrategia_A(graph, wave, warehouse, inventory) -> list[int]:
    """Recorrido en orden de los pedidos."""

def estrategia_B(graph, wave, warehouse, inventory) -> list[int]:
    """Recorrido por vecino más cercano (Greedy)."""

    #ETAPA 3: ------------------------------------------------------------------------
    def generar_waves(pedidos: list[Order], inventory, warehouse, config: dict) -> list[Wave]:
    """
    Agrupa pedidos pendientes en waves usando Greedy:
      1. Ordenar por prioridad descendente.
      2. Tomar el más prioritario como semilla.
      3. Agregar pedidos con ubicaciones cercanas mientras quepan.
      4. Cortar cuando la wave esté llena.

    Devuelve la lista de waves generadas.
    """

def ordenar_por_prioridad(pedidos: list[Order]) -> list[Order]:
    """Helper: devuelve los pedidos ordenados por prioridad descendente."""

    # Estados de la simulación
INACTIVA    = "INACTIVA"
CORRIENDO   = "CORRIENDO"
PAUSADA     = "PAUSADA"
TERMINADA   = "TERMINADA"

class Simulation:
    def __init__(self, warehouse, inventory, waves, pickers, graph)

    # Atributos públicos
    warehouse : Warehouse
    inventory : InventoryManager
    waves     : list[Wave]
    pickers   : list[Picker]
    graph     : Graph
    estado    : str
    paso      : int

    def iniciar(self) -> None
    def pausar(self) -> None
    def reanudar(self) -> None
    def resetear(self) -> None
    def avanzar_paso(self) -> None
    def get_estado(self) -> dict
        """
        Devuelve un dict con:
            {estado, paso, pickers: [...], wave_actual, items_recogidos}
        """

        class Ventana:
    def __init__(self, simulation: Simulation)

    def dibujar_warehouse(self) -> None
    def dibujar_pickers(self) -> None
    def dibujar_recorrido(self, wave_id: str) -> None
    def actualizar(self) -> None
    def iniciar(self) -> None           # arranca el mainloop de Tkinter

    def main() -> None:
    """
    Punto de entrada de la aplicación.
    Flujo:
        1. Cargar escenario (Etapa 1).
        2. Construir inventario, pedidos, pickers (Etapa 3).
        3. Construir grafo (Etapa 2).
        4. Generar waves (Etapa 3).
        5. Calcular recorridos A y B (Etapa 2).
        6. Iniciar simulación (Etapa 4).
        7. Abrir ventana Tkinter (Etapa 4).
    """

if __name__ == "__main__":
    main()

#Apéndice A — Formato de los JSON de entrada
#Cada escenario tiene 5 secciones de nivel superior:

    {
  "warehouse": {
    "dimensiones":    {"ancho_x": int, "largo_y": int},
    "puertas":        [{"id": str, "tipo": str,
                        "ubicacion": {"x": int, "y": int}}],
    "zonas_despacho": [{"id": str, "puerta_id": str,
                        "ubicacion": {"x": int, "y": int},
                        "ancho": int, "alto": int,
                        "peso_max_kg": float}],
    "racks":          [{"id": str,
                        "ubicacion": {"x": int, "y": int},
                        "ancho": int, "alto": int}],
    "pasillos":       [{"id": str,
                        "ubicacion": {"x": int, "y": int},
                        "ancho": int, "alto": int,
                        "sentido": str}]
  },
  "pickers":   [{"id": str,
                 "posicion_inicial": {"x": int, "y": int},
                 "capacidad_carga_kg": float}],
  "productos": [{"id": str, "nombre": str, "rack_id": str,
                 "ubicacion": {"x": int, "y": int, "z": int},
                 "cantidad_disponible": int,
                 "peso_kg": float}],
  "pedidos":   [{"id": str, "prioridad": int, "estado": str,
                 "items": [{"producto_id": str,
                            "cantidad": int}]}],
  "configuracion": {"wave_max_pedidos": int,
                    "wave_max_productos": int}
}

