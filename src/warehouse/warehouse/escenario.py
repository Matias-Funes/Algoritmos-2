from dataclasses import dataclass, field

from warehouse.dominio.pedido import Pedido
from warehouse.warehouse.warehouse import Warehouse


@dataclass
class WaveConfig:
    max_pedidos: int = 3
    max_productos: int = 20


@dataclass
class Escenario:
    nombre: str
    warehouse: Warehouse
    pedidos: list[Pedido] = field(default_factory=list)
    wave_config: WaveConfig = field(default_factory=WaveConfig)
