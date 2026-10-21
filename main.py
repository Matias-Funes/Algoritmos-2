"""
main.py
=======
Punto de entrada del Sistema de Wave Picking (Etapa 1).
Carga el escenario básico, construye el Warehouse y muestra información.
"""


def main():
    print("=== Wave Picking System ===")
    try:
        from src.io.scenario_loader import cargar_escenario

        ruta = "data/scenarios/escenario_basico.json"
        print(f"Cargando escenario: {ruta}...")

        warehouse, productos, pedidos, pickers, config = cargar_escenario(ruta)

        print("\n✓ Escenario cargado con éxito")
        print("-" * 30)
        print(f"Dimensiones:      {warehouse.ancho_x} x {warehouse.largo_y}")
        print(f"Racks:            {len(warehouse.racks)}")
        print(f"Pasillos:         {len(warehouse.pasillos)}")
        print(f"Puertas:          {len(warehouse.puertas)}")
        print(f"Zonas de despacho:{len(warehouse.zonas)}")
        print(f"Productos:        {len(productos)}")
        print(f"Pedidos:          {len(pedidos)}")
        print(f"Pickers:          {len(pickers)}")
        print(f"Configuración:    {config}")
        print("-" * 30)

        print("\nMapa del Warehouse:")
        warehouse.print_ascii()

    except FileNotFoundError:
        print(f"Error: No se encontró el archivo {ruta}")
    except Exception as e:
        print(f"Error inesperado: {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
