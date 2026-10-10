from enum import Enum


class TipoNodo(Enum):
    PASILLO = "pasillo"
    RACK = "rack"
    DESPACHO = "despacho"
    PUERTA = "puerta"
