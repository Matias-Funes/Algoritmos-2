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
from pathlib import Path
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
                                            dibujar_circulo_hueco,
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
        "--niveles-por-rack", type=int, default=4,
        help="Cantidad de estantes físicos por rack"
    )
    parser.add_argument(
        "--estrategia", choices=list(ESTRATEGIAS.keys()), default="vecino_mas_cercano"
    )
    parser.add_argument(
        "--estrategia-waves",
        choices=[e.value for e in EstrategiaWaves],
        default=EstrategiaWaves.PRIORIDAD_Y_CERCANIA.value,
    )
    parser.add_argument(
        "--wave", type=int, default=0,
        help="Índice de la wave inicial (0-based)"
    )
    parser.add_argument(
        "--cargar", type=str, default=None,
        help="Ruta a un archivo JSON con un escenario guardado"
    )
    args = parser.parse_args()


    # --- Rama 1: cargar desde disco ---
    if args.cargar:
        print(f"Cargando escenario desde {args.cargar}...")
        from warehouse.io.cargador_json import cargar_escenario

        escenario = cargar_escenario(args.cargar)
        print(f"  Warehouse: {escenario.warehouse.ancho} x {escenario.warehouse.alto}")
        print(f"  Racks: {len(escenario.warehouse.racks)}")
        print(f"  Productos: {len(escenario.warehouse.productos)}")
        print(f"  Pedidos: {len(escenario.pedidos)}")
        print(f"  Waves: {len(escenario.waves)}")

        if not escenario.waves:
            raise SystemExit(
                "El archivo cargado no contiene waves. "
                "Generá el escenario de cero en lugar de cargarlo."
            )

        # Convertir el dict de resultados en la lista de tuplas que espera la UI
        resultados = [
            (w, escenario.resultados[w.id]) for w in escenario.waves
        ]
        estrategia = (
            escenario.sesion.estrategia_recorrido
            if escenario.sesion is not None
            else args.estrategia
        )
        indice_inicial = (
            escenario.sesion.wave_actual if escenario.sesion is not None else 0
        )
        paso_inicial = (
            escenario.sesion.indice_actual if escenario.sesion is not None else 0
        )

    # --- Rama 2: generar de cero ---
    else:
        # 1. Generar escenario
        print("Generando escenario...")
        cfg = ConfigGeneracion(
            n_bloques_racks=args.bloques,
            alto=args.alto,
            n_pedidos=args.pedidos,
            niveles_por_rack=args.niveles_por_rack,
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

        # Adjuntar waves y resultados al escenario, para que se puedan exportar
        escenario.waves = waves
        escenario.resultados = {w.id: r for w, r in resultados}

        estrategia = args.estrategia
        indice_inicial = args.wave
        paso_inicial = 0

    # 4. Calcular tamaño de canvas y celda_px según la pantalla
    # --- Setup de la ventana ---
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
        indice_inicial=args.wave,
        paso_inicial=paso_inicial,
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
        indice_inicial: int = 0,
        paso_inicial: int = 0,
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
        self._cargar_wave(indice_inicial, paso_inicial=paso_inicial)

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

        self.lbl_estado = tk.Label(panel, text="", anchor="w", font=("monospace", 10), width=45)
        self.lbl_estado.pack(side="left", padx=20)

        ttk.Button(panel, text="✕ Cerrar", command=self.root.destroy, width=10).pack(
            side="right", padx=2
        )

        ttk.Button(
            panel, text="📂 Cargar", command=self.cargar_sesion, width=12
        ).pack(side="right", padx=2)

        ttk.Button(
            panel, text="💾 Guardar", command=self.guardar_sesion, width=12
        ).pack(side="right", padx=2)

    # --- carga de wave ---

    def _cargar_wave(self, indice: int, paso_inicial: int = 0) -> None:
        if not (0 <= indice < len(self.resultados)):
            return
        self.pause()
        self.indice_actual = indice
        wave, resultado = self.resultados[indice]
        self.estado = EstadoSimulacion.desde_wave(
            wave, resultado, self.escenario.warehouse
        )

        # Restaurar la posición dentro de la wave
        if 0 <= paso_inicial <= len(self.estado.camino) - 1:
            self.estado.indice_actual = paso_inicial

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

        # Productos: un punto por nivel del rack.
        # Los niveles vacíos se dibujan como círculos huecos.
        # Los ocupados: gris (inventario), rojo (pendiente), verde (recogido).
        recogidos = self.estado.productos_recogidos()
        productos_de_la_wave = self.estado.productos_totales

        # Productos por rack
        productos_por_rack: dict[str, dict[int, str]] = {}
        for pid, prod in self.escenario.warehouse.productos.items():
            productos_por_rack.setdefault(prod.rack_id, {})[prod.z] = pid

        for rack_id, rack in self.escenario.warehouse.racks.items():
            cx_rack, cy_rack = centro_celda_px(self.coords, rack.x, rack.y)

            niveles = rack.niveles
            radio = self.celda_px * 0.09
            separacion = self.celda_px * 0.22

            prods_en_rack = productos_por_rack.get(rack_id, {})

            for z in range(1, niveles + 1):
                if niveles == 1:
                    y = cy_rack
                else:
                    # z=1 en la base (abajo), z=niveles en la cima (arriba)
                    # En pantalla "abajo" = y grande, "arriba" = y chico
                    z_relativo = (z - 1) / (niveles - 1)  # 0 para z=1, 1 para z=niveles
                    y = cy_rack + separacion * (niveles - 1) / 2 * (1 - 2 * z_relativo)

                pid = prods_en_rack.get(z)
                if pid is None:
                    # Estante vacío
                    dibujar_circulo_hueco(self.canvas, cx_rack, y, radio=radio)
                    continue

                # Elegir color según el rol del producto
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


        # Etiqueta de próxima parada
        proxima = None
        for i, idx_parada in enumerate(self.estado.indices_de_paradas):
            if self.estado.indice_actual < idx_parada:
                proxima = self.estado.nodos_paradas[i]
                break

        if proxima is not None:
            pids_parada = self.estado.nodo_a_productos.get(proxima, [])
            if pids_parada:
                prod = self.escenario.warehouse.productos[pids_parada[0]]
                rack = self.escenario.warehouse.racks[prod.rack_id]
                x0, y0, x1, y1 = self.coords[(rack.x, rack.y)]

                # Alterna izquierda/derecha según bloque del rack:
                # - rack izquierdo del bloque (x % 3 == 1) → etiqueta a la izquierda
                # - rack derecho del bloque  (x % 3 == 2) → etiqueta a la derecha
                if rack.x % 3 == 1:
                    text_x = x0 - 4
                    anchor = "e"
                else:
                    text_x = x1 + 4
                    anchor = "w"

                text_y = (y0 + y1) / 2

                self.canvas.create_text(
                    text_x,
                    text_y,
                    text=f"→ {rack.x},{rack.y}",
                    font=("monospace", 7, "bold"),
                    fill="#1565c0",
                    anchor=anchor,
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
            rack = self.escenario.warehouse.racks[prod.rack_id]

            cantidad_pedida = sum(
                item.cantidad
                for pedido in wave.pedidos
                for item in pedido.items
                if item.producto_id == pid
                )

            lbl = tk.Label(
                self.frame_productos,
                text=(
                    f"● {pid} "
                    f"({rack.x},{rack.y},{prod.z}) "
                    f"stock={prod.stock} pide={cantidad_pedida}"
                ),
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

    def guardar_sesion(self) -> None:
        from tkinter import filedialog

        from warehouse.io.exportador import exportar_escenario
        from warehouse.warehouse.escenario import Sesion

        # Determinar la ruta por defecto
        directorio_sesiones = Path(__file__).parent.parent / "data" / "sesiones"
        directorio_sesiones.mkdir(parents=True, exist_ok=True)

        path = filedialog.asksaveasfilename(
            initialdir=directorio_sesiones,
            initialfile=f"{self.escenario.nombre}.json",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("Todos", "*.*")],
            title="Guardar sesión como...",
        )
        if not path:
            return  # el usuario canceló

        # Sincronizar el estado actual antes de guardar
        self.escenario.sesion = Sesion(
            wave_actual=self.indice_actual,
            indice_actual=self.estado.indice_actual if self.estado else 0,
            estrategia_recorrido=self.estrategia,
        )

        try:
            exportar_escenario(self.escenario, path)
            self.lbl_estado.config(text=f"Guardado en {Path(path).name}")
        except Exception as e:
            self.lbl_estado.config(text=f"Error al guardar: {e}")

    def cargar_sesion(self) -> None:
        """Pide al usuario una sesión guardada y reinicia la app con --cargar."""
        import subprocess
        import sys
        from tkinter import filedialog, messagebox

        from warehouse.io.cargador_json import cargar_escenario

        self.pause()

        directorio_sesiones = Path(__file__).parent.parent / "data" / "sesiones"
        directorio_sesiones.mkdir(parents=True, exist_ok=True)

        path = filedialog.askopenfilename(
            initialdir=directorio_sesiones,
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("Todos", "*.*")],
            title="Cargar sesión",
        )
        if not path:
            return  # el usuario canceló

        # Validar ANTES de cerrar la app: si el archivo está roto, no perdemos nada.
        try:
            cargar_escenario(path)
        except Exception as e:
            messagebox.showerror("Error al cargar", f"No se pudo cargar:\n{e}")
            return

        # Lanzar el nuevo proceso con --cargar

        # Ruta absoluta de este script, para relanzarlo
        ruta_script = Path(__file__).resolve()

        # Redirigir stdout/stderr a un log y despegar el proceso del terminal
        log_path = Path(__file__).parent.parent / "data" / "sesiones" / "ultimo_lanzamiento.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        with open(log_path, "w") as log:
            subprocess.Popen(
                    [   # uso Popen ya que no bloquea: lanza el proceso y sigue
                     sys.executable,
                     str(ruta_script),
                     "--cargar",
                     path,
                     ],
                    start_new_session=True,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    )


        # Cerrar esta ventana (termina el mainloop)
        self.root.destroy()

if __name__ == "__main__":
    main()
