# src/ui/menu.py
# Vista del menú de bienvenida (solo tkinter).
# El fondo es una vista aérea de un almacén dibujada con el Canvas (racks, pasillos con
# flechas, zonas de despacho, cajas y pickers), siempre con la paleta de la aplicación.
import random
import tkinter as tk
from tkinter import messagebox, ttk

from src.ui.estilos import (
    AZUL_CLARO_GRISACEO, AZUL_GRISACEO, AZUL_MARINO_OSCURO, BEIGE_CLARO,
    BEIGE_DORADO, BLANCO, CREMA_PRINCIPAL, GRIS_VERDOSO, NEGRO_AZULADO, VERDE_OSCURO,
    FUENTE, crear_boton, px,
)

MODOS_WAVES = ["Wave Global (Flota)", "Wave por Picker"]
# Estrategia de recorrido (el controlador la lee con combo_estrategia.get())
ESTRATEGIAS = ["Vecino más cercano (B)", "Orden de pedidos (A)"]
TEXTO_SIN_JSON = "Ningún archivo JSON cargado"
TEXTO_SIN_MANUAL = "Sin configuración manual"
TEXTO_MANUAL_OK = "✔ Configuración manual cargada"

# Tonos del fondo (variaciones de la paleta, más oscuros para que el menú resalte)
COLOR_GRILLA = "#1F3349"
COLOR_RACK_BORDE = "#4D6C86"
COLOR_RACK_DIVISION = "#2F4A61"
COLOR_FLECHA = "#2D465E"


def dibujar_fondo_almacen(c, ancho, alto, celda):
    """Dibuja el almacén visto desde arriba. `c` puede ser cualquier objeto con los métodos
    create_rectangle / create_line / create_oval / create_polygon (un Canvas de tkinter)."""
    azar = random.Random(11)  # mismo dibujo en cada redibujado
    etiqueta = "fondo"
    columnas, filas = ancho // celda + 1, alto // celda + 1

    c.create_rectangle(0, 0, ancho, alto, fill=AZUL_MARINO_OSCURO, outline="", tags=etiqueta)
    for x in range(0, ancho + 1, celda):
        c.create_line(x, 0, x, alto, fill=COLOR_GRILLA, tags=etiqueta)
    for y in range(0, alto + 1, celda):
        c.create_line(0, y, ancho, y, fill=COLOR_GRILLA, tags=etiqueta)

    # --- Bandas de racks (de arriba hacia abajo) ---
    alto_banda = max(3, min(10, (filas - 15) // 2))
    y_banda_a = 2
    y_banda_b = y_banda_a + alto_banda + 4
    bandas = [y_banda_a]
    if y_banda_b + alto_banda + 5 <= filas:
        bandas.append(y_banda_b)
    for indice_banda, y0 in enumerate(bandas):
        k = 0
        while 2 + 5 * k + 2 < columnas - 1:
            x0 = 2 + 5 * k
            c.create_rectangle(x0 * celda, y0 * celda, (x0 + 2) * celda, (y0 + alto_banda) * celda,
                               fill=AZUL_GRISACEO, outline=COLOR_RACK_BORDE, width=2, tags=etiqueta)
            for fila in range(1, alto_banda):  # divisiones entre celdas del rack
                c.create_line(x0 * celda, (y0 + fila) * celda, (x0 + 2) * celda, (y0 + fila) * celda,
                              fill=COLOR_RACK_DIVISION, tags=etiqueta)
            c.create_line((x0 + 1) * celda, y0 * celda, (x0 + 1) * celda, (y0 + alto_banda) * celda,
                          fill=COLOR_RACK_DIVISION, tags=etiqueta)
            for fila in range(alto_banda):  # cajas sobre los racks
                for columna in (0, 1):
                    if azar.random() < 0.3:
                        m = max(3, celda // 6)
                        cx, cy = (x0 + columna) * celda, (y0 + fila) * celda
                        c.create_rectangle(cx + m, cy + m, cx + celda - m, cy + celda - m,
                                           fill=BEIGE_CLARO, outline=BEIGE_DORADO, tags=etiqueta)
            # flechas de sentido en el pasillo de la derecha (alternan arriba / abajo)
            sentido = -1 if (k + indice_banda) % 2 == 0 else 1
            cx = (x0 + 3.5) * celda
            for fila in range(0, alto_banda, 3):
                cy = (y0 + fila + 1.2) * celda
                r = celda * 0.28
                c.create_polygon(cx, cy + sentido * r, cx - r, cy - sentido * r, cx + r, cy - sentido * r,
                                 fill=COLOR_FLECHA, outline="", tags=etiqueta)
            k += 1

    # --- Línea central de los corredores horizontales ---
    for y0 in bandas:
        y = (y0 + alto_banda + 2) * celda
        c.create_line(0, y, ancho, y, fill=COLOR_FLECHA, dash=(8, 8), tags=etiqueta)
    y_final = (bandas[-1] + alto_banda + 2) * celda

    # --- Zonas de despacho con su puerta, sobre el borde inferior ---
    y_zona = alto // celda - 3  # la puerta queda justo sobre el borde inferior, completa
    if y_zona * celda > y_final + celda:
        for fraccion in (0.28, 0.72):
            xc = int(columnas * fraccion)
            x0 = xc - 3
            c.create_rectangle(x0 * celda, y_zona * celda, (x0 + 7) * celda, (y_zona + 2) * celda,
                               fill=VERDE_OSCURO, outline="#7D8A80", tags=etiqueta)
            for i in range(1, 7):
                c.create_line((x0 + i) * celda, y_zona * celda, (x0 + i) * celda, (y_zona + 2) * celda,
                              fill="#7D8A80", tags=etiqueta)
            c.create_line(x0 * celda, (y_zona + 1) * celda, (x0 + 7) * celda, (y_zona + 1) * celda,
                          fill="#7D8A80", tags=etiqueta)
            c.create_rectangle(xc * celda, (y_zona + 2) * celda, (xc + 1) * celda, (y_zona + 3) * celda,
                               fill=BEIGE_DORADO, outline=BEIGE_CLARO, tags=etiqueta)
            for i in range(3):  # cajas esperando en la zona
                bx = (x0 + 1 + 2 * i) * celda + celda // 5
                by = (y_zona - 1) * celda + celda // 5
                c.create_rectangle(bx, by, bx + celda * 0.6, by + celda * 0.6,
                                   fill=BEIGE_CLARO, outline=BEIGE_DORADO, tags=etiqueta)

    # --- Pickers con su recorrido punteado ---
    recorridos = [
        [(3, 1), (3, bandas[0] + alto_banda + 2), (min(columnas - 3, 18), bandas[0] + alto_banda + 2)],
        [(columnas - 4, bandas[0] + alto_banda + 2), (columnas - 4, bandas[-1] + alto_banda + 2),
         (max(4, columnas - 14), bandas[-1] + alto_banda + 2)],
    ]
    for puntos in recorridos:
        pts = []
        for px_celda, py_celda in puntos:
            pts += [(px_celda + 0.5) * celda, (py_celda + 0.5) * celda]
        c.create_line(*pts, fill=AZUL_CLARO_GRISACEO, width=2, dash=(2, 5), tags=etiqueta)
        ex, ey = pts[0], pts[1]  # el picker se dibuja al inicio del recorrido
        r = celda * 0.38
        c.create_oval(ex - r, ey - r, ex + r, ey + r, fill=BEIGE_DORADO, outline=BEIGE_CLARO,
                      width=2, tags=etiqueta)


class VistaMenu(tk.Frame):
    """Menú principal: cargar JSON, configuración manual e iniciar simulación.

    La vista no decide nada: avisa al controlador mediante los callbacks recibidos.
    """

    def __init__(self, master, on_cargar_json, on_config_manual, on_iniciar,
                 on_cargar_partida=None):
        super().__init__(master, bg=AZUL_MARINO_OSCURO)

        # --- Fondo: almacén dibujado, se ajusta al tamaño de la ventana ---
        self.canvas = tk.Canvas(self, bg=AZUL_MARINO_OSCURO, highlightthickness=0)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self._tamano_dibujado = None
        self._pendiente = None

        # --- Tarjeta central ---
        self.tarjeta = tk.Frame(self.canvas, bg=CREMA_PRINCIPAL, highlightthickness=3,
                                highlightbackground=BEIGE_DORADO)
        self._ventana = self.canvas.create_window(0, 0, window=self.tarjeta, anchor="center")

        banner = tk.Frame(self.tarjeta, bg=AZUL_MARINO_OSCURO, padx=60, pady=22)
        banner.pack(fill=tk.X)
        tk.Label(banner, text="WAVE PICKING", font=("Arial", 30, "bold"),
                 fg=BLANCO, bg=AZUL_MARINO_OSCURO).pack()
        tk.Label(banner, text="Simulador de preparación de pedidos en almacén",
                 font=("Arial", 11), fg=GRIS_VERDOSO, bg=AZUL_MARINO_OSCURO).pack(pady=(4, 0))
        tk.Frame(self.tarjeta, bg=BEIGE_DORADO, height=4).pack(fill=tk.X)

        cuerpo = tk.Frame(self.tarjeta, bg=CREMA_PRINCIPAL, padx=40, pady=26)
        cuerpo.pack()

        # --- Fila: cargar JSON (con estado a la izquierda) ---
        self.lbl_json = tk.Label(cuerpo, text=TEXTO_SIN_JSON, font=FUENTE,
                                 bg=CREMA_PRINCIPAL, fg=NEGRO_AZULADO, anchor="e", width=34)
        self.lbl_json.grid(row=0, column=0, sticky="e", padx=(0, 15), pady=8)
        crear_boton(cuerpo, "Cargar JSON", on_cargar_json, width=24).grid(
            row=0, column=1, sticky="ew", pady=8)

        # --- Fila: configuración manual (con estado a la izquierda) ---
        self.lbl_manual = tk.Label(cuerpo, text=TEXTO_SIN_MANUAL, font=FUENTE,
                                   bg=CREMA_PRINCIPAL, fg=NEGRO_AZULADO, anchor="e", width=34)
        self.lbl_manual.grid(row=1, column=0, sticky="e", padx=(0, 15), pady=8)
        crear_boton(cuerpo, "Configuración manual", on_config_manual, width=24).grid(
            row=1, column=1, sticky="ew", pady=8)

        # --- Fila: modo de waves (lo lee el controlador con combo_modo_waves.get()) ---
        tk.Label(cuerpo, text="Modo de waves:", font=FUENTE, bg=CREMA_PRINCIPAL,
                 fg=NEGRO_AZULADO, anchor="e", width=34).grid(
            row=2, column=0, sticky="e", padx=(0, 15), pady=8)
        self.combo_modo_waves = ttk.Combobox(cuerpo, values=MODOS_WAVES, state="readonly",
                                             font=FUENTE, width=24)
        self.combo_modo_waves.set(MODOS_WAVES[0])
        self.combo_modo_waves.grid(row=2, column=1, sticky="ew", pady=8)

        # --- Fila: estrategia de recorrido de los pickers ---
        tk.Label(cuerpo, text="Estrategia de recorrido:", font=FUENTE, bg=CREMA_PRINCIPAL,
                 fg=NEGRO_AZULADO, anchor="e", width=34).grid(
            row=3, column=0, sticky="e", padx=(0, 15), pady=8)
        self.combo_estrategia = ttk.Combobox(cuerpo, values=ESTRATEGIAS, state="readonly",
                                             font=FUENTE, width=24)
        self.combo_estrategia.current(0)  # B (vecino más cercano) por defecto
        self.combo_estrategia.grid(row=3, column=1, sticky="ew", pady=8)

        # --- Cargar partida (opcional) ---
        fila_inicio = 5
        if on_cargar_partida is not None:
            crear_boton(cuerpo, "Cargar partida guardada", on_cargar_partida, primario=False,
                        width=24).grid(row=4, column=1, sticky="ew", pady=8)

        # --- Separador e inicio ---
        tk.Frame(cuerpo, bg=GRIS_VERDOSO, height=1).grid(row=fila_inicio, column=0, columnspan=2,
                                                         sticky="ew", pady=(18, 6))
        crear_boton(cuerpo, "▶  Iniciar simulación", on_iniciar, width=24,
                    font=("Arial", 11, "bold")).grid(row=fila_inicio + 1, column=1,
                                                     sticky="ew", pady=(10, 8))

        # --- Aviso en línea (se muestra solo cuando hace falta) ---
        self.lbl_aviso = tk.Label(cuerpo, text="", font=FUENTE, bg=CREMA_PRINCIPAL,
                                  fg=BEIGE_DORADO, wraplength=px(520), justify=tk.CENTER)
        self.lbl_aviso.grid(row=fila_inicio + 2, column=0, columnspan=2, pady=(6, 0))

        self.canvas.bind("<Configure>", self._al_cambiar_tamano)

    # --- Fondo ---
    def _al_cambiar_tamano(self, evento):
        # Se redibuja una vez que el usuario termina de cambiar el tamaño (evita parpadeos).
        if self._pendiente is not None:
            self.after_cancel(self._pendiente)
        ancho, alto = evento.width, evento.height
        self.canvas.coords(self._ventana, ancho / 2, alto / 2)
        self._pendiente = self.after(80, lambda: self._redibujar(ancho, alto))

    def _redibujar(self, ancho, alto):
        self._pendiente = None
        if (ancho, alto) == self._tamano_dibujado or ancho < 50 or alto < 50:
            return
        self._tamano_dibujado = (ancho, alto)
        self.canvas.delete("fondo")
        dibujar_fondo_almacen(self.canvas, ancho, alto, px(28))
        self.canvas.tag_lower("fondo")  # el fondo siempre queda detrás de la tarjeta

    # --- API para el controlador ---
    def set_archivo_json(self, nombre=None):
        """Muestra el nombre del archivo JSON subido (o el texto por defecto si es None)."""
        if nombre:
            self.lbl_json.config(text=f"✔ {nombre}", fg=VERDE_OSCURO)
        else:
            self.lbl_json.config(text=TEXTO_SIN_JSON, fg=NEGRO_AZULADO)

    def set_config_manual(self, cargada):
        if cargada:
            self.lbl_manual.config(text=TEXTO_MANUAL_OK, fg=VERDE_OSCURO)
        else:
            self.lbl_manual.config(text=TEXTO_SIN_MANUAL, fg=NEGRO_AZULADO)

    def mostrar_aviso(self, texto):
        """Aviso cuando no hay JSON ni configuración manual: texto en la vista + ventana emergente."""
        self.lbl_aviso.config(text=texto)
        messagebox.showwarning("Faltan datos", texto, parent=self)

    def limpiar_aviso(self):
        self.lbl_aviso.config(text="")
