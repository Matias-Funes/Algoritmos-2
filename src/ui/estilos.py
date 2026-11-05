# src/ui/estilos.py
# Paleta de colores y helpers de estilo compartidos por todas las vistas (solo tkinter / ttk).
import sys
import tkinter as tk
from tkinter import ttk
 
# --- Paleta principal ---
AZUL_MARINO_OSCURO = "#192A3D"   # fondo del menú lateral / cabeceras oscuras
AZUL_MARINO = "#243D56"          # botones y elementos activos
AZUL_GRISACEO = "#3A556D"        # variaciones, hover, elementos azules
AZUL_CLARO_GRISACEO = "#A3B3BC"  # encabezado de tablas
GRIS_CLARO = "#D4D9DC"           # filas alternas
GRIS_VERDOSO = "#D0D3C7"         # fondos secundarios / bordes
VERDE_GRISACEO = "#C2C8BA"       # filas verdes
VERDE_OSCURO = "#67746A"         # estados "En stock" / correcto
BEIGE_DORADO = "#AE9B7A"         # estados "Bajo stock" / avisos
BEIGE_CLARO = "#EADFCB"          # filas beige / cajas de información
CREMA_PRINCIPAL = "#F5F0E6"      # fondo general de la aplicación
CREMA_GRISACEO = "#F0EBDE"       # paneles y áreas interiores
GRIS_CREMA = "#E5E2D8"           # barras y paneles secundarios
BLANCO = "#F6F9F8"               # iconos / textos muy claros
NEGRO_AZULADO = "#121C25"        # texto principal, sombras
 
FUENTE = ("Arial", 10)
FUENTE_NEGRITA = ("Arial", 10, "bold")
FUENTE_TITULO = ("Arial", 11, "bold")
 
# --- Nitidez en pantallas con escala > 100% (Windows) ---
ESCALA = 1.0  # se calcula en aplicar_estilos_ttk(); 1.0 = 96 DPI
 
 
def activar_dpi():
    """Hace que Windows no estire (y desenfoque) la ventana en pantallas con escala 125%, 150%, etc.
 
    Debe llamarse ANTES de crear el tk.Tk(). En otros sistemas no hace nada.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            ctypes.windll.user32.SetProcessDPIAware()
    except (AttributeError, OSError, ImportError):
        pass
 
 
def px(valor):
    """Escala un tamaño en píxeles según el DPI de la pantalla (los textos en puntos ya escalan solos)."""
    return int(round(valor * ESCALA))
 
 
def crear_boton(parent, texto, comando, primario=True, **opciones):
    """Botón cuadrado (relief plano, sin bordes redondeados) con colores de la paleta."""
    if primario:
        bg, fg, activo = AZUL_MARINO, BLANCO, AZUL_GRISACEO
    else:
        bg, fg, activo = GRIS_CREMA, NEGRO_AZULADO, GRIS_VERDOSO
    config = dict(
        text=texto,
        command=comando,
        bg=bg,
        fg=fg,
        activebackground=activo,
        activeforeground=BLANCO if primario else NEGRO_AZULADO,
        relief=tk.FLAT,
        bd=0,
        padx=12,
        pady=6,
        font=FUENTE,
        cursor="hand2",
        highlightthickness=0,
    )
    config.update(opciones)
    return tk.Button(parent, **config)
 
 
def crear_entry(parent, variable, ancho=8):
    return tk.Entry(
        parent,
        textvariable=variable,
        width=ancho,
        font=FUENTE,
        bg=BLANCO,
        fg=NEGRO_AZULADO,
        relief=tk.FLAT,
        highlightthickness=1,
        highlightbackground=GRIS_VERDOSO,
        highlightcolor=AZUL_GRISACEO,
        insertbackground=NEGRO_AZULADO,
    )
 
 
def crear_spinbox(parent, variable, desde=0, hasta=9999, ancho=6):
    return tk.Spinbox(
        parent,
        from_=desde,
        to=hasta,
        textvariable=variable,
        width=ancho,
        font=FUENTE,
        bg=BLANCO,
        fg=NEGRO_AZULADO,
        relief=tk.FLAT,
        highlightthickness=1,
        highlightbackground=GRIS_VERDOSO,
        highlightcolor=AZUL_GRISACEO,
        buttonbackground=GRIS_CREMA,
    )
 
 
def ajustar_ventana(root, ancho, alto, minimo=None):
    """Da tamaño y centra la ventana sin pasarse de la pantalla (deja lugar para la barra de tareas y el título)."""
    root.update_idletasks()
    pantalla_ancho = root.winfo_screenwidth()
    pantalla_alto = root.winfo_screenheight()
    ancho = min(px(ancho), int(pantalla_ancho * 0.95))
    alto = min(px(alto), int(pantalla_alto * 0.85))
    x = (pantalla_ancho - ancho) // 2
    y = max(0, (pantalla_alto - alto) // 2 - 20)
    root.geometry(f"{ancho}x{alto}+{x}+{y}")
    if minimo:
        root.minsize(min(px(minimo[0]), ancho), min(px(minimo[1]), alto))
 
 
def aplicar_estilos_ttk(root):
    """Configura Treeview, Notebook y Combobox (ttk) con la paleta. Llamar una vez tras crear el Tk."""
    global ESCALA
    ESCALA = max(1.0, root.winfo_fpixels("1i") / 96.0)
 
    estilo = ttk.Style(root)
    try:
        estilo.theme_use("clam")  # permite colorear widgets ttk
    except tk.TclError:
        pass
 
    estilo.configure(
        "Treeview",
        background=BLANCO,
        fieldbackground=BLANCO,
        foreground=NEGRO_AZULADO,
        rowheight=px(24),
        borderwidth=0,
        font=FUENTE,
    )
    estilo.map(
        "Treeview",
        background=[("selected", AZUL_GRISACEO)],
        foreground=[("selected", BLANCO)],
    )
    estilo.configure(
        "Treeview.Heading",
        background=AZUL_CLARO_GRISACEO,
        foreground=NEGRO_AZULADO,
        relief=tk.FLAT,
        font=FUENTE_NEGRITA,
    )
    estilo.map("Treeview.Heading", background=[("active", AZUL_CLARO_GRISACEO)])
 
    estilo.configure("TNotebook", background=CREMA_GRISACEO, borderwidth=0)
    estilo.configure(
        "TNotebook.Tab",
        background=GRIS_CREMA,
        foreground=NEGRO_AZULADO,
        padding=(14, 4),
        font=FUENTE,
    )
    estilo.map(
        "TNotebook.Tab",
        background=[("selected", AZUL_MARINO)],
        foreground=[("selected", BLANCO)],
    )
 
    estilo.configure(
        "TCombobox",
        fieldbackground=BLANCO,
        background=GRIS_CREMA,
        foreground=NEGRO_AZULADO,
        arrowcolor=AZUL_MARINO,
    )
    estilo.map("TCombobox", fieldbackground=[("readonly", BLANCO)])
 
    estilo.configure(
        "Vertical.TScrollbar",
        background=GRIS_VERDOSO,
        troughcolor=GRIS_CREMA,
        arrowcolor=AZUL_MARINO,
    )