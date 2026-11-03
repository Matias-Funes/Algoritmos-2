"""Punto de entrada unificado del proyecto.

Uso principal:
    python main.py menu        -> Abre la interfaz gráfica (Launcher).

Uso avanzado (por consola):
    python main.py simular --cargar data/escenarios/chico.json
    python main.py simular --bloques 6 --pedidos 40 --split
    python main.py experimentos
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from comparar_estrategias import main as run_experimentos  # noqa: E402
from demo_completa import main as run_simular  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    comando = sys.argv[1]
    resto = sys.argv[2:]

    if comando == "menu":
        # Abre la UI del menú principal
        run_simular(["--menu"])
    elif comando == "experimentos":
        run_experimentos(resto)
    elif comando == "simular":
        run_simular(resto)
    else:
        print(f"Comando desconocido: {comando}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
