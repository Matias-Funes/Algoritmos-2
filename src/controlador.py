# src/controlador.py
# Controlador: navega entre las vistas (menú, configuración, simulación).
# El armado del warehouse y de la simulación lo entrega main.py (constructor_simulacion).
import json
import sys
import tkinter as tk
import traceback
from pathlib import Path
from tkinter import filedialog, messagebox

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.io.scenario_builder import (
    ErrorConfiguracion,
    escenario_a_config,
    guardar_escenario,
)
from src.ui.configuracion import VistaConfiguracion
from src.ui.estilos import (
    CREMA_PRINCIPAL,
    activar_dpi,
    ajustar_ventana,
    aplicar_estilos_ttk,
    px,
)
from src.ui.menu import VistaMenu
from src.ui.visualization import Ventana

TIPOS_JSON = [("Archivos JSON", "*.json"), ("Todos los archivos", "*.*")]


class Controlador:
    def __init__(self, constructor_simulacion, tamano_celda=16, carpeta_json=None):
        """
        constructor_simulacion: función(ruta_json: Path) -> (warehouse, simulacion).
        tamano_celda: tamaño en píxeles de cada celda en la visualización.
        carpeta_json: carpeta donde se abre el explorador de archivos (opcional).
        """
        self.constructor_simulacion = constructor_simulacion
        self.tamano_celda = tamano_celda
        self.carpeta_json = carpeta_json

        activar_dpi()  # antes de crear Tk: evita el texto borroso en pantallas con escala > 100%
        self.root = tk.Tk()
        self.root.title("Wave Picking - Simulador")
        self.root.configure(bg=CREMA_PRINCIPAL)
        aplicar_estilos_ttk(self.root)

        self.vista_actual = None
        self.vista_config = None
        self.menu = None

        # Datos disponibles para la simulación
        self.ruta_json = None  # ruta del archivo JSON subido
        self.config_manual = None  # datos guardados desde la vista de configuración

        self.warehouse = None
        self.simulacion = None

    def iniciar(self):
        self.mostrar_menu()
        self.root.mainloop()

    # --- Navegación ---
    def _mostrar(self, vista, tamano=None, minimo=None):
        if self.vista_actual is not None:
            self.vista_actual.destroy()
        self.vista_actual = vista
        vista.pack(fill=tk.BOTH, expand=True)
        if tamano:
            ajustar_ventana(self.root, tamano[0], tamano[1], minimo)
        else:
            self.root.minsize(1, 1)  # saca el mínimo de la vista anterior
            self.root.geometry("")  # tamaño automático según el contenido

    def mostrar_menu(self):
        # Si venimos de la simulación, se deja pausada antes de destruir la vista.
        pausar = getattr(self.simulacion, "pausar", None)
        if pausar is not None:
            pausar()
        self.vista_config = None
        menu = VistaMenu(
            self.root,
            on_cargar_json=self.cargar_json,
            on_config_manual=self.abrir_configuracion,
            on_iniciar=self.iniciar_simulacion,
            on_cargar_partida=self.cargar_partida,
            on_cerrar=self.cerrar_aplicacion,
        )
        menu.set_archivo_json(Path(self.ruta_json).name if self.ruta_json else None)
        menu.set_config_manual(self.config_manual is not None)
        self.menu = menu
        self._mostrar(menu, (900, 600), (700, 500))

    def abrir_configuracion(self):
        vista = VistaConfiguracion(
            self.root,
            on_guardar=self.guardar_configuracion,
            on_exportar=self.exportar_json,
            on_importar=self.importar_json,
            on_volver=self.mostrar_menu,
        )
        if self.config_manual is not None:
            vista.cargar_configuracion(self.config_manual)
        self.vista_config = vista
        self._mostrar(vista, (1100, 620), (950, 500))

    def mostrar_simulacion(self):
        ancho_pantalla = self.root.winfo_screenwidth()
        alto_pantalla = self.root.winfo_screenheight()
        ancho_disponible = max(1, int(ancho_pantalla * 0.95) - 320)
        alto_disponible = max(1, int(alto_pantalla * 0.85) - 60)
        tamano_celda = min(
            px(self.tamano_celda),
            ancho_disponible // max(1, self.warehouse.ancho_x),
            alto_disponible // max(1, self.warehouse.largo_y),
        )
        ventana = Ventana(
            self.warehouse,
            tamano_celda=max(1, tamano_celda),
            master=self.root,
            on_volver=self.mostrar_menu,
            on_cerrar=self.cerrar_aplicacion,
        )
        # Si la simulación necesita la ventana para programar sus pasos (after), se la vincula.
        vincular = getattr(self.simulacion, "vincular_interfaz", None)
        if vincular is not None:
            vincular(ventana.root, ventana.actualizar_desde_simulacion)
        ventana.set_simulacion(self.simulacion)
        self._mostrar(ventana)  # tamaño automático según el warehouse
        ventana.actualizar_desde_simulacion()

    def cerrar_aplicacion(self):
        """Detiene callbacks de simulación y cierra la ventana principal."""
        pausar = getattr(self.simulacion, "pausar", None)
        if pausar is not None:
            pausar()
        self.root.destroy()

    # --- Menú ---
    def cargar_json(self):
        """Abre el explorador de archivos para elegir un JSON."""
        opciones = {"title": "Seleccionar archivo JSON", "filetypes": TIPOS_JSON}
        if self.carpeta_json and Path(self.carpeta_json).is_dir():
            opciones["initialdir"] = str(self.carpeta_json)
        ruta = filedialog.askopenfilename(**opciones)
        if not ruta:
            return
        try:
            with open(ruta, encoding="utf-8") as archivo:
                json.load(archivo)  # solo se comprueba que sea un JSON válido
        except (OSError, ValueError) as error:
            messagebox.showerror(
                "Error al cargar", f"No se pudo leer el archivo:\n{error}"
            )
            return
        self.ruta_json = ruta
        self.menu.set_archivo_json(Path(ruta).name)
        self.menu.limpiar_aviso()

    def iniciar_simulacion(self):
        """Va a la simulación si hay JSON; si no hay ningún dato, muestra un aviso."""
        if self.ruta_json is None and self.config_manual is None:
            self.menu.mostrar_aviso(
                "Cargue un archivo JSON o realice la configuración manual "
                "antes de iniciar la simulación."
            )
            return
        if self.ruta_json is None:
            # Solo hay configuración manual: se genera el escenario y se usa su archivo.
            try:
                self.ruta_json = str(self._generar_escenario(self.config_manual))
            except ErrorConfiguracion as error:
                messagebox.showerror(
                    "Configuración incompleta", error.mensaje_completo()
                )
                return
            except OSError as error:
                messagebox.showerror(
                    "Error al guardar", f"No se pudo crear el escenario:\n{error}"
                )
                return
        self.menu.set_archivo_json(Path(self.ruta_json).name)

        # Leemos el modo elegido en el menú (1 = Global, 0 = Por Picker)
        modo_elegido = self.menu.combo_modo_waves.get()
        estrategia_elegida = self.menu.combo_estrategia.get()

        try:
            # Le pasamos el modo a la función constructora
            self.warehouse, self.simulacion = self.constructor_simulacion(
                Path(self.ruta_json),
                modo_waves=modo_elegido,
                estrategia_recorrido=estrategia_elegida,
            )
        except (
            Exception
        ) as error:  # el escenario puede ser inválido: se informa sin cerrar la app
            traceback.print_exc()
            messagebox.showerror("No se pudo iniciar la simulación", str(error))
            return
        self.mostrar_simulacion()

    # --- Configuración manual ---
    def _carpeta_escenarios(self):
        if self.carpeta_json:
            return Path(self.carpeta_json)
        return Path.cwd() / "data" / "scenarios"

    def _generar_escenario(self, config):
        """Valida la configuración y escribe el JSON del escenario. Devuelve su ruta."""
        ruta, _escenario = guardar_escenario(config, self._carpeta_escenarios())
        return ruta

    def guardar_configuracion(self):
        config = self.vista_config.obtener_configuracion()
        try:
            ruta = self._generar_escenario(config)
        except ErrorConfiguracion as error:
            messagebox.showerror(
                "Revise la configuración",
                "No se pudo crear el escenario:\n\n" + error.mensaje_completo(),
            )
            return  # se queda en la vista para corregir
        except OSError as error:
            messagebox.showerror(
                "Error al guardar", f"No se pudo escribir el escenario:\n{error}"
            )
            return
        self.config_manual = config
        self.ruta_json = str(ruta)  # el escenario generado queda listo para simular
        messagebox.showinfo(
            "Configuración",
            f"Configuración guardada.\nEscenario creado: {ruta.name}\n"
            f"Carpeta: {ruta.parent}",
        )
        self.mostrar_menu()

    def exportar_json(self):
        ruta = filedialog.asksaveasfilename(
            title="Exportar configuración",
            defaultextension=".json",
            filetypes=TIPOS_JSON,
        )
        if not ruta:
            return
        try:
            with open(ruta, "w", encoding="utf-8") as archivo:
                json.dump(
                    self.vista_config.obtener_configuracion(),
                    archivo,
                    indent=2,
                    ensure_ascii=False,
                )
        except OSError as error:
            messagebox.showerror(
                "Error al exportar", f"No se pudo guardar el archivo:\n{error}"
            )

    def importar_json(self):
        ruta = filedialog.askopenfilename(
            title="Importar configuración", filetypes=TIPOS_JSON
        )
        if not ruta:
            return
        try:
            with open(ruta, encoding="utf-8") as archivo:
                datos = json.load(archivo)
        except (OSError, ValueError) as error:
            messagebox.showerror(
                "Error al importar", f"No se pudo leer el archivo:\n{error}"
            )
            return
        if not isinstance(datos, dict):
            messagebox.showerror(
                "Error al importar", "El archivo no tiene el formato esperado."
            )
            return
        if "warehouse" in datos:  # es un escenario del motor: se convierte
            try:
                datos, avisos = escenario_a_config(datos)
            except (ValueError, TypeError, KeyError) as error:
                messagebox.showerror("Error al importar", str(error))
                return
            self.vista_config.cargar_configuracion(datos)
            messagebox.showinfo("Importación", "\n".join(f"• {a}" for a in avisos))
            return
        self.vista_config.cargar_configuracion(datos)

    def cargar_partida(self):
        """Abre un JSON guardado y restaura la simulación."""
        ruta = filedialog.askopenfilename(
            title="Cargar Partida", filetypes=[("Archivos JSON", "*.json")]
        )
        if not ruta:
            return

        try:
            with open(ruta, encoding="utf-8") as f:
                datos = json.load(f)

            # Verificamos si es una partida guardada o un escenario normal
            snapshot = datos.get("snapshot_simulacion")
            if not snapshot:
                messagebox.showerror(
                    "Error", "El archivo no es una partida guardada válida."
                )
                return

            # Reconstruimos la simulación desde cero (usa el escenario base del JSON)
            self.warehouse, self.simulacion = self.constructor_simulacion(Path(ruta))

            # ¡Aplicamos la foto del tiempo!
            self.simulacion.restaurar_snapshot(snapshot)

            # Lo mandamos a la vista de simulación
            self.mostrar_simulacion()

        except Exception as error:
            traceback.print_exc()
            messagebox.showerror("Error al cargar", str(error))
