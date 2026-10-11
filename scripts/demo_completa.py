"""
Demo completa: genera un escenario grande, produce todas las waves y las
simula en secuencia en la misma ventana de tkinter.

Uso:
    python scripts/demo_completa.py
    python scripts/demo_completa.py --bloques 10 --alto 14 --pedidos 100
    python scripts/demo_completa.py --estrategia orden_pedidos
"""

import argparse
import tkinter as tk
from tkinter import ttk

from warehouse.algoritmos.recorridos import ESTRATEGIAS, recorrer_wave
from warehouse.generacion.generador import ConfigGeneracion, generar_escenario
from warehouse.generacion.validador import validar_escenario
from warehouse.simulacion.estado import EstadoSimulacion
from warehouse.visualizacion.render import (COLOR_CANVAS_FONDO, COLOR_PICKER,
                                            COLOR_PRODUCTO_INVENTARIO,
                                            COLOR_PRODUCTO_PENDIENTE,
                                            COLOR_PRODUCTO_RECOGIDO,
                                            COLOR_RECORRIDO_HECHO,
                                            COLOR_RECORRIDO_PENDIENTE,
                                            centro_celda_px,
                                            crear_panel_leyenda,
                                            dibujar_polilinea, dibujar_punto,
                                            dibujar_warehouse)
from warehouse.waves.generador_waves import EstrategiaWaves, generar_waves

# Tamaño fijo del área de dibujo
ANCHO_CANVAS = 1100
ALTO_CANVAS = 500


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bloques", type=int, default=6)
    parser.add_argument("--alto", type=int, default=10)
    parser.add_argument(
        "--pasillos-h",
        type=int,
        default=0,
        help="Cada cuántas filas poner pasillo horizontal (0=solo arriba/abajo)",
    )
    parser.add_argument("--pedidos", type=int, default=40)
    parser.add_argument("--max-pedidos-wave", type=int, default=3)
    parser.add_argument("--max-productos-wave", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--productos-por-rack", type=int, default=2,
        help="Cantidad de productos por rack (alturas z)"
    )
    parser.add_argument(
        "--estrategia", choices=list(ESTRATEGIAS.keys()), default="vecino_mas_cercano"
    )
    parser.add_argument(
        "--estrategia-waves",
        choices=[e.value for e in EstrategiaWaves],
        default=EstrategiaWaves.PRIORIDAD_Y_CERCANIA.value,
    )
    args = parser.parse_args()

    # 1. Generar escenario
    print("Generando escenario...")
    cfg = ConfigGeneracion(
        n_bloques_racks=args.bloques,
        alto=args.alto,
        n_pedidos=args.pedidos,
        productos_por_rack=args.productos_por_rack,
        cada_cuantas_filas_pasillo_horizontal=args.pasillos_h,
        seed=args.seed,
    )
    escenario = generar_escenario(cfg)
    validar_escenario(escenario)

    print(f"  Warehouse: {escenario.warehouse.ancho} x {escenario.warehouse.alto}")
    print(f"  Nodos en grafo: {len(escenario.warehouse.grafo)}")
    print(f"  Racks: {len(escenario.warehouse.racks)}")
    print(f"  Productos: {len(escenario.warehouse.productos)}")
    print(f"  Pedidos: {len(escenario.pedidos)}")

    # 2. Generar waves
    print("\nGenerando waves...")
    estrat_waves = EstrategiaWaves(args.estrategia_waves)
    waves = generar_waves(
        escenario.pedidos,
        escenario.warehouse,
        max_pedidos=args.max_pedidos_wave,
        max_productos=args.max_productos_wave,
        estrategia=estrat_waves,
    )
    print(f"  {len(waves)} waves generadas")

    # 3. Calcular recorridos de todas las waves
    print(f"\nCalculando recorridos ({args.estrategia})...")
    resultados = []
    for w in waves:
        r = recorrer_wave(w, escenario.warehouse, estrategia=args.estrategia)
        resultados.append((w, r))
        print(
            f"  {w.id}: {r.distancia_total:>6.1f} m, "
            f"{len(r.orden_paradas):>2d} paradas, "
            f"{r.nodos_visitados:>3d} nodos"
        )

    # 4. Calcular tamaño de canvas y celda_px según la pantalla
    root = tk.Tk()
    style = ttk.Style()
    style.theme_use("clam")  # o "alt", "default"
    root.withdraw()
    alto_pantalla = root.winfo_screenheight()
    ancho_pantalla = root.winfo_screenwidth()
    root.deiconify()

    ancho_canvas = min(950, ancho_pantalla - 400)
    alto_canvas = min(700, alto_pantalla - 250)

    margen = 20
    celda_px_w = (ancho_canvas - 2 * margen) // escenario.warehouse.ancho
    celda_px_h = (alto_canvas - 2 * margen) // escenario.warehouse.alto
    celda_px = max(4, min(celda_px_w, celda_px_h))
    print(f"\nCanvas: {ancho_canvas}x{alto_canvas}, celda: {celda_px}px")

    # 5. Simular todas las waves en secuencia
    print("Iniciando simulación. Cerrá la ventana para terminar.")
    SimulacionSecuencial(
        root,
        escenario,
        resultados,
        estrategia=args.estrategia,
        celda_px=celda_px,
        ancho_canvas=ancho_canvas,
        alto_canvas=alto_canvas,
    )

    # Centrar la ventana en pantalla
    root.update_idletasks()
    w = root.winfo_reqwidth()
    h = root.winfo_reqheight()
    x = max((root.winfo_screenwidth() - w) // 2, 0)
    y = max((root.winfo_screenheight() - h) // 2, 0)
    root.geometry(f"{w}x{h}+{x}+{y}")

    root.mainloop()


class SimulacionSecuencial:
    """Encadena la simulación de todas las waves en la misma ventana."""

    def __init__(
        self,
        root: tk.Tk,
        escenario,
        resultados: list,
        estrategia: str,
        celda_px: int = 30,
        ancho_canvas: int = ANCHO_CANVAS,
        alto_canvas: int = ALTO_CANVAS,
    ) -> None:
        self.root = root
        self.escenario = escenario
        self.resultados = resultados
        self.estrategia = estrategia
        self.celda_px = celda_px
        self.ancho_canvas = ancho_canvas
        self.alto_canvas = alto_canvas
        self.margen = 20
        self.indice_actual = 0
        self.after_id = None
        self.estado: EstadoSimulacion | None = None
        self.coords: dict = {}
        self.labels_productos: dict[str, tk.Label] = {}

        self.root.title(f"Demo — {len(resultados)} waves — {estrategia}")
        self._construir_ui()
        self._cargar_wave(0)

    def _construir_ui(self) -> None:
        # Header
        header = tk.Frame(self.root, bg=COLOR_CANVAS_FONDO)
        header.pack(side="top", fill="x", padx=10, pady=(10, 0))
        self.lbl_titulo = tk.Label(
            header,
            text="",
            anchor="w",
            bg=COLOR_CANVAS_FONDO,
            font=("sans-serif", 14, "bold"),
        )
        self.lbl_titulo.pack(side="left")

        # Barra de progreso
        self.progress = ttk.Progressbar(header, length=400, mode="determinate")
        self.progress.pack(side="left", padx=20)

        # Frame horizontal: canvas + leyenda
        frame_principal = tk.Frame(self.root, bg=COLOR_CANVAS_FONDO)
        frame_principal.pack(side="top", padx=10, pady=10)

        self.canvas = tk.Canvas(
            frame_principal,
            bg=COLOR_CANVAS_FONDO,
            width=self.ancho_canvas,
            height=self.alto_canvas,
            highlightthickness=1,
            highlightbackground="#cccccc",
        )

        self.canvas.pack(side="left", anchor="n")

        # Columna derecha: leyenda arriba, info abajo
        panel_derecho = tk.Frame(frame_principal, bg=COLOR_CANVAS_FONDO)
        panel_derecho.pack(side="left", fill="y", padx=(10, 0))

        panel_leyenda = crear_panel_leyenda(panel_derecho)
        panel_leyenda.pack(side="top", fill="x")

        # Panel info debajo de la leyenda
        panel_info = tk.LabelFrame(
            panel_derecho,
            text="Estado",
            padx=10,
            pady=8,
            bg=COLOR_CANVAS_FONDO,
            font=("sans-serif", 10, "bold"),
        )
        panel_info.pack(side="top", fill="both", expand=True, pady=(10, 0))

        self.lbl_info_paso = tk.Label(
            panel_info, anchor="w", bg=COLOR_CANVAS_FONDO, font=("monospace", 9)
        )
        self.lbl_info_paso.pack(fill="x")
        self.lbl_info_prod = tk.Label(
            panel_info, anchor="w", bg=COLOR_CANVAS_FONDO, font=("monospace", 9)
        )
        self.lbl_info_prod.pack(fill="x")
        self.lbl_info_prio = tk.Label(
            panel_info, anchor="w", bg=COLOR_CANVAS_FONDO, font=("monospace", 9)
        )
        self.lbl_info_prio.pack(fill="x", pady=(0, 6))

        tk.Label(
            panel_info,
            text="Productos:",
            anchor="w",
            bg=COLOR_CANVAS_FONDO,
            font=("sans-serif", 9, "bold"),
        ).pack(fill="x")
        self.frame_productos = tk.Frame(panel_info, bg=COLOR_CANVAS_FONDO)
        self.frame_productos.pack(fill="both", expand=True)

        # Panel de controles
        panel = tk.Frame(self.root)
        panel.pack(side="bottom", fill="x", padx=10, pady=8)

        self.btn_play_pause = ttk.Button(
            panel, text="▶ Play", command=self.toggle_play_pause, width=10
        )
        self.btn_play_pause.pack(side="left", padx=2)

        ttk.Button(panel, text="⏮ Step atrás", command=self.step_atras, width=12).pack(
            side="left", padx=2
        )
        ttk.Button(panel, text="⏭ Step", command=self.step, width=8).pack(
            side="left", padx=2
        )
        ttk.Button(panel, text="⟲ Reset", command=self.reset, width=8).pack(
            side="left", padx=2
        )

        tk.Label(panel, text="  |  ").pack(side="left")

        self.btn_prev = ttk.Button(
            panel, text="◀ Wave ant.", command=self.wave_anterior, width=12
        )
        self.btn_prev.pack(side="left", padx=2)
        self.btn_next = ttk.Button(
            panel, text="Wave sig. ▶", command=self.wave_siguiente, width=12
        )
        self.btn_next.pack(side="left", padx=2)

        self.lbl_estado = tk.Label(panel, text="", anchor="w", font=("monospace", 10))
        self.lbl_estado.pack(side="left", padx=20)

        ttk.Button(panel, text="✕ Cerrar", command=self.root.destroy, width=10).pack(
            side="right", padx=2
        )

    # --- carga de wave ---

    def _cargar_wave(self, indice: int) -> None:
        if not (0 <= indice < len(self.resultados)):
            return
        self.pause()
        self.indice_actual = indice
        wave, resultado = self.resultados[indice]
        self.estado = EstadoSimulacion.desde_wave(
            wave, resultado, self.escenario.warehouse
        )
        self._construir_lista_productos()
        self._redibujar_todo()

    # --- dibujo ---

    def _redibujar_todo(self) -> None:

        self.canvas.delete("all")

        self.coords = dibujar_warehouse(
            self.canvas, self.escenario.warehouse, self.celda_px, self.margen
        )

        if self.estado is None:
            return

        def centro(nid: int) -> tuple[float, float]:
            nodo = self.escenario.warehouse.grafo.nodo(nid)
            return centro_celda_px(self.coords, nodo.posicion.x, nodo.posicion.y)

        # Recorrido completo punteado
        puntos = [centro(nid) for nid in self.estado.camino]
        dibujar_polilinea(
            self.canvas,
            puntos,
            color=COLOR_RECORRIDO_PENDIENTE,
            grosor=1,
            dash=(3, 3),
        )

        # Recorrido ya hecho
        idx = self.estado.indice_actual
        if idx >= 1:
            puntos_hechos = [centro(nid) for nid in self.estado.camino[: idx + 1]]
            dibujar_polilinea(
                self.canvas,
                puntos_hechos,
                color=COLOR_RECORRIDO_HECHO,
                grosor=3,
            )

        # Productos: mostramos TODOS los del warehouse en gris claro,
        # y destacamos los de la wave actual en rojo/verde.
        recogidos = self.estado.productos_recogidos()
        productos_de_la_wave = self.estado.productos_totales

        # Agrupar TODOS los productos del warehouse por rack
        productos_por_rack: dict[str, list[str]] = {}
        for pid, prod in self.escenario.warehouse.productos.items():
            productos_por_rack.setdefault(prod.rack_id, []).append(pid)

        for rack_id, pids in productos_por_rack.items():
            rack = self.escenario.warehouse.racks[rack_id]
            cx_rack, cy_rack = centro_celda_px(self.coords, rack.x, rack.y)

            # Ordenar por z
            pids_ordenados = sorted(
                pids,
                key=lambda p: self.escenario.warehouse.productos[p].z,
            )
            n = len(pids_ordenados)

            if n == 0:
                continue

            # Si hay demasiados, un solo punto grande
            if n > 6:
                dibujar_punto(
                    self.canvas,
                    cx_rack,
                    cy_rack,
                    radio=self.celda_px * 0.18,
                    color=COLOR_PRODUCTO_INVENTARIO,
                )
                continue

            # Distribuir verticalmente
            radio = self.celda_px * 0.10
            separacion = self.celda_px * 0.22

            for i, pid in enumerate(pids_ordenados):
                if n == 1:
                    y = cy_rack
                else:
                    y = cy_rack - (n - 1) * separacion / 2 + i * separacion

                if pid in recogidos:
                    color = COLOR_PRODUCTO_RECOGIDO
                elif pid in productos_de_la_wave:
                    color = COLOR_PRODUCTO_PENDIENTE
                else:
                    color = COLOR_PRODUCTO_INVENTARIO

                dibujar_punto(self.canvas, cx_rack, y, radio=radio, color=color)




        # Picker
        cx, cy = centro(self.estado.nodo_actual)
        dibujar_punto(
            self.canvas, cx, cy, radio=self.celda_px * 0.32, color=COLOR_PICKER
        )

        self._actualizar_label()

        self._actualizar_panel_info()

    def _redibujar(self) -> None:
        self._redibujar_todo()

    def _actualizar_label(self) -> None:
        if self.estado is None:
            return
        wave = self.resultados[self.indice_actual][0]
        self.lbl_titulo.config(
            text=f"Wave {wave.id}  ·  {self.estrategia}  ·  "
            f"{wave.cantidad_pedidos()} pedidos"
        )
        idx = self.estado.indice_actual
        total = len(self.estado.camino) - 1
        rec = len(self.estado.productos_recogidos())
        tot = len(self.estado.productos_totales)
        txt = (
            f"Wave {self.indice_actual + 1}/{len(self.resultados)}  |  "
            f"paso {idx:>3}/{total:<3}  |  "
            f"productos {rec:>2}/{tot:<2}"
        )
        if self.estado.completada:
            txt += "  ✔"
        self.lbl_estado.config(text=txt)
        self.btn_prev.config(state="normal" if self.indice_actual > 0 else "disabled")
        self.btn_next.config(
            state=(
                "normal"
                if self.indice_actual < len(self.resultados) - 1
                else "disabled"
            )
        )

    def _construir_lista_productos(self) -> None:
        """Crea los labels de productos una sola vez por wave."""
        # Limpiar labels viejos
        for widget in self.frame_productos.winfo_children():
            widget.destroy()
        self.labels_productos.clear()

        if self.estado is None:
            return


        wave = self.resultados[self.indice_actual][0]

        for pid in sorted(self.estado.productos_totales):
            prod = self.escenario.warehouse.productos[pid]
            cantidad_pedida = sum(
                item.cantidad
                for pedido in wave.pedidos
                for item in pedido.items
                if item.producto_id == pid
                )
            lbl = tk.Label(
                self.frame_productos,
                text=f"● {pid} stock={prod.stock}  pide={cantidad_pedida}",
                anchor="w",
                bg=COLOR_CANVAS_FONDO,
                fg=COLOR_PRODUCTO_PENDIENTE,  # arranca rojo
                font=("monospace", 9),
            )
            lbl.pack(fill="x")
            self.labels_productos[pid] = lbl

    def _actualizar_panel_info(self) -> None:
        if self.estado is None:
            return
        wave = self.resultados[self.indice_actual][0]

        idx = self.estado.indice_actual
        total = len(self.estado.camino) - 1
        rec = len(self.estado.productos_recogidos())
        tot = len(self.estado.productos_totales)

        self.lbl_info_paso.config(text=f"Paso: {idx} / {total}")
        self.lbl_info_prod.config(text=f"Productos: {rec} / {tot}")
        self.lbl_info_prio.config(text=f"Prioridad máx: {wave.prioridad_maxima()}")

        # Barra de progreso
        if total > 0:
            self.progress["value"] = (idx / total) * 100
        else:
            self.progress["value"] = 0

        # Solo actualizar el color de cada label. No destruir ni recrear.
        recogidos = self.estado.productos_recogidos()
        for pid, lbl in self.labels_productos.items():
            nuevo_color = (
                COLOR_PRODUCTO_RECOGIDO
                if pid in recogidos
                else COLOR_PRODUCTO_PENDIENTE
            )
            if lbl.cget("fg") != nuevo_color:
                lbl.config(fg=nuevo_color)

    # --- controles ---

    def toggle_play_pause(self) -> None:
        if self.after_id is not None:
            self.pause()
        else:
            self.play()

    def _actualizar_boton_play_pause(self) -> None:
        """Sincroniza el texto del botón con el estado de reproducción."""
        if self.after_id is not None:
            self.btn_play_pause.config(text="⏸ Pause")
        else:
            self.btn_play_pause.config(text="▶ Play")

    def play(self) -> None:
        if self.after_id is not None or self.estado is None or self.estado.completada:
            return
        self._tick()
        self._actualizar_boton_play_pause()

    def _tick(self) -> None:
        if self.estado is None or not self.estado.avanzar():
            self.after_id = None
            self._actualizar_boton_play_pause()
            return
        self._redibujar()
        if self.estado.completada:
            self.after_id = None
            self._actualizar_boton_play_pause()
        else:
            self.after_id = self.root.after(100, self._tick)

    def pause(self) -> None:
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        self._actualizar_boton_play_pause()

    def step(self) -> None:
        self.pause()
        if self.estado is not None:
            self.estado.avanzar()
            self._redibujar()

    def step_atras(self) -> None:
        self.pause()
        if self.estado is None:
            return
        if self.estado.retroceder():
            self._redibujar()

    def reset(self) -> None:
        self.pause()
        if self.estado is not None:
            self.estado.reiniciar()
            self._redibujar()

    def wave_anterior(self) -> None:
        if self.indice_actual > 0:
            self._cargar_wave(self.indice_actual - 1)

    def wave_siguiente(self) -> None:
        if self.indice_actual < len(self.resultados) - 1:
            self._cargar_wave(self.indice_actual + 1)


if __name__ == "__main__":
    main()
