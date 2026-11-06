# src/ui/configuracion.py
# Vista de configuración manual del almacén (solo tkinter / ttk).
#
# El usuario solo carga datos "de negocio". Los ids, las ubicaciones y el tamaño del
# almacén los genera src/io/scenario_builder.py al guardar.
import tkinter as tk
from tkinter import messagebox, ttk

from src.io.scenario_builder import (
    AUTOMATICO, ETIQUETAS_PUERTA, LARGO_RACK_MAX, LARGO_RACK_MIN, MAX_PUERTAS,
    capacidad_pickers, dimensiones_estimadas, id_pedido, id_picker, id_producto, id_zona, ids_puertas,
    ids_racks, reasignar_ids_en_texto, resolver_items, formatear_items,
)
from src.ui.estilos import (
    AZUL_MARINO, AZUL_MARINO_OSCURO, BEIGE_CLARO, BLANCO, CREMA_GRISACEO,
    CREMA_PRINCIPAL, GRIS_CLARO, GRIS_CREMA, GRIS_VERDOSO, NEGRO_AZULADO,
    FUENTE, FUENTE_TITULO,
    crear_boton, crear_entry, crear_spinbox, px,
)

TIPOS_PUERTA = list(ETIQUETAS_PUERTA.values())

FILAS_TABLA = 5     # filas visibles de cada tabla; si hay más, se desplaza con la rueda o la barra
MAX_PICKERS = 1000  # tope de pickers en total


def _tarjeta(master, titulo):
    """Devuelve (marco_externo, cuerpo). El marco externo se ubica con grid; el cuerpo recibe el contenido."""
    marco = tk.Frame(master, bg=CREMA_GRISACEO, highlightthickness=1,
                     highlightbackground=GRIS_VERDOSO)
    tk.Label(marco, text=titulo, font=FUENTE_TITULO, bg=CREMA_GRISACEO,
             fg=AZUL_MARINO, anchor="w").pack(fill=tk.X, padx=10, pady=(8, 2))
    cuerpo = tk.Frame(marco, bg=CREMA_GRISACEO)
    cuerpo.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
    return marco, cuerpo


class SeccionParametros(tk.Frame):
    """Grupo de campos numéricos simples (racks, configuración de waves)."""

    def __init__(self, master, campos, on_cambio=None):
        """campos: lista de (clave, etiqueta, valor_por_defecto, minimo, maximo)"""
        super().__init__(master, bg=CREMA_GRISACEO)
        self.campos = campos
        self.on_cambio = on_cambio
        self.vars = {}
        for fila, (clave, etiqueta, defecto, minimo, maximo) in enumerate(campos):
            tk.Label(self, text=etiqueta, font=FUENTE, bg=CREMA_GRISACEO,
                     fg=NEGRO_AZULADO, anchor="w").grid(row=fila, column=0, sticky="w", pady=4)
            var = tk.StringVar(value=str(defecto))
            var.trace_add("write", self._cambio)
            self.vars[clave] = var
            crear_spinbox(self, var, desde=minimo, hasta=maximo, ancho=8).grid(
                row=fila, column=1, sticky="e", padx=(15, 0), pady=4)
        self.columnconfigure(0, weight=1)

    def _cambio(self, *_args):
        if self.on_cambio:
            self.on_cambio()

    def obtener(self):
        resultado = {}
        for clave, _etiqueta, defecto, _min, _max in self.campos:
            try:
                resultado[clave] = int(self.vars[clave].get())
            except ValueError:
                resultado[clave] = defecto
        return resultado

    def cargar(self, datos):
        for clave, _etiqueta, defecto, _min, _max in self.campos:
            self.vars[clave].set(str(datos.get(clave, defecto)))

    def restablecer(self):
        for clave, _etiqueta, defecto, _min, _max in self.campos:
            self.vars[clave].set(str(defecto))


class SeccionTabla(tk.Frame):
    """Tabla + formulario para agregar elementos. Muestra 5 filas y se desplaza para ver el resto.

    campos: lista de dicts con
        clave, etiqueta, tipo ('str' | 'int' | 'float'), widget ('entry' | 'spin' | 'combo'),
        valores (lista o función que devuelve lista; solo combo), defecto, ancho, min/max (spin),
        solo_alta (True: al agregar crea esa cantidad de copias; al editar se ignora)
    columnas: lista de (encabezado, ancho_px, funcion(item) -> texto)
    generar_ids: función(lista_de_items) -> lista de ids. Los ids no se escriben: se asignan
        solos según el orden y se vuelven a calcular al agregar, editar o eliminar.
    validar: función(item, indice_edicion) -> mensaje de error o None. Puede corregir el item.
    on_renumerar: función({id_viejo: id_nuevo | None}) cuando cambian los ids de otros elementos
        (None = el elemento se eliminó). Sirve para actualizar las tablas que lo referencian.
    """

    def __init__(self, master, campos, columnas, texto_agregar, por_fila=4, on_cambio=None,
                 ayuda=None, generar_ids=None, validar=None, on_renumerar=None):
        super().__init__(master, bg=CREMA_GRISACEO)
        self.campos = campos
        self.columnas = columnas
        self.texto_agregar = texto_agregar
        self.on_cambio = on_cambio
        self.generar_ids = generar_ids
        self.validar = validar
        self.on_renumerar = on_renumerar
        self.items = []
        self.indice_edicion = None
        self.vars = {}

        # --- Tabla ---
        ids = [f"c{i}" for i in range(len(columnas))]
        marco_tabla = tk.Frame(self, bg=CREMA_GRISACEO)
        marco_tabla.pack(fill=tk.X)
        self.tabla = ttk.Treeview(marco_tabla, columns=ids, show="headings",
                                  height=FILAS_TABLA, selectmode="browse")
        barra_scroll = ttk.Scrollbar(marco_tabla, orient=tk.VERTICAL, command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=barra_scroll.set)
        for cid, (encabezado, ancho, _fn) in zip(ids, columnas):
            self.tabla.heading(cid, text=encabezado, anchor="w")
            self.tabla.column(cid, width=px(ancho), anchor="w", stretch=True)
        self.tabla.tag_configure("par", background=BLANCO)
        self.tabla.tag_configure("impar", background=GRIS_CLARO)
        barra_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tabla.pack(side=tk.LEFT, fill=tk.X, expand=True)

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
                widget = crear_spinbox(self.form, var, desde=campo.get("min", 0),
                                       hasta=campo.get("max", 9999), ancho=ancho)
            else:
                widget = crear_entry(self.form, var, ancho=ancho)
            widget.grid(row=fila + 1, column=col, sticky="ew", padx=2, pady=(0, 6))
            self.widgets[campo["clave"]] = widget
        for col in range(min(por_fila, len(campos))):
            self.form.columnconfigure(col, weight=1, uniform="campos")

        ultima_fila = ((len(campos) - 1) // por_fila) * 2 + 2
        ancho_columnas = min(por_fila, len(campos))
        self.btn_agregar = crear_boton(self.form, texto_agregar, self._agregar)
        self.btn_agregar.grid(row=ultima_fila, column=0, columnspan=ancho_columnas,
                              sticky="e", padx=2, pady=(2, 0))
        self.lbl_ayuda = None
        if ayuda is not None:
            self.lbl_ayuda = tk.Label(self.form, text=ayuda, font=("Arial", 8), bg=CREMA_GRISACEO,
                                      fg=NEGRO_AZULADO, anchor="w", justify=tk.LEFT,
                                      wraplength=px(420))
            self.lbl_ayuda.grid(row=ultima_fila, column=0, columnspan=ancho_columnas,
                                sticky="w", padx=2)

    def set_ayuda(self, texto):
        if self.lbl_ayuda is not None:
            self.lbl_ayuda.config(text=texto)

    # --- Combos dependientes ---
    def _valores_combo(self, campo):
        valores = campo.get("valores", [])
        return list(valores() if callable(valores) else valores)

    def _refrescar_combo(self, campo):
        self.widgets[campo["clave"]].configure(values=self._valores_combo(campo))

    # --- Ids automáticos ---
    def _foto(self):
        """Guarda (item, id) antes de un cambio para poder seguir a cada elemento después."""
        return [(item, item.get("id")) for item in self.items]

    def _asignar_ids(self):
        if self.generar_ids is None:
            return
        for item, nuevo in zip(self.items, self.generar_ids(self.items)):
            item["id"] = nuevo

    def _renumerar(self, previo):
        """Reasigna los ids y avisa qué ids cambiaron (o desaparecieron)."""
        self._asignar_ids()
        if self.generar_ids is None or self.on_renumerar is None:
            return
        vivos = {id(item) for item in self.items}
        mapa = {}
        for item, viejo in previo:
            if viejo is None:
                continue
            mapa[viejo] = item["id"] if id(item) in vivos else None
        cambios = {viejo: nuevo for viejo, nuevo in mapa.items() if viejo != nuevo}
        if cambios:
            self.on_renumerar(cambios)

    def reasignar(self, items):
        """Reemplaza los elementos (lo usan otras secciones al actualizar referencias)."""
        self.items = items
        self._asignar_ids()
        if self.indice_edicion is not None:
            self._limpiar_formulario()
        self.refrescar()

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
        if self.validar is not None:
            mensaje = self.validar(item, self.indice_edicion)
            if mensaje:
                messagebox.showwarning("Dato inválido", mensaje, parent=self)
                return
        copias = 1
        for campo in self.campos:
            if campo.get("solo_alta"):
                cantidad = item.pop(campo["clave"], 1)
                if self.indice_edicion is None:
                    copias = max(1, cantidad)
        previo = self._foto()
        if self.indice_edicion is None:
            for _ in range(copias):
                self.items.append(dict(item))
            ver = len(self.items) - 1
        else:
            ver = self.indice_edicion
            destino = self.items[ver]  # se edita en el lugar: conserva su identidad
            destino.clear()
            destino.update(item)
        self._limpiar_formulario()
        self._renumerar(previo)
        self.refrescar(ver)
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
            if campo.get("solo_alta"):
                self.vars[campo["clave"]].set("1")
            else:
                self.vars[campo["clave"]].set(str(item[campo["clave"]]))
        self.indice_edicion = indice
        self.btn_agregar.config(text="Guardar cambios")

    def _eliminar(self):
        seleccion = self.tabla.selection()
        if not seleccion:
            messagebox.showinfo("Eliminar", "Seleccione una fila de la tabla para eliminarla.", parent=self)
            return
        indice = int(seleccion[0])
        previo = self._foto()
        del self.items[indice]
        self._limpiar_formulario()
        self._renumerar(previo)
        self.refrescar()
        if self.on_cambio:
            self.on_cambio()

    # --- Tabla ---
    def refrescar(self, ver=None):
        """Vuelve a llenar la tabla con TODOS los elementos (se desplaza con rueda o barra).

        ver: índice del elemento que debe quedar a la vista.
        """
        hijos = self.tabla.get_children()
        if hijos:
            self.tabla.delete(*hijos)
        for posicion, item in enumerate(self.items):
            valores = [funcion(item) for (_enc, _ancho, funcion) in self.columnas]
            self.tabla.insert("", tk.END, iid=str(posicion), values=valores,
                              tags=("par" if posicion % 2 == 0 else "impar",))
        if ver is not None and 0 <= ver < len(self.items):
            self.tabla.see(str(ver))
        total = len(self.items)
        if total == 0:
            texto = "Sin elementos"
        elif total <= FILAS_TABLA:
            texto = f"Total: {total}"
        else:
            texto = f"Total: {total} (desplácese para ver todos)"
        self.lbl_info.config(text=texto)

    # --- API pública ---
    def obtener_items(self):
        return [dict(item) for item in self.items]

    def cargar_items(self, lista):
        self.items = [dict(item) for item in lista]
        self._limpiar_formulario()
        self._asignar_ids()
        self.refrescar()

    def vaciar(self):
        self.cargar_items([])

    def ids(self):
        return [item["id"] for item in self.items if "id" in item]


class VistaConfiguracion(tk.Frame):
    """Configuración manual del almacén. Al guardar, el controlador genera el escenario JSON."""

    RACKS_DEFECTO = [
        ("cantidad", "Cantidad de racks:", 6, 1, 500),
        ("largo", f"Largo de cada rack ({LARGO_RACK_MIN} a {LARGO_RACK_MAX}):", 6,
         LARGO_RACK_MIN, LARGO_RACK_MAX),
    ]
    WAVES_DEFECTO = [
        ("max_pedidos", "Máximo de pedidos por wave:", 3, 1, 9999),
        ("max_productos", "Máximo de productos por wave:", 15, 1, 9999),
        ("max_peso", "Peso máximo por wave (kg):", 1000, 1, 99999),
    ]

    def __init__(self, master, on_guardar, on_importar, on_volver, on_exportar=None):
        super().__init__(master, bg=CREMA_PRINCIPAL)

        # --- Encabezado ---
        cabecera = tk.Frame(self, bg=AZUL_MARINO_OSCURO, padx=20, pady=12)
        cabecera.pack(fill=tk.X)
        tk.Label(cabecera, text="⚙  Configuración del Almacén", font=("Arial", 18, "bold"),
                 bg=AZUL_MARINO_OSCURO, fg=BLANCO).pack(anchor="w")
        tk.Label(cabecera, text="Cargue los datos: los ids, las ubicaciones y el tamaño del "
                                "almacén se generan automáticamente",
                 font=FUENTE, bg=AZUL_MARINO_OSCURO, fg=GRIS_VERDOSO).pack(anchor="w")

        # --- Barra inferior (se empaqueta antes que el cuerpo para que siempre quede visible) ---
        barra = tk.Frame(self, bg=GRIS_CREMA, padx=12, pady=10)
        barra.pack(side=tk.BOTTOM, fill=tk.X)
        crear_boton(barra, "💾 Guardar y crear JSON", on_guardar).pack(side=tk.LEFT, padx=(0, 6))
        crear_boton(barra, "⭱ Importar JSON", on_importar, primario=False).pack(side=tk.LEFT, padx=6)
        if on_exportar is not None:
            crear_boton(barra, "⭳ Exportar configuración", on_exportar,
                        primario=False).pack(side=tk.LEFT, padx=6)
        crear_boton(barra, "⟲ Restablecer valores", self._confirmar_restablecer,
                    primario=False).pack(side=tk.LEFT, padx=6)
        crear_boton(barra, "← Volver al menú", on_volver, primario=False).pack(side=tk.RIGHT)

        # --- Cuerpo en pestañas ---
        # Sin Canvas ni scroll: cada pestaña entra completa en la ventana.
        self.pestanas = ttk.Notebook(self)
        self.pestanas.pack(fill=tk.BOTH, expand=True, padx=12, pady=(12, 6))
        self._construir_secciones()
        self.pestanas.bind("<<NotebookTabChanged>>", lambda _e: self._actualizar_ayuda_pedidos())
        self._actualizar_resumen()
        self._actualizar_ayuda_pedidos()

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
        pag_pp = self._nueva_pagina("Pickers y productos")
        pag_pedidos = self._nueva_pagina("Pedidos")

        # 1. Racks (todos del mismo tamaño) y tamaño automático del almacén
        marco, cuerpo = _tarjeta(pag_almacen, "Racks")
        self.sec_racks = SeccionParametros(cuerpo, self.RACKS_DEFECTO, on_cambio=self._actualizar_resumen)
        self.sec_racks.pack(fill=tk.X, pady=(6, 8))
        self.lbl_resumen = tk.Label(cuerpo, text="", font=("Arial", 9), bg=BEIGE_CLARO,
                                    fg=NEGRO_AZULADO, wraplength=px(380), justify=tk.LEFT,
                                    padx=10, pady=8)
        self.lbl_resumen.pack(fill=tk.X)
        self._colocar(marco, 0)

        # 2. Configuración de waves
        marco, cuerpo = _tarjeta(pag_almacen, "Configuración de Waves")
        self.sec_waves = SeccionParametros(cuerpo, self.WAVES_DEFECTO)
        self.sec_waves.pack(fill=tk.X, pady=(6, 8))
        tk.Label(cuerpo,
                 text="Estos valores limitan cuántos pedidos, productos y kilos pueden "
                      "agruparse en una wave de preparación.",
                 font=("Arial", 9), bg=BEIGE_CLARO, fg=NEGRO_AZULADO, wraplength=px(380),
                 justify=tk.LEFT, padx=10, pady=8).pack(fill=tk.X)
        self._colocar(marco, 1)

        # 3. Puertas
        marco, cuerpo = _tarjeta(pag_puertas, "Puertas")
        self.sec_puertas = SeccionTabla(
            cuerpo,
            campos=[{"clave": "tipo", "etiqueta": "Tipo de puerta", "widget": "combo",
                     "valores": TIPOS_PUERTA, "defecto": TIPOS_PUERTA[0], "ancho": 22}],
            columnas=[
                ("ID", 140, lambda i: i["id"]),
                ("Tipo", 150, lambda i: i["tipo"]),
            ],
            texto_agregar="+ Agregar puerta",
            generar_ids=lambda items: ids_puertas([i["tipo"] for i in items]),
            validar=self._validar_puerta,
            on_renumerar=self._puertas_renumeradas,
            on_cambio=self._actualizar_resumen,
            ayuda=f"Máximo {MAX_PUERTAS} puertas.",
        )
        self.sec_puertas.pack(fill=tk.X)
        self._colocar(marco, 0)

        # 4. Zonas de despacho (cada una queda frente a su puerta)
        marco, cuerpo = _tarjeta(pag_puertas, "Zonas de Despacho")
        self.sec_zonas = SeccionTabla(
            cuerpo,
            campos=[
                {"clave": "puerta", "etiqueta": "Puerta", "widget": "combo",
                 "valores": lambda: self.sec_puertas.ids(), "ancho": 18},
                {"clave": "peso_max", "etiqueta": "Peso máx. (kg)", "tipo": "float",
                 "defecto": 500.0, "ancho": 8},
            ],
            columnas=[
                ("ID", 80, lambda i: i["id"]),
                ("Puerta", 140, lambda i: i["puerta"]),
                ("Peso máx. (kg)", 100, lambda i: i["peso_max"]),
            ],
            texto_agregar="+ Agregar zona",
            por_fila=2,
            generar_ids=lambda items: [id_zona(n) for n in range(len(items))],
            validar=self._validar_zona,
            ayuda="Una zona por puerta. Debe haber una en una puerta de salida o mixta.",
        )
        self.sec_zonas.pack(fill=tk.X)
        self._colocar(marco, 1)

        # 5. Pickers
        marco, cuerpo = _tarjeta(pag_pp, "Pickers")
        self.sec_pickers = SeccionTabla(
            cuerpo,
            campos=[
                {"clave": "cantidad", "etiqueta": "Cantidad de pickers", "tipo": "int",
                 "widget": "spin", "defecto": 1, "ancho": 6, "min": 1, "max": MAX_PICKERS,
                 "solo_alta": True},
                {"clave": "capacidad", "etiqueta": "Capacidad de cada uno (kg)", "tipo": "float",
                 "defecto": 100.0, "ancho": 10},
            ],
            columnas=[
                ("ID", 90, lambda i: i["id"]),
                ("Capacidad (kg)", 130, lambda i: i["capacidad"]),
            ],
            texto_agregar="+ Agregar picker",
            generar_ids=lambda items: [id_picker(n) for n in range(len(items))],
            validar=self._validar_picker,
            por_fila=2,
            ayuda="Con «Cantidad» crea varios pickers iguales de una vez (hasta "
                  f"{MAX_PICKERS} en total).",
        )
        self.sec_pickers.pack(fill=tk.X)
        self._colocar(marco, 0)

        # 6. Productos (se ubican solos dentro del rack elegido)
        marco, cuerpo = _tarjeta(pag_pp, "Productos")
        self.sec_productos = SeccionTabla(
            cuerpo,
            campos=[
                {"clave": "nombre", "etiqueta": "Nombre", "ancho": 14},
                {"clave": "rack", "etiqueta": "Rack", "widget": "combo",
                 "valores": self._valores_rack, "defecto": AUTOMATICO, "ancho": 11},
                {"clave": "cantidad", "etiqueta": "Cant. disp.", "tipo": "int", "widget": "spin",
                 "defecto": 10, "ancho": 6, "min": 1},
                {"clave": "peso", "etiqueta": "Peso (kg)", "tipo": "float", "defecto": 1.0, "ancho": 7},
            ],
            columnas=[
                ("ID", 60, lambda i: i["id"]),
                ("Nombre", 130, lambda i: i["nombre"]),
                ("Rack", 80, lambda i: i["rack"]),
                ("Cant.", 50, lambda i: i["cantidad"]),
                ("Peso (kg)", 70, lambda i: i["peso"]),
            ],
            texto_agregar="+ Agregar producto",
            generar_ids=lambda items: [id_producto(n) for n in range(len(items))],
            validar=self._validar_producto,
            on_renumerar=self._productos_renumerados,
            on_cambio=self._actualizar_ayuda_pedidos,
            ayuda=f"Rack «{AUTOMATICO}»: reparte los productos entre los racks.",
        )
        self.sec_productos.pack(fill=tk.X)
        self._colocar(marco, 1)

        # 7. Pedidos
        marco, cuerpo = _tarjeta(pag_pedidos, "Pedidos")
        tk.Label(cuerpo,
                 text="Cómo escribir un pedido\n"
                      "• Cada producto: ID x cantidad      Ej: P001 x2\n"
                      "• Varios productos separados por comas:  P001 x2, P005 x1, P010 x3\n"
                      "• En lugar del ID puede usar el nombre exacto del producto.\n"
                      "• Si omite la cantidad se toma 1.  Prioridad: entero, mayor = más urgente.",
                 font=("Arial", 9), bg=BEIGE_CLARO, fg=NEGRO_AZULADO, justify=tk.LEFT,
                 anchor="w", padx=10, pady=8).pack(fill=tk.X, pady=(6, 8))
        self.sec_pedidos = SeccionTabla(
            cuerpo,
            campos=[
                {"clave": "prioridad", "etiqueta": "Prioridad", "tipo": "int", "widget": "spin",
                 "defecto": 1, "ancho": 5, "min": 1},
                {"clave": "productos", "etiqueta": "Productos (ID x cantidad, separados por comas)",
                 "ancho": 60},
            ],
            columnas=[
                ("ID", 70, lambda i: i["id"]),
                ("Prioridad", 70, lambda i: i["prioridad"]),
                ("Productos", 300, lambda i: i["productos"]),
            ],
            texto_agregar="+ Agregar pedido",
            por_fila=2,
            generar_ids=lambda items: [id_pedido(n) for n in range(len(items))],
            validar=self._validar_pedido,
            ayuda="",
        )
        self.sec_pedidos.pack(fill=tk.X)
        self._colocar(marco, 0, completo=True)

    # --- Datos auxiliares ---
    def _valores_rack(self):
        racks = self.sec_racks.obtener()
        return [AUTOMATICO] + ids_racks(racks["cantidad"], racks["largo"])

    def _actualizar_resumen(self):
        if not hasattr(self, "sec_puertas") or not hasattr(self, "lbl_resumen"):
            return
        racks = self.sec_racks.obtener()
        ancho, alto = dimensiones_estimadas(
            {"racks": racks, "puertas": self.sec_puertas.items})
        largo = min(max(racks["largo"], LARGO_RACK_MIN), LARGO_RACK_MAX)
        lugares = racks["cantidad"] * 2 * largo * 3
        self.lbl_resumen.config(
            text=f"Tamaño del almacén (automático): {ancho} x {alto} celdas.\n"
                 f"{racks['cantidad']} racks de 2 x {largo}, con lugar para {lugares} productos.")

    def _actualizar_ayuda_pedidos(self):
        if not hasattr(self, "sec_pedidos"):
            return
        productos = self.sec_productos.items
        if not productos:
            texto = "Primero agregue productos (pestaña «Pickers y productos»)."
        else:
            texto = (f"Hay {len(productos)} productos ({productos[0]['id']} a {productos[-1]['id']}). "
                     "Formato: ID x cantidad, separados por comas.")
        self.sec_pedidos.set_ayuda(texto)

    # --- Validaciones al agregar ---
    def _validar_puerta(self, _item, indice):
        if indice is None and len(self.sec_puertas.items) >= MAX_PUERTAS:
            return f"Se admiten como máximo {MAX_PUERTAS} puertas."
        return None

    def _validar_zona(self, item, indice):
        puerta = item["puerta"]
        if puerta not in self.sec_puertas.ids():
            return "Elija una puerta existente (agréguela primero en «Puertas»)."
        if item["peso_max"] <= 0:
            return "El peso máximo debe ser mayor que 0."
        for posicion, zona in enumerate(self.sec_zonas.items):
            if posicion != indice and zona["puerta"] == puerta:
                return f"La puerta {puerta} ya tiene una zona de despacho."
        return None

    def _validar_picker(self, item, indice):
        if item["capacidad"] <= 0:
            return "La capacidad debe ser mayor que 0."
        if indice is None:
            nuevos = item.get("cantidad", 1)
            if len(self.sec_pickers.items) + nuevos > MAX_PICKERS:
                return f"Se admiten como máximo {MAX_PICKERS} pickers en total."
            cabe = capacidad_pickers(
                {"racks": self.sec_racks.obtener(), "puertas": self.sec_puertas.items})
            if len(self.sec_pickers.items) + nuevos > cabe:
                return (f"Con este almacén solo caben {cabe} pickers (uno por celda de pasillo). "
                        "Aumente los racks o reduzca los pickers.")
        return None

    def _validar_producto(self, item, _indice):
        if item["cantidad"] < 1:
            return "La cantidad disponible debe ser de 1 o más."
        if item["peso"] <= 0:
            return "El peso debe ser mayor que 0."
        if item["rack"] not in self._valores_rack():
            return "Elija un rack de la lista o «Automático»."
        return None

    def _validar_pedido(self, item, _indice):
        if item["prioridad"] < 1:
            return "La prioridad debe ser de 1 o más."
        try:
            items = resolver_items(item["productos"], self.sec_productos.items)
        except ValueError as error:
            return str(error)
        unidades = sum(cantidad for _id, cantidad in items)
        limites = self.sec_waves.obtener()
        if unidades > limites["max_productos"]:
            return (f"El pedido tiene {unidades} unidades y una wave admite como máximo "
                    f"{limites['max_productos']}. Reduzca el pedido o aumente el máximo de "
                    "productos por wave.")
        peso_de = {p["id"]: p["peso"] for p in self.sec_productos.items}
        peso = sum(peso_de[i] * c for i, c in items)
        if peso > limites["max_peso"]:
            return (f"El pedido pesa {peso:g} kg y una wave admite como máximo "
                    f"{limites['max_peso']} kg. Reduzca el pedido o aumente el peso máximo por wave.")
        item["productos"] = formatear_items(items)  # queda escrito con ids
        return None

    # --- Referencias entre tablas cuando cambian los ids ---
    def _puertas_renumeradas(self, mapa):
        nuevas, quitadas = [], 0
        for zona in self.sec_zonas.items:
            destino = mapa.get(zona["puerta"], zona["puerta"])
            if destino is None:
                quitadas += 1
                continue
            zona["puerta"] = destino
            nuevas.append(zona)
        self.sec_zonas.reasignar(nuevas)
        if quitadas:
            messagebox.showinfo("Zonas eliminadas",
                                f"Se eliminaron {quitadas} zona(s) de despacho porque su puerta "
                                "ya no existe.", parent=self)

    def _productos_renumerados(self, mapa):
        nuevos, pedidos_quitados, items_quitados = [], 0, 0
        for pedido in self.sec_pedidos.items:
            texto, quitados = reasignar_ids_en_texto(pedido["productos"], mapa)
            items_quitados += quitados
            if not texto:
                pedidos_quitados += 1
                continue
            pedido["productos"] = texto
            nuevos.append(pedido)
        self.sec_pedidos.reasignar(nuevos)
        if items_quitados:
            messagebox.showinfo(
                "Pedidos actualizados",
                f"Se quitaron {items_quitados} producto(s) eliminados de los pedidos"
                + (f" y {pedidos_quitados} pedido(s) quedaron vacíos, por lo que se eliminaron."
                   if pedidos_quitados else "."), parent=self)

    # --- API pública ---
    def obtener_configuracion(self):
        """Devuelve todo lo ingresado como diccionario (lo consume scenario_builder)."""
        return {
            "racks": self.sec_racks.obtener(),
            "puertas": self.sec_puertas.obtener_items(),
            "zonas_despacho": self.sec_zonas.obtener_items(),
            "pickers": self.sec_pickers.obtener_items(),
            "productos": self.sec_productos.obtener_items(),
            "pedidos": self.sec_pedidos.obtener_items(),
            "waves": self.sec_waves.obtener(),
        }

    def cargar_configuracion(self, datos):
        """Carga en la vista un diccionario con la misma estructura que obtener_configuracion()."""
        self.sec_racks.cargar(datos.get("racks", {}))
        self.sec_waves.cargar(datos.get("waves", {}))
        self.sec_puertas.cargar_items(datos.get("puertas", []))
        self.sec_zonas.cargar_items(datos.get("zonas_despacho", []))
        self.sec_pickers.cargar_items(datos.get("pickers", []))
        self.sec_productos.cargar_items(datos.get("productos", []))
        self.sec_pedidos.cargar_items(datos.get("pedidos", []))
        self._actualizar_resumen()
        self._actualizar_ayuda_pedidos()

    def restablecer(self):
        self.sec_racks.restablecer()
        self.sec_waves.restablecer()
        for seccion in (self.sec_puertas, self.sec_zonas, self.sec_pickers,
                        self.sec_productos, self.sec_pedidos):
            seccion.vaciar()
        self._actualizar_resumen()
        self._actualizar_ayuda_pedidos()

    def _confirmar_restablecer(self):
        if messagebox.askyesno("Restablecer valores",
                               "Se borrarán todos los datos ingresados. ¿Desea continuar?",
                               parent=self):
            self.restablecer()