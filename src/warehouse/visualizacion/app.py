import tkinter as tk

from warehouse.algoritmos.recorridos import ResultadoRecorrido
from warehouse.dominio.wave import Wave
from warehouse.simulacion.estado import EstadoSimulacion
from warehouse.visualizacion.render import (
    COLOR_PICKER,
    COLOR_PRODUCTO_PENDIENTE,
    COLOR_PRODUCTO_RECOGIDO,
    COLOR_RECORRIDO_HECHO,
    COLOR_RECORRIDO_PENDIENTE,
    centro_celda_px,
    dibujar_polilinea,
    dibujar_punto,
    dibujar_warehouse,
    dibujar_zonas,
)
from warehouse.warehouse.escenario import Escenario


class AppSimulacion:
    """App tkinter para simular el recorrido de una wave."""

    def __init__(
        self,
        root: tk.Tk,
        escenario: Escenario,
        wave: Wave,
        resultado: ResultadoRecorrido,
        celda_px: int = 40,
        velocidad_ms: int = 120,
    ) -> None:
        self.root = root
        self.escenario = escenario
        self.wave = wave
        self.resultado = resultado
        self.estado = EstadoSimulacion.desde_wave(wave, resultado, escenario.warehouse)
        self.celda_px = celda_px
        self.margen = 20
        self.velocidad_ms = velocidad_ms
        self.after_id: str | None = None
        self.coords: dict[tuple[int, int], tuple[float, float, float, float]] = {}

        self._construir_ui()
        self._redibujar()

    # --- UI ---

    def _construir_ui(self) -> None:
        self.root.title(f"Wave {self.wave.id} — {self.resultado.estrategia}")

        self.canvas = tk.Canvas(
            self.root,
            bg="white",
            width=self.escenario.warehouse.ancho * self.celda_px + 2 * self.margen,
            height=self.escenario.warehouse.alto * self.celda_px + 2 * self.margen,
        )
        self.canvas.pack(side="top")

        frame = tk.Frame(self.root)
        frame.pack(side="bottom", fill="x", padx=10, pady=8)

        tk.Button(frame, text="▶ Play", command=self.play, width=8).pack(
            side="left", padx=2
        )
        tk.Button(frame, text="⏸ Pause", command=self.pause, width=8).pack(
            side="left", padx=2
        )
        tk.Button(frame, text="⏭ Step", command=self.step, width=8).pack(
            side="left", padx=2
        )
        tk.Button(frame, text="⟲ Reset", command=self.reset, width=8).pack(
            side="left", padx=2
        )

        self.lbl_estado = tk.Label(frame, text="", anchor="w", font=("monospace", 10))
        self.lbl_estado.pack(side="left", padx=20)

    # --- dibujo ---

    def _redibujar(self) -> None:
        self.canvas.delete("all")
        self.coords = dibujar_warehouse(
            self.canvas, self.escenario.warehouse, self.celda_px, self.margen
        )
        dibujar_zonas(self.canvas, self.escenario.warehouse, self.coords)  # ← nuevo
        self._dibujar_recorrido_completo()
        self._dibujar_recorrido_hecho()
        self._dibujar_productos()
        self._dibujar_picker()
        self._actualizar_label()

    def _centro_de_nodo(self, nid: int) -> tuple[float, float]:
        nodo = self.escenario.warehouse.grafo.nodo(nid)
        return centro_celda_px(self.coords, nodo.posicion.x, nodo.posicion.y)

    def _dibujar_recorrido_completo(self) -> None:
        puntos = [self._centro_de_nodo(nid) for nid in self.estado.camino]
        dibujar_polilinea(
            self.canvas,
            puntos,
            color=COLOR_RECORRIDO_PENDIENTE,
            grosor=1,
            dash=(3, 3),
        )

    def _dibujar_recorrido_hecho(self) -> None:
        idx = self.estado.indice_actual
        if idx < 1:
            return
        puntos = [self._centro_de_nodo(nid) for nid in self.estado.camino[: idx + 1]]
        dibujar_polilinea(self.canvas, puntos, color=COLOR_RECORRIDO_HECHO, grosor=3)

    def _dibujar_productos(self) -> None:
        recogidos = self.estado.productos_recogidos()
        for pid in self.estado.productos_totales:
            prod = self.escenario.warehouse.productos[pid]
            nodo = self.escenario.warehouse.grafo.nodo(prod.nodo_picking)
            cx, cy = centro_celda_px(self.coords, nodo.posicion.x, nodo.posicion.y)
            color = (
                COLOR_PRODUCTO_RECOGIDO
                if pid in recogidos
                else COLOR_PRODUCTO_PENDIENTE
            )
            dibujar_punto(self.canvas, cx, cy, radio=self.celda_px * 0.22, color=color)

    def _dibujar_picker(self) -> None:
        cx, cy = self._centro_de_nodo(self.estado.nodo_actual)
        dibujar_punto(
            self.canvas, cx, cy, radio=self.celda_px * 0.32, color=COLOR_PICKER
        )

    def _actualizar_label(self) -> None:
        idx = self.estado.indice_actual
        total = len(self.estado.camino) - 1
        rec = len(self.estado.productos_recogidos())
        tot = len(self.estado.productos_totales)
        txt = (
            f"Wave {self.wave.id}  |  paso {idx:>3}/{total:<3}  |  "
            f"productos {rec:>2}/{tot:<2}"
        )
        if self.estado.completada:
            txt += "  ✔ COMPLETADA"
        self.lbl_estado.config(text=txt)

    # --- controles ---

    def play(self) -> None:
        if self.after_id is not None:
            return
        if self.estado.completada:
            return
        self._tick()

    def _tick(self) -> None:
        if not self.estado.avanzar():
            self.after_id = None
            return
        self._redibujar()
        if self.estado.completada:
            self.after_id = None
        else:
            self.after_id = self.root.after(self.velocidad_ms, self._tick)

    def pause(self) -> None:
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None

    def step(self) -> None:
        self.pause()
        self.estado.avanzar()
        self._redibujar()

    def reset(self) -> None:
        self.pause()
        self.estado.reiniciar()
        self._redibujar()
