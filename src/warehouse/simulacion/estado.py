from dataclasses import dataclass, field

from warehouse.algoritmos.recorridos import ResultadoRecorrido
from warehouse.dominio.wave import Wave
from warehouse.warehouse.warehouse import Warehouse


@dataclass
class EstadoSimulacion:
    wave_id: str
    camino: list[int]  # secuencia completa de nodos
    nodo_a_productos: dict[int, list[str]]  # nodo_picking -> [producto_ids]
    productos_totales: set[str]
    indices_de_paradas: list[int]
    nodos_paradas: list[int]
    indice_actual: int = 0

    # --- construcción ---

    @classmethod
    def desde_wave(
        cls,
        wave: Wave,
        resultado: ResultadoRecorrido,
        warehouse: Warehouse,
    ) -> "EstadoSimulacion":
        mapa: dict[int, list[str]] = {}
        for pid in wave.ubicaciones_requeridas():
            producto = warehouse.productos.get(pid)
            if producto is None:
                raise ValueError(
                    f"La wave {wave.id} referencia producto inexistente: {pid}"
                )
            mapa.setdefault(producto.nodo_picking, []).append(pid)

        return cls(
            wave_id=wave.id,
            camino=list(resultado.camino_completo),
            nodo_a_productos=mapa,
            productos_totales=set(wave.ubicaciones_requeridas()),
            indices_de_paradas=list(resultado.indices_de_paradas),
            nodos_paradas=list(resultado.orden_paradas),
        )

    # --- consultas ---

    @property
    def nodo_actual(self) -> int:
        return self.camino[self.indice_actual]

    @property
    def al_final(self) -> bool:
        return self.indice_actual >= len(self.camino) - 1

    @property
    def completada(self) -> bool:
        return self.al_final and self.productos_recogidos() == self.productos_totales

    def productos_recogidos(self) -> set[str]:
        """Productos recogidos hasta el paso actual (inclusive), contando solo las
        paradas que el picker ya alcanzó."""
        recogidos: set[str] = set()
        for i, nodo_parada in enumerate(self.nodos_paradas):
            if i >= len(self.indices_de_paradas):
                break
            if self.indice_actual >= self.indices_de_paradas[i]:
                recogidos.update(self.nodo_a_productos.get(nodo_parada, ()))
        return recogidos

    def productos_pendientes(self) -> set[str]:
        return self.productos_totales - self.productos_recogidos()

    # --- mutación ---

    def avanzar(self) -> bool:
        """Avanza un paso. Devuelve False si ya estaba al final."""
        if self.al_final:
            return False
        self.indice_actual += 1
        return True

    def retroceder(self) -> bool:
        """Retrocede un paso. Devuelve False si ya estaba al inicio."""
        if self.indice_actual <= 0:
            return False
        self.indice_actual -= 1
        return True

    def reiniciar(self) -> None:
        self.indice_actual = 0
