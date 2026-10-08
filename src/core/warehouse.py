"""
warehouse.py
============
Modelado físico del Warehouse como GRAFO NO DIRIGIDO PONDERADO
representado con LISTAS DE ADYACENCIA (Unidad 4 del programa).

Estructuras internas:
    _nodes     : dict {node_id (int) -> Node}            acceso O(1) promedio
    _adjacency : dict {node_id (int) -> {vecino: peso}}  acceso O(1) promedio

Complejidad espacial global: O(V + E).

NO se utilizan librerías de grafos ni estructuras autogeneradas.
Todo está implementado desde cero.

Autor: Equipo Wave Picking - Algoritmos y Estructuras de Datos 2 (UNCUYO)
"""

import math


# ---------------------------------------------------------------------------
# 1. Posición tetra <x, y, z>
# ---------------------------------------------------------------------------
class Position:
    """
    Coordenada física dentro del warehouse.
    Inmutable en la práctica: se implementan __hash__ y __eq__ para poder
    usarla como clave de diccionarios (ej. en la Tabla Hash de inventario).
    """

    def __init__(self, x, y, z=0.0):
        self.x = x
        self.y = y
        self.z = z

    def distance_to(self, other):
        """
        Distancia euclídea 3D.
        Complejidad temporal: O(1).
        """
        dx = self.x - other.x
        dy = self.y - other.y
        dz = self.z - other.z
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def manhattan_to(self, other):
        """Distancia Manhattan 3D.  Complejidad: O(1)."""
        return abs(self.x - other.x) + abs(self.y - other.y) + abs(self.z - other.z)

    def as_tuple(self):
        return (self.x, self.y, self.z)

    def __eq__(self, other):
        if not isinstance(other, Position):
            return False
        return self.x == other.x and self.y == other.y and self.z == other.z

    def __hash__(self):
        return hash((self.x, self.y, self.z))

    def __repr__(self):
        return "<%s,%s,%s>" % (self.x, self.y, self.z)


# ---------------------------------------------------------------------------
# 2. Tipos de nodo (constantes de clase, sin Enum)
# ---------------------------------------------------------------------------
class NodeType:
    INTERSECTION = "INTERSECTION"   # Cruce de pasillos
    RACK         = "RACK"           # Estantería
    DISPATCH     = "DISPATCH"       # Zona de despacho
    DOOR         = "DOOR"           # Muelle


# ---------------------------------------------------------------------------
# 3. Nodo del grafo
# ---------------------------------------------------------------------------
class Node:
    """
    Un nodo del warehouse.

    Atributos:
        node_id   : int, identificador único.
        position  : Position (coordenada tetra).
        node_type : str (ver NodeType).
        metadata  : dict libre (rack_id, zone_name, etc.).
    """

    def __init__(self, node_id, position, node_type=NodeType.INTERSECTION, metadata=None):
        self.node_id = node_id
        self.position = position
        self.node_type = node_type
        self.metadata = metadata if metadata is not None else {}

    def __hash__(self):
        return hash(self.node_id)

    def __eq__(self, other):
        return isinstance(other, Node) and self.node_id == other.node_id

    def __repr__(self):
        return "Node(id=%s, pos=%s, type=%s)" % (
            self.node_id, self.position, self.node_type
        )


# ---------------------------------------------------------------------------
# 4. Grafo del Warehouse (listas de adyacencia)
# ---------------------------------------------------------------------------
class WarehouseGraph:
    """
    Grafo no dirigido ponderado que modela el warehouse.

    INVARIANTES:
        - Todo node_id en _adjacency existe en _nodes.
        - Toda arista (u, v) con peso w implica (v, u) con peso w
          (grafo no dirigido) salvo que se indique directed=True.

    COMPLEJIDAD ESPACIAL TOTAL: O(V + E).
    """

    def __init__(self, name="Warehouse"):
        self.name = name
        self._nodes = {}        # {node_id: Node}
        self._adjacency = {}    # {node_id: {vecino_id: peso}}
        self._edge_count = 0    # aristas NO dirigidas (cada par cuenta 1)

    # ------------------------------------------------------------------
    # 4.1 Operaciones sobre NODOS
    # ------------------------------------------------------------------
    def add_node(self, node_id, position, node_type=NodeType.INTERSECTION, **metadata):
        """
        Inserta un nodo en el grafo.
        Complejidad temporal: O(1) promedio (inserción en dict).
        Complejidad espacial:  O(1).
        Lanza ValueError si el node_id ya existe.
        """
        if node_id in self._nodes:
            raise ValueError("El nodo %s ya existe en el warehouse." % node_id)
        node = Node(node_id, position, node_type, metadata)
        self._nodes[node_id] = node
        self._adjacency[node_id] = {}
        return node

    def remove_node(self, node_id):
        """
        Elimina un nodo y todas sus aristas incidentes.
        Complejidad temporal: O(grado(node_id)) + O(1) dicts.
        Peor caso (nodo hub): O(V).
        """
        if node_id not in self._nodes:
            raise KeyError("El nodo %s no existe." % node_id)

        # Eliminar referencias inversas en los vecinos
        for neighbor in list(self._adjacency[node_id].keys()):
            del self._adjacency[neighbor][node_id]
            self._edge_count -= 1

        del self._adjacency[node_id]
        del self._nodes[node_id]

    def get_node(self, node_id):
        """Recupera un nodo por id.  Complejidad: O(1) promedio."""
        return self._nodes[node_id]

    def has_node(self, node_id):
        """Pertenencia de nodo.  Complejidad: O(1) promedio."""
        return node_id in self._nodes

    # ------------------------------------------------------------------
    # 4.2 Operaciones sobre ARISTAS (pasillos)
    # ------------------------------------------------------------------
    def add_edge(self, u, v, weight=None, bidirectional=True):
        """
        Agrega un pasillo entre u y v.
        Si weight es None -> se calcula la distancia euclídea entre posiciones.
        Si bidirectional es False -> arista dirigida (u -> v).
        Complejidad temporal: O(1) promedio.
        Devuelve el peso asignado.
        """
        if u not in self._nodes or v not in self._nodes:
            raise KeyError("Alguno de los nodos %s, %s no existe." % (u, v))
        if u == v:
            raise ValueError("No se permiten auto-lazos (u == v).")
        if weight is None:
            weight = self._nodes[u].position.distance_to(self._nodes[v].position)
        if weight <= 0:
            raise ValueError("El peso debe ser positivo, se recibió %s." % weight)

        if v not in self._adjacency[u]:
            self._edge_count += 1

        self._adjacency[u][v] = weight
        if bidirectional:
            self._adjacency[v][u] = weight

        return weight

    def remove_edge(self, u, v, bidirectional=True):
        """
        Elimina el pasillo u-v.
        Complejidad temporal: O(1) promedio.
        """
        if v in self._adjacency.get(u, {}):
            del self._adjacency[u][v]
            self._edge_count -= 1
        if bidirectional and u in self._adjacency.get(v, {}):
            del self._adjacency[v][u]

    def has_edge(self, u, v):
        """Verifica si existe pasillo u-v.  Complejidad: O(1) promedio."""
        return v in self._adjacency.get(u, {})

    def get_weight(self, u, v):
        """
        Devuelve el peso del pasillo u-v.
        Complejidad: O(1) promedio.  Lanza KeyError si no existe.
        """
        return self._adjacency[u][v]

    def get_neighbors(self, node_id):
        """
        Devuelve el dict {vecino: peso} del nodo.
        Complejidad: O(1) promedio.  OJO: devuelve la referencia interna.
        """
        return self._adjacency.get(node_id, {})

    # ------------------------------------------------------------------
    # 4.3 Consultas globales
    # ------------------------------------------------------------------
    def node_count(self):
        """Cantidad de nodos.  O(1)."""
        return len(self._nodes)

    def edge_count(self):
        """Cantidad de aristas no dirigidas.  O(1)."""
        return self._edge_count

    def nodes(self):
        """Itera sobre todos los nodos.  O(V)."""
        return iter(self._nodes.values())

    def edges(self):
        """
        Itera aristas únicas (u < v para no duplicar).
        Complejidad: O(V + E).
        """
        for u in self._adjacency:
            for v in self._adjacency[u]:
                if u < v:
                    yield (u, v, self._adjacency[u][v])

    def nodes_by_type(self, node_type):
        """Filtra nodos por tipo.  Complejidad: O(V)."""
        result = []
        for node in self._nodes.values():
            if node.node_type == node_type:
                result.append(node)
        return result

    def find_nearest_node(self, position, node_type=None):
        """
        Búsqueda lineal del nodo más cercano a una posición dada,
        con filtro opcional por tipo.
        Complejidad temporal: O(V).
        Complejidad espacial:  O(1).
        """
        best = None
        best_dist = float("inf")
        for node in self._nodes.values():
            if node_type is not None and node.node_type != node_type:
                continue
            d = node.position.distance_to(position)
            if d < best_dist:
                best_dist = d
                best = node
        return best

    def get_dispatch_node(self):
        """Devuelve el nodo de despacho principal.  O(V)."""
        dispatches = self.nodes_by_type(NodeType.DISPATCH)
        if not dispatches:
            raise LookupError("El warehouse no tiene zona de despacho definida.")
        return dispatches[0]

    # ------------------------------------------------------------------
    # 4.4 Persistencia
    # ------------------------------------------------------------------
    def to_dict(self):
        """Serializa el grafo a un dict JSON-friendly.  O(V + E)."""
        nodes_list = []
        for n in self._nodes.values():
            nodes_list.append({
                "node_id": n.node_id,
                "position": n.position.as_tuple(),
                "node_type": n.node_type,
                "metadata": n.metadata,
            })
        edges_list = []
        for (u, v, w) in self.edges():
            edges_list.append({"u": u, "v": v, "weight": w})
        return {"name": self.name, "nodes": nodes_list, "edges": edges_list}

    @staticmethod
    def from_dict(data):
        """Reconstruye un grafo desde un dict.  O(V + E)."""
        g = WarehouseGraph(name=data.get("name", "Warehouse"))
        for n in data["nodes"]:
            x, y, z = n["position"]
            g.add_node(
                n["node_id"],
                Position(x, y, z),
                n["node_type"],
                **n.get("metadata", {})
            )
        for e in data["edges"]:
            g.add_edge(e["u"], e["v"], e["weight"])
        return g

    # ------------------------------------------------------------------
    # 4.5 Dunders
    # ------------------------------------------------------------------
    def __len__(self):
        return len(self._nodes)

    def __contains__(self, node_id):
        return node_id in self._nodes

    def __repr__(self):
        return "WarehouseGraph(name=%r, V=%d, E=%d)" % (
            self.name, len(self._nodes), self._edge_count
        )


# ---------------------------------------------------------------------------
# 5. Demo de uso (python -m src.core.warehouse)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=== Demo: WarehouseGraph ===\n")

    wh = WarehouseGraph(name="Demo Central")

    wh.add_node(0, Position(0, 0, 0), NodeType.DISPATCH, zone_name="A")
    wh.add_node(1, Position(0, 5, 0))
    wh.add_node(2, Position(5, 5, 0))
    wh.add_node(3, Position(10, 5, 0))
    wh.add_node(4, Position(10, 0, 0))
    wh.add_node(10, Position(0, 10, 2), NodeType.RACK, rack_id="R10")
    wh.add_node(11, Position(5, 10, 1), NodeType.RACK, rack_id="R11")
    wh.add_node(12, Position(10, 10, 3), NodeType.RACK, rack_id="R12")

    wh.add_edge(0, 1)
    wh.add_edge(1, 2)
    wh.add_edge(2, 3)
    wh.add_edge(3, 4)
    wh.add_edge(4, 0)
    wh.add_edge(1, 10)
    wh.add_edge(2, 11)
    wh.add_edge(3, 12)

    print(wh)
    print("Nodos totales: %d" % wh.node_count())
    print("Aristas totales: %d" % wh.edge_count())

    print("\n-- Vecinos del nodo 2 --")
    for vecino, peso in wh.get_neighbors(2).items():
        print("  %s  (peso = %.2f)" % (vecino, peso))

    print("\n-- Racks del warehouse --")
    for rack in wh.nodes_by_type(NodeType.RACK):
        print("  %s" % rack)

    print("\n-- Nodo más cercano a (5, 9, 0) --")
    print("  %s" % wh.find_nearest_node(Position(5, 9, 0)))