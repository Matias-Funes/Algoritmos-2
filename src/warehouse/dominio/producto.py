from dataclasses import dataclass


@dataclass
class Producto:
    id: str
    nombre: str
    rack_id: str  # referencia al Rack donde vive
    z: int  # altura dentro del rack
    stock: int
    nodo_picking: int = (
        -1
    )  # id de nodo del grafo desde donde se recoge. Se asigna al construir el grafo (-1 = sin asignar)
