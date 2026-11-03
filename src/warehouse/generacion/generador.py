import random
from dataclasses import dataclass

from warehouse.dominio.pedido import Pedido
from warehouse.dominio.picker import Picker
from warehouse.dominio.producto import Producto
from warehouse.warehouse.escenario import Escenario, WaveConfig
from warehouse.warehouse.warehouse import Warehouse


@dataclass
class ConfigGeneracion:
    # geometría
    n_bloques_racks: int = 3
    ancho_pasillo: int = 3
    ancho_bloque_racks: int = 2
    alto: int = 16
    cada_cuantas_filas_pasillo_horizontal: int = 0  # 0 = solo arriba/abajo
    margen_inferior: int = 5  # filas vacías abajo
    margen_superior: int = 5  # filas vacías arriba
    n_zonas: int = 1

    n_pickers: int = 2
    picker_capacidad_kg: float = 500.0
    peso_max_zona_kg: float = 800.0
    n_zonas: int = 1

    # productos
    niveles_por_rack: int = 3  # altura física del rack
    productos_por_rack: int = 2  # niveles efectivamente ocupados
    stock_min: int = 10
    stock_max: int = 50
    peso_min_kg: float = 0.5
    peso_max_kg: float = 8.0

    # pedidos
    n_pedidos: int = 10
    max_productos_por_pedido: int = 3

    # waves
    max_pedidos_wave: int = 3
    max_productos_wave: int = 20

    # reproducibilidad
    seed: int | None = None

    def __post_init__(self) -> None:
        if self.n_bloques_racks <= 0:
            raise ValueError("n_bloques_racks debe ser > 0")
        if self.ancho_pasillo <= 0:
            raise ValueError("ancho_pasillo debe ser > 0")
        if self.ancho_bloque_racks <= 0:
            raise ValueError("ancho_bloque_racks debe ser > 0")
        if self.alto < 3:
            raise ValueError("alto debe ser >= 3 (pasillos arriba y abajo + racks)")
        if self.niveles_por_rack <= 0:
            raise ValueError("niveles_por_rack debe ser > 0")
        if self.productos_por_rack > self.niveles_por_rack:
            raise ValueError(
                f"productos_por_rack ({self.productos_por_rack}) no puede ser mayor "
                f"que niveles_por_rack ({self.niveles_por_rack})"
            )
        if self.stock_min > self.stock_max:
            raise ValueError("stock_min no puede ser mayor que stock_max")
        if self.cada_cuantas_filas_pasillo_horizontal < 0:
            raise ValueError("cada_cuantas_filas_pasillo_horizontal debe ser >= 0")
        if self.margen_inferior < 0 or self.margen_superior < 0:
            raise ValueError("Los márgenes deben ser >= 0")
        if self.margen_inferior + self.margen_superior >= self.alto - 2:
            raise ValueError("Los márgenes dejan muy poco espacio para los racks")


# --- helpers de geometría ---


def _calcular_ancho(config: ConfigGeneracion) -> int:
    return config.ancho_pasillo + config.n_bloques_racks * (
        config.ancho_bloque_racks + config.ancho_pasillo
    )


def _patron_columnas(config: ConfigGeneracion) -> list[str]:
    """Devuelve una lista de 'P' (pasillo) o 'R' (rack) de longitud ancho."""
    patron: list[str] = []
    for _ in range(config.ancho_pasillo):
        patron.append("P")
    for _ in range(config.n_bloques_racks):
        for _ in range(config.ancho_bloque_racks):
            patron.append("R")
        for _ in range(config.ancho_pasillo):
            patron.append("P")
    return patron


def _es_fila_pasillo_horizontal(y: int, config: ConfigGeneracion) -> bool:
    """Devuelve True si la fila y debe ser un pasillo horizontal completo."""
    # Los bordes siempre son pasillos
    if y == 0 or y == config.alto - 1:
        return True
    # Márgenes superior e inferior
    if y < config.margen_inferior:
        return True
    if y >= config.alto - config.margen_superior:
        return True
    # Pasillos intermedios (si están configurados)
    if config.cada_cuantas_filas_pasillo_horizontal > 0:
        return (
            y - config.margen_inferior
        ) % config.cada_cuantas_filas_pasillo_horizontal == 0
    return False


def _celdas_transitables(
    config: ConfigGeneracion, patron: list[str]
) -> set[tuple[int, int]]:
    ancho = len(patron)
    celdas: set[tuple[int, int]] = set()

    for y in range(config.alto):
        if _es_fila_pasillo_horizontal(y, config):
            # Toda la fila es transitable
            for x in range(ancho):
                celdas.add((x, y))
        else:
            # Solo columnas P (pasillos verticales)
            for x in range(ancho):
                if patron[x] == "P":
                    celdas.add((x, y))

    return celdas


def _posiciones_racks(
    config: ConfigGeneracion, patron: list[str]
) -> list[tuple[int, int, int, int]]:
    """Devuelve lista de (x, y, ancho, alto) para cada rack rectangular.

    Estrategia:
      - Cada bloque de columnas R contiguas forma un rack.
      - El rack se corta verticalmente por cada pasillo horizontal.
    """
    ancho = len(patron)
    rectangulos: list[tuple[int, int, int, int]] = []

    # 1. Encontrar bloques de columnas R
    bloques: list[tuple[int, int]] = []  # (x_inicio, ancho_bloque)
    x = 0
    while x < ancho:
        if patron[x] == "P":
            x += 1
            continue
        x_inicio = x
        while x < ancho and patron[x] == "R":
            x += 1
        bloques.append((x_inicio, x - x_inicio))

    # 2. Para cada bloque, cortar verticalmente por pasillos horizontales
    for x_inicio, ancho_bloque in bloques:
        y = 0
        while y < config.alto:
            if _es_fila_pasillo_horizontal(y, config):
                y += 1
                continue
            y_inicio = y
            while y < config.alto and not _es_fila_pasillo_horizontal(y, config):
                y += 1
            alto_rack = y - y_inicio
            rectangulos.append((x_inicio, y_inicio, ancho_bloque, alto_rack))

    return rectangulos


# --- construcción ---


def _construir_estructura(
    config: ConfigGeneracion, rng: random.Random
) -> tuple[Warehouse, list[str]]:
    ancho = _calcular_ancho(config)
    patron = _patron_columnas(config)
    assert len(patron) == ancho

    w = Warehouse(ancho, config.alto)
    w.construir_grafo(_celdas_transitables(config, patron))

    # --- 1. Agregar Pasillos Horizontales (AMBOS) ---
    for y in range(config.alto):
        if _es_fila_pasillo_horizontal(y, config):
            w.agregar_pasillo(f"PAS_H_{y}", 0, y, ancho, 1, "AMBOS")

    # --- 2. Agregar Pasillos Verticales (alternando N y S) ---
    y = 0
    while y < config.alto:
        if _es_fila_pasillo_horizontal(y, config):
            y += 1
            continue
        y_inicio = y
        while y < config.alto and not _es_fila_pasillo_horizontal(y, config):
            y += 1
        alto_bloque = y - y_inicio

        x = 0
        v_count = 0
        while x < ancho:
            if patron[x] == "P":
                x_inicio = x
                while x < ancho and patron[x] == "P":
                    x += 1
                ancho_pasillo = x - x_inicio

                # Alternamos N (arriba) y S (abajo) igual que el Anexo A.3
                sentido = "N" if v_count % 2 == 0 else "S"

                w.agregar_pasillo(
                    f"PAS_V_{y_inicio}_{x_inicio}",
                    x_inicio,
                    y_inicio,
                    ancho_pasillo,
                    alto_bloque,
                    sentido,
                )
                v_count += 1
            else:
                x += 1

    # --- 3. Puertas y Zonas de Despacho ---
    # Validar que quepan las zonas con al menos 3 celdas de separación
    ancho_estimado_zona = 7
    espacio_requerido = (config.n_zonas * ancho_estimado_zona) + (
        (config.n_zonas - 1) * 3
    )
    if espacio_requerido > ancho:
        raise ValueError(
            f"No hay espacio para {config.n_zonas} zonas. Máximo permitido para este ancho es {ancho // 10}."
        )

    ancho_zona = min(7, max(3, (ancho // config.n_zonas) - 3))

    for i in range(config.n_zonas):
        paso = ancho // config.n_zonas
        x_centro = i * paso + (paso // 2)
        x1 = max(0, x_centro - ancho_zona // 2)
        x2 = min(ancho - 1, x1 + ancho_zona - 1)
        x_puerta = (x1 + x2) // 2

        w.agregar_puerta(f"PUERTA_{i+1}", x_puerta, 0, "OUTBOUND")
        w.agregar_zona_despacho(
            f"ZONA_{i+1}",
            (x1, 1),
            (x2, 2),
            puerta_id=f"PUERTA_{i+1}",
            peso_max_kg=config.peso_max_zona_kg,
        )

    # --- 4. Racks ---
    rack_ids: list[str] = []
    for i, (rx, ry, rancho, ralto) in enumerate(
        _posiciones_racks(config, patron), start=1
    ):
        # Validación: uno de los lados debe valer 2
        if not (rancho == 2 or ralto == 2):
            raise ValueError(
                f"Rack generado con dimensiones inválidas: "
                f"ancho={rancho}, alto={ralto}"
            )
        rid = f"R{i:03d}"
        w.agregar_rack(rid, rx, ry, rancho, ralto, niveles=config.niveles_por_rack)
        rack_ids.append(rid)

    return w, rack_ids


def _generar_productos(
    config: ConfigGeneracion,
    w: Warehouse,
    rack_ids: list[str],
    rng: random.Random,
) -> list[Producto]:
    productos: list[Producto] = []
    pid = 1
    for rack_id in rack_ids:
        rack = w.racks[rack_id]
        # Todos los slots (x, y, z) disponibles en este rack
        slots: list[tuple[int, int, int]] = [
            (rx, ry, z)
            for rx in range(rack.x, rack.x + rack.ancho)
            for ry in range(rack.y, rack.y + rack.alto)
            for z in range(1, rack.niveles + 1)
        ]
        n_prods = min(config.productos_por_rack, len(slots))
        elegidos = rng.sample(slots, n_prods)

        for px, py, pz in elegidos:
            prod = Producto(
                id=f"P{pid:04d}",
                nombre=f"Producto {pid}",
                rack_id=rack_id,
                x=px,
                y=py,
                z=pz,
                cantidad_disponible=rng.randint(config.stock_min, config.stock_max),
                peso_kg=round(
                    rng.uniform(config.peso_min_kg, config.peso_max_kg), 2
                ),  # sin el 2, rng.uniform() te va a tirar números como 3.1415926535... y te va a ensuciar los JSON de guardado y los logs. Redondear a 2 decimales (centésimas de kilo) es lo estándar para pesos.
            )
            w.agregar_producto(prod)
            productos.append(prod)
            pid += 1
    return productos


def _generar_pedidos(
    config: ConfigGeneracion,
    productos: list[Producto],
    rng: random.Random,
) -> list[Pedido]:
    pedidos: list[Pedido] = []

    # Llevamos un registro del stock disponible para no pasarnos
    stock_disponible = {p.id: p.cantidad_disponible for p in productos}

    for i in range(1, config.n_pedidos + 1):
        prioridad = rng.randint(1, 5)
        pedido = Pedido(id=f"PED{i:03d}", prioridad=prioridad)

        # Solo podemos elegir productos que tengan al menos 1 unidad en stock
        candidatos = [p for p in productos if stock_disponible[p.id] > 0]

        # Si ya no queda stock de nada, cortamos la generación de pedidos
        if not candidatos:
            break

        n_items = rng.randint(1, min(config.max_productos_por_pedido, len(candidatos)))
        elegidos = rng.sample(candidatos, n_items)

        for prod in elegidos:
            # Queremos pedir entre 1 y 3, pero como máximo lo que haya en stock
            max_a_pedir = min(3, stock_disponible[prod.id])
            cantidad = rng.randint(1, max_a_pedir)

            pedido.agregar_item(prod.id, cantidad)
            stock_disponible[prod.id] -= cantidad  # Descontamos el stock virtual

        pedidos.append(pedido)

    return pedidos


# --- API pública ---


def generar_escenario(config: ConfigGeneracion) -> Escenario:
    rng = random.Random(config.seed)

    w, rack_ids = _construir_estructura(config, rng)
    productos = _generar_productos(config, w, rack_ids, rng)
    pedidos = _generar_pedidos(config, productos, rng)

    nombre = (
        f"gen_b{config.n_bloques_racks}"
        f"_a{config.alto}"
        f"_p{len(productos)}"
        f"_o{len(pedidos)}"
    )
    if config.cada_cuantas_filas_pasillo_horizontal > 0:
        nombre += f"_ph{config.cada_cuantas_filas_pasillo_horizontal}"
    if config.seed is not None:
        nombre += f"_s{config.seed}"

    # Crear pickers dinámicamente
    from warehouse.dominio.picker import Picker

    pickers = []
    for i in range(config.n_pickers):
        # Los distribuimos a lo largo del pasillo inferior (y=1)
        x_pos = 1 + (i * 2)
        pickers.append(
            Picker(
                id=f"PK_{i+1:02d}",
                posicion_inicial=(x_pos, 1),
                capacidad_carga_kg=config.picker_capacidad_kg,
            )
        )

    return Escenario(
        nombre=nombre,
        warehouse=w,
        pedidos=pedidos,
        pickers=pickers,
        wave_config=WaveConfig(
            max_pedidos=config.max_pedidos_wave,
            max_productos=config.max_productos_wave,
        ),
        seed=config.seed,
    )
