# Se usan dos estructuras segun la operacion que domina:
# - Queue enlazada permite encolar y desencolar por los extremos en O(1).
# - La cola de prioridad usa el heap dinamico porque necesita extraer el menor
#   valor repetidamente, en O(log n), como hace Dijkstra.
from .heap import *


# Cola FIFO: `head` es el proximo elemento y `tail` el ultimo agregado.
class Queue:

    class Node:
        def __init__(self, value=None):
            self.value = value
            self.nextNode = None

    def __init__(self):  # funcion que inicializa los elementos de la queue
        self.head = None
        self.tail = None

    def enqueue(self, element):
        """ingresa los elementos a una queue, O(1)"""
        newNode = Queue.Node(element)

        # Mantener ambos extremos evita recorrer la lista para agregar al final.
        if self.head is None:
            self.head = newNode
            self.tail = newNode
        else:
            self.tail.nextNode = newNode
            self.tail = newNode

    def dequeue(self):
        """saca los elementos de la queue, si no tiene nada retorna "None", O(1)"""
        if self.head is None:
            return None

        element = self.head.value
        self.head = self.head.nextNode

        if self.head is None:
            self.tail = None

        return element

    def printQueue(self):
        """hace un print de la queue, O(n)"""
        currentNode = self.head
        while currentNode is not None:
            print(f"[{currentNode.value}]", end="")
            currentNode = currentNode.nextNode
        print()


class minPriorityQueue:
    """Cola de prioridad de minimos (sale primero la MENOR prioridad), pensada
    para Dijkstra: la prioridad es la distancia y el elemento es el nodo.

    Guarda tuplas en un minHeap. Si dos prioridades
    empatan, Python compara los elementos, asi que estos deben ser comparables
    entre si (numeros o strings, como los nodos de un grafo)

    """

    def __init__(self):
        # se crea el heap
        self._heap = []

    def enqueue(self, elemento, prioridad):
        """Agrega un elemento con su prioridad. O(log n)"""
        # Cada entrada es (prioridad, elemento): la raiz del min-heap queda
        # siempre disponible para extraer el siguiente costo mas bajo.
        self._heap.append((prioridad, elemento))
        siftUp(self._heap, len(self._heap) - 1, isMaxHeap=False)

    def dequeue(self):
        """Quita y devuelve (prioridad, elemento) con la menor prioridad. O(log n)"""
        if not self._heap:
            raise IndexError("la cola de prioridad esta vacia")

        menor = self._heap[0]
        ultimo = self._heap.pop()

        if self._heap:
            self._heap[0] = ultimo
            minHeapify(self._heap, len(self._heap), 0)

        return menor

    def seeHead(self):
        """Devuelve (sin quitar) (prioridad, elemento) con la menor prioridad. O(1)"""
        if not self._heap:
            raise IndexError("la cola de prioridad esta vacia")
        return self._heap[0]

    def isEmpty(self):
        return len(self._heap) == 0

    def __len__(self):
        return len(self._heap)
