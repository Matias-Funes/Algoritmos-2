import sys
from pathlib import Path

# Este script de consola reutiliza el constructor de main.py, pero no crea Tk:
# permite inspeccionar una corrida completa y sus metricas desde terminal.
# Se agrega la raiz al path para poder importar el punto de entrada y src/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import time

from main import construir_simulacion


def correr_prueba(ruta_json):
    print(f"=== PROBANDO ESCENARIO: {ruta_json} ===")
    t_inicio = time.time()

    # 1. Construir el mismo motor que usa la app, sin iniciar la interfaz.
    try:
        warehouse, simulacion = construir_simulacion(Path(ruta_json))
    except Exception as e:
        print(f"❌ ERROR AL CONSTRUIR: {e}")
        return

    # 2. Cada llamada avanza un paso sincronizado; el tope detecta un posible
    # bloqueo en lugar de dejar este programa de diagnostico girando sin fin.
    pasos = 0
    try:
        while simulacion.avanzar_paso():
            pasos += 1
            if pasos > 10000:  # Límite de seguridad
                print("⚠️ Límite de 10000 pasos alcanzado. Posible deadlock.")
                break
    except Exception as e:
        print(f"❌ ERROR EN EJECUCIÓN (Paso {pasos}): {e}")
        return

    t_fin = time.time()

    # 3. Consultar el estado final permite comparar cobertura, distancia y
    # pickers activos sin depender de elementos graficos.
    estado = simulacion.get_estado()

    print("\n=== RESULTADOS ===")
    print(f"✅ Simulación terminada en {pasos} pasos.")
    print(f"⏱️ Tiempo real de CPU: {t_fin - t_inicio:.2f} segundos.")
    print(
        f"📦 Productos recogidos: {estado['productos_recogidos']} / {estado['total_productos']}"
    )
    print(f"📏 Distancia total recorrida: {estado['distancia']} m")
    print(f"🚨 Faltantes: {len(estado['faltantes'])}")

    # Verificamos si quedó algún picker trabado
    trabados = [p["id"] for p in estado["pickers"] if p["activo"]]
    if trabados:
        print(f"⚠️ PICKERS ATRAPADOS: {trabados}")
    else:
        print("✅ Todos los pickers terminaron su trabajo.")

    print("=" * 40 + "\n")


if __name__ == "__main__":
    # Prueba con tus escenarios
    correr_prueba("data/scenarios/escenario_basico.json")
    correr_prueba("data/scenarios/escenario_grande.json")
