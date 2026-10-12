from __future__ import annotations  # las anotaciones se evalúen como strings.

from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
)  # TYPE_CHECKING evita el import en runtime (evitar el ciclo de imports)

from warehouse.dominio.pedido import Pedido
from warehouse.dominio.wave import Wave
from warehouse.warehouse.warehouse import Warehouse

if TYPE_CHECKING:
    from warehouse.algoritmos.recorridos import ResultadoRecorrido


@dataclass
class WaveConfig:
    max_pedidos: int = 3
    max_productos: int = 20


@dataclass
class Sesion:
    wave_actual: int = 0
    indice_actual: int = 0
    estrategia_recorrido: str = "vecino_mas_cercano"


@dataclass
class Escenario:
    nombre: str
    warehouse: Warehouse
    pedidos: list[Pedido] = field(default_factory=list)
    wave_config: WaveConfig = field(default_factory=WaveConfig)
    seed: int | None = None
    waves: list[Wave] = field(default_factory=list)
    resultados: dict[str, "ResultadoRecorrido"] = field(default_factory=dict)
    sesion: Sesion | None = None
