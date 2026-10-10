from dataclasses import dataclass, field

from warehouse.dominio.estado_pedido import EstadoPedido
from warehouse.dominio.item_pedido import ItemPedido


@dataclass
class Pedido:
    id: str
    items: list[ItemPedido] = field(default_factory=list)
    prioridad: int = 3  # 1..5, mayor = más prioritario
    estado: EstadoPedido = EstadoPedido.PENDIENTE

    def __post_init__(self) -> None:
        if not 1 <= self.prioridad <= 5:
            raise ValueError(f"Prioridad fuera de rango [1,5]: {self.prioridad}")

    # --- consultas ---
    def cantidad_total_productos(self) -> int:
        """Suma todas las cantidades pedidas."""
        return sum(item.cantidad for item in self.items)

    def productos_ids(self) -> set[str]:
        return {item.producto_id for item in self.items}

    def tiene_producto(self, producto_id: str) -> bool:
        return any(item.producto_id == producto_id for item in self.items)

    # --- mutación ---
    def agregar_item(self, producto_id: str, cantidad: int) -> None:
        """Agrega un item. Si el producto ya existe, suma la cantidad."""
        for item in self.items:
            if item.producto_id == producto_id:
                item.cantidad += cantidad
                return
        self.items.append(ItemPedido(producto_id, cantidad))
