"""
inventory.py
============
Gestión de productos mediante una TABLA HASH PROPIA.

Estrategia de colisiones: ENCADENAMIENTO (redireccionamiento cerrado).
Cada bucket es una lista enlazada simple implementada con la clase _ChainNode.

Unidad 3 del programa.

Complejidad temporal (n = elementos, m = buckets, α = n/m):
    insert / search / delete: O(1 + α) promedio
                              O(n)      peor caso (todas las claves colisionan)

Estrategia de redimensionamiento: duplicar capacidad cuando α > 0.75.
Tras el rehash, α baja a ~0.375.

NO se usa dict de Python para almacenar los pares (k,v): se implementa
manualmente con listas enlazadas dentro de cada bucket.

Autor: Equipo Wave Picking - Algoritmos y Estructuras de Datos 2 (UNCUYO)
"""

from .warehouse import Position


# ---------------------------------------------------------------------------
# 1. Modelo de Producto (punto 4 del PDF)
# ---------------------------------------------------------------------------
class Product:
    """
    Producto del catálogo.

    Campos mínimos exigidos por el PDF:
        - Identificador único (product_id)
        - Nombre            (name)
        - Ubicación         (location: Position tetra)
        - Cantidad dispon.  (stock)
    """

    def __init__(self, product_id, name, location, stock=0):
        if not product_id:
            raise ValueError("product_id no puede ser vacío.")
        if stock < 0:
            raise ValueError("Stock negativo no permitido: %s" % stock)
        self.product_id = product_id
        self.name = name
        self.location = location
        self.stock = stock

    def to_dict(self):
        return {
            "product_id": self.product_id,
            "name": self.name,
            "location": self.location.as_tuple(),
            "stock": self.stock,
        }

    @staticmethod
    def from_dict(d):
        x, y, z = d["location"]
        return Product(d["product_id"], d["name"], Position(x, y, z), d["stock"])

    def __repr__(self):
        return "Product(%r, %r, %s, stock=%d)" % (
            self.product_id, self.name, self.location, self.stock
        )


# ---------------------------------------------------------------------------
# 2. Nodo de la cadena (lista enlazada) para manejo de colisiones
# ---------------------------------------------------------------------------
class _ChainNode:
    """
    Nodo de la lista enlazada que resuelve las colisiones dentro de un bucket.
    __slots__ reduce el overhead de memoria (no es una estructura de datos
    adicional, es solo una directiva de Python para ahorrar RAM).
    """

    __slots__ = ("key", "value", "next")

    def __init__(self, key, value, nxt=None):
        self.key = key
        self.value = value
        self.next = nxt


# ---------------------------------------------------------------------------
# 3. Tabla Hash con encadenamiento
# ---------------------------------------------------------------------------
class HashTable:
    """
    Tabla Hash con redireccionamiento cerrado por encadenamiento.

    Atributos privados:
        _buckets  : lista de cabezas de cadena (m posiciones).
        _capacity : cantidad de buckets (m).
        _size     : cantidad de pares (k, v) almacenados (n).
    """

    INITIAL_CAPACITY = 16
    MIN_CAPACITY = 8
    LOAD_FACTOR_THRESHOLD = 0.75

    def __init__(self, capacity=16):
        if capacity < self.MIN_CAPACITY:
            capacity = self.MIN_CAPACITY
        self._capacity = capacity
        self._size = 0
        self._buckets = [None] * capacity

    # ------------------------------------------------------------------
    # 3.1 Función hash
    # ------------------------------------------------------------------
    @staticmethod
    def _hash(key):
        """
        Función hash polinomial (djb2):
            h_0 = 5381
            h_i = h_{i-1} * 33 + ord(c_i)   (mod 2^31)

        Complejidad temporal: O(L), con L = longitud de la clave.
        Para IDs cortos (ej. "P001"), es efectivamente O(1).
        """
        h = 5381
        for ch in str(key):
            h = ((h << 5) + h) + ord(ch)   # h * 33 + ord(ch)
        return h & 0x7FFFFFFF

    def _bucket_index(self, key):
        """Mapea la clave a un índice en [0, _capacity).  O(1)."""
        return self._hash(key) % self._capacity

    # ------------------------------------------------------------------
    # 3.2 API principal
    # ------------------------------------------------------------------
    def insert(self, key, value):
        """
        Inserta o actualiza el par (key, value).

        Complejidad temporal:
            - Caso promedio: O(1 + α), con α = n/m.
            - Peor caso:     O(n).
        Si la clave ya existe, se ACTUALIZA el valor.
        """
        idx = self._bucket_index(key)
        current = self._buckets[idx]
        while current is not None:
            if current.key == key:
                current.value = value
                return
            current = current.next

        # No existía: insertar al frente de la cadena (O(1))
        self._buckets[idx] = _ChainNode(key, value, self._buckets[idx])
        self._size += 1
        self._maybe_resize()

    def search(self, key):
        """
        Busca una clave.  Devuelve el valor o lanza KeyError.
        Complejidad temporal: O(1 + α) promedio, O(n) peor caso.
        """
        idx = self._bucket_index(key)
        current = self._buckets[idx]
        while current is not None:
            if current.key == key:
                return current.value
            current = current.next
        raise KeyError("Clave no encontrada: %r" % key)

    def get(self, key, default=None):
        """Versión no-throwing de search().  O(1 + α) promedio."""
        try:
            return self.search(key)
        except KeyError:
            return default

    def delete(self, key):
        """
        Elimina la clave (y su valor).
        Complejidad temporal: O(1 + α) promedio, O(n) peor caso.
        Lanza KeyError si la clave no existe.
        """
        idx = self._bucket_index(key)
        current = self._buckets[idx]
        prev = None
        while current is not None:
            if current.key == key:
                if prev is None:
                    self._buckets[idx] = current.next
                else:
                    prev.next = current.next
                self._size -= 1
                return
            prev = current
            current = current.next
        raise KeyError("Clave no encontrada: %r" % key)

    def contains(self, key):
        """Pertenencia.  O(1 + α) promedio."""
        return self.get(key, _SENTINEL) is not _SENTINEL

    # ------------------------------------------------------------------
    # 3.3 Gestión del factor de carga
    # ------------------------------------------------------------------
    def load_factor(self):
        """α = n / m.  O(1)."""
        return self._size / self._capacity

    def _maybe_resize(self):
        """
        Duplica la capacidad si α supera el umbral.
        El rehash es O(n) amortizado.
        """
        if self.load_factor() > self.LOAD_FACTOR_THRESHOLD:
            self._rehash(self._capacity * 2)

    def _rehash(self, new_capacity):
        """
        Reconstruye la tabla con nueva capacidad.
        Complejidad temporal: O(n + m).
        Complejidad espacial:  O(n + m).
        """
        old_buckets = self._buckets
        self._capacity = new_capacity
        self._buckets = [None] * new_capacity
        self._size = 0
        for head in old_buckets:
            current = head
            while current is not None:
                # Reinsertamos SIN llamar a _maybe_resize (evita recursión)
                idx = self._hash(current.key) % self._capacity
                self._buckets[idx] = _ChainNode(
                    current.key, current.value, self._buckets[idx]
                )
                self._size += 1
                current = current.next

    # ------------------------------------------------------------------
    # 3.4 Iteradores y dunders
    # ------------------------------------------------------------------
    def keys(self):
        """Itera todas las claves.  O(n + m)."""
        for head in self._buckets:
            current = head
            while current is not None:
                yield current.key
                current = current.next

    def values(self):
        """Itera todos los valores.  O(n + m)."""
        for head in self._buckets:
            current = head
            while current is not None:
                yield current.value
                current = current.next

    def items(self):
        """Itera pares (clave, valor).  O(n + m)."""
        for head in self._buckets:
            current = head
            while current is not None:
                yield current.key, current.value
                current = current.next

    def __len__(self):
        return self._size

    def __contains__(self, key):
        return self.contains(key)

    def __setitem__(self, key, value):
        self.insert(key, value)

    def __getitem__(self, key):
        return self.search(key)

    def __delitem__(self, key):
        self.delete(key)

    def __repr__(self):
        return "HashTable(size=%d, capacity=%d, alpha=%.2f)" % (
            self._size, self._capacity, self.load_factor()
        )


# Sentinela para 'contains' sin ambigüedad con None
_SENTINEL = object()


# ---------------------------------------------------------------------------
# 4. Gestor de inventario (fachada sobre HashTable)
# ---------------------------------------------------------------------------
class InventoryManager:
    """
    Fachada de alto nivel para el inventario del warehouse.
    Internamente usa una HashTable indexada por product_id.
    Todas las operaciones heredan la complejidad O(1 + α) promedio.
    """

    def __init__(self):
        self._table = HashTable()

    # --- CRUD de productos ---
    def add_product(self, product):
        """Inserta o reemplaza un producto.  O(1) promedio."""
        self._table.insert(product.product_id, product)

    def get_product(self, product_id):
        """Recupera un producto.  O(1) promedio.  KeyError si no existe."""
        return self._table.search(product_id)

    def remove_product(self, product_id):
        """Elimina un producto.  O(1) promedio."""
        self._table.delete(product_id)

    def has_product(self, product_id):
        """Pertenencia.  O(1) promedio."""
        return self._table.contains(product_id)

    # --- Gestión de stock ---
    def update_stock(self, product_id, delta):
        """
        Suma 'delta' al stock (delta puede ser negativo).
        Devuelve el nuevo stock.  O(1) promedio.
        """
        product = self._table.search(product_id)
        new_stock = product.stock + delta
        if new_stock < 0:
            raise ValueError(
                "Stock insuficiente para %s: actual=%d, delta=%d" % (
                    product_id, product.stock, delta
                )
            )
        product.stock = new_stock
        return new_stock

    def reserve_stock(self, product_id, quantity):
        """
        Intenta reservar 'quantity' unidades.
        Devuelve True si había stock suficiente (y lo descuenta),
        False en caso contrario.  O(1) promedio.
        """
        if quantity < 0:
            raise ValueError("quantity debe ser >= 0")
        product = self._table.search(product_id)
        if product.stock < quantity:
            return False
        product.stock -= quantity
        return True

    def get_location(self, product_id):
        """Ubicación del producto.  O(1) promedio."""
        return self._table.search(product_id).location

    # --- Consultas globales ---
    def all_products(self):
        """Itera todos los productos.  O(n)."""
        return self._table.values()

    def __len__(self):
        return len(self._table)

    def __contains__(self, product_id):
        return self._table.contains(product_id)

    def to_dict(self):
        return {"products": [p.to_dict() for p in self.all_products()]}

    @staticmethod
    def from_dict(data):
        inv = InventoryManager()
        for pd in data["products"]:
            inv.add_product(Product.from_dict(pd))
        return inv

    def __repr__(self):
        return "InventoryManager(products=%d)" % len(self)


# ---------------------------------------------------------------------------
# 5. Demo de uso (python -m src.core.inventory)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=== Demo: HashTable + InventoryManager ===\n")

    inv = InventoryManager()

    productos = [
        Product("P001", "Tornillo M4",    Position(0, 10, 2), 20),
        Product("P002", "Tuerca M4",      Position(5, 10, 1), 15),
        Product("P003", "Arandela",       Position(10, 10, 3), 30),
        Product("P004", "Martillo",       Position(5, 5, 1), 10),
        Product("P005", "Destornillador", Position(0, 5, 0), 25),
    ]
    for p in productos:
        inv.add_product(p)

    print(inv)
    print("Factor de carga: %.3f" % inv._table.load_factor())
    print("Capacidad de buckets: %d" % inv._table._capacity)

    print("\n-- Consultas O(1) --")
    for pid in ["P001", "P003", "P005"]:
        prod = inv.get_product(pid)
        print("  %s: %s @ %s  stock=%d" % (pid, prod.name, prod.location, prod.stock))

    print("\n-- Reserva de stock --")
    print("  reserve P001 x5 -> %s  (nuevo stock: %d)" % (
        inv.reserve_stock("P001", 5), inv.get_product("P001").stock
    ))
    print("  reserve P001 x100 -> %s  (stock insuficiente)" % inv.reserve_stock("P001", 100))
    print("  reserve P002 x3 -> %s  (nuevo stock: %d)" % (
        inv.reserve_stock("P002", 3), inv.get_product("P002").stock
    ))

    print("\n-- Producto inexistente --")
    print("  ¿P999 en inventario? %s" % inv.has_product("P999"))

    print("\nTotal de productos indexados: %d" % len(inv))