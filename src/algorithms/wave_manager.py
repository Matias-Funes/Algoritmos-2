

from src.algorithms.pathfinding import CacheDistancias
from src.core.order import EN_WAVE
from src.core.wave import Wave

INFINITO = float("inf")


def _celdas_piso(orden, inventory, grafo):
    """Celdas del grafo (pasillo) desde donde el picker toma los productos de
    la orden: las vecinas a la celda de cada producto, sin repetir. El grafo
    solo tiene celdas de pasillo, asi que un vecino que esta en el grafo es
    una celda transitable. O(k) promedio, con k = items."""
    celdas = []
    for producto_id, _ in orden.items:
        x, y = inventory.obtener_producto(producto_id).ubicacion[:2]
        for vecina in ((x, y), (x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if vecina in grafo.adj and vecina not in celdas:
                celdas.append(vecina)
    return celdas


def _distancia_entre_pedidos(cache, celdas_a, celdas_b):
    """Menor distancia (yendo de A hacia B) entre alguna celda de A y alguna
    celda de B. O(|A| * |B|) consultas al cache."""
    return min((cache.distancia(u, v) for u in celdas_a for v in celdas_b),
               default=INFINITO)


def generar_waves(pedidos_pendientes, inventory, warehouse, config):
    """Agrupa los pedidos PENDIENTES en waves y devuelve la lista de waves.

    Complejidad (r = pedidos pendientes, U = celdas de pasillo distintas
    desde las que se consulta, a = celdas por pedido, constante):
    ordenar O(r log r); un Dijkstra por cada celda de origen, una sola vez
    gracias al cache, O(U (V + E) log V); y cada pedido que se suma a una
    wave actualiza la distancia de los restantes con O(r a^2) consultas al
    cache mas un reordenamiento O(r log r).
    """

    grafo = warehouse
    cache = CacheDistancias(grafo) # memoriza los Dijkstra de toda la corrida

    # 1. Solo pedidos pendientes con items, del mas al menos prioritario.
    #    sort es estable: a igual prioridad se respeta el orden de llegada.
    restantes = [p for p in pedidos_pendientes
                 if p.esta_pendiente() and p.items]
    restantes.sort(key=lambda p: int(p.prioridad), reverse=True)

    piso = {id(p): _celdas_piso(p, inventory, grafo) for p in restantes}
    waves = []

    while restantes:
        wave = Wave(
            f"WAVE_{len(waves) + 1:03d}",
            config["max_pedidos"],
            config["max_productos"],
            config["peso_max_kg"],
        )

        # 2. El pedido mas prioritario abre la wave
        semilla = restantes.pop(0)
        if not wave.agregar_pedido(semilla, inventory):
            continue # no entra ni en una wave vacia: queda PENDIENTE
        semilla.cambiar_estado(EN_WAVE)

        # distancia de cada pedido restante a lo que ya tiene la wave
        lejania = {id(q): _distancia_entre_pedidos(cache, piso[id(semilla)], piso[id(q)])
                   for q in restantes}

        # 3. Sumar pedidos mientras quepan: mayor prioridad primero y,
        #    a igual prioridad, el mas cercano a lo que ya tiene la wave
        while restantes:
            agregado = None
            # sorted es estable: si empatan prioridad y distancia, gana el que llego antes
            for p in sorted(restantes, key=lambda q: (- int(q.prioridad), lejania[id(q)])):
                if wave.agregar_pedido(p, inventory):
                    agregado = p
                    break
            if agregado is None:
                break # 4. no entra ninguno: se cierra la wave

            agregado.cambiar_estado(EN_WAVE)
            restantes.remove(agregado)
            for q in restantes:
                lejania[id(q)] = min(
                    lejania[id(q)],
                    _distancia_entre_pedidos(cache, piso[id(agregado)], piso[id(q)]),
                )

        waves.append(wave)

    return waves