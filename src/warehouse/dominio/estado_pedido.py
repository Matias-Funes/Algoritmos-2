from enum import Enum


class EstadoPedido(Enum):
    PENDIENTE = "PENDIENTE"
    EN_WAVE = "EN_WAVE"
    EN_PREPARACION = "EN_PREPARACION"
    PREPARADO = "PREPARADO"
