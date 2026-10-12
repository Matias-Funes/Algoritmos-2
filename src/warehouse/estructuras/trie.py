"""
Módulo trie.py
Implementación del TAD Trie usando LinkedList como contenedor de hijos.

Complejidad de las operaciones principales (m = longitud de la palabra,
|Σ| = tamaño del alfabeto):
    - insert:  O(m · |Σ|)   (O(m) en caso promedio)
    - search:  O(m · |Σ|)   (O(m) en caso promedio)
    - delete:  O(m · |Σ|)
    - startsWith:  O(|prefix| · |Σ|)
    - autocomplete:O(|prefix| · |Σ| + N)
"""

from warehouse.estructuras.linkedlist import LinkedList, append
from warehouse.estructuras.linkedlist import delete as ll_delete
from warehouse.estructuras.linkedlist import insert as ll_insert

# ============================================================
# Estructura base
# ============================================================


class TrieNode:
    """
    Nodo del Trie.

    Atributos:
        key (Str | None): carácter almacenado (None sólo en la raíz).
        isEndOfWord (bool): indicador de fin de palabra.
        children (LinkedList): lista de TrieNode hijos.
    """

    def __init__(self, key: str | None = None) -> None:
        self.key: str | None = key
        self.isEndOfWord: bool = False
        self.children: LinkedList["TrieNode"] = LinkedList()

    def __repr__(self) -> str:
        """Representación para debug: inequívoca y reconstruible."""
        mark = "*" if self.isEndOfWord else ""
        return f"TrieNode({self.key!r}{mark})"

    def __str__(self) -> str:
        """Representación legible para el usuario."""
        return str(self.key) if self.key is not None else "root"

    def __eq__(self, other: object) -> bool:
        """
        Igualdad por clave y marca de fin de palabra.

        Nota: dos nodos en ramas distintas del Trie con la misma letra
        serán 'iguales' según este criterio. Eso es intencional: la
        comparación es a nivel de 'qué letra represento', no de
        'dónde estoy'. Para `_find_child` esto es seguro porque
        comparamos hermanos (hijos del mismo padre), donde no puede
        haber claves duplicadas.
        """
        if not isinstance(other, TrieNode):
            return NotImplemented
        return self.key == other.key and self.isEndOfWord == other.isEndOfWord


class Trie:
    """
    Árbol Trie. La raíz es un nodo sin clave.
    """

    def __init__(self) -> None:
        self.root: TrieNode = TrieNode(None)
        self.size: int = 0  # cantidad de palabras distintas almacenadas


# ============================================================
# Helpers internos
# ============================================================


def _find_child(node: TrieNode, key: str) -> TrieNode | None:
    """
    Busca un hijo de `node` cuya clave sea `key`.

    Recorre la LinkedList de hijos linealmente (no podemos usar
    `search` del TAD porque necesitamos el nodo, no la posición).

    Complejidad: O(|Σ|) en el peor caso, O(1) en promedio.
    """
    c = node.children.head
    while c is not None:
        if c.value is not None and c.value.key is not None:
            if c.value.key == key:
                return c.value
            if c.value.key > key:
                return None  # early exit: ya pasamos el punto
        c = c.nextNode
    return None


# ============================================================
# Operaciones del TAD Trie
# ============================================================


def insert(trie: Trie, word: str) -> None:
    """
    Inserta una palabra en el Trie.

    Si la palabra ya existía, no hace nada (no duplica).

    Complejidad: O(m · |Σ|), donde m = len(word).

    Args:
        trie (Trie): Trie donde insertar.
        word (str): Palabra a insertar.

    Returns:
        None
    """
    word = word.lower()  # ← normaliza
    node = trie.root
    for char in word:
        child = _find_child(node, char)
        if child is None:
            child = TrieNode(char)
            _insert_child_sorted(node, child)
        node = child

    if not node.isEndOfWord:
        node.isEndOfWord = True
        trie.size += 1


def _insert_child_sorted(node: TrieNode, child: TrieNode) -> None:
    """
    Inserta `child` en `node.children` manteniendo el orden
    alfabético por `key`.

    Estrategia: recorre la lista hasta encontrar el primer hijo
    cuya `key` sea mayor que la del nuevo, e inserta ANTES.
    Si ninguno es mayor, va al final.

    Complejidad: O(|Σ|) en el peor caso, O(1) si va al principio
    (el TAD `insert` con position=0 usa `add`, que es O(1)).
    """
    c = node.children.head
    pos = 0
    while c is not None:
        if c.value is not None and child.key is not None:
            # Si la key existente es mayor, insertamos acá.
            if c.value.key is not None and c.value.key > child.key:
                ll_insert(node.children, child, pos)
                return
        pos += 1
        c = c.nextNode

    # Si llegamos al final, el nuevo es mayor que todos.
    append(node.children, child)


def search(trie: Trie, word: str) -> bool:
    """
    Verifica si `word` está almacenada como palabra completa en el Trie.

    Complejidad: O(m · |Σ|).

    Args:
        trie (Trie): Trie donde buscar.
        word (str): Palabra a buscar.

    Returns:
        bool: True si la palabra existe (con marca de fin de palabra).
    """
    word = word.lower()
    node = trie.root
    for char in word:
        child = _find_child(node, char)
        if child is None:
            return False
        node = child
    return node.isEndOfWord


def startsWith(trie: Trie, prefix: str) -> bool:
    """
    Verifica si existe al menos una palabra que comience con `prefix`.

    Complejidad: O(|prefix| · |Σ|).
    """
    prefix = prefix.lower()
    node = trie.root
    for char in prefix:
        child = _find_child(node, char)
        if child is None:
            return False
        node = child
    return True


# ---------- delete ----------


def _delete_helper(node: TrieNode, word: str, index: int) -> bool:
    """
    Función recursiva auxiliar para `delete`.

    Devuelve True si `node` debe ser eliminado del padre
    (es decir: quedó sin hijos y no es fin de palabra).
    """
    # Caso base: llegamos al final de la palabra
    if index == len(word):
        if not node.isEndOfWord:
            return False  # la palabra no existía
        node.isEndOfWord = False
        # Si no tiene hijos, este nodo se puede eliminar
        return node.children.size == 0

    # Buscar el hijo correspondiente al carácter actual
    char = word[index]
    child = _find_child(node, char)
    if child is None:
        return False  # caso 1: no está en el trie

    should_delete = _delete_helper(child, word, index + 1)

    if should_delete:
        ll_delete(node.children, child)
        # Si este nodo no es fin de palabra y se quedó sin hijos,
        # también puede eliminarse en cascada
        return (not node.isEndOfWord) and node.children.size == 0

    return False


def delete(trie: Trie, word: str) -> bool:
    """
    Elimina una palabra del Trie.

    Contempla los 4 casos clásicos:
        1. La palabra no está           -> no se modifica nada.
        2. Palabra única                -> se borran todos sus nodos.
        3. Palabra prefijo de otra      -> sólo se desmarca fin de palabra.
        4. Palabra que contiene a otra  -> se borran nodos hasta la
                                           primera hoja "compartida".

    Complejidad: O(m · |Σ|).

    Args:
        trie (Trie): Trie donde eliminar.
        word (str): Palabra a eliminar.

    Returns:
        bool: True si se eliminó, False si no existía.
    """
    if not search(trie, word):  # caso 1
        return False

    _delete_helper(trie.root, word, 0)
    trie.size -= 1
    return True


# ============================================================
# Utilidades de visualización / depuración
# ============================================================


def get_all_words(trie: Trie) -> LinkedList[str]:
    """
    Devuelve todas las palabras almacenadas (recorrido preorden).

    Complejidad: O(N), donde N = cantidad total de nodos.

    Returns:
        LinkedList[str]: Lista con todas las palabras del Trie.
                         Vacía si el Trie no tiene palabras.
    """
    result: LinkedList[str] = LinkedList()
    _collect(trie.root, "", result)
    return result


def _collect(node: TrieNode, current: str, out: LinkedList[str]) -> None:
    """
    DFS preorder que acumula en `out` las palabras terminadas
    en el subárbol de `node`. `current` es el prefijo acumulado.

    Complejidad: O(N), N = nodos del subárbol.
    """
    if node.isEndOfWord:
        append(out, current)
    c = node.children.head
    while c is not None:
        if c.value is not None:
            _collect(c.value, current + str(c.value.key), out)
        c = c.nextNode


# ============================================================
# Autocompletado
# ============================================================


def _go_to_prefix(trie: Trie, prefix: str) -> TrieNode | None:
    """
    Navega desde la raíz hasta el nodo que representa `prefix`.

    Complejidad: O(|prefix| · |Σ|).

    Returns:
        TrieNode | None: El nodo del último carácter del prefijo,
                         o None si el prefijo no existe.
    """
    prefix = prefix.lower()
    node = trie.root
    for char in prefix:
        child = _find_child(node, char)
        if child is None:
            return None
        node = child
    return node


def autocomplete(trie: Trie, prefix: str) -> LinkedList[str]:
    """
    Devuelve todas las palabras almacenadas que comienzan con `prefix`.

    El prefijo en sí mismo también cuenta si está marcado como
    fin de palabra (ej: insertaste "ho" y "hola"; autocomplete("ho")
    devuelve ambas).

    Complejidad: O(|prefix| · |Σ| + N), N = nodos del subárbol.

    Args:
        trie (Trie): Trie a consultar.
        prefix (str): Prefijo a completar.

    Returns:
        LinkedList[str]: Palabras que empiezan con `prefix`.
                         Lista vacía si no hay ninguna.
    """
    prefix = prefix.lower()
    start = _go_to_prefix(trie, prefix)
    if start is None:
        return LinkedList()

    results: LinkedList[str] = LinkedList()
    _collect(start, prefix, results)
    return results


def autocomplete_top_k(trie: Trie, prefix: str, k: int) -> LinkedList[str]:
    """
    Igual que `autocomplete` pero corta al alcanzar k resultados.

    Útil para UIs donde no querés materializar miles de coincidencias.

    Complejidad: O(|prefix| · |Σ| + k · m).

    Args:
        trie (Trie): Trie a consultar.
        prefix (str): Prefijo a completar.
        k (int): Cantidad máxima de resultados.

    Returns:
        LinkedList[str]: Hasta k palabras que empiezan con `prefix`.
    """
    if k <= 0:
        return LinkedList()

    prefix = prefix.lower()
    start = _go_to_prefix(trie, prefix)
    if start is None:
        return LinkedList()

    results: LinkedList[str] = LinkedList()
    _collect_limited(start, prefix, results, k)
    return results


def _collect_limited(
    node: TrieNode,
    current: str,
    out: LinkedList[str],
    k: int,
) -> bool:
    """
    DFS que corta apenas `out` alcanza k elementos.

    Returns:
        bool: True si hay que detener el recorrido.
    """
    if node.isEndOfWord:
        append(out, current)
        if out.size >= k:
            return True

    c = node.children.head
    while c is not None:
        if c.value is not None:
            if _collect_limited(c.value, current + str(c.value.key), out, k):
                return True
        c = c.nextNode
    return False


def count_with_prefix(trie: Trie, prefix: str) -> int:
    """
    Cuenta cuántas palabras comienzan con `prefix` sin materializarlas.

    Complejidad: O(|prefix| · |Σ| + N).

    Returns:
        int: Cantidad de coincidencias.
    """
    prefix = prefix.lower()
    start = _go_to_prefix(trie, prefix)
    if start is None:
        return 0
    return _count_words(start)


def _count_words(node: TrieNode) -> int:
    """Cuenta palabras en el subárbol de `node`. O(N)."""
    total = 1 if node.isEndOfWord else 0
    c = node.children.head
    while c is not None:
        if c.value is not None:
            total += _count_words(c.value)
        c = c.nextNode
    return total


# ============================================================
# Radix Sort
# ============================================================


def radix_sort(words: list[str]) -> LinkedList[str]:
    """
    Ordena una lista de strings usando Radix Sort MSD vía Trie.

    Construye un Trie (cuyos hijos quedan ordenados alfabéticamente
    al insertar) y lo recorre en preorder. El orden de los hijos
    garantiza el orden lexicográfico del resultado.

    Complejidad: O(N + k), donde:
        N = suma de longitudes de todas las palabras
        k = cantidad de nodos del Trie
    Es decir: O(N), sin comparaciones entre palabras.

    Args:
        words (list[str]): Palabras a ordenar. Se normalizan a minúscula.

    Returns:
        LinkedList[str]: Palabras ordenadas lexicográficamente.
    """
    trie: Trie = Trie()
    for word in words:
        insert(trie, word)

    result: LinkedList[str] = LinkedList()
    _collect_ordered(trie.root, "", result)
    return result


def _collect_ordered(node: TrieNode, current: str, out: LinkedList[str]) -> None:
    """
    Preorder DFS. Como los hijos están ordenados por inserción,
    no hace falta ordenarlos acá.

    Complejidad: O(N), N = nodos del subárbol.
    """
    if node.isEndOfWord:
        append(out, current)
    c = node.children.head
    while c is not None:
        if c.value is not None:
            _collect_ordered(c.value, current + (c.value.key or ""), out)
        c = c.nextNode


# ============================================================
# Display
# ============================================================


def display(trie: Trie) -> None:
    """
    Imprime el Trie de forma jerárquica.
    El asterisco (*) marca fin de palabra.
    """
    print(f"root  (palabras: {trie.size})")
    c = trie.root.children.head
    while c is not None:
        if c.value is not None:
            _display_node(c.value, "  ")
        c = c.nextNode


def _display_node(node: TrieNode, prefix: str) -> None:
    mark = " *" if node.isEndOfWord else ""
    print(f"{prefix}{node.key}{mark}")
    c = node.children.head
    while c is not None:
        if c.value is not None:
            _display_node(c.value, prefix + "  ")
        c = c.nextNode


def _show_children(trie: Trie, path: str) -> None:
    """
    Helper de debug: imprime los hijos del nodo ubicado en `path`.

    `path` es el string del camino desde la raíz (ej: "ho", "hol").
    Si el camino no existe, avisa por consola en lugar de explotar.

    Complejidad: O(|path| · |Σ| + |Σ|).

    Args:
        trie (Trie): Trie a consultar.
        path (str): Camino desde la raíz (vacío = raíz).

    Returns:
        None
    """
    from warehouse.estructuras.linkedlist import (
        printList,
    )  # import local para no ensuciar el módulo

    node = _go_to_prefix(trie, path) if path else trie.root
    if node is None:
        print(f"Camino '{path}' no existe")
        return

    label = f"'{path}'" if path else "raíz"
    print(f"Hijos de {label}:")
    printList(node.children)
