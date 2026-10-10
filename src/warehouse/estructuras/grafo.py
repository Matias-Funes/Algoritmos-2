from dataclasses import dataclass
from typing import Optional

from warehouse.dominio.posicion import Posicion
from warehouse.dominio.tipo_nodo import TipoNodo


@dataclass
class Nodo:
    id: int
    posicion: Posicion
    tipo: TipoNodo
    producto_id: Optional[str] = None  # solo si tipo == RACK


@dataclass
class Arista:
    origen: int
    destino: int
    peso: float = 1.0


class Grafo:
    def __init__(self) -> None:
        self._nodos: dict[int, Nodo] = {}
        self._adyacencia: dict[int, list[Arista]] = {}
        self._siguiente_id: int = 0

    # --- construcción ---
    def agregar_nodo(
        self, posicion: Posicion, tipo: TipoNodo, producto_id: Optional[str] = None
    ) -> int:
        nid = self._siguiente_id
        self._siguiente_id += 1
        self._nodos[nid] = Nodo(nid, posicion, tipo, producto_id)
        self._adyacencia[nid] = []
        return nid

    def agregar_arista(self, u: int, v: int, peso: float = 1.0) -> None:
        self._adyacencia[u].append(Arista(u, v, peso))
        self._adyacencia[v].append(Arista(v, u, peso))

    # --- consulta ---
    def nodo(self, nid: int) -> Nodo:
        return self._nodos[nid]

    def vecinos(self, nid: int) -> list[Arista]:
        return self._adyacencia[nid]

    def peso(self, u: int, v: int) -> float:
        for a in self._adyacencia[u]:
            if a.destino == v:
                return a.peso
        raise KeyError(f"No existe arista {u}->{v}")

    def nodos(self):
        return self._nodos.values()

    def contiene(self, nid: int) -> bool:
        return nid in self._nodos

    def __len__(self) -> int:
        return len(self._nodos)
