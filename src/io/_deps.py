"""
_deps.py
========
Resuelve las dependencias del módulo io contra las clases de src/core/.

Mientras Integrante A no entregue cell.py y warehouse.py, se usa un
stub definido en tests/_stub_warehouse.py. Cuando A entregue, el
try() va a importar la versión real automáticamente.

Este módulo es temporal. Cuando A entregue, se puede simplificar
a imports directos.
"""

try:
    from src.core.cell import Pasillo, Puerta, Rack, ZonaDespacho
    from src.core.warehouse import Warehouse

    USANDO_STUB = False
except ImportError:
    from tests._stub_warehouse import Pasillo, Puerta, Rack, Warehouse, ZonaDespacho

    USANDO_STUB = True


__all__ = [
    "Warehouse",
    "Rack",
    "Pasillo",
    "Puerta",
    "ZonaDespacho",
    "USANDO_STUB",
]
