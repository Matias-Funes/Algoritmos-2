"""
Script de experimentación.

Genera escenarios de 3 tamaños con 3 seeds cada uno, produce waves y compara
las dos estrategias de recorrido. Guarda resultados en CSV.

Uso:
    python scripts/comparar_estrategias.py
"""

import csv
import json
import statistics
from dataclasses import asdict, replace
from pathlib import Path
from time import perf_counter

from warehouse.algoritmos.recorridos import ESTRATEGIAS, recorrer_wave
from warehouse.generacion.generador import ConfigGeneracion, generar_escenario
from warehouse.generacion.validador import validar_escenario
from warehouse.waves.generador_waves import EstrategiaWaves, generar_waves

# --- configuración del experimento ---


def _configs_base() -> dict[str, ConfigGeneracion]:
    """Configuración geométrica por tamaño. El seed se asigna en el loop."""
    return {
        "chico": ConfigGeneracion(
            n_bloques_racks=2,
            alto=5,
            n_pedidos=10,
            max_productos_por_pedido=3,
            productos_por_rack=2,
            max_pedidos_wave=3,
            max_productos_wave=20,
        ),
        "mediano": ConfigGeneracion(
            n_bloques_racks=4,
            alto=8,
            n_pedidos=30,
            max_productos_por_pedido=4,
            productos_por_rack=2,
            max_pedidos_wave=4,
            max_productos_wave=30,
        ),
        "grande": ConfigGeneracion(
            n_bloques_racks=8,
            alto=12,
            n_pedidos=100,
            max_productos_por_pedido=5,
            productos_por_rack=3,
            max_pedidos_wave=5,
            max_productos_wave=50,
        ),
    }


SEEDS = [1, 2, 3]
ESTRATEGIA_WAVES = EstrategiaWaves.PRIORIDAD_Y_CERCANIA


# --- pipeline de un escenario ---


def _correr_escenario(
    nombre_tamano: str,
    cfg: ConfigGeneracion,
    filas_waves: list[dict],
) -> None:
    """Genera un escenario, produce waves y registra métricas por wave
    en filas_waves (append in-place)."""

    t0 = perf_counter()
    escenario = generar_escenario(cfg)
    validar_escenario(escenario)
    t_gen = perf_counter() - t0

    t0 = perf_counter()
    waves = generar_waves(
        escenario.pedidos,
        escenario.warehouse,
        max_pedidos=cfg.max_pedidos_wave,
        max_productos=cfg.max_productos_wave,
        estrategia=ESTRATEGIA_WAVES,
    )
    t_waves = perf_counter() - t0

    escenario_id = f"{nombre_tamano}_s{cfg.seed}"

    for wave in waves:
        for nombre_estrat in ESTRATEGIAS:
            resultado = recorrer_wave(
                wave,
                escenario.warehouse,
                estrategia=nombre_estrat,
            )
            filas_waves.append(
                {
                    "escenario": escenario_id,
                    "tamano": nombre_tamano,
                    "seed": cfg.seed,
                    "ancho": escenario.warehouse.ancho,
                    "alto": escenario.warehouse.alto,
                    "n_racks": len(escenario.warehouse.racks),
                    "n_productos": len(escenario.warehouse.productos),
                    "n_nodos_grafo": len(escenario.warehouse.grafo),
                    "t_gen_escenario_s": t_gen,
                    "t_gen_waves_s": t_waves,
                    "wave_id": wave.id,
                    "wave_n_pedidos": wave.cantidad_pedidos(),
                    "wave_n_productos": wave.cantidad_productos(),
                    "wave_prio_max": wave.prioridad_maxima(),
                    "estrategia_recorrido": nombre_estrat,
                    "n_paradas": len(resultado.orden_paradas),
                    "distancia_total": resultado.distancia_total,
                    "nodos_visitados": resultado.nodos_visitados,
                    "aristas_recorridas": resultado.aristas_recorridas,
                    "t_recorrido_s": resultado.tiempo_segundos,
                }
            )


# --- agregación de resultados ---


def _resumir(filas_waves: list[dict]) -> list[dict]:
    """Agrupa por (escenario, estrategia_recorrido) y calcula agregados."""
    grupos: dict[tuple, list[dict]] = {}
    for fila in filas_waves:
        clave = (fila["escenario"], fila["estrategia_recorrido"])
        grupos.setdefault(clave, []).append(fila)

    resumen: list[dict] = []
    for (escenario, estrategia), filas in sorted(grupos.items()):
        distancias = [f["distancia_total"] for f in filas]
        tiempos = [f["t_recorrido_s"] for f in filas]
        nodos = [f["nodos_visitados"] for f in filas]
        aristas = [f["aristas_recorridas"] for f in filas]

        primera = filas[0]
        resumen.append(
            {
                "escenario": escenario,
                "tamano": primera["tamano"],
                "seed": primera["seed"],
                "ancho": primera["ancho"],
                "alto": primera["alto"],
                "n_racks": primera["n_racks"],
                "n_productos": primera["n_productos"],
                "n_nodos_grafo": primera["n_nodos_grafo"],
                "t_gen_escenario_s": primera["t_gen_escenario_s"],
                "t_gen_waves_s": primera["t_gen_waves_s"],
                "estrategia_recorrido": estrategia,
                "n_waves": len(filas),
                "dist_total": sum(distancias),
                "dist_media": statistics.mean(distancias),
                "dist_mediana": statistics.median(distancias),
                "dist_min": min(distancias),
                "dist_max": max(distancias),
                "t_recorrido_total_s": sum(tiempos),
                "t_recorrido_medio_ms": statistics.mean(tiempos) * 1000,
                "nodos_totales": sum(nodos),
                "aristas_totales": sum(aristas),
            }
        )
    return resumen


# --- persistencia ---


def _guardar_csv(filas: list[dict], path: Path) -> None:
    if not filas:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    campos = list(filas[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(filas)


def _guardar_config(configs: dict[str, ConfigGeneracion], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "seeds": SEEDS,
        "estrategia_waves": ESTRATEGIA_WAVES.value,
        "estrategias_recorrido": list(ESTRATEGIAS.keys()),
        "tamanos": {nombre: asdict(cfg) for nombre, cfg in configs.items()},
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# --- impresión de resumen ---


def _imprimir_resumen(resumen: list[dict]) -> None:
    print()
    print(
        f"{'escenario':<15} {'estrategia':<20} "
        f"{'n_waves':>8} {'dist_total':>12} {'dist_media':>12} "
        f"{'t_total_ms':>12}"
    )
    print("-" * 85)
    for fila in resumen:
        print(
            f"{fila['escenario']:<15} "
            f"{fila['estrategia_recorrido']:<20} "
            f"{fila['n_waves']:>8} "
            f"{fila['dist_total']:>12.1f} "
            f"{fila['dist_media']:>12.2f} "
            f"{fila['t_recorrido_total_s'] * 1000:>12.2f}"
        )


# --- main ---


def main() -> None:
    raiz = Path(__file__).parent.parent
    dir_resultados = raiz / "data" / "resultados"

    configs = _configs_base()
    filas_waves: list[dict] = []

    print("Corriendo experimentos...")
    for nombre_tamano, base in configs.items():
        for seed in SEEDS:
            cfg = replace(base, seed=seed)
            print(f"  {nombre_tamano} seed={seed}...", end=" ", flush=True)
            t0 = perf_counter()
            _correr_escenario(nombre_tamano, cfg, filas_waves)
            print(f"OK ({perf_counter() - t0:.2f}s)")

    resumen = _resumir(filas_waves)

    _guardar_csv(filas_waves, dir_resultados / "resultados_waves.csv")
    _guardar_csv(resumen, dir_resultados / "resultados_resumen.csv")
    _guardar_config(configs, dir_resultados / "config_experimento.json")

    print()
    print(f"Total de filas: {len(filas_waves)}")
    print(f"Resultados guardados en: {dir_resultados}")
    _imprimir_resumen(resumen)


if __name__ == "__main__":
    main()
