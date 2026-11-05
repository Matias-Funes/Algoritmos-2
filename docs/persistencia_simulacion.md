# Persistencia de escenarios y partidas

## Alcance actual

`src/io/persistence.py` guarda escenarios con el mismo formato que consume
`src/io/scenario_loader.py`. `crear_datos_escenario()` acepta registros crudos
del JSON o modelos de dominio; `guardar_escenario()` crea la carpeta destino y
reemplaza el archivo de forma atómica.

El guardado de escenario es distinto al guardado de una partida. No debe
contener posiciones actuales, asignaciones internas, rutas, stock consumido ni
contadores de simulación. El JSON existente de `data/scenarios/` no cambia.

## Contrato recomendado para una partida reanudable

Una partida guardada debe representar un único estado global, correspondiente
al final de un tick. El archivo debe tener una versión de formato independiente
del formato del escenario y contener, como mínimo:

- Datos del escenario original (o una referencia más una validación de que el
  escenario disponible es el mismo).
- Fase/wave activa y si esa fase ya terminó.
- Posición, carga e items transportados de cada picker.
- Stock actual de cada producto.
- Demanda pendiente global o por picker.
- Tick, distancia, recolecciones, faltantes y descargas.
- Por picker: objetivo actual, tramo dinámico, índice del tramo, estado activo y
  ticks bloqueado.
- Estado acumulado entre fases que mantiene `_SimulationTk`.

No serializar el grafo ni `CacheDistancias`: se reconstruyen desde el warehouse.
Al cargar, validar la versión y los IDs de productos/pickers, reconstruir el
escenario y el grafo, y restaurar el estado antes de actualizar la interfaz.
Una partida guardada debe abrirse pausada para que no avance antes de que el
usuario lo indique.

## Avanzar y retroceder un tick

El historial debe guardar el estado completo anterior a cada llamada que avance
la simulación, incluyendo tanto `Simulation` como `_SimulationTk`. Al retroceder,
se restaura ese estado y se refresca la vista; no basta con mover los pickers,
porque también cambian stock, demanda, métricas, objetivos y posibles fases.

Al cargar una partida, el primer estado del historial debe ser exactamente el
estado persistido. Así, retroceder después de reanudar devuelve al mismo
instante guardado. Los snapshots del historial pueden mantenerse en memoria;
el archivo de partida solo necesita el estado actual.
