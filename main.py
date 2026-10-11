"""Punto de entrada unificado del proyecto.

Uso:
    python main.py experimentos
    python main.py simular --bloques 6 --pedidos 40
    python main.py simular --wave 3 --estrategia orden_pedidos
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).parent / "scripts"


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    comando = sys.argv[1]
    resto = sys.argv[2:]

    if comando == "experimentos":
        subprocess.run(
            [sys.executable, str(SCRIPTS / "comparar_estrategias.py"), *resto]
        )
    elif comando == "simular":
        subprocess.run([sys.executable, str(SCRIPTS / "demo_completa.py"), *resto])
    else:
        print(f"Comando desconocido: {comando}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
