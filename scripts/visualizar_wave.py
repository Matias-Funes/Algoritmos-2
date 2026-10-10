"""
Lanza la app de simulación para una wave.

Uso:
    python scripts/visualizar_wave.py [--wave N] [--estrategia X]
"""

import argparse
import tkinter as tk

from warehouse.algoritmos.recorridos import ESTRATEGIAS, recorrer_wave
from warehouse.generacion.generador import ConfigGeneracion, generar_escenario
from warehouse.visualizacion.app import AppSimulacion
from warehouse.waves.generador_waves import EstrategiaWaves, generar_waves


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--wave", type=int, default=0, help="Índice de la wave (0-based)"
    )
    parser.add_argument(
        "--estrategia",
        choices=list(ESTRATEGIAS.keys()),
        default="vecino_mas_cercano",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--celda", type=int, default=40, help="Tamaño de celda en píxeles"
    )
    args = parser.parse_args()

    escenario = generar_escenario(
        ConfigGeneracion(n_bloques_racks=4, alto=6, n_pedidos=15, seed=args.seed)
    )
    waves = generar_waves(
        escenario.pedidos,
        escenario.warehouse,
        max_pedidos=3,
        max_productos=30,
        estrategia=EstrategiaWaves.PRIORIDAD_Y_CERCANIA,
    )

    if args.wave >= len(waves):
        raise SystemExit(
            f"Wave {args.wave} no existe. Hay {len(waves)} waves (0..{len(waves)-1})."
        )

    wave = waves[args.wave]
    resultado = recorrer_wave(wave, escenario.warehouse, estrategia=args.estrategia)

    print(
        f"Wave {wave.id}: {wave.cantidad_pedidos()} pedidos, "
        f"{wave.cantidad_productos()} productos, "
        f"{len(resultado.orden_paradas)} paradas"
    )
    print(f"Distancia total: {resultado.distancia_total}")
    print(f"Nodos visitados: {resultado.nodos_visitados}")

    root = tk.Tk()
    AppSimulacion(root, escenario, wave, resultado, celda_px=args.celda)
    root.mainloop()


if __name__ == "__main__":
    main()
