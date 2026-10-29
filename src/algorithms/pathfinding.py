"""
pathfinding.py
==============
Algoritmos de búsqueda de caminos y estrategias de recorrido para el Wave Picking.

Decisiones de diseño destacadas:
1. Uso de Estructuras Propias: Se reemplazó el uso de diccionarios nativos de Python
   y la librería `heapq` por la HashTable (con encadenamiento) y la Priority Queue
   implementadas por el equipo.
2. Optimización de Dijkstra: Se utiliza una subclase de HashTable con el método de la
   multiplicación para manejar las tuplas (x,y) como claves.
3. Memoización: Se implementó `CacheDistancias` para evitar recalcular Dijkstra O(V) veces
   sobre el mismo origen, reduciendo el costo de consultas repetidas a O(1).
"""

import math
import time
from typing import TYPE_CHECKING, Any, Optional

from src.core.inventory import HashTable

from .queues import minPriorityQueue

# Usamos TYPE_CHECKING para evitar importaciones circulares en tiempo de ejecución,
# pero permitir que el editor y los type hints conozcan las clases.
if TYPE_CHECKING:
    from src.core.graph_builder import Graph
    from src.core.inventory import GestorInventario
    from src.core.warehouse import Warehouse
    from src.core.wave import Wave


class RutaInalcanzableError(Exception):
    """Se lanza cuando no existe un camino válido entre dos puntos."""

    pass


class HashTablePathfinding(HashTable):
    """
    Subclase de la HashTable de inventory.py.
    Se sobreescribe la función hash para usar el Método de la Multiplicación
    de Knuth, que es más robusto académicamente para distribuir las claves.
    """

    def _hash(self, clave):
        # 1. Si la clave es una tupla (x, y) que representa una coordenada,
        # la convertimos a un entero único usando una combinación polinomial.
        if isinstance(clave, tuple):
            k = 0
            for elemento in clave:
                k = k * 31 + int(elemento)
        else:
            # Si la clave ya es un entero (ej: un ID), la usamos directamente
            k = int(clave)

        # 2. Aplicamos el Método de la Multiplicación:
        # h(k) = floor(m * (k * A mod 1)), donde A = (sqrt(5) - 1) / 2
        A = (math.sqrt(5) - 1) / 2
        producto = k * A
        parte_fraccionaria = producto % 1

        # 3. Multiplicamos por la capacidad de la tabla y redondeamos hacia abajo
        return math.floor(self.capacidad * parte_fraccionaria)


# -------------------------------------------------------------------------
# ALGORITMOS BASE
# -------------------------------------------------------------------------


def dijkstra(
    grafo: "Graph", origen: tuple[int, int]
) -> tuple[HashTablePathfinding, HashTablePathfinding, int]:
    """
    Calcula distancias y predecesores desde el nodo 'origen' hacia todos los demás.

    Entradas:
        grafo: Instancia de Graph con el mapa de adyacencia.
        origen: Tupla (x, y) del nodo de partida.

    Salidas:
        distances: HashTable con las distancias mínimas desde el origen.
        previous: HashTable con los predecesores para reconstruir caminos.
        visitados: Entero con la cantidad de nodos extraídos y procesados.

    Complejidad Temporal: O((|V| + |E|) * log |V|) usando una cola de prioridad (min-heap),
    donde V es la cantidad de vértices (celdas de pasillo) y E las aristas (conexiones).
    Complejidad Espacial: O(|V|) para guardar las tablas de distancias y predecesores.
    """
    # Usamos nuestra HashTable como arreglo asociativo para distancias y predecesores.
    # Su búsqueda e inserción es O(1) promedio.
    distances = HashTablePathfinding()
    previous = HashTablePathfinding()

    # Inicializamos el origen
    distances.insertarHT(origen, 0)
    previous.insertarHT(origen, None)

    # Cola de prioridad implementada por el equipo con un Min-Heap.
    queue = minPriorityQueue()
    queue.enqueue(origen, 0)
    visitados = 0  # inicializo contador de nodos visitados

    while not queue.isEmpty():
        # Extraemos el nodo con la menor distancia acumulada conocida. O(log |V|)
        dist, u = queue.dequeue()

        # Si la distancia en cola es mayor a la que ya registramos, es un nodo obsoleto (lazy deletion)
        if dist > distances.obtenerHT(u, float("inf")):
            continue

        visitados += 1  # Solo contamos los nodos realmente procesados

        # Exploramos los vecinos. 'grafo.get_neighbors(u)' debe devolver {vecino: peso}.
        for v, weight in grafo.get_neighbors(u).items():
            newDist = dist + weight

            # Buscamos la distancia actual del vecino (si no está, es infinito)
            dist_actual_v = distances.obtenerHT(v, float("inf"))

            # Si encontramos un camino más corto hacia 'v', actualizamos (Relajación)
            if newDist < dist_actual_v:
                distances.insertarHT(v, newDist)
                previous.insertarHT(v, u)
                queue.enqueue(v, newDist)

    return distances, previous, visitados


class CacheDistancias:
    """
    Patrón de diseño: Memoización / Caché.

    Evita ejecutar el algoritmo de Dijkstra O(|V|) veces para el mismo origen.
    La primera vez que se consulta un origen, corre Dijkstra O((|V|+|E|)log|V|).
    Las consultas posteriores desde ese mismo origen son O(1).

    Utiliza la HashTable para guardar un "mapa de mapas" (Origen -> {Destino -> Distancia}).
    """

    def __init__(self, grafo: "Graph") -> None:
        self._grafo = grafo
        self._cache = HashTablePathfinding()  # Guarda {origen: HashTable_de_distancias}
        self._predecesores = (
            HashTablePathfinding()
        )  # Guarda {origen: HashTable_de_predecesores}
        self._visitados = (
            HashTablePathfinding()
        )  # Guarda {origen: HashTable_de_nodos_visitados}

    def _asegurar_origen(self, origen: tuple[int, int]) -> None:
        """Corre Dijkstra solo si este origen no fue consultado antes. O(1) o O(Dijkstra)."""
        if not self._cache.contieneHT(origen):
            dist, pred, visitados = dijkstra(self._grafo, origen)  # desempaquetamos
            self._cache.insertarHT(origen, dist)
            self._predecesores.insertarHT(origen, pred)
            self._visitados.insertarHT(origen, visitados)  # guardamos

    def distancia(self, u: tuple[int, int], v: tuple[int, int]) -> float:
        """Devuelve la distancia de u a v. O(1) si ya se calculó desde 'u'."""
        self._asegurar_origen(u)
        dist_desde_u = self._cache.buscarHT(u)
        return dist_desde_u.obtenerHT(v, float("inf"))

    def nodos_visitados(self, origen: tuple[int, int]) -> int:
        """Devuelve la cantidad de nodos visitados desde un origen. O(1) si está cacheado."""
        self._asegurar_origen(origen)
        return self._visitados.buscarHT(origen)

    def camino(self, u: tuple[int, int], v: tuple[int, int]) -> list[tuple[int, int]]:
        """
        Reconstruye el camino más corto de u a v usando los predecesores.
        Complejidad Temporal: O(L) donde L es la longitud del camino devuelto.
        Complejidad Espacial: O(L) para almacenar el camino.
        """
        self._asegurar_origen(u)
        dist_desde_u = self._cache.buscarHT(u)

        # Si v no está en la tabla o su distancia es infinita, no hay camino.
        if not dist_desde_u.contieneHT(v) or dist_desde_u.obtenerHT(v) == float("inf"):
            return []

        pred_desde_u = self._predecesores.buscarHT(u)
        camino = []
        actual = v
        # Retrocedemos desde el destino hasta el origen usando los predecesores
        while actual is not None:
            camino.append(actual)
            actual = pred_desde_u.obtenerHT(actual, None)

        camino.reverse()  # Invertimos la lista para que vaya de u a v
        return camino


# -------------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------------


def obtener_celda_piso(producto: Any, warehouse: "Warehouse") -> tuple[int, int]:
    """
    Dado que los productos están DENTRO de un rack (ej: x=3, y=5, z=1),
    el picker no puede pisar el rack. Esta función busca una celda de PASILLO
    adyacente (arriba, abajo, izquierda o derecha) para que el picker se pare ahí.

    Complejidad Temporal: O(1) (evalúa máximo 4 vecinos).
    Lanza RutaInalcanzableError si el producto está rodeado de paredes/racks.
    """
    x, y = producto.ubicacion[0], producto.ubicacion[1]
    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        nx, ny = x + dx, y + dy
        if 0 <= nx < warehouse.ancho_x and 0 <= ny < warehouse.largo_y:
            if warehouse.grid[ny][nx].tipo == "PASILLO":
                return (nx, ny)

    raise RutaInalcanzableError(
        f"El producto en ({x},{y}) está bloqueado, sin pasillo adyacente."
    )


def obtener_puntos_de_interes(
    wave: "Wave", warehouse: "Warehouse", inventory: "GestorInventario"
) -> list[tuple[int, int]]:
    """
    Extrae todas las celdas de piso (x,y) únicas que el picker debe visitar para esta wave.
    Deduplica preservando el orden de pedido original.

    Complejidad Temporal: O(K) donde K es la cantidad total de items en la wave.
    """
    puntos = []
    for pedido in wave.pedidos:
        for prod_id, cantidad in pedido.items:
            prod = inventory.obtener_producto(prod_id)
            if prod:
                puntos.append(obtener_celda_piso(prod, warehouse))

    return list(dict.fromkeys(puntos))


# -------------------------------------------------------------------------
# ESTRATEGIAS DE RECORRIDO
# -------------------------------------------------------------------------


def estrategia_A(
    graph: "Graph",
    wave: "Wave",
    warehouse: "Warehouse",
    inventory: "GestorInventario",
    cache: Optional[CacheDistancias] = None,
) -> dict[str, Any]:
    """
    Estrategia A: Orden de los pedidos.
    Visita los productos en el orden estricto en que aparecen en los pedidos.

    Complejidad Temporal: O(K * C), donde K es la cantidad de productos a recoger y
    C es el costo de consultar el caché (O(1) si el origen ya fue cacheado).
    Retorna un dict con métricas.
    """
    tiempo_inicio = time.perf_counter()
    if cache is None:
        cache = CacheDistancias(graph)

    puntos = obtener_puntos_de_interes(wave, warehouse, inventory)
    if not puntos:
        return {
            "ruta": [],
            "distancia_total": 0,
            "tiempo_ejecucion_ms": 0,
            "nodos_visitados": 0,
        }

    if len(puntos) == 1:
        return {
            "ruta": [puntos[0]],
            "distancia_total": 0,
            "tiempo_ejecucion_ms": (time.perf_counter() - tiempo_inicio) * 1000,
            "nodos_visitados": cache.nodos_visitados(puntos[0]),
        }

    camino_total = []
    actual = puntos[0]
    distancia_total = 0
    origenes_consultados = set()

    for siguiente in puntos[1:]:
        tramo = cache.camino(actual, siguiente)

        if not tramo:
            raise RutaInalcanzableError(f"No hay ruta entre {actual} y {siguiente}.")

        distancia_total += cache.distancia(actual, siguiente)
        origenes_consultados.add(actual)

        # Evitamos duplicar el nodo de conexión entre un tramo y el siguiente
        if camino_total and camino_total[-1] == tramo[0]:
            camino_total.extend(tramo[1:])
        else:
            camino_total.extend(tramo)
        actual = siguiente

    tiempo_fin = time.perf_counter()

    return {
        "ruta": camino_total,
        "distancia_total": distancia_total,
        "tiempo_ejecucion_ms": (tiempo_fin - tiempo_inicio) * 1000,
        "nodos_visitados": sum(cache.nodos_visitados(o) for o in origenes_consultados),
    }


def estrategia_B(
    graph: "Graph",
    wave: "Wave",
    warehouse: "Warehouse",
    inventory: "GestorInventario",
    cache: Optional[CacheDistancias] = None,
) -> dict[str, Any]:
    """
    Estrategia B: Vecino más cercano (Heurística Greedy).
    Desde la posición actual, calcula la distancia a todos los pendientes
    y se mueve al más cercano. Repite hasta vaciar la lista.

    Complejidad Temporal: O(K^2) consultas de distancia. Gracias al caché,
    las consultas repetidas desde el mismo nodo son O(1).
    Retorna un dict con métricas.
    """
    tiempo_inicio = time.perf_counter()
    if cache is None:
        cache = CacheDistancias(graph)

    pendientes = obtener_puntos_de_interes(wave, warehouse, inventory)
    if not pendientes:
        return {
            "ruta": [],
            "distancia_total": 0,
            "tiempo_ejecucion_ms": 0,
            "nodos_visitados": 0,
        }

    if len(pendientes) == 1:
        return {
            "ruta": [pendientes[0]],
            "distancia_total": 0,
            "tiempo_ejecucion_ms": (time.perf_counter() - tiempo_inicio) * 1000,
            "nodos_visitados": cache.nodos_visitados(pendientes[0]),
        }

    actual = pendientes[0]
    camino_total = []
    pendientes.remove(actual)
    distancia_total = 0
    origenes_consultados = set()

    while pendientes:
        mejor_vecino = None
        menor_distancia = float("inf")

        # Buscamos el pendiente más cercano
        for candidato in pendientes:
            d = cache.distancia(actual, candidato)
            if d < menor_distancia:
                menor_distancia = d
                mejor_vecino = candidato

        if mejor_vecino and menor_distancia != float("inf"):
            tramo = cache.camino(actual, mejor_vecino)

            distancia_total += menor_distancia
            origenes_consultados.add(actual)

            if camino_total and camino_total[-1] == tramo[0]:
                camino_total.extend(tramo[1:])
            else:
                camino_total.extend(tramo)
            actual = mejor_vecino
            pendientes.remove(mejor_vecino)
        else:
            raise RutaInalcanzableError(
                f"El picker quedó bloqueado en {actual}. No hay camino a los puntos restantes."
            )

    tiempo_fin = time.perf_counter()
    return {
        "ruta": camino_total,
        "distancia_total": distancia_total,
        "tiempo_ejecucion_ms": (tiempo_fin - tiempo_inicio) * 1000,
        "nodos_visitados": sum(cache.nodos_visitados(o) for o in origenes_consultados),
    }


def matriz_distancias(
    graph: "Graph",
    nodos: list[tuple[int, int]],
    cache: Optional[CacheDistancias] = None,
) -> HashTablePathfinding:
    """
    Calcula una matriz de distancias all-pairs entre un conjunto de nodos.
    Utiliza el caché para evitar ejecutar Dijkstra de más.

    Entradas:
        graph: Grafo del almacén.
        nodos: Lista de tuplas (x,y) de los puntos a calcular.
        cache: Caché pre-construido opcional.

    Salidas:
        matriz: HashTable propia de la forma {origen: HashTable_de_{destino: distancia}}.

    Complejidad Temporal: O(U * (V+E)logV), donde U es la cantidad de nodos únicos consultados como origen.
    Complejidad Espacial: O(U^2) para almacenar todos los pares de distancias.
    """
    if cache is None:
        cache = CacheDistancias(graph)

    matriz = HashTablePathfinding()
    for origen in nodos:
        fila_distancias = HashTablePathfinding()
        for destino in nodos:
            fila_distancias.insertarHT(destino, cache.distancia(origen, destino))

        matriz.insertarHT(origen, fila_distancias)

    return matriz


def expandir_ruta(
    graph: "Graph",
    lista_waypoints: list[tuple[int, int]],
    cache: Optional[CacheDistancias] = None,
) -> list[tuple[int, int]]:
    """
    Recibe una lista de puntos [(x1,y1), (x2,y2)] y devuelve la ruta completa
    celda por celda, usando Dijkstra para unir los tramos.

    Entradas:
        graph: Grafo del almacén.
        lista_waypoints: Lista de coordenadas clave.
        cache: Caché pre-construido opcional.

    Salidas:
        ruta_expandida: Lista continua de tuplas (x,y) que forman el camino.

    Complejidad Temporal: O(K * L), donde K es el número de waypoints y L la longitud promedio del camino entre ellos.
    """
    if not lista_waypoints:
        return []

    if len(lista_waypoints) == 1:
        return list(lista_waypoints)

    if cache is None:
        cache = CacheDistancias(graph)

    ruta_expandida = []

    for i in range(len(lista_waypoints) - 1):
        origen = lista_waypoints[i]
        destino = lista_waypoints[i + 1]

        tramo = cache.camino(origen, destino)
        if not tramo:
            raise RutaInalcanzableError(
                f"Imposible expandir ruta: bloqueo entre {origen} y {destino}."
            )

        if ruta_expandida and ruta_expandida[-1] == tramo[0]:
            ruta_expandida.extend(tramo[1:])
        else:
            ruta_expandida.extend(tramo)

    return ruta_expandida
