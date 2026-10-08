
from .queues import*

def dijkstra(graph, source):
    """Calcula el camino de costo mínimo desde 'source' hasta todos los nodos.

    graph: WarehouseGraph. Se usan graph.nodes() y graph.get_neighbors(u),
    que devuelve {vecino: peso}. (Los pesos no pueden ser negativos) y
    Retorna (distances, previous), indexados por node_id,
    O((V + E) log V)
    """
    distances = {node.node_id: float("inf") for node in graph.nodes()}
    previous = {node.node_id: None for node in graph.nodes()}

    distances[source] = 0

    queue = minPriorityQueue()
    queue.enqueue(source, 0)

    while not queue.isEmpty():
        dist, u = queue.dequeue()

        if dist > distances[u]:
            continue

        for v, weight in graph.get_neighbors(u).items():
            newDist = dist + weight

            if newDist < distances[v]:
                distances[v] = newDist
                previous[v] = u
                queue.enqueue(v, newDist)

    return distances, previous


def shortestPath(previous, source, target):
    """Reconstruye el camino mínimo de source a target a partir de 'previous'.
    Retorna la lista de nodos, o None si target no es alcanzable. O(V)"""
    path = []
    node = target

    while node is not None:
        path.append(node)
        node = previous[node]

    path.reverse()

    if path[0] != source:
        return None

    return path