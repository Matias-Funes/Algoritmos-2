from dataclasses import dataclass


@dataclass
class ItemPedido:
    producto_id: str
    cantidad: int

    def __post_init__(self) -> None:
        if self.cantidad <= 0:
            raise ValueError(f"La cantidad debe ser > 0, recibí {self.cantidad}")
