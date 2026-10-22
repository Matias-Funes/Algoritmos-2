# src/core/graph_builder.py
# ---------------------------------------------------------------
# Construye el grafo de circulación (dirigido) a partir de la
# grilla del warehouse.
# ---------------------------------------------------------------

from src.core.cell import PASILLO, N, S, E, O, AMBOS

class Graph:
    """
    Grafo dirigido con listas de adyacencia.
    """
    def __init__(self):
        # adj[u] = {v1: peso1, v2: peso2, ...}
        self.adj = {}
        self.edges_count = 0

    def add_node(self, node_id):
        """Agrega un nodo si no existe."""
        if node_id not in self.adj:
            self.adj[node_id] = {}

    def add_edge(self, u, v, weight=1.0):
        """Agrega una arista dirigida u -> v."""
        if u not in self.adj or v not in self.adj:
            raise KeyError("Nodos %s o %s no existen" % (u, v))
        self.adj[u][v] = weight
        self.edges_count += 1

    def get_neighbors(self, u):
        """Devuelve {vecino: peso} del nodo u."""
        return self.adj.get(u, {})

    def node_count(self):
        return len(self.adj)

    def edge_count(self):
        return self.edges_count


def construir_grafo(warehouse):
    """
    Recorre la grilla y crea el grafo de circulación.
    Cada celda PASILLO es un nodo (usamos (x, y) como ID).
    """
    g = Graph()

    # 1. Crear un nodo por cada celda transitable
    for y in range(warehouse.largo_y):
        for x in range(warehouse.ancho_x):
            if warehouse.grid[y][x].es_transitable():
                g.add_node((x, y))

    # 2. Crear las aristas respetando los sentidos
    for y in range(warehouse.largo_y):
        for x in range(warehouse.ancho_x):
            cell = warehouse.grid[y][x]
            if not cell.es_transitable():
                continue

            # Revisar los 4 vecinos (Arriba, Abajo, Derecha, Izquierda)
            
            # --- Hacia arriba (Norte, +y) ---
            if cell.sentido in (N, AMBOS):
                vecino = (x, y + 1)
                if vecino in g.adj:
                    g.add_edge((x, y), vecino)

            # --- Hacia abajo (Sur, -y) ---
            if cell.sentido in (S, AMBOS):
                vecino = (x, y - 1)
                if vecino in g.adj:
                    g.add_edge((x, y), vecino)

            # --- Hacia la derecha (Este, +x) ---
            if cell.sentido in (E, AMBOS):
                vecino = (x + 1, y)
                if vecino in g.adj:
                    g.add_edge((x, y), vecino)

            # --- Hacia la izquierda (Oeste, -x) ---
            if cell.sentido in (O, AMBOS):
                vecino = (x - 1, y)
                if vecino in g.adj:
                    g.add_edge((x, y), vecino)

    return g