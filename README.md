# Warehouse Picking — Simulador de Wave Picking

Simulador de preparación de pedidos en un centro de distribución (warehouse),
con generación de waves, cálculo de recorridos y visualización interactiva.

Proyecto desarrollado para la materia **Algoritmos y Estructuras de Datos II**.
Aplica estructuras y algoritmos vistos en clase: grafos, BFS, Dijkstra, colas
de prioridad, y distintas heurísticas de ruteo.

---

## Tabla de contenidos

- [Descripción general](#descripción-general)
- [Cómo ejecutar](#cómo-ejecutar)
- [Arquitectura](#arquitectura)
- [Modelo del warehouse](#modelo-del-warehouse)
- [Algoritmos implementados](#algoritmos-implementados)
- [Experimentos y resultados](#experimentos-y-resultados)
- [Análisis de complejidad](#análisis-de-complejidad)
- [Respuestas a preguntas del informe](#respuestas-a-preguntas-del-informe)
- [Limitaciones y trabajo futuro](#limitaciones-y-trabajo-futuro)

---

## Descripción general

Una empresa de e-commerce recibe pedidos con productos distribuidos en
distintas ubicaciones del warehouse. Procesar cada pedido individualmente
genera recorridos innecesarios. El sistema implementa **Wave Picking**:
agrupa pedidos en *waves* que se preparan conjuntamente, y calcula el
recorrido óptimo (o heurísticamente bueno) para cada wave.

Componentes principales:

- **Modelado del warehouse** como grafo: pasillos, racks, zonas de despacho
  y puertas.
- **Generación automática de escenarios** parametrizable y reproducible.
- **Generación de waves** con dos estrategias.
- **Cálculo de recorridos** con dos estrategias.
- **Simulación interactiva** con play/pause/step/reset.
- **Análisis experimental** con métricas y gráficos.

---

## Cómo ejecutar

### Requisitos

- Python 3.11 o superior
- Un entorno virtual recomendado (`venv`, `virtualenv`, `conda`)

### Instalación

```bash
git clone <repo>
cd algoritmos_2_warehouse
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

El extra `dev` instala `pytest`, `pandas`, `matplotlib` y `jupyter`.

### Correr tests

```bash
pytest -v
```

Se ejecutan ~129 tests unitarios que cubren:
- Grafo y warehouse
- Dominio (productos, pedidos, waves)
- Cargador y exportador JSON
- Generador de escenarios y validador
- BFS, Dijkstra y cache de distancias
- Estrategias de recorrido
- Estado de simulación

### Generar escenarios y comparar estrategias

```bash
python scripts/comparar_estrategias.py
```

Corre 9 escenarios (3 tamaños × 3 seeds), genera waves y compara las dos
estrategias de recorrido. Guarda resultados en `data/resultados/`:

- `resultados_waves.csv` — una fila por wave × estrategia
- `resultados_resumen.csv` — agregados por escenario × estrategia
- `config_experimento.json` — configuración exacta (reproducibilidad)

### Visualizar una wave

```bash
python scripts/visualizar_wave.py --wave 0 --estrategia vecino_mas_cercano
```

Se abre una ventana tkinter con:
- Warehouse renderizado (pasillos, racks, zona de despacho, puerta).
- Productos pendientes en rojo, recogidos en verde.
- Recorrido completo punteado en gris, ya recorrido en azul.
- Picker como círculo azul.
- Controles: **Play**, **Pause**, **Step**, **Reset**.

Opciones:

```bash
python scripts/visualizar_wave.py --wave 2 --estrategia orden_pedidos --celda 30
```

### Notebook de análisis

```bash
jupyter lab
```

Abrir `notebooks/comparacion_estrategias.ipynb`. Carga los CSV, genera
gráficos comparativos y muestra respuestas numéricas a las preguntas del
informe.

---

## Arquitectura

```
src/warehouse/
├── dominio/         Entidades puras: Posicion, Producto, Rack, Pedido, Wave
├── estructuras/     TDA: Grafo (nodos + aristas)
├── warehouse/       Contenedor principal y Escenario
├── io/              Cargador y exportador JSON
├── generacion/      Generador de escenarios y validador
├── algoritmos/      BFS, Dijkstra, cache de distancias, recorridos
├── waves/           Generador de waves
├── simulacion/      Estado de simulación (play/pause/step)
└── visualizacion/   Render tkinter
```

Separación de responsabilidades:

- **Dominio** no conoce algoritmos.
- **Estructuras** define TDA genéricos (reemplazables por la librería propia
  de Algoritmos II).
- **Algoritmos** opera sobre estructuras y dominio, sin saber de UI.
- **Simulación** es un state machine puro, testeable sin UI.
- **Visualización** solo dibuja; toda la lógica está afuera.

---

## Modelo del warehouse

El warehouse se modela como un **grafo no dirigido con pesos**:

- **Nodos**: celdas transitables del warehouse (pasillos, zona de despacho,
  puertas).
- **Aristas**: conexiones horizontales y verticales entre celdas adyacentes.
  Peso = 1 (puede extenderse a distintos costos).
- **Racks**: NO son nodos del grafo. Son celdas bloqueadas. Cada rack tiene
  un **nodo de picking** adyacente (horizontal) desde donde el operario
  alcanza el producto.
- **Zonas de despacho**: rectángulos que se modelan con un nodo
  representativo (el centro) para el pathfinding.
- **Puertas**: nodos específicos en los bordes, conectados a los pasillos.

### Layout por defecto (generado)

```
y = alto-1  ──────────────────────────────────────
            │ P │ R │ R │ P │ R │ R │ P │ R │ R │ P │
            │ P │ R │ R │ P │ R │ R │ P │ R │ R │ P │
            ...
y = 1       │ P │ R │ R │ P │ R │ R │ P │ R │ R │ P │
y = 0       ──────────────────────────────────────
              ↑                                   ↑
        zona de despacho A                  puerta OUTBOUND
```

Los racks van agrupados en **bloques** de `ancho_bloque_racks` columnas
adyacentes, separados por pasillos de `ancho_pasillo`. Hay pasillos
horizontales arriba y abajo que conectan todas las columnas.

**Invariante clave:** todo nodo de picking es alcanzable desde la zona de
despacho caminando exclusivamente por pasillos. El validador lo verifica con
BFS.

### Justificación del modelo

- Se descartó modelar los racks como nodos caminables porque:
  - No reflejan la realidad física (no se camina dentro de un rack).
  - Duplican la cantidad de nodos y aristas sin agregar información útil.
  - El enunciado pide "recorrido por pasillos existentes".
- El nodo de picking adyacente al rack modela el hecho de que el operario
  se para **al lado** del rack y agarra el producto.

---

## Algoritmos implementados

### Búsqueda en anchura (BFS)

Usado por el validador para verificar que todos los nodos de picking son
alcanzables desde la zona de despacho.

- **Tiempo:** O(V + E)
- **Espacio:** O(V)

### Dijkstra

Calcula distancias mínimas desde un nodo origen a todos los demás, con cola
de prioridad (heap binario).

- **Tiempo:** O((V + E) log V)
- **Espacio:** O(V)

### Cache de distancias

Como el cálculo de recorridos consulta distancias muchas veces entre los
mismos nodos, se cachea el resultado de Dijkstra por origen. La primera
consulta desde un origen corre Dijkstra; las siguientes son O(1).

- **Costo total:** a lo sumo O(k · (V + E) log V), donde k = orígenes
  distintos consultados.

### Generación de waves

Dos estrategias implementadas:

1. **PRIORIDAD:** ordena pedidos por prioridad descendente (desempate por id)
   y los agrupa en waves por capacidad.
2. **PRIORIDAD_Y_CERCANIA:** toma el pedido más prioritario como semilla, y
   luego agrega iterativamente el pedido más cercano geográficamente a los
   ya incluidos, respetando capacidades.

- **Tiempo PRIORIDAD:** O(n log n + n · m), donde n = pedidos, m = waves.
- **Tiempo PRIORIDAD_Y_CERCANIA:** O(n log n + n² · p), donde p = productos
  por pedido (dominado por el cálculo de distancias mínimas).

### Estrategias de recorrido

Dada una wave ya cerrada:

1. **ORDEN_PEDIDOS:** visita las ubicaciones en el orden en que aparecen en
   los pedidos. Simple, determinista, sin heurística.
2. **VECINO_MAS_CERCANO:** greedy. Desde la posición actual, se mueve a la
   parada no visitada más cercana (por distancia de Dijkstra). Termina
   volviendo al despacho.

Ambas empiezan y terminan en el nodo representativo de la zona de despacho.

- **Tiempo ORDEN_PEDIDOS:** O(k) consultas al cache.
- **Tiempo VECINO_MAS_CERCANO:** O(k²) consultas al cache, donde k = paradas.

El cache hace que las consultas sean O(1) tras el primer Dijkstra por origen,
por lo que el costo de ambas estrategias es dominado por la cantidad de
orígenes distintos consultados.

---

## Experimentos y resultados

### Configuración

Tres tamaños de escenario, cada uno con 3 seeds distintas (1, 2, 3):

| Tamaño | Bloques de racks | Alto | Nodos | Racks | Pedidos |
|---|---|---|---|---|---|
| Chico | 2 | 5 | ~23 | 12 | 10 |
| Mediano | 4 | 8 | ~56 | 48 | 30 |
| Grande | 8 | 12 | ~140 | 160 | 100 |

Estrategia de waves: `PRIORIDAD_Y_CERCANIA`.
Estrategias de recorrido comparadas: `ORDEN_PEDIDOS` vs `VECINO_MAS_CERCANO`.

### Resultados

Distancia total promedio por tamaño y estrategia:

| Tamaño | orden_pedidos | vecino_mas_cercano | Mejora |
|---|---|---|---|
| Chico | 93.3 | 72.7 | **22.1%** |
| Mediano | 464.7 | 338.7 | **27.1%** |
| Grande | 3835.3 | 2118.7 | **44.8%** |

**Vecino más cercano ganó en 9 de 9 escenarios.**

### Análisis

1. **La mejora crece con el tamaño.** A mayor cantidad de paradas, más
   arbitrario se vuelve el orden de los pedidos, y más provecho saca una
   heurística que considera la geometría.

2. **Menor varianza.** El boxplot muestra que `vecino_mas_cercano` no solo
   tiene menor mediana; también menor dispersión. Es más predecible.

3. **Sin costo extra en tiempo.** El cache de distancias hace que el costo
   de las O(k²) consultas sea despreciable frente al costo de los Dijkstra
   iniciales. Ambas estrategias tienen tiempos casi idénticos.

4. **Trade-off distancia vs tiempo: inexistente en este experimento.**
   Vecino más cercano domina en ambas dimensiones.

---

## Análisis de complejidad

Para cada algoritmo, complejidad temporal y espacial:

| Algoritmo | Tiempo | Espacio |
|---|---|---|
| BFS | O(V + E) | O(V) |
| Dijkstra (heap) | O((V + E) log V) | O(V) |
| Cache de distancias | O(k · Dijkstra) amortizado | O(k · V) |
| Generación de waves (prioridad) | O(n log n + n · m) | O(n) |
| Generación de waves (cercanía) | O(n log n + n² · p) | O(n) |
| Recorrido (orden pedidos) | O(k) consultas | O(k) |
| Recorrido (vecino más cercano) | O(k²) consultas | O(k) |

Donde V = nodos del grafo, E = aristas, n = pedidos, m = waves, k = paradas
de una wave, p = productos por pedido.

### Comportamiento empírico

Los experimentos confirman:

- **Crecimiento lineal** del tiempo con la cantidad de nodos del grafo
  (ver `grafico_tiempos.png`). Con 140 nodos, el tiempo total de recorrido
  es ~80 ms por escenario.
- **Diferencia despreciable** entre las dos estrategias de recorrido en
  tiempo de ejecución.
- **Diferencia significativa** entre las dos estrategias de recorrido en
  distancia total, con gap creciente por tamaño.

---

## Respuestas a preguntas del informe

### 1. ¿Cómo fue modelado el Warehouse?

Como un grafo no dirigido con pesos unitarios. Los nodos son celdas
transitables (pasillos, zona de despacho, puertas). Los racks son celdas
bloqueadas que **no** son nodos del grafo; cada producto tiene un
`nodo_picking` adyacente desde donde el operario lo alcanza.

### 2. ¿Qué representación de la estructura de datos utilizaron y por qué?

**Lista de adyacencia** (`dict[int, list[Arista]]`). Razones:

- Los grafos de warehouse son **dispersos**: cada nodo tiene a lo sumo 4
  vecinos.
- La lista de adyacencia usa O(V + E) espacio, contra O(V²) de la matriz.
- Iterar vecinos es O(grado), esencial para BFS y Dijkstra.
- Flexibilidad para agregar/quitar nodos sin reasignar memoria.

Se complementa con un `dict[(x, y)] → id` para mapear posiciones a nodos,
necesario para construir el grafo por grilla.

### 3. ¿Qué algoritmos utilizaron?

- **BFS** para validar alcanzabilidad desde la zona de despacho.
- **Dijkstra** para distancias mínimas entre nodos.
- **Cache de distancias** para evitar recalcular Dijkstra entre mismos nodos.
- **Greedy de vecino más cercano** para el recorrido de una wave.
- **Greedy de prioridad + cercanía** para agrupar pedidos en waves.

### 4. ¿Por qué eligieron dichos algoritmos?

- **BFS** es la forma natural de validar alcanzabilidad con complejidad
  óptima O(V + E).
- **Dijkstra** es correcto y eficiente con pesos no negativos (los nuestros
  son positivos). Alternativas como Bellman-Ford o Floyd-Warshall son más
  costosas sin beneficio en este caso.
- **Vecino más cercano** es una heurística conocida, simple, determinista y
  rápida. No es óptima, pero da buenos resultados en la práctica y no usa
  metaheurísticas prohibidas.
- **Prioridad + cercanía** combina la restricción del negocio (priorizar
  pedidos urgentes) con la optimización geográfica.

### 5. ¿Qué ocurre si todos los pasillos tienen el mismo largo?

Los pesos de las aristas son todos iguales a 1. En ese caso:

- **BFS** y **Dijkstra** calculan las mismas distancias (BFS sería más
  eficiente por no usar heap, pero la diferencia es logarítmica).
- El criterio de "vecino más cercano" se reduce a "vecino con menor
  distancia Manhattan dentro de los pasillos".
- La distancia total es proporcional a la cantidad de aristas recorridas.

En este proyecto, todos los pasillos tienen largo unitario. Si en un caso
real hubiera pasillos de distintos largos, bastaría con asignar pesos
distintos a las aristas; el resto del sistema no cambia.

### 6. ¿Cómo cambia el comportamiento cuando aumenta el tamaño del Warehouse?

- **Distancia total:** crece linealmente con la cantidad de pedidos, y el
  gap entre estrategias crece también (22% → 27% → 45%).
- **Tiempo:** crece linealmente con la cantidad de nodos del grafo.
- **Calidad de la heurística:** mejora el desempeño relativo de
  `vecino_mas_cercano` a mayor escala, porque el orden arbitrario de los
  pedidos se vuelve más costoso.

### 7. ¿Cómo determinaron la distancia entre las ubicaciones de una wave?

Con **Dijkstra** desde cada nodo de picking relevante, cacheando los
resultados. La distancia entre dos productos es la distancia mínima entre
sus nodos de picking en el grafo.

### 8. ¿Cómo decidieron qué pedidos pertenecen a una misma wave?

Con la estrategia **PRIORIDAD_Y_CERCANIA**:

1. Se toma el pedido más prioritario como semilla.
2. Se agrega iterativamente el pedido más cercano geográficamente a los ya
   incluidos (distancia mínima entre productos), respetando las capacidades
   `max_pedidos` y `max_productos`.

Prioriza pedidos urgentes y luego agrupa por proximidad.

### 9. ¿Qué estrategia utilizaron para ordenar las ubicaciones de una wave?

Dos:

- **ORDEN_PEDIDOS:** orden en que aparecen los productos en los pedidos.
- **VECINO_MAS_CERCANO:** greedy desde el despacho, eligiendo siempre la
  parada más cercana no visitada.

### 10. ¿Qué diferencias existen entre las estrategias implementadas?

| Aspecto | ORDEN_PEDIDOS | VECINO_MAS_CERCANO |
|---|---|---|
| Criterio | Orden de aparición | Distancia geométrica |
| Complejidad | O(k) consultas | O(k²) consultas |
| Optimalidad | Ninguna | Ninguna (greedy) |
| Determinismo | Determinista | Determinista |
| Distancia típica | Mayor | Menor |
| Tiempo | Similar | Similar |

### 11. ¿Cuál presenta menor distancia recorrida?

`VECINO_MAS_CERCANO` en los 9 escenarios probados, con mejora del 22% al
45%.

### 12. ¿Cuál presenta menor tiempo de ejecución?

Ambas presentan **tiempos casi idénticos** en los experimentos, gracias al
cache de distancias. La diferencia es inferior al 2% en todos los casos.

### 13. ¿Existe una estrategia que sea mejor en todos los escenarios?

En nuestros experimentos, `VECINO_MAS_CERCANO` ganó en los 9 escenarios
probados (3 tamaños × 3 seeds). Sin embargo:

- **No es garantizable en general.** El algoritmo de vecino más cercano es
  greedy y no encuentra el óptimo global.
- **No es 2-aproximado** en general (a diferencia del MST-based tour para
  TSP métrico).
- En escenarios con distribuciones espaciales patológicas podría perder
  contra `ORDEN_PEDIDOS`.

### 14. ¿Qué trade-offs encontraron?

En este experimento: **ninguno significativo.** `VECINO_MAS_CERCANO` gana
en distancia sin pagar tiempo extra, gracias al cache.

En un escenario más grande (k >> cientos de paradas), el O(k²) de las
consultas podría hacerse notar, aunque el cache amortigua buena parte.
Trabajo futuro: medir con k > 1000 paradas.

### 15. ¿Qué modificaciones realizarían para un Warehouse real?

- **Pasillos dirigidos** (sentido único): agregar aristas dirigidas al
  grafo. Impacta en Dijkstra (que ya soporta dirigidos) y en la
  construcción del grafo.
- **Múltiples operarios trabajando simultáneamente** en la misma wave:
  requiere coordinación y reasignación dinámica.
- **Ubicaciones múltiples por producto** (mismo producto en varios racks):
  cambia el modelo de dominio y los algoritmos de asignación.
- **Restricciones de capacidad del picker** (peso, volumen): agregan un
  problema de bin packing.
- **Pasillos con distintos costos** según tráfico: se resuelve con pesos
  distintos en las aristas.
- **Distancias no Manhattan** (pasillos curvos, atajos): el grafo ya lo
  soporta; solo cambia la construcción.
- **Optimización de asignación wave-picker**: problema de scheduling.
- **Persistencia en base de datos** en lugar de JSON.
- **Interfaz web** en lugar de tkinter.

---

## Limitaciones y trabajo futuro

- El vecino más cercano no garantiza óptimo. Podría compararse con
  **Christofides** (2-aproximado para TSP métrico) o con una **búsqueda
  local 2-opt** sobre el resultado greedy.
- El modelo no soporta pasillos dirigidos ni costos variables.
- La simulación es de un solo picker. No hay concurrencia.
- Los experimentos se limitan a 3 tamaños × 3 seeds. Extender con más
  configuraciones daría mayor confianza estadística.
- El tiempo de generación de escenarios grandes puede mejorarse con
  estructuras más eficientes (por ejemplo, índices espaciales).
- Falta interfaz de usuario para seleccionar waves desde la app.

---

## Estructuras de datos y algoritmos usados (referencia)

Alineado con lo visto en clase:

- **Grafo** con lista de adyacencia
- **Hash table** (dict) para productos, pedidos, racks, zonas, puertas
- **Cola de prioridad** (heap) en Dijkstra
- **BFS** para alcanzabilidad
- **Dijkstra** para distancias mínimas
- **Greedy** para vecino más cercano
- **Greedy con prioridad** para generación de waves
- **State machine** para la simulación

Estructuras vistas pero no utilizadas actualmente (potencial uso futuro):

- **AVL Tree / BST**: para ordenar pedidos por prioridad si se necesita
  búsqueda por rango.
- **B-Tree**: para persistencia en disco de grandes volúmenes.
- **Trie**: para autocompletado de nombres de productos en la UI.
- **Prim / Kruskal**: para análisis de conectividad o clustering de
  ubicaciones.

---

## Licencia

Trabajo académico. Uso libre con atribución.


