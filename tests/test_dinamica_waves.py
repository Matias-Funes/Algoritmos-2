import pytest

from warehouse.dominio.pedido import Pedido
from warehouse.dominio.picker import Picker
from warehouse.dominio.producto import Producto
from warehouse.dominio.wave import Wave
from warehouse.simulacion.dinamica import SimulacionDinamica
from warehouse.warehouse.warehouse import Warehouse


def _setup(n_waves=2, tareas_por_wave=2, n_pickers=2, prios=None):
    """Warehouse 15x3 con 4 racks, N waves con M tareas cada una."""
    w = Warehouse(15, 3)
    rack_cells = set()
    for rx in (2, 5, 8, 11):
        rack_cells.add((rx, 1))
        rack_cells.add((rx + 1, 1))
    transitables = {(x, y) for x in range(15) for y in range(3)} - rack_cells
    w.construir_grafo(transitables)
    w.agregar_puerta("D1", 0, 0, "OUTBOUND")
    w.agregar_zona_despacho("A", (1, 0), (3, 0), puerta_id="D1", peso_max_kg=500.0)

    for i, rx in enumerate((2, 5, 8, 11)):
        w.agregar_rack(f"R{i+1}", rx, 1, 2, 1)
        w.agregar_producto(
            Producto(
                id=f"PA{i+1}",
                nombre=f"A{i+1}",
                rack_id=f"R{i+1}",
                x=rx,
                y=1,
                z=1,
                cantidad_disponible=10,
                peso_kg=1.0,
            )
        )

    waves = []
    for wi in range(n_waves):
        prio = prios[wi] if prios else 3
        wave = Wave(id=f"W{wi+1}", max_pedidos=10, max_productos=100)
        p = Pedido(id=f"P{wi+1}", prioridad=prio)
        for t in range(tareas_por_wave):
            prod_idx = (wi * tareas_por_wave + t) % 4 + 1
            p.agregar_item(f"PA{prod_idx}", 1)
        wave.agregar_pedido(p)
        wave.cerrar()
        waves.append(wave)

    pickers = [
        Picker(id=f"PK{i+1:02d}", posicion_inicial=(0, 2), capacidad_carga_kg=50.0)
        for i in range(n_pickers)
    ]
    return w, waves, pickers


def _correr(sim: SimulacionDinamica, max_pasos=1000) -> int:
    pasos = 0
    while not sim.completada and pasos < max_pasos:
        sim.avanzar()
        pasos += 1
    return pasos


# ---------- binding estricto ----------


def test_picker_no_cambia_de_wave_mientras_haya_tareas():
    """Un picker bound a W no suelta W hasta no poder reclamar nada más."""
    w, waves, pickers = _setup(n_waves=1, tareas_por_wave=2, n_pickers=1)
    sim = SimulacionDinamica.desde_waves(waves, pickers, w)
    pk = next(iter(sim.pickers.values()))

    while pk.fase != "TERMINADO" and sim.paso_actual < 500:
        if pk.wave_actual is not None:
            assert pk.wave_actual == "W1"
        sim.avanzar()

    assert pk.fase == "TERMINADO"
    assert "W1" in sim.waves_completadas


# ---------- pull de siguiente wave ----------


def test_picker_libre_agarra_siguiente_wave():
    """Con 3 waves y 2 pickers, al terminar su wave cada uno toma la próxima."""
    w, waves, pickers = _setup(n_waves=3, tareas_por_wave=2, n_pickers=2)
    sim = SimulacionDinamica.desde_waves(waves, pickers, w)
    _correr(sim)

    assert len(sim.waves_completadas) == 3
    # Cada wave fue tocada por al menos 1 picker y se completó
    for w_id in ("W1", "W2", "W3"):
        assert w_id in sim.waves_completadas
        assert sim.distancia_por_wave[w_id] > 0


# ---------- cap dinámico ----------


def test_cap_dinamico_wave_chica():
    """Wave de 1 tarea → cap=1, solo 1 picker se le asigna aunque haya 3 libres."""
    w, waves, pickers = _setup(n_waves=1, tareas_por_wave=1, n_pickers=3)
    sim = SimulacionDinamica.desde_waves(waves, pickers, w)

    # Primer tick: solo 1 picker bound a W1 (cap = ceil(1/5) = 1)
    sim.avanzar()
    en_w1 = sum(1 for ep in sim.pickers.values() if ep.wave_actual == "W1")
    assert en_w1 == 1


# ---------- join a wave en curso ----------


def test_join_a_wave_en_curso():
    """Wave con 6 tareas (cap=2) — 2 pickers pueden estar en ella a la vez."""
    w, waves, pickers = _setup(n_waves=1, tareas_por_wave=6, n_pickers=2)
    # Ajustamos items_por_picker para que el cap sea 2
    sim = SimulacionDinamica.desde_waves(waves, pickers, w)
    sim.items_por_picker = 3  # ceil(6/3) = 2

    sim.avanzar()
    en_w1 = sum(1 for ep in sim.pickers.values() if ep.wave_actual == "W1")
    assert en_w1 == 2


# ---------- distancia por wave ----------


def test_distancia_por_wave_acumula():
    """Al final, la suma de distancia_por_wave <= distancia_total.

    La diferencia son movimientos de pickers ociosos (sin wave asignada),
    por ejemplo cuando se apartan para no bloquear a un picker activo.
    Esos movimientos cuentan en `distancia_total` pero no en ninguna wave.
    """
    w, waves, pickers = _setup(n_waves=3, tareas_por_wave=2, n_pickers=2)
    sim = SimulacionDinamica.desde_waves(waves, pickers, w)
    _correr(sim)

    suma = sum(sim.distancia_por_wave.values())
    assert suma <= sim.distancia_total
    for w_id in ("W1", "W2", "W3"):
        assert sim.distancia_por_wave[w_id] > 0


# ---------- completada ----------


def test_waves_completadas_todas_al_final():
    w, waves, pickers = _setup(n_waves=3, tareas_por_wave=2, n_pickers=2)
    sim = SimulacionDinamica.desde_waves(waves, pickers, w)
    _correr(sim)

    assert sim.completada
    assert set(sim.waves_completadas) == {"W1", "W2", "W3"}
    assert not sim.waves_pendientes
    assert not sim.waves_activas


# ---------- migrados de test_multi_picker.py (deprecado) ----------


def test_dos_pickers_completan_waves_distintas_sin_colisiones():
    """Migrado de test_multi_picker.py::test_multi_picker_avanza_sin_colisiones.

    Con 2 pickers y 2 waves con 1 tarea cada una, ambos pickers terminan
    en TERMINADO y la unión de productos_recogidos cubre los productos
    de ambas waves.
    """
    w, waves, pickers = _setup(n_waves=2, tareas_por_wave=1, n_pickers=2)
    sim = SimulacionDinamica.desde_waves(waves, pickers, w)
    _correr(sim, max_pasos=1000)

    assert sim.completada

    todos: set[str] = set()
    for ep in sim.pickers.values():
        assert ep.fase == "TERMINADO", f"Picker {ep.picker.id} en fase {ep.fase}"
        todos.update(ep.productos_recogidos)

    # PA1 sale de W1, PA2 sale de W2 (ver _setup)
    assert todos == {"PA1", "PA2"}


def test_invariante_no_hay_dos_pickers_en_la_misma_celda():
    """Migrado de test_multi_picker.py::test_multi_picker_resuelve_colision_swap.

    Verifica el invariante de §3.6 del enunciado: en cada paso, no puede
    haber dos pickers en la misma celda.

    Nota: el test original validaba que ambos pickers quedaran bloqueados
    para siempre en un swap de celdas (era una limitación conocida del
    modelo viejo). Acá lo reformulamos como invariante de corrección:
    "sin colisiones en toda la simulación", que es lo que el enunciado
    realmente exige.
    """
    w, waves, pickers = _setup(n_waves=3, tareas_por_wave=2, n_pickers=2)
    # El _setup pone a todos en (0, 2). Distintas posiciones iniciales
    # para que el estado inicial no viole el invariante por construcción.
    pickers[0].posicion_inicial = (0, 2)
    pickers[1].posicion_inicial = (0, 0)

    sim = SimulacionDinamica.desde_waves(waves, pickers, w)

    for _ in range(1000):
        activos = [
            ep.nodo_actual for ep in sim.pickers.values() if ep.fase != "TERMINADO"
        ]
        assert len(activos) == len(set(activos)), f"Colisión detectada: {activos}"
        if sim.completada:
            break
        sim.avanzar()

    assert sim.completada
