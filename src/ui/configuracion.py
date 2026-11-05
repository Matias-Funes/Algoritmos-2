
# src/ui/configuracion.py

# src/ui/configuracion.py
# Vista de configuración del almacén (solo tkinter / ttk).
import tkinter as tk
from tkinter import messagebox, ttk

from src.ui.estilos import (
    AZUL_MARINO, AZUL_MARINO_OSCURO, BEIGE_CLARO, BLANCO, CREMA_GRISACEO,
    CREMA_PRINCIPAL, GRIS_CLARO, GRIS_CREMA, GRIS_VERDOSO, NEGRO_AZULADO,
    FUENTE, FUENTE_TITULO,
    crear_boton, crear_entry, crear_spinbox, px,
)

SENTIDOS = ["N", "S", "E", "O", "AMBOS"]
FLECHAS = {"N": "↑ N", "S": "↓ S", "E": "→ E", "O": "← O", "AMBOS": "↔ Ambos"}
TIPOS_PUERTA = ["Salida (OUTBOUND)", "Entrada (INBOUND)"]
ESTADOS_PEDIDO = ["Pendiente", "En proceso", "Completado"]

MAX_VISIBLES = 3  # cada tabla muestra solo los últimos 3 elementos agregados


def _tarjeta(master, titulo):
    """Devuelve (marco_externo, cuerpo). El marco externo se ubica con grid; el cuerpo recibe el contenido."""
    marco = tk.Frame(master, bg=CREMA_GRISACEO, highlightthickness=1,
                     highlightbackground=GRIS_VERDOSO)
    tk.Label(marco, text=titulo, font=FUENTE_TITULO, bg=CREMA_GRISACEO,
             fg=AZUL_MARINO, anchor="w").pack(fill=tk.X, padx=10, pady=(8, 2))
    cuerpo = tk.Frame(marco, bg=CREMA_GRISACEO)
    cuerpo.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
    return marco, cuerpo


def _ubicacion(item):
    return f"({item['x']}, {item['y']})"


def _dimensiones(item):
    return f"{item['ancho']} x {item['alto']}"


class SeccionParametros(tk.Frame):
    """Grupo de campos numéricos simples (dimensiones del almacén, configuración de waves)."""

    def __init__(self, master, campos):
        """campos: lista de (clave, etiqueta, valor_por_defecto)"""
        super().__init__(master, bg=CREMA_GRISACEO)
        self.campos = campos
        self.vars = {}
        for fila, (clave, etiqueta, defecto) in enumerate(campos):
            tk.Label(self, text=etiqueta, font=FUENTE, bg=CREMA_GRISACEO,
                     fg=NEGRO_AZULADO, anchor="w").grid(row=fila, column=0, sticky="w", pady=4)
            var = tk.StringVar(value=str(defecto))
            self.vars[clave] = var
            crear_spinbox(self, var, desde=1, hasta=9999, ancho=8).grid(
                row=fila, column=1, sticky="e", padx=(15, 0), pady=4)
        self.columnconfigure(0, weight=1)

    def obtener(self):
        resultado = {}
        for clave, _etiqueta, defecto in self.campos:
            try:
                resultado[clave] = int(self.vars[clave].get())
            except ValueError:
                resultado[clave] = defecto
        return resultado

    def cargar(self, datos):
        for clave, _etiqueta, defecto in self.campos:
            self.vars[clave].set(str(datos.get(clave, defecto)))

    def restablecer(self):
        for clave, _etiqueta, defecto in self.campos:
            self.vars[clave].set(str(defecto))


class SeccionTabla(tk.Frame):
    """Tabla + formulario para agregar elementos. Muestra solo los últimos 3 ingresados.

    campos: lista de dicts con
    clave, etiqueta, tipo ('str' | 'int' | 'float'), widget ('entry' | 'spin' | 'combo'),
    valores (lista o función que devuelve lista; solo combo), defecto, ancho
    columnas: lista de (encabezado, ancho_px, funcion(item) -> texto)
    """

    def __init__(self, master, campos, columnas, texto_agregar, por_fila=4, on_cambio=None, ayuda=None):
        super().__init__(master, bg=CREMA_GRISACEO)
        self.campos = campos
        self.columnas = columnas
        self.texto_agregar = texto_agregar
        self.on_cambio = on_cambio
        self.items = []
        self.indice_edicion = None
        self.vars = {}

        # --- Tabla ---
        ids = [f"c{i}" for i in range(len(columnas))]
        self.tabla = ttk.Treeview(self, columns=ids, show="headings",
                                  height=MAX_VISIBLES, selectmode="browse")
        for cid, (encabezado, ancho, _fn) in zip(ids, columnas):
            self.tabla.heading(cid, text=encabezado, anchor="w")
            self.tabla.column(cid, width=px(ancho), anchor="w", stretch=True)
        self.tabla.tag_configure("par", background=BLANCO)
        self.tabla.tag_configure("impar", background=GRIS_CLARO)
        self.tabla.pack(fill=tk.X)

        # --- Barra de acciones (info + editar / eliminar) ---
        barra = tk.Frame(self, bg=CREMA_GRISACEO)
        barra.pack(fill=tk.X, pady=(4, 6))
        self.lbl_info = tk.Label(barra, text="Sin elementos", font=("Arial", 9),
                                 bg=CREMA_GRISACEO, fg=NEGRO_AZULADO)
        self.lbl_info.pack(side=tk.LEFT)
        crear_boton(barra, "🗑 Eliminar", self._eliminar, primario=False,
                    padx=8, pady=2).pack(side=tk.RIGHT, padx=(4, 0))
        crear_boton(barra, "✎ Editar", self._editar, primario=False,
                    padx=8, pady=2).pack(side=tk.RIGHT)

        # --- Formulario ---
        self.form = tk.Frame(self, bg=CREMA_GRISACEO)
        self.form.pack(fill=tk.X)
        self.widgets = {}
        for i, campo in enumerate(campos):
            fila = (i // por_fila) * 2
            col = i % por_fila
            tk.Label(self.form, text=campo["etiqueta"], font=("Arial", 9),
                     bg=CREMA_GRISACEO, fg=NEGRO_AZULADO, anchor="w").grid(
                row=fila, column=col, sticky="w", padx=2)
            var = tk.StringVar(value=str(campo.get("defecto", "")))
            self.vars[campo["clave"]] = var
            ancho = campo.get("ancho", 8)
            tipo_widget = campo.get("widget", "entry")
            if tipo_widget == "combo":
                widget = ttk.Combobox(self.form, textvariable=var, state="readonly",
                                      width=ancho, font=FUENTE,
                                      values=self._valores_combo(campo),
                                      postcommand=lambda c=campo: self._refrescar_combo(c))
            elif tipo_widget == "spin":
                widget = crear_spinbox(self.form, var, ancho=ancho)
            else:
                widget = crear_entry(self.form, var, ancho=ancho)
            widget.grid(row=fila + 1, column=col, sticky="ew", padx=2, pady=(0, 6))
            self.widgets[campo["clave"]] = widget
        for col in range(min(por_fila, len(campos))):
            self.form.columnconfigure(col, weight=1, uniform="campos")

        ultima_fila = ((len(campos) - 1) // por_fila) * 2 + 2
        self.btn_agregar = crear_boton(self.form, texto_agregar, self._agregar)
        self.btn_agregar.grid(row=ultima_fila, column=0, columnspan=min(por_fila, len(campos)),
                              sticky="e", padx=2, pady=(2, 0))
        if ayuda:
            tk.Label(self.form, text=ayuda, font=("Arial", 8), bg=CREMA_GRISACEO, fg=NEGRO_AZULADO,
                     anchor="w", justify=tk.LEFT).grid(row=ultima_fila, column=0,
                                                       columnspan=min(por_fila, len(campos)),
                                                       sticky="w", padx=2)

    # --- Combos dependientes ---
    def _valores_combo(self, campo):
        valores = campo.get("valores", [])
        return list(valores() if callable(valores) else valores)

    def _refrescar_combo(self, campo):
        self.widgets[campo["clave"]].configure(values=self._valores_combo(campo))

    # --- Formulario ---
    def _leer_formulario(self):
        item = {}
        for campo in self.campos:
            texto = self.vars[campo["clave"]].get().strip()
            if texto == "":
                messagebox.showwarning("Campo vacío", f"Complete el campo «{campo['etiqueta']}».",
                                       parent=self)
                return None
            tipo = campo.get("tipo", "str")
            try:
                if tipo == "int":
                    item[campo["clave"]] = int(texto)
                elif tipo == "float":
                    item[campo["clave"]] = float(texto.replace(",", "."))
                else:
                    item[campo["clave"]] = texto
            except ValueError:
                detalle = "un número entero" if tipo == "int" else "un número"
                messagebox.showwarning("Valor inválido",
                                       f"«{campo['etiqueta']}» debe ser {detalle}.", parent=self)
                return None
        return item

    def _limpiar_formulario(self):
        for campo in self.campos:
            self.vars[campo["clave"]].set(str(campo.get("defecto", "")))
        self.indice_edicion = None
        self.btn_agregar.config(text=self.texto_agregar)

    def _agregar(self):
        item = self._leer_formulario()
        if item is None:
            return
        if self.indice_edicion is None:
            self.items.append(item)
        else:
            self.items[self.indice_edicion] = item
        self._limpiar_formulario()
        self.refrescar()
        if self.on_cambio:
            self.on_cambio()

    def _editar(self):
        seleccion = self.tabla.selection()
        if not seleccion:
            messagebox.showinfo("Editar", "Seleccione una fila de la tabla para editarla.", parent=self)
            return
        indice = int(seleccion[0])
        item = self.items[indice]
        for campo in self.campos:
            self.vars[campo["clave"]].set(str(item[campo["clave"]]))
        self.indice_edicion = indice
        self.btn_agregar.config(text="Guardar cambios")

    def _eliminar(self):
        seleccion = self.tabla.selection()
        if not seleccion:
            messagebox.showinfo("Eliminar", "Seleccione una fila de la tabla para eliminarla.", parent=self)
            return
        indice = int(seleccion[0])
        del self.items[indice]
        self._limpiar_formulario()
        self.refrescar()
        if self.on_cambio:
            self.on_cambio()

    # --- Tabla ---
    def refrescar(self):
        for fila in self.tabla.get_children():
            self.tabla.delete(fila)
        visibles = self.items[-MAX_VISIBLES:]
        desplazamiento = len(self.items) - len(visibles)
        for pos, item in enumerate(visibles):
            valores = [funcion(item) for (_enc, _ancho, funcion) in self.columnas]
            self.tabla.insert("", tk.END, iid=str(desplazamiento + pos), values=valores,
                              tags=("par" if pos % 2 == 0 else "impar",))
        total = len(self.items)
        if total == 0:
            self.lbl_info.config(text="Sin elementos")
        elif total <= MAX_VISIBLES:
            self.lbl_info.config(text=f"Total: {total}")
        else:
            self.lbl_info.config(text=f"Mostrando los últimos {MAX_VISIBLES} de {total}")

    # --- API pública ---
    def obtener_items(self):
        return [dict(item) for item in self.items]

    def cargar_items(self, lista):
        self.items = [dict(item) for item in lista]
        self._limpiar_formulario()
        self.refrescar()

    def vaciar(self):
        self.cargar_items([])

    def ids(self):
        return [item["id"] for item in self.items if "id" in item]


class VistaConfiguracion(tk.Frame):
    """Configuración manual del almacén. Solo arma la interfaz; no valida ni construye el warehouse."""

    DIMENSIONES_DEFECTO = [("ancho", "Ancho (X):", 18), ("largo", "Largo (Y):", 16)]
    WAVES_DEFECTO = [("max_pedidos", "Máximo de pedidos por wave:", 3),
                     ("max_productos", "Máximo de productos por wave:", 15)]

    def __init__(self, master, on_guardar, on_exportar, on_importar, on_volver):
        super().__init__(master, bg=CREMA_PRINCIPAL)

        # --- Encabezado ---
        cabecera = tk.Frame(self, bg=AZUL_MARINO_OSCURO, padx=20, pady=12)
        cabecera.pack(fill=tk.X)
        tk.Label(cabecera, text="⚙  Configuración del Almacén", font=("Arial", 18, "bold"),
                 bg=AZUL_MARINO_OSCURO, fg=BLANCO).pack(anchor="w")
        tk.Label(cabecera, text="Configure la estructura, inventario y parámetros de preparación",
                 font=FUENTE, bg=AZUL_MARINO_OSCURO, fg=GRIS_VERDOSO).pack(anchor="w")

        # --- Barra inferior (se empaqueta antes que el cuerpo para que siempre quede visible) ---
        barra = tk.Frame(self, bg=GRIS_CREMA, padx=12, pady=10)
        barra.pack(side=tk.BOTTOM, fill=tk.X)
        crear_boton(barra, "💾 Guardar configuración", on_guardar).pack(side=tk.LEFT, padx=(0, 6))
        crear_boton(barra, "⭳ Exportar JSON", on_exportar, primario=False).pack(side=tk.LEFT, padx=6)
        crear_boton(barra, "⭱ Importar JSON", on_importar, primario=False).pack(side=tk.LEFT, padx=6)
        crear_boton(barra, "⟲ Restablecer valores", self._confirmar_restablecer,
                    primario=False).pack(side=tk.LEFT, padx=6)
        crear_boton(barra, "← Volver al menú", on_volver, primario=False).pack(side=tk.RIGHT)

        # --- Cuerpo en pestañas ---
        # Sin Canvas ni scroll: cada pestaña entra completa en la ventana, así no hay que repintar
        # widgets desplazándose (la causa de que los elementos se vieran estirados).
        self.pestanas = ttk.Notebook(self)
        self.pestanas.pack(fill=tk.BOTH, expand=True, padx=12, pady=(12, 6))
        self._construir_secciones()

    # --- Pestañas ---
    def _nueva_pagina(self, titulo):
        pagina = tk.Frame(self.pestanas, bg=CREMA_PRINCIPAL, padx=8, pady=8)
        pagina.columnconfigure(0, weight=1, uniform="col")
        pagina.columnconfigure(1, weight=1, uniform="col")
        self.pestanas.add(pagina, text=titulo)
        return pagina

    def _colocar(self, tarjeta, columna, completo=False):
        # sticky="new": se pega arriba y se estira solo a lo ancho, nunca a lo alto.
        if completo:
            tarjeta.grid(row=0, column=0, columnspan=2, sticky="new", pady=6)
        else:
            tarjeta.grid(row=0, column=columna, sticky="new",
                         padx=(0, 6) if columna == 0 else (6, 0), pady=6)

    def _construir_secciones(self):
        pag_almacen = self._nueva_pagina("Almacén")
        pag_puertas = self._nueva_pagina("Puertas y zonas")
        pag_racks = self._nueva_pagina("Racks y pasillos")
        pag_pp = self._nueva_pagina("Pickers y productos")
        pag_pedidos = self._nueva_pagina("Pedidos")

        # 1. Dimensiones del almacén
        marco, cuerpo = _tarjeta(pag_almacen, "Dimensiones del Almacén")
        self.sec_dimensiones = SeccionParametros(cuerpo, self.DIMENSIONES_DEFECTO)
        self.sec_dimensiones.pack(fill=tk.X, pady=(6, 0))
        self._colocar(marco, 0)

        # 2. Puertas
        marco, cuerpo = _tarjeta(pag_puertas, "Puertas")
        self.sec_puertas = SeccionTabla(
            cuerpo,
            campos=[
                {"clave": "id", "etiqueta": "ID", "ancho": 12},
                {"clave": "tipo", "etiqueta": "Tipo", "widget": "combo", "valores": TIPOS_PUERTA,
                 "defecto": TIPOS_PUERTA[0], "ancho": 16},
                {"clave": "x", "etiqueta": "X", "tipo": "int", "widget": "spin", "defecto": 0, "ancho": 5},
                {"clave": "y", "etiqueta": "Y", "tipo": "int", "widget": "spin", "defecto": 0, "ancho": 5},
            ],
            columnas=[
                ("ID", 110, lambda i: i["id"]),
                ("Tipo", 130, lambda i: i["tipo"]),
                ("Ubicación (X, Y)", 110, _ubicacion),
            ],
            texto_agregar="+ Agregar puerta",
        )
        self.sec_puertas.pack(fill=tk.X)
        self._colocar(marco, 0)

        # 3. Zonas de despacho
        marco, cuerpo = _tarjeta(pag_puertas, "Zonas de Despacho")
        self.sec_zonas = SeccionTabla(
            cuerpo,
            campos=[
                {"clave": "id", "etiqueta": "ID", "ancho": 10},
                {"clave": "puerta", "etiqueta": "Puerta", "widget": "combo",
                 "valores": lambda: self.sec_puertas.ids(), "ancho": 12},
                {"clave": "x", "etiqueta": "X", "tipo": "int", "widget": "spin", "defecto": 0, "ancho": 5},
                {"clave": "y", "etiqueta": "Y", "tipo": "int", "widget": "spin", "defecto": 0, "ancho": 5},
                {"clave": "ancho", "etiqueta": "Ancho", "tipo": "int", "widget": "spin", "defecto": 1, "ancho": 5},
                {"clave": "alto", "etiqueta": "Alto", "tipo": "int", "widget": "spin", "defecto": 1, "ancho": 5},
                {"clave": "peso_max", "etiqueta": "Peso máx. (kg)", "tipo": "float", "defecto": 500.0, "ancho": 8},
            ],
            columnas=[
                ("ID", 70, lambda i: i["id"]),
                ("Puerta", 100, lambda i: i["puerta"]),
                ("Ubicación", 70, _ubicacion),
                ("Ancho x Alto", 80, _dimensiones),
                ("Peso máx. (kg)", 90, lambda i: i["peso_max"]),
            ],
            texto_agregar="+ Agregar zona",
        )
        self.sec_zonas.pack(fill=tk.X)
        self._colocar(marco, 1)

        # 4. Racks
        marco, cuerpo = _tarjeta(pag_racks, "Racks")
        self.sec_racks = SeccionTabla(
            cuerpo,
            campos=[
                {"clave": "id", "etiqueta": "ID", "ancho": 10},
                {"clave": "x", "etiqueta": "X", "tipo": "int", "widget": "spin", "defecto": 0, "ancho": 5},
                {"clave": "y", "etiqueta": "Y", "tipo": "int", "widget": "spin", "defecto": 0, "ancho": 5},
                {"clave": "ancho", "etiqueta": "Ancho", "tipo": "int", "widget": "spin", "defecto": 1, "ancho": 5},
                {"clave": "alto", "etiqueta": "Alto", "tipo": "int", "widget": "spin", "defecto": 1, "ancho": 5},
            ],
            columnas=[
                ("ID", 90, lambda i: i["id"]),
                ("Ubicación (X, Y)", 120, _ubicacion),
                ("Dimensiones (Ancho x Alto)", 150, _dimensiones),
            ],
            texto_agregar="+ Agregar rack",
            por_fila=5,
        )
        self.sec_racks.pack(fill=tk.X)
        self._colocar(marco, 0)

        # 4b. Pasillos
        marco, cuerpo = _tarjeta(pag_racks, "Pasillos")
        self.sec_pasillos = SeccionTabla(
            cuerpo,
            campos=[
                {"clave": "id", "etiqueta": "ID", "ancho": 10},
                {"clave": "x", "etiqueta": "X", "tipo": "int", "widget": "spin", "defecto": 0, "ancho": 5},
                {"clave": "y", "etiqueta": "Y", "tipo": "int", "widget": "spin", "defecto": 0, "ancho": 5},
                {"clave": "ancho", "etiqueta": "Ancho", "tipo": "int", "widget": "spin", "defecto": 1, "ancho": 5},
                {"clave": "alto", "etiqueta": "Alto", "tipo": "int", "widget": "spin", "defecto": 1, "ancho": 5},
                {"clave": "sentido", "etiqueta": "Sentido", "widget": "combo", "valores": SENTIDOS,
                 "defecto": "AMBOS", "ancho": 8},
            ],
            columnas=[
                ("ID", 80, lambda i: i["id"]),
                ("Ubicación (X, Y)", 110, _ubicacion),
                ("Ancho x Alto", 90, _dimensiones),
                ("Sentido", 70, lambda i: FLECHAS.get(i["sentido"], i["sentido"])),
            ],
            texto_agregar="+ Agregar pasillo",
            por_fila=3,
        )
        self.sec_pasillos.pack(fill=tk.X)
        self._colocar(marco, 1)

        # 5. Pickers
        marco, cuerpo = _tarjeta(pag_pp, "Pickers")
        self.sec_pickers = SeccionTabla(
            cuerpo,
            campos=[
                {"clave": "id", "etiqueta": "ID", "ancho": 10},
                {"clave": "x", "etiqueta": "X inicial", "tipo": "int", "widget": "spin", "defecto": 0, "ancho": 5},
                {"clave": "y", "etiqueta": "Y inicial", "tipo": "int", "widget": "spin", "defecto": 0, "ancho": 5},
                {"clave": "capacidad", "etiqueta": "Capacidad (kg)", "tipo": "float", "defecto": 100.0, "ancho": 8},
            ],
            columnas=[
                ("ID", 90, lambda i: i["id"]),
                ("Posición inicial (X, Y)", 150, _ubicacion),
                ("Capacidad (kg)", 110, lambda i: i["capacidad"]),
            ],
            texto_agregar="+ Agregar picker",
        )
        self.sec_pickers.pack(fill=tk.X)
        self._colocar(marco, 0)

        # 6. Productos
        marco, cuerpo = _tarjeta(pag_pp, "Productos")
        self.sec_productos = SeccionTabla(
            cuerpo,
            campos=[
                {"clave": "id", "etiqueta": "ID", "ancho": 8},
                {"clave": "nombre", "etiqueta": "Nombre", "ancho": 14},
                {"clave": "rack", "etiqueta": "Rack", "widget": "combo",
                 "valores": lambda: self.sec_racks.ids(), "ancho": 8},
                {"clave": "x", "etiqueta": "X", "tipo": "int", "widget": "spin", "defecto": 0, "ancho": 5},
                {"clave": "y", "etiqueta": "Y", "tipo": "int", "widget": "spin", "defecto": 0, "ancho": 5},
                {"clave": "z", "etiqueta": "Z", "tipo": "int", "widget": "spin", "defecto": 1, "ancho": 5},
                {"clave": "cantidad", "etiqueta": "Cant. disp.", "tipo": "int", "widget": "spin",
                 "defecto": 1, "ancho": 6},
                {"clave": "peso", "etiqueta": "Peso (kg)", "tipo": "float", "defecto": 1.0, "ancho": 7},
            ],
            columnas=[
                ("ID", 50, lambda i: i["id"]),
                ("Nombre", 110, lambda i: i["nombre"]),
                ("Rack", 50, lambda i: i["rack"]),
                ("Ubicación (X, Y, Z)", 110, lambda i: f"({i['x']}, {i['y']}, {i['z']})"),
                ("Cant.", 50, lambda i: i["cantidad"]),
                ("Peso (kg)", 70, lambda i: i["peso"]),
            ],
            texto_agregar="+ Agregar producto",
        )
        self.sec_productos.pack(fill=tk.X)
        self._colocar(marco, 1)

        # 7. Pedidos
        marco, cuerpo = _tarjeta(pag_pedidos, "Pedidos")
        self.sec_pedidos = SeccionTabla(
            cuerpo,
            campos=[
                {"clave": "id", "etiqueta": "ID", "ancho": 10},
                {"clave": "prioridad", "etiqueta": "Prioridad", "tipo": "int", "widget": "spin",
                 "defecto": 1, "ancho": 5},
                {"clave": "estado", "etiqueta": "Estado", "widget": "combo", "valores": ESTADOS_PEDIDO,
                 "defecto": ESTADOS_PEDIDO[0], "ancho": 12},
                {"clave": "productos", "etiqueta": "Productos", "ancho": 24},
            ],
            columnas=[
                ("ID", 70, lambda i: i["id"]),
                ("Prioridad", 70, lambda i: i["prioridad"]),
                ("Estado", 90, lambda i: i["estado"]),
                ("Productos", 190, lambda i: i["productos"]),
            ],
            texto_agregar="+ Agregar pedido",
            ayuda="Productos: ej. P001 x2, P002 x1",
        )
        self.sec_pedidos.pack(fill=tk.X)
        self._colocar(marco, 0, completo=True)

        # 8. Configuración de waves
        marco, cuerpo = _tarjeta(pag_almacen, "Configuración de Waves")
        self.sec_waves = SeccionParametros(cuerpo, self.WAVES_DEFECTO)
        self.sec_waves.pack(fill=tk.X, pady=(6, 8))
        tk.Label(cuerpo,
                 text="Estos valores limitan cuántos pedidos y productos pueden agruparse "
                      "en una wave de preparación.",
                 font=("Arial", 9), bg=BEIGE_CLARO, fg=NEGRO_AZULADO, wraplength=px(380),
                 justify=tk.LEFT, padx=10, pady=8).pack(fill=tk.X)
        self._colocar(marco, 1)

    # --- API pública ---
    def obtener_configuracion(self):
        """Devuelve todo lo ingresado como diccionario (listo para serializar a JSON)."""
        return {
            "almacen": self.sec_dimensiones.obtener(),
            "puertas": self.sec_puertas.obtener_items(),
            "zonas_despacho": self.sec_zonas.obtener_items(),
            "racks": self.sec_racks.obtener_items(),
            "pasillos": self.sec_pasillos.obtener_items(),
            "pickers": self.sec_pickers.obtener_items(),
            "productos": self.sec_productos.obtener_items(),
            "pedidos": self.sec_pedidos.obtener_items(),
            "waves": self.sec_waves.obtener(),
        }

    def cargar_configuracion(self, datos):
        """Carga en la vista un diccionario con la misma estructura que obtener_configuracion()."""
        self.sec_dimensiones.cargar(datos.get("almacen", {}))
        self.sec_puertas.cargar_items(datos.get("puertas", []))
        self.sec_zonas.cargar_items(datos.get("zonas_despacho", []))
        self.sec_racks.cargar_items(datos.get("racks", []))
        self.sec_pasillos.cargar_items(datos.get("pasillos", []))
        self.sec_pickers.cargar_items(datos.get("pickers", []))
        self.sec_productos.cargar_items(datos.get("productos", []))
        self.sec_pedidos.cargar_items(datos.get("pedidos", []))
        self.sec_waves.cargar(datos.get("waves", {}))

    def restablecer(self):
        self.sec_dimensiones.restablecer()
        self.sec_waves.restablecer()
        for seccion in (self.sec_puertas, self.sec_zonas, self.sec_racks, self.sec_pasillos,
                        self.sec_pickers, self.sec_productos, self.sec_pedidos):
            seccion.vaciar()

    def _confirmar_restablecer(self):
        if messagebox.askyesno("Restablecer valores",
                               "Se borrarán todos los datos ingresados. ¿Desea continuar?",
                               parent=self):
            self.restablecer()