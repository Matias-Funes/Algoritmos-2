
import csv 
import json 
from pathlib import Path 
from time import perf_counter 

from src.algorithms.pathfinding import CacheDistancias, estrategia_A, estrategia_B 
from src.algorithms.wave_manager import generar_waves 
from src.core.graph_builder import construir_grafo 
from src.core.inventory import GestorInventario, Producto 
from src.core.order import PENDIENTE, Orden 
from src.core.warehouse import Pasillo, Puerta, Rack, Warehouse, ZonaDespacho 

RAIZ = Path(__file__).resolve().parents[2] 
DIR_ESCENARIOS = RAIZ / "data" / "scenarios" 
ARCHIVO_CSV = RAIZ / "data" / "results" / "experimentos.csv" 
COLUMNAS = ["Escenario", "Estrategia", "Tiempo_ms", "Distancia", "Nodos_Visitados"] 

REPETICIONES = 5 # se toma el mejor tiempo de N corridas 

ESTRATEGIAS = {"A": estrategia_A, "B": estrategia_B} 


# ================================================================= 
# 1. Carga de escenarios (JSON) 
# ================================================================= 
def construir_warehouse(datos): 
    """Arma el Warehouse a partir de la seccion "warehouse" del JSON. 
    O(ancho * largo).""" 
    dim = datos["dimensiones"] 
    wh = Warehouse(dim["ancho_x"], dim["largo_y"]) 

    for p in datos["pasillos"]: 
        u = p["ubicacion"] 
        wh.add_pasillo(Pasillo(p["id"], u["x"], u["y"], p["ancho"], p["alto"], p["sentido"])) 
    for r in datos["racks"]: 
        u = r["ubicacion"] 
        wh.add_rack(Rack(r["id"], u["x"], u["y"], r["ancho"], r["alto"])) 
    for p in datos["puertas"]: 
        u = p["ubicacion"] 
        wh.add_puerta(Puerta(p["id"], p["tipo"], u["x"], u["y"])) 
    for z in datos["zonas_despacho"]: 
        u = z["ubicacion"] 
        wh.add_zona_despacho(ZonaDespacho( 
            z["id"], z["puerta_id"], u["x"], u["y"], z["ancho"], z["alto"], z["peso_max_kg"] 
        )) 

    wh.rellenar_pasillos_implicitos() 
    return wh 


def cargar_escenario(ruta): 
    """Lee un JSON de escenario y devuelve un dict con: warehouse, 
    inventario, pedidos y config (limites de cada wave).""" 
    with open(ruta, encoding="utf-8") as f: 
        datos = json.load(f) 

    inv = GestorInventario() 
    for p in datos["productos"]: 
        u = p["ubicacion"] 
        inv.agregar_producto(Producto( 
            p["id"], p["nombre"], p["rack_id"], (u["x"], u["y"], u["z"]), 
            p["cantidad_disponible"], p["peso_kg"], 
        )) 

    pedidos = [ 
        Orden(p["id"], p["prioridad"], 
            [(i["producto_id"], i["cantidad"]) for i in p["items"]], 
            p.get("estado", PENDIENTE)) 
        for p in datos["pedidos"] 
    ] 

    cfg = datos["configuracion"] 
    peso_max = cfg.get("wave_peso_max_kg", 
        max(pk["capacidad_carga_kg"] for pk in datos["pickers"])) 
    config = { 
        "max_pedidos": cfg["wave_max_pedidos"], 
        "max_productos": cfg["wave_max_productos"], 
        "peso_max_kg": peso_max, 
    } 
    return { 
        "warehouse": construir_warehouse(datos["warehouse"]), 
        "inventario": inv, 
        "pedidos": pedidos, 
        "config": config, 
    } 


def nombre_escenario(ruta): 
    """'escenario_grande.json' -> 'grande'; 'generado.json' -> 'generado'.""" 
    nombre = Path(ruta).stem 
    prefijo = "escenario_" 
    return nombre[len(prefijo):] if nombre.startswith(prefijo) else nombre 


def listar_escenarios(directorio=DIR_ESCENARIOS): 
    """Rutas de los .json del directorio, de menor a mayor cantidad de pedidos.""" 
    def cantidad_pedidos(ruta): 
        with open(ruta, encoding="utf-8") as f: 
            return len(json.load(f)["pedidos"]) 
    return sorted(Path(directorio).glob("*.json"), 
        key=lambda r: (cantidad_pedidos(r), r.name)) 


# ================================================================= 
# 2. Medicion 
# ================================================================= 
class CacheConConteo(CacheDistancias): 
    """CacheDistancias que ademas cuenta los nodos alcanzados por cada 
    Dijkstra que corre (no cambia el resultado).""" 

    def __init__(self, grafo): 
        super().__init__(grafo) 
        self.nodos_visitados = 0 

    def _asegurar_origen(self, origen): 
        if not self._cache.contieneHT(origen): 
            super()._asegurar_origen(origen) 
            self.nodos_visitados += len(self._cache.buscarHT(origen)) 


def longitud_camino(grafo, camino): 
    """Suma de los pesos de las aristas del camino (lista de celdas).""" 
    return sum(grafo.get_neighbors(u)[v] for u, v in zip(camino, camino[1:])) 


def correr_escenario(nombre, escenario, repeticiones=REPETICIONES): 
    """Arma las waves del escenario y corre cada estrategia sobre todas 
    las waves. Devuelve (filas, waves): una fila (dict) por estrategia.""" 
    wh = escenario["warehouse"] 
    inv = escenario["inventario"] 
    grafo = construir_grafo(wh) 
    waves = generar_waves(escenario["pedidos"], inv, grafo, escenario["config"]) 

    filas = [] 
    for etiqueta, estrategia in ESTRATEGIAS.items(): 
        mejor_ms = float("inf") 
        for _ in range(repeticiones): 
            distancia = nodos = 0 
            inicio = perf_counter() 
            for wave in waves: 
                cache = CacheConConteo(grafo) 
                camino = estrategia(grafo, wave, wh, inv, cache) 
                distancia += longitud_camino(grafo, camino) 
                nodos += cache.nodos_visitados 
            mejor_ms = min(mejor_ms, (perf_counter() - inicio) * 1000) 

        distancia = round(distancia, 3) 
        if distancia == int(distancia): 
            distancia = int(distancia) 
        filas.append({ 
            "Escenario": nombre, 
            "Estrategia": etiqueta, 
            "Tiempo_ms": round(mejor_ms, 3), 
            "Distancia": distancia, 
            "Nodos_Visitados": nodos, 
        }) 
    return filas, waves 


def escribir_csv(filas, ruta=ARCHIVO_CSV): 
    """Escribe el CSV; crea la carpeta (data/results) si no existe.""" 
    ruta = Path(ruta) 
    ruta.parent.mkdir(parents=True, exist_ok=True) 
    with open(ruta, "w", newline="", encoding="utf-8") as f: 
        escritor = csv.DictWriter(f, fieldnames=COLUMNAS) 
        escritor.writeheader() 
        escritor.writerows(filas) 
    return ruta 


def main(directorio=DIR_ESCENARIOS, salida=ARCHIVO_CSV): 
    rutas = listar_escenarios(directorio) 
    if not rutas: 
        raise SystemExit(f"No hay escenarios (.json) en {directorio}") 

    filas = [] 
    for ruta in rutas: 
        nombre = nombre_escenario(ruta) 
        escenario = cargar_escenario(ruta) 
        pedidos = escenario["pedidos"] 
        print(f"Escenario {nombre}: {len(pedidos)} pedidos, " 
              f"{len(escenario['inventario'])} productos, {escenario['config']}") 

        nuevas, waves = correr_escenario(nombre, escenario) 
        asignados = sum(len(w) for w in waves) 
        print(f"  {len(waves)} waves, {asignados}/{len(pedidos)} pedidos asignados") 
        filas.extend(nuevas) 

    ruta_csv = escribir_csv(filas, salida) 
    print(f"\nResultados guardados en {ruta_csv}\n") 
    print("%-10s %-10s %10s %10s %16s" % tuple(COLUMNAS)) 
    for f in filas: 
        print("%-10s %-10s %10.3f %10s %16d" % tuple(f[c] for c in COLUMNAS)) 


if __name__ == "__main__": 
    main()