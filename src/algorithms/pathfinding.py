"""
pathfinding.py
==============
Algoritmos de búsqueda de caminos y estrategias de recorrido (Etapa 2).
"""

import heapq  # instruido

# -------------------------------------------------------------------------
# ALGORITMO BASE
# -------------------------------------------------------------------------


def dijkstra(graph, inicio, fin):
    """
    Encuentra el camino más corto entre inicio y fin.
    Devuelve una lista de nodos (tuplas) representando el camino.
    Si no hay camino, devuelve una lista vacía [].
    """
    if inicio == fin:
        return [inicio]

    # Distancias iniciales: infinito para todos, 0 para el inicio
    distancias = {inicio: 0}
    predecesores = {}

    # Cola de prioridad: (distancia_acumulada, nodo_actual)
    cola = [(0, inicio)]

    while cola:
        dist_actual, actual = heapq.heappop(cola)

        # Si ya encontramos un camino más corto a este nodo, lo ignoramos
        if dist_actual > distancias.get(actual, float("inf")):
            continue

        if actual == fin:
            break

        # Explorar vecinos (asumimos que graph.get_neighbors devuelve {vecino: peso})
        vecinos = (
            graph.get_neighbors(actual)
            if hasattr(graph, "get_neighbors")
            else graph.get(actual, {})
        )

        for vecino, peso in vecinos.items():
            nueva_dist = dist_actual + peso

            if nueva_dist < distancias.get(vecino, float("inf")):
                distancias[vecino] = nueva_dist
                predecesores[vecino] = actual
                heapq.heappush(cola, (nueva_dist, vecino))

    # Reconstruir el camino
    if fin not in predecesores and inicio != fin:
        return []

    camino = []
    actual = fin
    while actual is not None:
        camino.append(actual)
        actual = predecesores.get(actual)
    camino.reverse()
    return camino


# -------------------------------------------------------------------------
# HELPERS (Para no depender de otros módulos)
# -------------------------------------------------------------------------


def obtener_celda_piso(producto, warehouse):
    """
    Dado un Producto (que está DENTRO de un rack en x,y,z),
    busca una celda de PASILLO adyacente para que el picker se pare a recogerlo.
    """
    x, y = producto.ubicacion[0], producto.ubicacion[1]

    # Buscamos en las 4 direcciones ortogonales
    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
        nx, ny = x + dx, y + dy
        if 0 <= nx < warehouse.ancho_x and 0 <= ny < warehouse.largo_y:
            if warehouse.grid[ny][nx].tipo == "PASILLO":
                return (nx, ny)
    return (x, y)  # Fallback por si falla la adyacencia (no debería pasar)


def obtener_puntos_de_interes(wave, warehouse, inventory):
    """Devuelve una lista de celdas de piso [(x,y), ...] a visitar para esta wave."""
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


def estrategia_A(graph, wave, warehouse, inventory):
    """
    Estrategia A: Orden de los pedidos.
    Arma el recorrido yendo a los productos en el orden en que aparecen en los pedidos.
    """
    puntos_a_visitar = obtener_puntos_de_interes(wave, warehouse, inventory)
    if not puntos_a_visitar:
        return []

    # Asumimos que arrancamos en el primer punto (o podrías usar el picker)
    camino_total = []
    actual = puntos_a_visitar[0]

    for siguiente in puntos_a_visitar[1:]:
        tramo = dijkstra(graph, actual, siguiente)
        if tramo:
            # Evitamos duplicar el nodo de conexión
            if camino_total and camino_total[-1] == tramo[0]:
                camino_total.extend(tramo[1:])
            else:
                camino_total.extend(tramo)
        actual = siguiente

    return camino_total


def estrategia_B(graph, wave, warehouse, inventory):
    """
    Estrategia B: Vecino más cercano (Greedy).
    Desde la posición actual, va al producto pendiente más cercano.
    """
    pendientes = obtener_puntos_de_interes(wave, warehouse, inventory)
    if not pendientes:
        return []

    actual = pendientes[0]  # O el despacho inicial
    camino_total = []
    pendientes.remove(actual)

    while pendientes:
        mejor_vecino = None
        mejor_camino = None
        menor_distancia = float("inf")

        # Probamos ir a todos los pendientes
        for candidato in pendientes:
            camino = dijkstra(graph, actual, candidato)
            if camino and len(camino) < menor_distancia:
                menor_distancia = len(camino)
                mejor_vecino = candidato
                mejor_camino = camino

        if mejor_vecino:
            if camino_total and camino_total[-1] == mejor_camino[0]:
                camino_total.extend(mejor_camino[1:])
            else:
                camino_total.extend(mejor_camino)
            actual = mejor_vecino
            pendientes.remove(mejor_vecino)
        else:
            break  # No hay más caminos accesibles

    return camino_total


def matriz_distancias(graph, nodos):
    """
    Calcula la distancia mínima entre todos los pares de nodos.
    Devuelve {nodo_origen: {nodo_destino: distancia}}.
    """
    matriz = {}
    for origen in nodos:
        matriz[origen] = {}
        for destino in nodos:
            if origen == destino:
                matriz[origen][destino] = 0
            else:
                camino = dijkstra(graph, origen, destino)
                # Si no hay camino, la distancia es infinita
                matriz[origen][destino] = len(camino) - 1 if camino else float("inf")
    return matriz
