# scripts/graficos.py
import pandas as pd
import matplotlib.pyplot as plt
import os

# Aseguramos que exista la carpeta de resultados
os.makedirs("data/results", exist_ok=True)


# --- GRÁFICO 1: Estrategia A vs B (Distancia y Tiempo) ---
def generar_grafico_comparacion():
    try:
        df = pd.read_csv("data/results/experimentos.csv")
    except FileNotFoundError:
        print("No se encontró experimentos.csv")
        return

    # Tomamos el escenario más grande o el "generado" para comparar
    # (Ajusta 'Escenario' si tus nombres son distintos)
    escenario_objetivo = df["Escenario"].unique()[0]
    df_filtrado = df[df["Escenario"] == escenario_objetivo]

    fig, ax1 = plt.subplots(figsize=(8, 5))

    # Gráfico de barras para Distancia
    color_dist = "#193B59"
    ax1.set_xlabel("Estrategia", fontweight="bold")
    ax1.set_ylabel("Distancia Total (metros)", color=color_dist, fontweight="bold")
    barras = ax1.bar(
        df_filtrado["Estrategia"], df_filtrado["Distancia"], color=color_dist, width=0.4
    )
    ax1.tick_params(axis="y", labelcolor=color_dist)

    # Añadir etiquetas de valor sobre las barras
    for barra in barras:
        yval = barra.get_height()
        ax1.text(
            barra.get_x() + barra.get_width() / 2,
            yval + 1,
            int(yval),
            ha="center",
            va="bottom",
            fontweight="bold",
        )

    # Gráfico de líneas para Tiempo en un eje secundario
    ax2 = ax1.twinx()
    color_tiempo = "#147D5A"
    ax2.set_ylabel("Tiempo (ms)", color=color_tiempo, fontweight="bold")
    ax2.plot(
        df_filtrado["Estrategia"],
        df_filtrado["Tiempo_ms"],
        color=color_tiempo,
        marker="o",
        linewidth=3,
        markersize=8,
    )
    ax2.tick_params(axis="y", labelcolor=color_tiempo)

    plt.title(
        f"Comparación A vs B (Escenario: {escenario_objetivo})", fontweight="bold"
    )
    plt.tight_layout()
    plt.savefig("data/results/grafico_comparacion.png", dpi=300)
    plt.close()
    print("✅ Gráfico de comparación generado.")


# --- GRÁFICO 2: Escalabilidad (Tiempo vs Tamaño del Almacén) ---
def generar_grafico_escalabilidad():
    try:
        df = pd.read_csv("data/results/resultados_experimentos.csv")
    except FileNotFoundError:
        print("No se encontró resultados_experimentos.csv")
        return

    # Filtrar solo los escenarios generados automáticamente (Chico, Mediano, Grande, Enorme)
    # Si no usas esos nombres, ajusta el filtro
    df_gen = df[df["escenario"].isin(["Chico", "Mediano", "Grande", "Enorme"])]

    if df_gen.empty:
        print("No hay datos de escalabilidad para graficar.")
        return

    plt.figure(figsize=(8, 5))
    plt.plot(
        df_gen["escenario"],
        df_gen["tiempo_cpu_seg"],
        marker="s",
        color="#D9A441",
        linewidth=3,
        markersize=10,
    )

    plt.title(
        "Escalabilidad: Tiempo de Simulación vs Tamaño del Warehouse", fontweight="bold"
    )
    plt.xlabel("Tamaño del Escenario", fontweight="bold")
    plt.ylabel("Tiempo de CPU (segundos)", fontweight="bold")
    plt.grid(axis="y", linestyle="--", alpha=0.7)

    for i, txt in enumerate(df_gen["tiempo_cpu_seg"]):
        plt.annotate(
            f"{txt}s",
            (df_gen["escenario"].iloc[i], txt),
            textcoords="offset points",
            xytext=(0, 10),
            ha="center",
        )

    plt.tight_layout()
    plt.savefig("data/results/grafico_escalabilidad.png", dpi=300)
    plt.close()
    print("✅ Gráfico de escalabilidad generado.")


if __name__ == "__main__":
    generar_grafico_comparacion()
    generar_grafico_escalabilidad()
