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

from src.core.inventory import HashTable

from .queues import minPriorityQueue


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


def dijkstra(graph, source):
    """
    Calcula distancias y predecesores desde el nodo 'source' hacia todos los demás.

    Complejidad Temporal: O((V + E) * log V) usando una cola de prioridad (min-heap),
    donde V es la cantidad de vértices (celdas de pasillo) y E las aristas (conexiones).
    Complejidad Espacial: O(V) para guardar las tablas de distancias y predecesores.

    Retorna: (distances, previous) - Ambas son instancias de HashTablePathfinding.
    """
    # Usamos nuestra HashTable como arreglo asociativo para distancias y predecesores.
    # Su búsqueda e inserción es O(1) promedio.
    distances = HashTablePathfinding()
    previous = HashTablePathfinding()

    # Inicializamos el origen
    distances.insertarHT(source, 0)
    previous.insertarHT(source, None)

    # Cola de prioridad implementada por el equipo con un Min-Heap.
    queue = minPriorityQueue()
    queue.enqueue(source, 0)

    while not queue.isEmpty():
        # Extraemos el nodo con la menor distancia acumulada conocida. O(log V)
        dist, u = queue.dequeue()

        # Si la distancia en cola es mayor a la que ya registramos, es un nodo obsoleto (lazy deletion)
        if dist > distances.obtenerHT(u, float("inf")):
            continue

        # Exploramos los vecinos. 'graph.get_neighbors(u)' debe devolver {vecino: peso}.
        for v, weight in graph.get_neighbors(u).items():
            newDist = dist + weight

            # Buscamos la distancia actual del vecino (si no está, es infinito)
            dist_actual_v = distances.obtenerHT(v, float("inf"))

            # Si encontramos un camino más corto hacia 'v', actualizamos (Relajación)
            if newDist < dist_actual_v:
                distances.insertarHT(v, newDist)
                previous.insertarHT(v, u)
                queue.enqueue(v, newDist)

    return distances, previous


class CacheDistancias:
    """
    Patrón de diseño: Memoización / Caché.

    Evita ejecutar el algoritmo de Dijkstra O(V) veces para el mismo origen.
    La primera vez que se consulta un origen, corre Dijkstra O((V+E)logV).
    Las consultas posteriores desde ese mismo origen son O(1).

    Utiliza la HashTable para guardar un "mapa de mapas" (Origen -> {Destino -> Distancia}).
    """

    def __init__(self, grafo) -> None:
        self._grafo = grafo
        self._cache = HashTablePathfinding()  # Guarda {origen: HashTable_de_distancias}
        self._predecesores = (
            HashTablePathfinding()
        )  # Guarda {origen: HashTable_de_predecesores}

    def _asegurar_origen(self, origen) -> None:
        """Corre Dijkstra solo si este origen no fue consultado antes."""
        if not self._cache.contieneHT(origen):
            dist, pred = dijkstra(self._grafo, origen)
            self._cache.insertarHT(origen, dist)
            self._predecesores.insertarHT(origen, pred)

    def distancia(self, u, v) -> float:
        """Devuelve la distancia de u a v. O(1) si ya se calculó desde 'u'."""
        self._asegurar_origen(u)
        dist_desde_u = self._cache.buscarHT(u)
        return dist_desde_u.obtenerHT(v, float("inf"))

    def camino(self, u, v) -> list:
        """Reconstruye el camino más corto de u a v usando los predecesores."""
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
            actual = pred_desde_u.obtenerHT(actual)

        camino.reverse()  # Invertimos la lista para que vaya de u a v
        return camino


# -------------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------------


def obtener_celda_piso(producto, warehouse):
    """
    Dado que los productos están DENTRO de un rack (ej: x=3, y=5, z=1),
    el picker no puede pisar el rack. Esta función busca una celda de PASILLO
    adyacente (arriba, abajo, izquierda o derecha) para que el picker se pare ahí.
    """
    x, y = producto.ubicacion[0], producto.ubicacion[1]
    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        nx, ny = x + dx, y + dy
        if 0 <= nx < warehouse.ancho_x and 0 <= ny < warehouse.largo_y:
            if warehouse.grid[ny][nx].tipo == "PASILLO":
                return (nx, ny)
    return (x, y)  # Fallback


def obtener_puntos_de_interes(wave, warehouse, inventory):
    """Extrae todas las celdas de piso (x,y) que el picker debe visitar para esta wave."""
    puntos = []
    for pedido in wave.pedidos:
        for prod_id, cantidad in pedido.items:
            prod = inventory.obtener_producto(prod_id)
            if prod:
                puntos.append(obtener_celda_piso(prod, warehouse))
    return puntos


# -------------------------------------------------------------------------
# ESTRATEGIAS DE RECORRIDO
# -------------------------------------------------------------------------


def estrategia_A(graph, wave, warehouse, inventory, cache=None):
    """
    Estrategia A: Orden de los pedidos.
    Visita los productos en el orden estricto en que aparecen en los pedidos.

    Complejidad: O(K * C), donde K es la cantidad de productos a recoger y
    C es el costo de consultar el caché (O(1) si el origen ya fue cacheado).
    """
    if cache is None:
        cache = CacheDistancias(graph)

    puntos = obtener_puntos_de_interes(wave, warehouse, inventory)
    if not puntos:
        return []

    camino_total = []
    actual = puntos[0]

    for siguiente in puntos[1:]:
        tramo = cache.camino(actual, siguiente)
        if tramo:
            # Evitamos duplicar el nodo de conexión entre un tramo y el siguiente
            if camino_total and camino_total[-1] == tramo[0]:
                camino_total.extend(tramo[1:])
            else:
                camino_total.extend(tramo)
        actual = siguiente

    return camino_total


def estrategia_B(graph, wave, warehouse, inventory, cache=None):
    """
    Estrategia B: Vecino más cercano (Heurística Greedy).
    Desde la posición actual, calcula la distancia a todos los pendientes
    y se mueve al más cercano. Repite hasta vaciar la lista.

    Complejidad: O(K^2) consultas de distancia. Gracias al caché,
    las consultas repetidas desde el mismo nodo son O(1).
    """
    if cache is None:
        cache = CacheDistancias(graph)

    pendientes = obtener_puntos_de_interes(wave, warehouse, inventory)
    if not pendientes:
        return []

    actual = pendientes[0]
    camino_total = []
    pendientes.remove(actual)

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
            if camino_total and camino_total[-1] == tramo[0]:
                camino_total.extend(tramo[1:])
            else:
                camino_total.extend(tramo)
            actual = mejor_vecino
            pendientes.remove(mejor_vecino)
        else:
            break  # No hay más caminos accesibles

    return camino_total


def matriz_distancias(graph, nodos, cache=None):
    """
    Calcula una matriz de distancias all-pairs entre un conjunto de nodos.
    Utiliza el caché para evitar ejecutar Dijkstra de más.

    Retorna: dict {nodo_origen: {nodo_destino: distancia}}
    Complejidad: O(U * (V+E)logV), donde U es la cantidad de nodos únicos consultados como origen.
    """
    if cache is None:
        cache = CacheDistancias(graph)

    matriz = {}
    for origen in nodos:
        matriz[origen] = {}
        for destino in nodos:
            matriz[origen][destino] = cache.distancia(origen, destino)

    return matriz
