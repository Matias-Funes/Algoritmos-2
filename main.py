"""Visualización básica de un almacén modelado como un grafo.

Esta primera versión solo construye el mundo y lo dibuja. No incluye
algoritmos de ruteo, pedidos ni simulación del operario.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

import pygame


Point = Tuple[float, float]


class Graph:
    """Grafo no dirigido con coordenadas y lista de adyacencia."""

    def __init__(self) -> None:
        self.coordinates: Dict[str, Point] = {}
        self.adjacency: Dict[str, Dict[str, float]] = {}

    def add_node(self, node_id: str, x: float, y: float) -> None:
        """Agrega o actualiza un nodo transitable."""
        self.coordinates[node_id] = (x, y)
        self.adjacency.setdefault(node_id, {})

    def add_edge(self, first: str, second: str) -> None:
        """Agrega una arista bidireccional con peso euclidiano."""
        if first not in self.coordinates or second not in self.coordinates:
            raise KeyError("Ambos extremos de la arista deben existir en el grafo")

        first_point = self.coordinates[first]
        second_point = self.coordinates[second]
        distance = math.dist(first_point, second_point)
        self.adjacency[first][second] = distance
        self.adjacency[second][first] = distance

    def nodes(self) -> Iterable[Tuple[str, Point]]:
        return self.coordinates.items()

    def edges(self) -> Iterable[Tuple[str, str, float]]:
        """Devuelve cada arista no dirigida una sola vez."""
        seen = set()
        for first, neighbors in self.adjacency.items():
            for second, weight in neighbors.items():
                edge = frozenset((first, second))
                if edge not in seen:
                    seen.add(edge)
                    yield first, second, weight


@dataclass(frozen=True)
class Rack:
    """Rectángulo ocupado por una estantería."""

    rectangle: pygame.Rect


@dataclass
class Warehouse:
    graph: Graph
    racks: List[Rack]
    dispatch_area: pygame.Rect


def build_warehouse(
    width: int = 1200,
    height: int = 720,
    vertical_aisles: int = 6,
    horizontal_rows: int = 4,
) -> Warehouse:
    """Construye pasillos verticales, transversales, racks y despacho."""
    graph = Graph()
    racks: List[Rack] = []

    margin_x = 100
    top = 90
    dispatch_height = 100
    bottom = height - dispatch_height - 35
    aisle_spacing = (width - 2 * margin_x) / (vertical_aisles - 1)
    row_spacing = (bottom - top) / horizontal_rows
    x_positions = [
        margin_x + index * aisle_spacing for index in range(vertical_aisles)
    ]
    y_positions = [top + index * row_spacing for index in range(horizontal_rows + 1)]

    for row, y in enumerate(y_positions):
        for column, x in enumerate(x_positions):
            graph.add_node(f"n{row}_{column}", x, y)

    for row in range(len(y_positions)):
        for column in range(vertical_aisles - 1):
            graph.add_edge(f"n{row}_{column}", f"n{row}_{column + 1}")

    for column in range(vertical_aisles):
        for row in range(len(y_positions) - 1):
            graph.add_edge(f"n{row}_{column}", f"n{row + 1}_{column}")

    rack_width = max(24, int(aisle_spacing * 0.5))
    rack_height = max(22, int(row_spacing * 0.72))
    rack_x_offset = int(aisle_spacing * 0.25)
    for row in range(horizontal_rows):
        rack_y = int((y_positions[row] + y_positions[row + 1]) / 2 - rack_height / 2)
        for column in range(vertical_aisles - 1):
            rack_x = int(x_positions[column] + rack_x_offset)
            racks.append(Rack(pygame.Rect(rack_x, rack_y, rack_width, rack_height)))

    dispatch_area = pygame.Rect(
        margin_x - 40, height - dispatch_height, width - 2 * (margin_x - 40), dispatch_height - 20
    )
    dispatch_y = dispatch_area.top
    for column, x in enumerate(x_positions):
        graph.add_node(f"dispatch_{column}", x, dispatch_y)
        graph.add_edge(f"n{len(y_positions) - 1}_{column}", f"dispatch_{column}")

    return Warehouse(graph, racks, dispatch_area)


BACKGROUND = (245, 247, 250)
AISLE = (67, 105, 140)
NODE = (30, 80, 120)
RACK = (196, 145, 65)
RACK_BORDER = (120, 80, 25)
DISPATCH = (102, 170, 112)
TEXT = (35, 42, 50)


def draw_warehouse(screen: pygame.Surface, warehouse: Warehouse, font: pygame.font.Font) -> None:
    screen.fill(BACKGROUND)

    for first, second, _ in warehouse.graph.edges():
        start = warehouse.graph.coordinates[first]
        end = warehouse.graph.coordinates[second]
        pygame.draw.line(screen, AISLE, start, end, 4)

    for rack in warehouse.racks:
        pygame.draw.rect(screen, RACK, rack.rectangle, border_radius=3)
        pygame.draw.rect(screen, RACK_BORDER, rack.rectangle, width=2, border_radius=3)

    pygame.draw.rect(screen, DISPATCH, warehouse.dispatch_area, border_radius=8)
    pygame.draw.rect(screen, (45, 110, 65), warehouse.dispatch_area, width=3, border_radius=8)
    label = font.render("DESPACHO", True, TEXT)
    screen.blit(label, label.get_rect(center=warehouse.dispatch_area.center))

    for _, (x, y) in warehouse.graph.nodes():
        pygame.draw.circle(screen, NODE, (round(x), round(y)), 7)

    title = font.render("Almacén - grafo de pasillos", True, TEXT)
    screen.blit(title, (24, 20))


def run() -> None:
    pygame.init()
    screen = pygame.display.set_mode((1200, 720))
    pygame.display.set_caption("Grafo base del almacén")
    font = pygame.font.Font(None, 28)
    clock = pygame.time.Clock()
    warehouse = build_warehouse(*screen.get_size())
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                running = False

        draw_warehouse(screen, warehouse, font)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    run()
