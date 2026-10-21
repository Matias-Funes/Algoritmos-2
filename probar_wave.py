import sys
from pathlib import Path

# Permite importar los módulos dentro de src/
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from core.inventory import GestorInventario, Producto
from core.order import Orden
from core.wave import Wave


# Crear inventario y cargar productos
inventario = GestorInventario()

inventario.agregar_producto(
    Producto("P001", "Monitor", "R1", (3, 5, 1), 10, 6.5)
)
inventario.agregar_producto(
    Producto("P002", "Teclado", "R1", (3, 6, 1), 10, 1.2)
)
inventario.agregar_producto(
    Producto("P003", "Mouse", "R2", (8, 5, 1), 10, 0.3)
)

# Crear una wave:
# máximo 3 órdenes, 10 unidades y 30 kg
wave = Wave(
    wave_id="WAVE_001",
    capacidad_max_pedidos=3,
    capacidad_max_productos=10,
    peso_max_kg=30.0,
)

# Crear una orden vacía y probar que no se agregue
orden_vacia = Orden("PED_VACIO", 1, [])

try:
    wave.agregar_pedido(orden_vacia, inventario)
except ValueError as error:
    print(f"Orden vacía rechazada: {error}")

print(f"Órdenes en la wave después del intento: {len(wave)}")

# Crear órdenes con productos
orden_1 = Orden(
    "PED_001",
    5,
    [("P001", 2), ("P002", 1)],
)

orden_2 = Orden(
    "PED_002",
    3,
    [("P003", 2)],
)

# agregar_pedido devuelve True si la orden se agregó
# y False si no cabe en la wave
agregada_1 = wave.agregar_pedido(orden_1, inventario)
agregada_2 = wave.agregar_pedido(orden_2, inventario)

print(f"¿Se agregó PED_001? {agregada_1}")
print(f"¿Se agregó PED_002? {agregada_2}")

# Consultar los datos de la wave
print(f"\nWave: {wave.id}")
print(f"Órdenes: {[orden.orden_id for orden in wave.pedidos]}")
print(f"Cantidad de órdenes: {len(wave)}")
print(f"Cantidad de productos/unidades: {wave.cantidad_productos()}")
print(f"Peso total: {wave.peso_total(inventario):.2f} kg")