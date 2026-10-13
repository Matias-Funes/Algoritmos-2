"""
Módulo linkedlist.py
Implementación del TAD Secuencia usando una lista simplemente enlazada.

Complejidad de las operaciones principales:
    - add:        O(1)
    - append:     O(1)
    - search:     O(n)
    - insert:     O(position)
    - delete:     O(n)
    - length:     O(1) gracias al atributo size
    - access:     O(position)
    - update:     O(position)
    - reverseList: O(n)
    - revert:     O(n)
    - copyLinkedList: O(n)
"""

from typing import Any, Generic, TypeVar

# ============================================================
# Estructuras base
# ============================================================

T = TypeVar("T")


class Node(Generic[T]):
    def __init__(self, value: T | None = None) -> None:
        self.value: T | None = value
        self.nextNode: Node[T] | None = None


class LinkedList(Generic[T]):
    def __init__(self) -> None:
        self.head: Node[T] | None = None
        self.tail: Node[T] | None = None
        self.size: int = 0


# ============================================================
# Operaciones del TAD Secuencia
# ============================================================


def add(L: LinkedList[T], element: T) -> None:
    """
    Agrega un elemento al comienzo de L.

    Complejidad: O(1).

    Args:
        L (LinkedList): Lista sobre la cual agregar el elemento.
        element (Any): Valor del elemento a agregar.

    Returns:
        None
    """
    # node = Node()
    # node.value = element
    node = Node(element)  # esta linea equivale a las dos anteriores
    node.nextNode = L.head
    L.head = node
    if L.tail is None:  # ← si la lista estaba vacía
        L.tail = node
    L.size += 1


def append(L: LinkedList[T], element: T) -> None:
    """
    Agrega un elemento al final de L.

    Complejidad: O(1).

    Args:
        L (LinkedList): Lista sobre la cual agregar.
        element (Any): Valor del elemento a agregar.

    Returns:
        None
    """
    node = Node(element)
    if L.tail is None:  # lista vacía
        L.head = node
        L.tail = node
    else:  # el LSP ya sabe que L.tail es Node aquí
        L.tail.nextNode = node
        L.tail = node
    L.size += 1


def printList(L: LinkedList[T]) -> None:
    """
    Muestra en forma consecutiva los elementos de la lista.

    Complejidad: O(n).

    Args:
        L (LinkedList): Lista a imprimir.

    Returns:
        None
    """
    if L.head is None:
        print("[]")
        return

    node = L.head
    while node is not None:
        if node.nextNode is not None:
            print(node.value, end=" --> ")
        else:
            print(node.value)
        node = node.nextNode


def search(L: LinkedList[T], element: T) -> int | None:
    """
    Busca la primera ocurrencia de un elemento en la lista.

    Complejidad: O(n).

    Args:
        L (LinkedList): Lista donde buscar.
        element (Any): Valor del elemento a buscar.

    Returns:
        int | None: Posición (0-based) de la primera ocurrencia,
                    o None si el elemento no se encuentra.
    """
    node = L.head
    cont = 0
    while node is not None:
        if node.value == element:
            return cont
        cont += 1
        node = node.nextNode

    return None


def insert(L: LinkedList[T], element: T, position: int) -> int | None:
    """
    Inserta un elemento en la posición indicada.

    Complejidad: O(position) — O(1) si position=0.

    Args:
        L (LinkedList): Lista donde insertar.
        element (Any): Valor del elemento a insertar.
        position (int): Posición donde insertar (0-based).

    Returns:
        int | None: La posición donde se insertó, o None si la
                    posición es inválida.
    """
    if position < 0 or position > L.size:
        return None

    if position == 0:
        add(L, element)
        return 0

    node = L.head
    cont = 0
    while node is not None:
        if cont == position - 1:
            newNode = Node(element)
            newNode.nextNode = node.nextNode
            node.nextNode = newNode
            L.size += 1
            return position
        cont += 1
        node = node.nextNode

    return None


def length(L: LinkedList[T]) -> int:
    """
    Devuelve la cantidad de elementos de la lista.

    Complejidad: O(1) gracias al atributo size.

    Args:
        L (LinkedList): Lista a medir.

    Returns:
        int: Número de elementos.
    """
    return L.size


def delete(L: LinkedList[T], element: T) -> int | None:
    """
    Elimina la primera ocurrencia de un elemento.

    Desvincula el nodo de la cadena y decrementa el tamaño.

    Complejidad: O(n).

    Args:
        L (LinkedList): Lista donde eliminar.
        element (Any): Valor del elemento a eliminar.

    Returns:
        int | None: Posición del elemento eliminado, o None si
                    no se encontró.
    """
    if L.head is None:
        return None

    # Caso 1: el elemento está en el head
    if L.head.value == element:
        L.head = L.head.nextNode
        if L.head is None:  # la lista quedó vacía
            L.tail = None
        L.size -= 1
        return 0

    # Caso 2: el elemento está en medio o al final
    node = L.head
    cont = 0
    while node.nextNode is not None:
        if node.nextNode.value == element:
            node.nextNode = node.nextNode.nextNode
            if node.nextNode is None:  # ← borramos el último
                L.tail = node
            L.size -= 1
            return cont + 1
        cont += 1
        node = node.nextNode

    return None  # no se encontró


def access(L: LinkedList[T], position: int) -> Any | None:
    """
    Accede al elemento en la posición indicada.

    Complejidad: O(position).

    Args:
        L (LinkedList): Lista a consultar.
        position (int): Posición (0-based).

    Returns:
        Any | None: Valor del elemento, o None si la posición
                    está fuera de rango.
    """
    if position < 0 or position >= L.size:
        return None

    node = L.head
    cont = 0
    while node is not None:
        if cont == position:
            return node.value
        cont += 1
        node = node.nextNode

    return None


def update(L: LinkedList[T], element: T, position: int) -> int | None:
    """
    Cambia el valor del elemento en la posición indicada.

    Complejidad: O(position).

    Args:
        L (LinkedList): Lista a modificar.
        element (Any): Nuevo valor.
        position (int): Posición (0-based).

    Returns:
        int | None: La posición donde se actualizó, o None si la
                    posición está fuera de rango.
    """
    if position < 0 or position >= L.size:
        return None

    node = L.head
    cont = 0
    while node is not None:
        if cont == position:
            node.value = element
            return position
        cont += 1
        node = node.nextNode

    return None


def revert(L: LinkedList[T]) -> LinkedList[T] | None:
    """
    Devuelve una nueva lista con los elementos en orden invertido.

    No modifica la lista original.

    Complejidad: O(n).

    Args:
        L (LinkedList): Lista a invertir.

    Returns:
        LinkedList | None: Nueva lista invertida, o None si L está vacía.
    """
    if L.head is None:
        return None

    reverted_list = LinkedList()
    node = L.head
    while node is not None:
        add(reverted_list, node.value)
        node = node.nextNode
    return reverted_list


def reverseList(L: LinkedList[T]) -> None:
    """
    Invierte el orden de la lista in-place (modifica la original).

    Complejidad: O(n).

    Args:
        L (LinkedList): Lista a invertir.

    Returns:
        None
    """
    prev = None
    current = L.head
    while current is not None:
        siguiente = current.nextNode  # ← renombrado para no pisar builtin 'next'
        current.nextNode = prev
        prev = current
        current = siguiente
    L.head = prev


def copyLinkedList(L: LinkedList[T]) -> LinkedList[T] | None:
    """
    Devuelve una copia de la lista de entrada, preservando el orden.

    Complejidad: O(n).

    Args:
        L (LinkedList): Lista a copiar.

    Returns:
        LinkedList | None: Nueva lista con los mismos elementos en el
                           mismo orden, o None si L está vacía.
    """
    if L.head is None:
        return None

    copy_list = LinkedList()
    # Insertamos al frente y luego invertimos para preservar el orden.
    node = L.head
    while node is not None:
        add(copy_list, node.value)
        node = node.nextNode

    reverseList(copy_list)
    return copy_list


def to_python_list(L: LinkedList[T]) -> list[T]:
    """
    Convierte una LinkedList a una lista de Python.

    Útil para interoperar con código que no usa el TAD.

    Complejidad: O(n).

    Args:
        L (LinkedList): Lista a convertir.

    Returns:
        list: Lista de Python con los mismos elementos, en el mismo orden.
    """
    result: list[T] = []
    c = L.head
    while c is not None:
        result.append(c.value)
        c = c.nextNode
    return result
