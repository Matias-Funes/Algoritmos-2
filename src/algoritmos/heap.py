# esta implementado por arrays dinamicos de python en vez de listas enlazadas para mejorar la complejidad temporal

#--------------------------------------------------------------------------------
def heapify(L, size, i, isMaxHeap=True):
    """mantiene la condicion de heap y lo evalua segun la entrada como maxHeap o minHeap,
    O(log n), mejor caso O(1)"""

    target_idx = i

    left = 2 * i + 1
    right = 2 * i + 2

    # Max-Heap cuando isMaxHeap = True (el padre es => que sus hijos)
    if isMaxHeap:

        if left < size and L[left] > L[target_idx]:
            target_idx = left

        if right < size and L[right] > L[target_idx]:
            target_idx = right

    # Min-Heap cuando isMaxHeap = False (el padre es <= que sus hijos)
    else:

        if left < size and L[left] < L[target_idx]:
            target_idx = left

        if right < size and L[right] < L[target_idx]:
            target_idx = right

    # Si alguno de los hijos es mejor que el nodo actual la condicion ya se cumple
    if target_idx != i:

        L[i], L[target_idx] = L[target_idx], L[i]

        heapify(L, size, target_idx, isMaxHeap)

def siftUp(L, i, isMaxHeap=True):
    """Sube el elemento en la posicion i hasta restaurar la condicion de heap,se necesita para insertar
    O(log n), mejor caso O(1)"""

    while i > 0:
        padre = (i - 1) // 2

        if isMaxHeap:
            debe_subir = L[i] > L[padre]
        else:
            debe_subir = L[i] < L[padre]

        if not debe_subir:
            return

        L[i], L[padre] = L[padre], L[i]
        i = padre


# estas 4 funciones se podrian simplificar pero a la hora de
# llamar a las funciones se tendria que especificar en un parametro
# el tipo de heap

def maxHeapify(L, size, i):
    """aplica heapify para maxHeap"""
    heapify(L, size, i, isMaxHeap=True)


def minHeapify(L, size, i):
    """aplica heapify para minHeap"""
    heapify(L, size, i, isMaxHeap=False)


def buildMaxHeap(L):
    # crea un maxHeap
    n = len(L)

    for i in range((n // 2) - 1, -1, -1):
        maxHeapify(L, n, i)


def buildMinHeap(L):
    # crea un minHeap
    n = len(L)

    for i in range((n // 2) - 1, -1, -1):
        minHeapify(L, n, i)

#---------------------------------------------------------------------------


def heapSort(L, ascending=True):
    """ordena el heap segun se requiera que sea acendente o decendiente
    , se tiene que especificar un array y true si es acendiete, false decendiente
    , O(n log n)
    si el array es vacio retorna "None" """
    n = len(L)

    if n <= 1:
        return # retorna None ya que el array no tiene elementos

    # Construir el Heap
    if ascending:
        buildMaxHeap(L)
    else:
        buildMinHeap(L)

    # Ordenar
    for i in range(n - 1, 0, -1):

        # Intercambiar raíz con último elemento
        L[0], L[i] = L[i], L[0]

        # Reorganizar la parte que todavía no está ordenada
        if ascending:
            maxHeapify(L, i, 0)
        else:
            minHeapify(L, i, 0)

