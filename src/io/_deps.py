"""
_deps.py
========
Resuelve las dependencias del módulo io contra las clases de src/core/.

ESTADO ACTUAL: Integrante A todavía no entregó cell.py / warehouse.py.
Por eso el DEFAULT es usar el stub.

Cambiar el default cuando A entregue:
    - Cuando src/core/cell.py y src/core/warehouse.py tengan las clases
      del contrato, cambiar DEFAULT_STUB = False (o borrar el stub y
      simplificar este archivo a imports directos).

Forzar comportamiento:
    USAR_STUB=1  -> usa stub
    USAR_STUB=0  -> usa clases reales (falla ruidosamente si no existen)
"""

import os

# ----------------------------------------------------------------
# Cambiar a False cuando Juli entregue cell.py y warehouse.py.
# ----------------------------------------------------------------
DEFAULT_STUB = False


def _resolver_forzar_stub():
    valor = os.environ.get("USAR_STUB")
    if valor is None:
        return DEFAULT_STUB
    return valor == "1"


FORZAR_STUB = _resolver_forzar_stub()


if FORZAR_STUB:
    from tests._stub_warehouse import Pasillo, Puerta, Rack, Warehouse, ZonaDespacho

    USANDO_STUB = True
else:

    # Importamos las celdas y constantes desde cell.py
    from src.core.cell import DESPACHO, PASILLO, PUERTA, RACK, VACIA, Cell

    # Importamos los elementos físicos desde warehouse.py
    from src.core.warehouse import Pasillo, Puerta, Rack, Warehouse, ZonaDespacho

    USANDO_STUB = False


__all__ = [
    "Warehouse",
    "Rack",
    "Pasillo",
    "Puerta",
    "ZonaDespacho",
    "USANDO_STUB",
    "FORZAR_STUB",
]
