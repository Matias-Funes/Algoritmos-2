from warehouse.estructuras.linkedlist import LinkedList
from warehouse.estructuras.trie import (
    Trie,
    autocomplete,
    delete,
    insert,
    search,
    startsWith,
)


def _to_list(ll: LinkedList) -> list:
    """Convierte una LinkedList a lista de Python."""
    result = []
    c = ll.head
    while c is not None:
        result.append(c.value)
        c = c.nextNode
    return result


def test_insert_y_search():
    t = Trie()
    insert(t, "hola")
    insert(t, "mundo")
    assert search(t, "hola") is True
    assert search(t, "mundo") is True
    assert search(t, "holas") is False
    assert search(t, "ho") is False


def test_insert_no_duplica():
    t = Trie()
    insert(t, "hola")
    insert(t, "hola")
    assert t.size == 1


def test_insert_case_insensitive():
    t = Trie()
    insert(t, "HOLA")
    assert search(t, "hola") is True
    assert search(t, "HOLA") is True
    assert search(t, "HoLa") is True


def test_starts_with():
    t = Trie()
    insert(t, "hola")
    insert(t, "hombre")
    assert startsWith(t, "ho") is True
    assert startsWith(t, "hol") is True
    assert startsWith(t, "xyz") is False


def test_autocomplete():
    t = Trie()
    for w in ["caja", "caja chica", "caja grande", "bolsa", "tubo"]:
        insert(t, w)
    assert _to_list(autocomplete(t, "caj")) == ["caja", "caja chica", "caja grande"]
    assert _to_list(autocomplete(t, "bo")) == ["bolsa"]
    assert _to_list(autocomplete(t, "xyz")) == []


def test_delete_palabra_unica():
    t = Trie()
    insert(t, "hola")
    assert delete(t, "hola") is True
    assert search(t, "hola") is False
    assert t.size == 0


def test_delete_palabra_prefijo_de_otra():
    t = Trie()
    insert(t, "ho")
    insert(t, "hola")
    assert delete(t, "ho") is True
    assert search(t, "ho") is False
    assert search(t, "hola") is True  # sigue estando


def test_delete_palabra_que_contiene_otra():
    t = Trie()
    insert(t, "hola")
    insert(t, "hol")
    assert delete(t, "hola") is True
    assert search(t, "hola") is False
    assert search(t, "hol") is True


def test_delete_palabra_inexistente():
    t = Trie()
    insert(t, "hola")
    assert delete(t, "xyz") is False
    assert t.size == 1
