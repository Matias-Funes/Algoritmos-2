from collections import defaultdict

from warehouse.dominio.pedido import Pedido
from warehouse.waves.generador_waves import ItemWave


def validar_cobertura_waves(
    pedidos: list[Pedido],
    items_por_wave: dict[str, list[ItemWave]],
) -> None:
    """Lanza ValueError si la unión de items por wave NO cubre exactamente
    los pedidos (faltan unidades, sobran, o hay cantidades <= 0)."""
    demanda: dict[tuple[str, str], int] = defaultdict(int)
    for p in pedidos:
        for it in p.items:
            demanda[(p.id, it.producto_id)] += it.cantidad

    oferta: dict[tuple[str, str], int] = defaultdict(int)
    for wave_id, items in items_por_wave.items():
        for iw in items:
            if iw.cantidad <= 0:
                raise ValueError(
                    f"Wave {wave_id}: cantidad no positiva en "
                    f"({iw.pedido_id}, {iw.producto_id}) = {iw.cantidad}"
                )
            oferta[(iw.pedido_id, iw.producto_id)] += iw.cantidad

    faltantes = {
        k: v - oferta.get(k, 0) for k, v in demanda.items() if oferta.get(k, 0) < v
    }
    if faltantes:
        raise ValueError(f"Cobertura incompleta — faltan: {faltantes}")

    sobrantes = {
        k: v - demanda.get(k, 0) for k, v in oferta.items() if v > demanda.get(k, 0)
    }
    if sobrantes:
        raise ValueError(f"Cobertura excedida — sobran: {sobrantes}")
