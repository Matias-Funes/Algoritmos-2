


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

