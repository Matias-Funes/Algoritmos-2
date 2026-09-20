# Visualización base del almacén

Este proyecto contiene el primer paso del proyecto semestral: un almacén
representado por un grafo no dirigido con lista de adyacencia. El programa
dibuja los pasillos, nodos transitables, racks y la zona de despacho usando
Pygame.

## Requisitos

- Python 3.10 o superior
- Pygame

Instalación de la dependencia:

```bash
python -m pip install pygame
```

## Ejecución

Desde la carpeta del proyecto:

```bash
python main.py
```

La ventana se puede cerrar con el botón de cierre o presionando `Esc`.

La clase `Graph` y la función `build_warehouse` contienen la lógica del mundo.
`draw_warehouse` y `run` se ocupan exclusivamente de la visualización y del
bucle de Pygame. Esta versión no incluye todavía ruteo, pedidos ni simulación
del operario.