# Simulador de Wave Picking

Aplicación de escritorio para simular la preparación de pedidos en un almacén.
Permite cargar o crear escenarios, agrupar pedidos en waves y visualizar el
recorrido de los pickers.

## Requisitos

- Python 3.10 o superior.
- Tkinter, necesario para la interfaz gráfica. En Windows suele instalarse
  junto con Python; en algunas distribuciones de Linux se instala por separado
  (por ejemplo, con `sudo apt install python3-tk` en Debian o Ubuntu).
- Git, si se va a clonar el repositorio.

El proyecto utiliza la biblioteca estándar de Python; no requiere instalar
paquetes con `pip`.

## Instalación

Cloná el repositorio y entrá a la carpeta:

```bash
git clone https://github.com/Matias-Funes/Algoritmos-2.git
cd Algoritmos-2
```

Creá un entorno virtual:

```bash
python -m venv .venv
```

Activá el entorno virtual según tu sistema.

**Windows (PowerShell):**

```powershell
.\.venv\Scripts\Activate.ps1
```

**Linux o macOS:**

```bash
source .venv/bin/activate
```

Si Windows no reconoce `python`, podés usar el lanzador `py` para crear el
entorno: `py -3 -m venv .venv`. También es posible ejecutar la aplicación con
el Python del entorno sin activarlo: `.\.venv\Scripts\python.exe main.py`.

## Ejecutar la aplicación

Desde la carpeta del repositorio:

```bash
python main.py
```

Se abrirá el menú de la aplicación. Desde allí podés:

1. Elegir **Cargar JSON** y seleccionar un escenario, o abrir
   **Configuración manual** para crear uno.
2. Seleccionar una estrategia de recorrido.
3. Presionar **Iniciar simulación**.

También podés indicar un escenario al iniciar. Por ejemplo:

```bash
python main.py data/scenarios/escenario_basico.json
```

Hay escenarios de ejemplo en `data/scenarios/`. La interfaz permite iniciar,
pausar, avanzar o retroceder pasos, reiniciar y guardar una partida.

## Ejecutar las pruebas

```bash
python -m unittest discover -s tests -v
```

## Estructura del proyecto

- `main.py`: punto de entrada y armado de la simulación.
- `src/core/`: modelos de productos, pedidos, pickers y almacén.
- `src/algorithms/`: algoritmos de rutas y generación de waves.
- `src/simulation/`: motor de simulación.
- `src/io/`: carga y persistencia de escenarios.
- `src/ui/`: interfaz gráfica.
- `tests/`: pruebas automatizadas.
- `docs/`: documentación técnica.
