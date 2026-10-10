from dataclasses import dataclass

from warehouse.dominio.posicion import Posicion


@dataclass
class Puerta:
    id: str
    posicion: Posicion
    tipo: str  # "INBOUND" | "OUTBOUND" | "AMBOS"
    nodo: int
