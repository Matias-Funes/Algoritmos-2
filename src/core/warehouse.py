# warehouse.py
# Fase 1, version minima.
# Modela el almacen como un grafo NO dirigido y ponderado (Unidad 4).
#
# IMPORTANTE:
#   - El GRAFO circula por el piso: los nodos usan <x, y> (z siempre 0).
#   - La altura z NO se recorre: es un atributo de cada PRODUCTO (ver inventory.py).

import math

#contenedor de coordenadas 
class Position:
    """
    Posicion fisica dentro del almacen.

    - Para NODOS del grafo (intersecciones, racks, despacho): usar z=0.
      Representan un punto en el piso.
    - Para PRODUCTOS: usar z=1, 2, 3... segun la altura del estante.
    """
    #init es para inicializar 
    def __init__(self, x, y, z=0):
        self.x = x
        self.y = y
        self.z = z

    def distance_to(self, other):
        """
        Distancia euclidea entre dos posiciones.
        porque el picker camina por el piso.  La z se ignora en el recorrido.
        Complejidad: O(1).
        """
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)

    #representacion 
    def __repr__(self):
        # %%% casillas vacias 
        return "<%s,%s,%s>" % (self.x, self.y, self.z)


class Warehouse:
    """
    Almacen como grafo no dirigido ponderado.

    Estructuras internas:
      - self.nodes      : { id_nodo -> Position }        (posiciones en el piso)
      - self.adjacency  : { id_nodo -> { vecino -> peso } }  (listas de adyacencia)
    """

    #diccionarios (hashmaps) para almacenar nodos y adyacencias
    #warehouse.nodes["A1"] = Position(0, 0, 0)
    #warehouse.adjacency["A1"]["A2"] = 10 
    def __init__(self):
        self.nodes = {} #mapea el nodo con su posicion
        self.adjacency = {}
    #complejidad O(1) promedio para agregar nodos y aristas

    # --------------------------------------------------------------
    # metodo 
    # Agregar un nodo (una posicion fisica del piso)
    # --------------------------------------------------------------
    def add_node(self, node_id, position):
        """
        Agrega un nodo del piso.  Posicion debe tener z=0 idealmente.
        Complejidad: O(1) promedio.
        """
        if node_id in self.nodes:
            raise ValueError("El nodo %s ya existe." % node_id)
        self.nodes[node_id] = position
        self.adjacency[node_id] = {}

    # --------------------------------------------------------------
    # Agregar una arista (un pasillo)
    # --------------------------------------------------------------
    def add_edge(self, u, v, weight=None):
        """
        Conecta los nodos u y v con un pasillo.
        Si no le pasas 'weight', usa la distancia euclidea 2D entre las posiciones.
        Complejidad: O(1) promedio.
        """
        #verificacion de existencia de nodos y auto-lazos
        if u not in self.nodes or v not in self.nodes:
            raise KeyError("Alguno de los nodos no existe.")
        if u == v:
            raise ValueError("No se permiten auto-lazos.")

        if weight is None:
            weight = self.nodes[u].distance_to(self.nodes[v])

        # Grafo NO dirigido -> guardamos las dos direcciones
        self.adjacency[u][v] = weight
        self.adjacency[v][u] = weight

    # --------------------------------------------------------------
    # Consultas
    # --------------------------------------------------------------
    def get_neighbors(self, node_id):
        """Diccionario {vecino: peso}.  O(1) promedio."""
        return self.adjacency.get(node_id, {})

    def node_count(self):
        return len(self.nodes)

    def edge_count(self):
        total = 0
        for vecinos in self.adjacency.values():
            total += len(vecinos)
        return total // 2   # cada arista esta guardada dos veces


# ------------------------------------------------------------------
# Demo al final del archivo (para probar que funciona)
# ------------------------------------------------------------------
if __name__ == "__main__":
    wh = Warehouse() #creo un almacen

    # Nodos en el piso (z=0)
    wh.add_node(1, Position(0, 0))     # despacho
    wh.add_node(2, Position(5, 0))     # interseccion
    wh.add_node(3, Position(5, 5))     # interseccion
    wh.add_node(4, Position(10, 5))    # base de un rack
    wh.add_node(5, Position(10, 10))   # base de otro rack

    # Pasillos
    wh.add_edge(1, 2)
    wh.add_edge(2, 3)
    wh.add_edge(3, 4)
    wh.add_edge(4, 5)

    print("Nodos en el piso:  ", wh.node_count())
    print("Pasillos (aristas):", wh.edge_count())
    print("Vecinos del nodo 2:", wh.get_neighbors(2))