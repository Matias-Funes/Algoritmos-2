from dataclasses import dataclass


@dataclass
class ZonaDespacho:
    id: str
    p1: tuple[int, int]
    p2: tuple[int, int]
    nodo_representativo: int  # id de nodo del grafo
