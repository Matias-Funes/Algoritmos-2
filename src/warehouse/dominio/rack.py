from dataclasses import dataclass


@dataclass
class Rack:
    id: str
    x: int
    y: int
    niveles: int = 4  # cantidad de estantes físicos del rack
