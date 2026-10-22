
class Producto:
    def __init__(self, producto_id, nombre, rack_id, ubicacion, cantidad_disponible=0, peso_kg=0.0):
        self.producto_id: str = producto_id
        self.nombre: str = nombre
        self.rack_id: str = rack_id
        self.ubicacion: tuple = ubicacion
        self.cantidad_disponible: int = cantidad_disponible
        self.peso_kg: float = peso_kg

    def to_dict(self):
        """Crea un diccionario a partir de la instancia del objeto para guardarla en un .JSON"""
        return {
            "nombre": self.nombre,
            "id": self.producto_id,
            "rack_id": self.rack_id,
            "ubicacion": self.ubicacion,
            "cantidad_disponible": self.cantidad_disponible,
            "peso_kg": self.peso_kg
        }

    @staticmethod
    def del_dict(d: dict):
        """retorma un producto a partir de sus valores en el diccionario"""
        return Producto(
            producto_id=d["id"],
            nombre=d["nombre"],
            rack_id=d["rack_id"],
            ubicacion=tuple(d["ubicacion"]),  # JSON guarda las tuplas como listas
            cantidad_disponible=d["cantidad_disponible"],
            peso_kg=d["peso_kg"]
        )


# --------------------------------HASH-------------------------------------------------------

class nodoH:
    """clase la cual es la base para la implementacion de los nodos de las listas
    enlazadas de la hash table 
    """

    # se puede implementar una estructura de lista pero se tiene que modificar el tipo de nodo
    def __init__(self, clave, valor):
        self.clave = clave
        self.valor = valor
        self.siguiente = None


class HashTable:
    """implementacion de la hash table, utiliza una funcion hash generada por python la cual
    cambia cada vez que se ejecuta el programa

    se implemento con un array dinamico de python para la tabla y una lista enlazada para las coliciones
    """

    def __init__(self, capacidad: int = 16):
        """cosntructor de la hash table"""

        self.capacidad = capacidad
        self.casillas = [None] * self.capacidad  # lista con longitud = capacidad y None en cada posicion
        self.cantidad = 0  # cantidad de elementos guardados

    def _hash(self, clave):
        """crea el hash para una clave, O(1)"""
        return hash(clave) % self.capacidad

    def insertarHT(self, clave, valor):
        """inserta un valor en la hash table, si el valor ya existe actualiza el valor para esa clave
        si el valor no existe lo inserta, retorna "None", O(1) promedio, O(n) peor caso, O(n^2) si hay rehashing """

        indice = self._hash(clave)

        # ----------------La casilla esta vacia---------------------
        if self.casillas[indice] is None:
            self.casillas[indice] = nodoH(clave, valor)
            self.cantidad += 1
            if self.factorDeCarga() >= 0.75:
                self.reescalaDeLaTablaHash()
            return

        # ----------------La casilla tiene elementos (colision o clave repetida)---------------------
        actual = self.casillas[indice]
        while actual:
            if actual.clave == clave:
                actual.valor = valor  # Actualiza si la clave ya existe
                return
            if actual.siguiente is None:
                break
            actual = actual.siguiente

        actual.siguiente = nodoH(clave, valor)
        self.cantidad += 1
        if self.factorDeCarga() >= 0.75:
            self.reescalaDeLaTablaHash()

    def buscarHT(self, clave):
        """busca una clave en la tabla y retorna el valor si lo encuentra, en caso de 
        no encontrarlo produce un keyerror para atrapar con try, O(1) promedio, O(n) peor caso """

        indice = self._hash(clave)
        actual = self.casillas[indice]

        while actual:
            if actual.clave == clave:
                return actual.valor
            actual = actual.siguiente

        raise KeyError(f"La clave '{clave}' no existe en la tabla.")

    def obtenerHT(self, clave, default=None):
        """obtiene un elemento a traves de su clave si lo encuentra devuelve el valor sino 
        devuelve "None", no genera un error como buscar, O(1) promedio, O(n) peor"""

        indice = self._hash(clave)
        actual = self.casillas[indice]

        while actual:
            if actual.clave == clave:
                return actual.valor
            actual = actual.siguiente

        return default

    def eliminarHT(self, clave):
        """elimina un elemento por su clave, retorna "None" si fue eliminado o genera un
        keyerror si la clave no existe,  O(1) promedio, O(n) peor 
        """
        indice = self._hash(clave)

        if self.casillas[indice] is None:
            raise KeyError(f"La clave '{clave}' no existe en la tabla.")

        actual = self.casillas[indice]
        if actual.clave == clave:
            self.casillas[indice] = actual.siguiente
            self.cantidad -= 1
            return None

        anterior = actual
        actual = actual.siguiente

        while actual:
            if actual.clave == clave:
                anterior.siguiente = actual.siguiente
                self.cantidad -= 1
                return None
            anterior = actual
            actual = actual.siguiente

        raise KeyError(f"La clave '{clave}' no existe en la tabla.")

    def contieneHT(self, clave):
        """verifica si la clave esta en la hash table, si lo encuentra retorna True, sino False
        , O(1) promedio, O(n) peor"""
        indice = self._hash(clave)
        actual = self.casillas[indice]

        while actual:
            if actual.clave == clave:
                return True
            actual = actual.siguiente
        return False

    def factorDeCarga(self):
        """calcula el factor de carga de la tabla hash, O(1) peor caso"""
        return self.cantidad / self.capacidad

    def reescalaDeLaTablaHash(self):
        """aumenta en 2 el tamaño de la tabla hash en caso de que el factor de carga sea 
        mayor a 0.75,  O(n) promedio, O(n^2) peor"""
        casillasAnteriores = self.casillas

        self.capacidad *= 2
        self.casillas = [None] * self.capacidad
        self.cantidad = 0  # Se recalculará al reinsertar

        for casilla in casillasAnteriores:
            actual = casilla
            while actual:
                siguiente = actual.siguiente
                self.insertarHT(actual.clave, actual.valor)
                actual = siguiente

    def __len__(self):
        """retorna la cantidad de elementos que contiene la tabla, O(1) peor caso"""
        return self.cantidad


# --------------------------------GESTOR DE INVENTARIO---------------------------------------

class GestorInventario:
    """Guarda los productos en una HashTable cuya clave es el producto_id,
    asi buscar, agregar y eliminar cuesta O(1) en promedio"""

    def __init__(self):
        self.productos = HashTable()

    def agregar_producto(self, producto: Producto):
        """Agrega un producto. Lanza ValueError si el id ya existe, O(1) promedio, O(n) peor"""

        if self.productos.contieneHT(producto.producto_id):
            raise ValueError(f"Ya existe un producto con id '{producto.producto_id}'.")
        self.productos.insertarHT(producto.producto_id, producto)

    def obtener_producto(self, producto_id: str):
        """Devuelve el Producto. Lanza KeyError si no existe, O(1) promedio, O(n) peor"""

        return self.productos.buscarHT(producto_id)

    def eliminar_producto(self, producto_id: str):
        """Elimina el producto y lo devuelve. Lanza KeyError si no existe, O(1) promedio, O(n) peor"""

        producto = self.productos.buscarHT(producto_id)
        self.productos.eliminarHT(producto_id)
        return producto

    def tiene_producto(self, producto_id: str):
        return self.productos.contieneHT(producto_id)

    def reservar_stock(self, producto_id: str, cantidad: int):
        """Descuenta 'cantidad' del stock disponible (para armar un pedido).
        Lanza ValueError si la cantidad es invalida o no alcanza el stock,
        y KeyError si el producto no existe,  O(1) promedio, O(n) peor"""

        if cantidad <= 0:
            raise ValueError("La cantidad a reservar debe ser mayor a 0.")

        producto = self.productos.buscarHT(producto_id)

        if producto.cantidad_disponible < cantidad:
            raise ValueError(
                f"Stock insuficiente para '{producto_id}': "
                f"disponible {producto.cantidad_disponible}, pedido {cantidad}."
            )

        producto.cantidad_disponible -= cantidad
        return True

    def actualizar_stock(self, producto_id: str, delta: int):
        """Suma 'delta' al stock (positivo = ingreso, negativo = egreso),
        Lanza ValueError si el stock quedaria negativo,  O(1) promedio, O(n) peor"""

        producto = self.productos.buscarHT(producto_id)

        nuevo_stock = producto.cantidad_disponible + delta
        if nuevo_stock < 0:
            raise ValueError(
                f"El stock de '{producto_id}' no puede quedar negativo "
                f"({producto.cantidad_disponible} {delta:+d})."
            )

        producto.cantidad_disponible = nuevo_stock
        return nuevo_stock

    def obtener_ubicacion(self, producto_id: str):
        """Devuelve la ubicacion (tupla) del producto dentro del warehouse, O(1) promedio, O(n) peor"""

        return self.productos.buscarHT(producto_id).ubicacion

    def todos_los_productos(self):
        """Devuelve una lista con todos los productos, O(m+n) peor caso"""

        productos = []
        for casilla in self.productos.casillas:
            actual = casilla
            while actual:
                productos.append(actual.valor)
                actual = actual.siguiente
        return productos

    def __len__(self):
        """cantidad de productos, O(1) peor caso"""
        return len(self.productos)



if __name__ == "__main__":
    print("=== Prueba de Inventory ===")
    inv = GestorInventario()
    
    # 1. Agregar un producto
    p1 = Producto("P001", "Monitor", "R1", (3, 5, 1), cantidad_disponible=10, peso_kg=6.5)
    inv.agregar_producto(p1)
    print(f"Producto agregado: {p1.nombre} (Stock: {p1.cantidad_disponible})")
    
    # 2. Probar reserva de stock
    inv.reservar_stock("P001", 2)
    print(f"Stock después de reservar 2: {inv.obtener_producto('P001').cantidad_disponible}")
    
    # 3. Probar búsqueda y ubicación
    print(f"Ubicación de P001: {inv.obtener_ubicacion('P001')}")
    print(f"¿Existe P001?: {inv.tiene_producto('P001')}")
