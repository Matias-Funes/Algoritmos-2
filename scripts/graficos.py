# scripts/graficos.py
import os

import matplotlib.pyplot as plt
import pandas as pd

os.makedirs("data/results", exist_ok=True)


def generar_grafico_comparacion_escenario(escenario_objetivo):
    try:
        df = pd.read_csv("data/results/experimentos.csv")
    except FileNotFoundError:
        print("No se encontró experimentos.csv")
        return

    # Filtramos por el escenario que le pasemos (ej: "grande")
    df_filtrado = df[df["Escenario"].str.contains(escenario_objetivo, case=False)]

    if df_filtrado.empty:
        print(f"No hay datos para el escenario: {escenario_objetivo}")
        print(f"Escenarios disponibles: {df['Escenario'].unique()}")
        return

    # Agrupamos solo por columnas numéricas
    df_filtrado = (
        df_filtrado.groupby("Estrategia").mean(numeric_only=True).reset_index()
    )

    # --- CREACIÓN DE LA FIGURA ---
    fig, ax1 = plt.subplots(figsize=(8, 5))

    # Eje 1: Distancia (Barras)
    color_dist = "#193B59"
    ax1.set_xlabel("Estrategia", fontweight="bold")
    ax1.set_ylabel("Distancia Total (metros)", color=color_dist, fontweight="bold")
    barras = ax1.bar(
        df_filtrado["Estrategia"], df_filtrado["Distancia"], color=color_dist, width=0.4
    )
    ax1.tick_params(axis="y", labelcolor=color_dist)

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

    # Eje 2: Tiempo (Línea)
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
        f"Comparación A vs B (Escenario: {escenario_objetivo.capitalize()})",
        fontweight="bold",
    )
    plt.tight_layout()
    plt.savefig(f"data/results/grafico_comparacion_{escenario_objetivo}.png", dpi=300)
    plt.close()
    print(f"✅ Gráfico de comparación ({escenario_objetivo}) generado.")


def generar_grafico_escalabilidad():
    try:
        df = pd.read_csv("data/results/resultados_experimentos.csv")
    except FileNotFoundError:
        print("No se encontró resultados_experimentos.csv")
        return

    # Filtramos solo los 4 escenarios generados
    df_gen = df[df["escenario"].isin(["Chico", "Mediano", "Grande", "Enorme"])]

    if df_gen.empty:
        print("No se encontraron escenarios generados para escalabilidad.")
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
    generar_grafico_escalabilidad()
    generar_grafico_comparacion_escenario("grande")
    generar_grafico_comparacion_escenario("generado")

# scripts/graficos.py
import os

import matplotlib.pyplot as plt
import pandas as pd

os.makedirs("data/results", exist_ok=True)
