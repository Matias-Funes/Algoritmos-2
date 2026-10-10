


```text
warehouse-picking/
│
├── data/
│   ├── escenarios/              # archivos de configuración (JSON)
│   │   ├── escenario_chico.json
│   │   ├── escenario_mediano.json
│   │   └── escenario_grande.json
│   └── layouts/                 # layouts opcionales (grillas en texto)
│
├── src/
│   └── warehouse/
│       ├── __init__.py
│       │
│       ├── dominio/             # entidades puras, sin algoritmos
│       │   ├── __init__.py
│       │   ├── posicion.py
│       │   ├── producto.py
│       │   ├── rack.py
│       │   ├── pedido.py
│       │   ├── wave.py
│       │   ├── zona.py
│       │   └── puerta.py
│       │
│       ├── estructuras/         # grafo + TDA auxiliares
│       │   ├── __init__.py
│       │   ├── grafo.py
│       │   └── cola_prioridad.py
│       │
│       ├── warehouse/           # el contenedor principal
│       │   ├── __init__.py
│       │   └── warehouse.py
│       │
│       ├── generacion/          # generación automática de escenarios
│       │   ├── __init__.py
│       │   ├── generador.py
│       │   └── validador.py
│       │
│       ├── algoritmos/          # BFS, DFS, Dijkstra, Prim, Kruskal...
│       │   ├── __init__.py
│       │   ├── busqueda.py
│       │   ├── caminos.py
│       │   └── recorridos.py    # estrategias de recorrido de waves
│       │
│       ├── waves/               # lógica de generación de waves
│       │   ├── __init__.py
│       │   └── generador_waves.py
│       │
│       ├── io/                  # cargar/guardar escenarios
│       │   ├── __init__.py
│       │   ├── cargador_json.py
│       │   └── exportador.py
│       │
│       └── visualizacion/       # UI / render (al final)
│           ├── __init__.py
│           └── render.py
│
├── tests/
│   ├── test_grafo.py
│   ├── test_warehouse.py
│   ├── test_generador.py
│   └── test_recorridos.py
│
├── notebooks/                   # análisis y comparación de algoritmos
│   └── comparacion_estrategias.ipynb
│
├── main.py                      # punto de entrada CLI o demo
├── requirements.txt
└── README.md
```


