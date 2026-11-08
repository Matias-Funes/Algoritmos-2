

# src/ui/estilos.py
# Paleta de colores y helpers de estilo compartidos por todas las vistas.
# Compatible con Tkinter y ttk.

import sys
import tkinter as tk
from tkinter import ttk


# ==========================================================
# PALETA DE COLORES
# ==========================================================

# Azul: estructura, navegación y encabezados
AZUL_MARINO_OSCURO = "#193B59"    # Encabezados y fondos oscuros
AZUL_MARINO = "#24577A"           # Botones y elementos activos
AZUL_GRISACEO = "#34769A"         # Hover y selección
AZUL_CLARO_GRISACEO = "#DCE7EF"   # Encabezados de tablas

# Gris azulado: fondos y superficies
GRIS_CLARO = "#E9EFF4"            # Fondo general
GRIS_VERDOSO = "#B8C9D8"          # Bordes y separadores
VERDE_GRISACEO = "#D9EEE5"        # Fondos verdes suaves

# Verde: acciones positivas y estados correctos
VERDE_OSCURO = "#147D5A"          # Guardar, confirmar y correcto

# Amarillo: advertencias
BEIGE_DORADO = "#D9A441"          # Bajo stock y advertencias
BEIGE_CLARO = "#FFF3D6"           # Fondos de advertencia

# Fondos generales
CREMA_PRINCIPAL = "#E9EFF4"       # Fondo principal de la aplicación
CREMA_GRISACEO = "#FFFFFF"        # Paneles y áreas interiores
GRIS_CREMA = "#DCE7EF"            # Barras y paneles secundarios

# Textos
BLANCO = "#FFFFFF"                # Textos sobre fondos oscuros
NEGRO_AZULADO = "#193B59"         # Texto principal

# Estados de error
ROJO = "#B94747"                  # Errores y eliminación
ROJO_CLARO = "#F8E3E3"            # Fondo de errores

# Bordes
BORDE = "#B8C9D8"


# ==========================================================
# FUENTES
# ==========================================================

FUENTE = ("Segoe UI", 10)
FUENTE_NEGRITA = ("Segoe UI", 10, "bold")
FUENTE_TITULO = ("Segoe UI", 11, "bold")


# ==========================================================
# CONFIGURACIÓN DPI
# ==========================================================

ESCALA = 1.0


def activar_dpi():
    """
    Hace que Windows no estire ni desenfoque la ventana
    en pantallas con escala 125%, 150%, etc.

    Debe llamarse ANTES de crear tk.Tk().
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
    """
    Escala un tamaño en píxeles según el DPI de la pantalla.
    """

    return int(round(valor * ESCALA))


# ==========================================================
# BOTONES
# ==========================================================

def crear_boton(parent, texto, comando, primario=True, **opciones):
    """
    Crea botones con los colores de la paleta.

    primario=True:
        Botón azul principal.

    primario=False:
        Botón secundario gris azulado.
    """

    if primario:
        bg = AZUL_MARINO
        fg = BLANCO
        activo = AZUL_GRISACEO

    else:
        bg = GRIS_CREMA
        fg = NEGRO_AZULADO
        activo = GRIS_VERDOSO

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

    boton = tk.Button(parent, **config)
    color_normal = boton.cget("bg")
    color_hover = boton.cget("activebackground")
    boton._hover_normal_background = color_normal
    boton.bind(
        "<Enter>",
        lambda _event: boton.config(bg=color_hover)
        if boton["state"] != tk.DISABLED
        else None,
    )
    boton.bind(
        "<Leave>",
        lambda _event: boton.config(
            bg=boton._hover_normal_background
        )
        if boton["state"] != tk.DISABLED
        else None,
    )
    return boton


# ==========================================================
# CAMPOS DE ENTRADA
# ==========================================================

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
        highlightbackground=BORDE,
        highlightcolor=AZUL_MARINO,

        insertbackground=NEGRO_AZULADO,
    )


# ==========================================================
# SPINBOX
# ==========================================================

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
        highlightbackground=BORDE,
        highlightcolor=AZUL_MARINO,

        buttonbackground=GRIS_CREMA,

        insertbackground=NEGRO_AZULADO,
    )


# ==========================================================
# CONFIGURACIÓN DE VENTANAS
# ==========================================================

def ajustar_ventana(root, ancho, alto, minimo=None):
    """
    Da tamaño y centra la ventana sin exceder
    las dimensiones de la pantalla.
    """

    root.update_idletasks()

    pantalla_ancho = root.winfo_screenwidth()
    pantalla_alto = root.winfo_screenheight()

    ancho = min(px(ancho), int(pantalla_ancho * 0.95))
    alto = min(px(alto), int(pantalla_alto * 0.85))

    x = (pantalla_ancho - ancho) // 2
    y = max(0, (pantalla_alto - alto) // 2 - 20)

    root.geometry(f"{ancho}x{alto}+{x}+{y}")

    if minimo:
        root.minsize(
            min(px(minimo[0]), ancho),
            min(px(minimo[1]), alto)
        )


# ==========================================================
# ESTILOS TTK
# ==========================================================

def aplicar_estilos_ttk(root):
    """
    Configura Treeview, Notebook, Combobox y Scrollbar.

    Llamar una sola vez después de crear tk.Tk().
    """

    global ESCALA

    ESCALA = max(1.0, root.winfo_fpixels("1i") / 96.0)

    estilo = ttk.Style(root)

    try:
        estilo.theme_use("clam")

    except tk.TclError:
        pass

    # ------------------------------------------------------
    # TABLAS: TREEVIEW
    # ------------------------------------------------------

    estilo.configure(
        "Treeview",

        background=BLANCO,
        fieldbackground=BLANCO,
        foreground=NEGRO_AZULADO,

        rowheight=px(26),

        borderwidth=0,
        font=FUENTE,
    )

    estilo.map(
        "Treeview",

        background=[
            ("selected", AZUL_MARINO)
        ],

        foreground=[
            ("selected", BLANCO)
        ],
    )

    # Encabezados de tablas

    estilo.configure(
        "Treeview.Heading",

        background=AZUL_CLARO_GRISACEO,
        foreground=NEGRO_AZULADO,

        relief=tk.FLAT,

        font=FUENTE_NEGRITA,

        padding=(6, 6),
    )

    estilo.map(
        "Treeview.Heading",

        background=[
            ("active", AZUL_GRISACEO)
        ],

        foreground=[
            ("active", BLANCO)
        ],
    )

    # ------------------------------------------------------
    # PESTAÑAS: NOTEBOOK
    # ------------------------------------------------------

    estilo.configure(
        "TNotebook",

        background=CREMA_PRINCIPAL,

        borderwidth=0,
    )

    estilo.configure(
        "TNotebook.Tab",

        background=GRIS_CREMA,
        foreground=NEGRO_AZULADO,

        padding=(14, 6),

        font=FUENTE,

        borderwidth=0,
    )

    estilo.map(
        "TNotebook.Tab",

        background=[
            ("selected", AZUL_MARINO),
            ("active", AZUL_GRISACEO),
        ],

        foreground=[
            ("selected", BLANCO),
            ("active", BLANCO),
        ],
    )

    # ------------------------------------------------------
    # COMBOBOX
    # ------------------------------------------------------

    estilo.configure(
        "TCombobox",

        fieldbackground=BLANCO,
        background=GRIS_CREMA,

        foreground=NEGRO_AZULADO,
        font=FUENTE,

        arrowcolor=AZUL_MARINO,

        padding=4,
    )

    estilo.map(
        "TCombobox",

        fieldbackground=[
            ("readonly", BLANCO)
        ],

        foreground=[
            ("readonly", NEGRO_AZULADO)
        ],

        selectbackground=[
            ("readonly", AZUL_MARINO)
        ],

        selectforeground=[
            ("readonly", BLANCO)
        ],
    )

    # ------------------------------------------------------
    # SCROLLBAR
    # ------------------------------------------------------

    estilo.configure(
        "Vertical.TScrollbar",

        background=AZUL_CLARO_GRISACEO,
        troughcolor=CREMA_PRINCIPAL,

        arrowcolor=AZUL_MARINO,

        borderwidth=0,
        relief=tk.FLAT,
        width=px(12),
    )

    estilo.map(
        "Vertical.TScrollbar",

        background=[
            ("active", AZUL_GRISACEO)
        ],
    )

    estilo.configure(
        "Horizontal.TScrollbar",

        background=AZUL_CLARO_GRISACEO,
        troughcolor=CREMA_PRINCIPAL,

        arrowcolor=AZUL_MARINO,

        borderwidth=0,
        relief=tk.FLAT,
        width=px(12),
    )

    estilo.map(
        "Horizontal.TScrollbar",

        background=[
            ("active", AZUL_GRISACEO)
        ],
    )
