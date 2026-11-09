import sys
from pathlib import Path

# Script de stress: genera escenarios de distintos tamaños y ejecuta el mismo
# constructor y motor que la aplicacion, pero sin abrir una ventana.
# Se agrega la raiz al path para importar esos modulos desde scripts/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import contextlib
import csv
import io
import time

from main import construir_simulacion
from src.io.scenario_generator import generar_escenario


def correr_experimento(ruta_json):
    """Corre la simulación sin UI y devuelve las métricas. Silencia los prints de main.py."""
    t_inicio = time.time()

    # El constructor imprime el progreso normal de la app; el redireccionamiento
    # lo captura para que una serie larga solo muestre el resumen por escenario.
    f = io.StringIO()
    try:
        with contextlib.redirect_stdout(f):
            _, simulacion = construir_simulacion(ruta_json)

            pasos = 0
            while simulacion.avanzar_paso():
                pasos += 1
                if pasos > 20000:  # Límite de seguridad
                    break
    except Exception as e:
        print(f"  -> ❌ Error en simulación: {e}")
        return None

    t_fin = time.time()
    estado = simulacion.get_estado()

    return {
        "pasos": pasos,
        "tiempo_cpu_seg": round(t_fin - t_inicio, 3),
        "recogidos": estado["productos_recogidos"],
        "total": estado["total_productos"],
        "distancia": estado["distancia"],
        "faltantes": len(estado["faltantes"]),
        "completado": (
            "Sí" if estado["productos_recogidos"] == estado["total_productos"] else "No"
        ),
    }


def test_masivo_generados():
    """Genera escenarios con stock suficiente y los prueba."""
    print("\n--- INICIANDO PRUEBAS CON ESCENARIOS GENERADOS ---")
    configuraciones = [
        {"nombre": "Chico", "params": (20, 20, 5, 30, 10)},
        {"nombre": "Mediano", "params": (40, 30, 15, 150, 30)},
        {"nombre": "Grande", "params": (60, 40, 22, 400, 60)},
        {"nombre": "Enorme", "params": (80, 50, 30, 800, 100)},
    ]

    resultados = []
    ruta_temp = Path("data/scenarios/temp_experimento.json")

    # Se reutiliza un archivo temporal para no acumular cientos de JSON de prueba.
    for config in configuraciones:
        print(f"\nGenerando escenario {config['nombre']}...")
        generar_escenario(
            ancho_x=config["params"][0],
            largo_y=config["params"][1],
            cant_racks=config["params"][2],
            cant_productos=config["params"][3],
            cant_pedidos=config["params"][4],
            ruta_salida=str(ruta_temp),
        )

        metricas = correr_experimento(ruta_temp)
        if metricas:
            metricas["escenario"] = config["nombre"]
            resultados.append(metricas)
            print(
                f"  -> Tiempo: {metricas['tiempo_cpu_seg']}s | Distancia: {metricas['distancia']}m | Completado: {metricas['completado']} ({metricas['recogidos']}/{metricas['total']})"
            )

    if ruta_temp.exists():
        ruta_temp.unlink()
    return resultados


def test_todos_los_escenarios_carpeta():
    """Prueba todos los .json que estén en la carpeta data/scenarios/."""
    print("\n--- PROBANDO TODOS LOS ESCENARIOS DE LA CARPETA ---")
    carpeta = Path("data/scenarios")
    resultados = []

    # Se omiten entradas temporales o deliberadamente invalidas; los escenarios
    # restantes se ejecutan sin modificar sus archivos.
    for ruta in carpeta.glob("*.json"):
        # Saltamos los temporales o los inválidos
        if "temp_" in ruta.name or "invalido" in ruta.name:
            continue

        print(f"Simulando {ruta.name}...")
        metricas = correr_experimento(ruta)
        if metricas:
            metricas["escenario"] = ruta.name
            resultados.append(metricas)
            print(
                f"  -> Tiempo: {metricas['tiempo_cpu_seg']}s | Distancia: {metricas['distancia']}m | Completado: {metricas['completado']} ({metricas['recogidos']}/{metricas['total']})"
            )

    return resultados


def main():
    print("Iniciando suite de pruebas...")

    # 1. Pruebas de escalabilidad
    resultados_generados = test_masivo_generados()

    # 2. Pruebas de los escenarios base
    resultados_carpeta = test_todos_los_escenarios_carpeta()

    # Unificamos todos los resultados
    resultados_finales = resultados_generados + resultados_carpeta

    # Guardar en CSV
    if resultados_finales:
        ruta_csv = Path("data/results/resultados_experimentos.csv")
        ruta_csv.parent.mkdir(parents=True, exist_ok=True)
        # Nos aseguramos de que todos tengan las mismas columnas
        columnas = [
            "escenario",
            "pasos",
            "tiempo_cpu_seg",
            "recogidos",
            "total",
            "distancia",
            "faltantes",
            "completado",
        ]
        with open(ruta_csv, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columnas, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(resultados_finales)
        print(f"\n✅ Todos los resultados guardados en: {ruta_csv}")


if __name__ == "__main__":
    main()
