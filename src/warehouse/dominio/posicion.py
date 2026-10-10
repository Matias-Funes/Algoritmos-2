from dataclasses import dataclass


@dataclass(frozen=True)
class Posicion:
    x: int
    y: int
    z: int = 0

    def xy(self) -> tuple[int, int]:
        return (self.x, self.y)
