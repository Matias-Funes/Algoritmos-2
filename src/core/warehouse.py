# src/core/warehouse.py
# ---------------------------------------------------------------
# Modela el warehouse completo como una GRILLA 2D de Cells.
#
# Estructura principal:
#     self.grid[y][x]  ->  Cell(x, y)
#
# Este modulo NO construye el grafo (eso lo hace graph_builder.py).
# Solo carga, valida y expone el modelo fisico.
# ---------------------------------------------------------------

from src.core.cell import (
    Cell,
    VACIA, PASILLO, RACK, PUERTA, DESPACHO,
    N, S, E, O, AMBOS,
)


# =================================================================
# 1. Clase base: Rectangulo
# =================================================================
class Rectangulo:
    """
    Un rectangulo del warehouse.

    Las celdas van desde (x, y) hasta (x + ancho - 1, y + alto - 1)
    inclusive.  Regla del PDF.

    Complejidad: todas las operaciones son O(1) salvo celdas() que
    es O(ancho * alto).
    """

    def __init__(self, elem_id, x, y, ancho, alto):
        if ancho <= 0 or alto <= 0:
            raise ValueError("ancho y alto deben ser > 0")
        self.id = elem_id
        self.x = x
        self.y = y
        self.ancho = ancho
        self.alto = alto

    def celdas(self):
        """
        Devuelve la lista de todas las coordenadas (x, y) del rectangulo.
        Complejidad: O(ancho * alto).
        """
        resultado = []
        for dy in range(self.alto):
            for dx in range(self.ancho):
                resultado.append((self.x + dx, self.y + dy))
        return resultado

    def contiene(self, x, y):
        """
        True si (x, y) cae dentro del rectangulo.
        Complejidad: O(1).
        """
        return (self.x <= x < self.x + self.ancho and
                self.y <= y < self.y + self.alto)

    def __repr__(self):
        return "%s(%s@(%d,%d) %dx%d)" % (
            self.__class__.__name__, self.id, self.x, self.y,
            self.ancho, self.alto
        )


# =================================================================
# 2. Subclases especializadas
# =================================================================
class Rack(Rectangulo):
    """
    Estanteria.  Regla del PDF: uno de sus dos lados (ancho o alto)
    debe valer 2, porque los productos se acceden desde el costado.

    Ejemplo: Rack("R1", x=3, y=5, ancho=2, alto=6)
             Ocupa las celdas (3..4, 5..10).
             Columna x=3 se accede desde el pasillo x=2.
             Columna x=4 se accede desde el pasillo x=5.
    """

    def __init__(self, rack_id, x, y, ancho, alto):
        super().__init__(rack_id, x, y, ancho, alto)
        if ancho != 2 and alto != 2:
            raise ValueError(
                "Rack %s: uno de ancho/alto debe ser 2 (es %dx%d)"
                % (rack_id, ancho, alto)
            )


class Pasillo(Rectangulo):
    """
    Pasillo declarado con un sentido de circulacion.

    Ejemplo: Pasillo("PAS_V0", x=0, y=5, ancho=3, alto=6, sentido="N")
    """

    SENTIDOS_VALIDOS = (N, S, E, O, AMBOS)

    def __init__(self, pas_id, x, y, ancho, alto, sentido):
        super().__init__(pas_id, x, y, ancho, alto)
        if sentido not in self.SENTIDOS_VALIDOS:
            raise ValueError(
                "Sentido invalido: %s. Debe ser uno de %s"
                % (sentido, self.SENTIDOS_VALIDOS)
            )
        self.sentido = sentido


class ZonaDespacho(Rectangulo):
    """
    Zona de despacho con limite de peso.

    Esta asociada a una puerta y se ubica frente a ella.
    """

    def __init__(self, zona_id, puerta_id, x, y, ancho, alto, peso_max_kg):
        super().__init__(zona_id, x, y, ancho, alto)
        self.puerta_id = puerta_id
        self.peso_max_kg = peso_max_kg


class Puerta:
    """
    Puerta sobre el borde del warehouse.

    No hereda de Rectangulo porque ocupa una sola celda.
    """

    TIPOS_VALIDOS = ("INBOUND", "OUTBOUND", "AMBOS")

    def __init__(self, puerta_id, tipo, x, y):
        if tipo not in self.TIPOS_VALIDOS:
            raise ValueError(
                "Tipo de puerta invalido: %s. Debe ser uno de %s"
                % (tipo, self.TIPOS_VALIDOS)
            )
        self.id = puerta_id
        self.tipo = tipo
        self.x = x
        self.y = y

    def __repr__(self):
        return "Puerta(%s,%s@(%d,%d))" % (self.id, self.tipo, self.x, self.y)


# =================================================================
# 3. Clase principal: Warehouse
# =================================================================
class Warehouse:
    """
    El almacen completo.

    Estructura:
        self.grid       : lista de listas [y][x] -> Cell
        self.racks      : dict {rack_id -> Rack}
        self.pasillos   : dict {pas_id -> Pasillo}
        self.puertas    : dict {puerta_id -> Puerta}
        self.zonas      : dict {zona_id -> ZonaDespacho}

    Complejidad espacial: O(ancho_x * largo_y).
    """

    def __init__(self, ancho_x, largo_y):
        if ancho_x <= 0 or largo_y <= 0:
            raise ValueError("Dimensiones deben ser > 0")
        self.ancho_x = ancho_x
        self.largo_y = largo_y

        # Creamos la grilla llena de celdas VACIAS
        self.grid = []
        for y in range(largo_y):
            fila = []
            for x in range(ancho_x):
                fila.append(Cell(x, y))
            self.grid.append(fila)

        self.racks = {}
        self.pasillos = {}
        self.puertas = {}
        self.zonas = {}

    # --------------------------------------------------------------
    # 3.1 Helpers internos de validacion
    # --------------------------------------------------------------
    def _dentro_del_tablero(self, x, y):
        """True si (x, y) esta dentro de las dimensiones.  O(1)."""
        return 0 <= x < self.ancho_x and 0 <= y < self.largo_y

    def _validar_rectangulo_dentro(self, r):
        """
        Verifica que todo el rectangulo caiga dentro del tablero.
        Complejidad: O(1).
        """
        if r.x < 0 or r.y < 0:
            raise ValueError("%s: esquina fuera del tablero" % r.id)
        if r.x + r.ancho > self.ancho_x:
            raise ValueError(
                "%s: excede ancho_x (llega a %d, max %d)"
                % (r.id, r.x + r.ancho, self.ancho_x)
            )
        if r.y + r.alto > self.largo_y:
            raise ValueError(
                "%s: excede largo_y (llega a %d, max %d)"
                % (r.id, r.y + r.alto, self.largo_y)
            )

    def _validar_celdas_libres(self, r):
        """
        Verifica que ninguna celda del rectangulo este ya ocupada.
        Complejidad: O(ancho * alto).
        """
        for (x, y) in r.celdas():
            c = self.grid[y][x]
            if c.tipo != VACIA:
                raise ValueError(
                    "Solapamiento en (%d,%d): ya es %s (ref=%s), "
                    "se intenta poner %s"
                    % (x, y, c.tipo, c.ref_id, r.id)
                )

    def _marcar_rectangulo(self, r, tipo, sentido=AMBOS):
        """
        Pinta todas las celdas del rectangulo con un tipo y sentido.
        Complejidad: O(ancho * alto).
        """
        for (x, y) in r.celdas():
            c = self.grid[y][x]
            c.tipo = tipo
            c.sentido = sentido
            c.ref_id = r.id

    # --------------------------------------------------------------
    # 3.2 API publica: agregar elementos
    # --------------------------------------------------------------
    def add_rack(self, rack):
        """
        Agrega un rack al warehouse.
        Valida: dentro del tablero, sin solapamiento.
        Complejidad: O(ancho * alto).
        """
        self._validar_rectangulo_dentro(rack)
        self._validar_celdas_libres(rack)
        self._marcar_rectangulo(rack, RACK)
        self.racks[rack.id] = rack

    def add_pasillo(self, pasillo):
        """
        Agrega un pasillo declarado.
        Valida: dentro del tablero, sin solapamiento.
        Complejidad: O(ancho * alto).
        """
        self._validar_rectangulo_dentro(pasillo)
        self._validar_celdas_libres(pasillo)
        self._marcar_rectangulo(pasillo, PASILLO, pasillo.sentido)
        self.pasillos[pasillo.id] = pasillo

    def add_puerta(self, puerta):
        """
        Agrega una puerta.  Debe estar sobre el borde del warehouse.
        Complejidad: O(1).
        """
        if not self._dentro_del_tablero(puerta.x, puerta.y):
            raise ValueError("Puerta %s fuera del tablero" % puerta.id)

        en_borde = (puerta.x == 0 or
                    puerta.x == self.ancho_x - 1 or
                    puerta.y == 0 or
                    puerta.y == self.largo_y - 1)
        if not en_borde:
            raise ValueError(
                "Puerta %s no esta sobre el borde (pos=%d,%d)"
                % (puerta.id, puerta.x, puerta.y)
            )

        c = self.grid[puerta.y][puerta.x]
        if c.tipo != VACIA:
            raise ValueError(
                "Puerta %s se solapa con %s" % (puerta.id, c.tipo)
            )

        c.tipo = PUERTA
        c.ref_id = puerta.id
        self.puertas[puerta.id] = puerta

    def add_zona_despacho(self, zona):
        """
        Agrega una zona de despacho.
        Complejidad: O(ancho * alto).
        """
        self._validar_rectangulo_dentro(zona)
        self._validar_celdas_libres(zona)
        self._marcar_rectangulo(zona, DESPACHO)
        self.zonas[zona.id] = zona

    # --------------------------------------------------------------
    # 3.3 Rellenar celdas sueltas como pasillos implicitos
    # --------------------------------------------------------------
    def rellenar_pasillos_implicitos(self):
        """
        Cualquier celda VACIA pasa a ser PASILLO con sentido AMBOS.
        Esto refleja la regla del PDF:
            'Las celdas de pasillo que no pertenezcan a ningun
             pasillo declarado se consideran de sentido AMBOS.'
        Complejidad: O(ancho_x * largo_y).
        """
        for fila in self.grid:
            for c in fila:
                if c.tipo == VACIA:
                    c.tipo = PASILLO
                    c.sentido = AMBOS

    # --------------------------------------------------------------
    # 3.4 Debug: imprimir el warehouse como ASCII
    # --------------------------------------------------------------
    def print_ascii(self):
        """
        Imprime el warehouse por consola (debug visual).

        Simbolos:
            .  pasillo AMBOS o no declarado
            ^  pasillo sentido N
            v  pasillo sentido S
            >  pasillo sentido E
            <  pasillo sentido O
            #  rack
            P  puerta
            D  zona de despacho
            (espacio)  celda vacia
        """
        # Mapa de tipo -> simbolo
        tipo_simbolo = {
            PASILLO:  ".",
            RACK:     "#",
            PUERTA:   "P",
            DESPACHO: "D",
            VACIA:    " ",
        }
        # Mapa de sentido -> simbolo (solo si tipo == PASILLO)
        sentido_simbolo = {
            N:     "^",
            S:     "v",
            E:     ">",
            O:     "<",
            AMBOS: ".",
        }

        # Encabezado con coordenadas x
        cabecera = "    "
        for x in range(self.ancho_x):
            cabecera += str(x % 10)
        print(cabecera)

        # Filas de arriba hacia abajo (y descendente)
        for y in range(self.largo_y - 1, -1, -1):
            linea = ""
            for x in range(self.ancho_x):
                c = self.grid[y][x]
                if c.tipo == PASILLO:
                    linea += sentido_simbolo[c.sentido]
                else:
                    linea += tipo_simbolo[c.tipo]
            print("%3d " % y + linea)

        # Repetimos cabecera abajo
        print(cabecera)

    # --------------------------------------------------------------
    # 3.5 Consultas auxiliares
    # --------------------------------------------------------------
    def get_cell(self, x, y):
        """Devuelve la Cell en (x, y).  O(1)."""
        if not self._dentro_del_tablero(x, y):
            raise IndexError("(%d,%d) fuera del tablero" % (x, y))
        return self.grid[y][x]

    def celdas_transitables(self):
        """
        Devuelve una lista de todas las celdas PASILLO.
        Complejidad: O(ancho_x * largo_y).
        """
        resultado = []
        for fila in self.grid:
            for c in fila:
                if c.es_transitable():
                    resultado.append(c)
        return resultado

    def __repr__(self):
        return "Warehouse(%dx%d, racks=%d, pasillos=%d, puertas=%d, zonas=%d)" % (
            self.ancho_x, self.largo_y,
            len(self.racks), len(self.pasillos),
            len(self.puertas), len(self.zonas)
        )


# =================================================================
# DEMO  (ejecutar con: python -m src.core.warehouse)
# =================================================================
if __name__ == "__main__":
    print("=== Prueba de Warehouse ===\n")

    # Mini warehouse 12x7
    wh = Warehouse(ancho_x=12, largo_y=7)

    # Un rack 2x4 en (3, 2)
    wh.add_rack(Rack("R1", x=3, y=2, ancho=2, alto=4))

    # Otro rack 2x4 en (8, 2)
    wh.add_rack(Rack("R2", x=8, y=2, ancho=2, alto=4))

    # Pasillo a la izquierda del R1, sentido N
    wh.add_pasillo(Pasillo("PAS_V0", x=1, y=2, ancho=2, alto=4, sentido=N))

    # Pasillo entre R1 y R2, sentido S
    wh.add_pasillo(Pasillo("PAS_V1", x=5, y=2, ancho=3, alto=4, sentido=S))

    # Pasillo a la derecha de R2, sentido N
    wh.add_pasillo(Pasillo("PAS_V2", x=10, y=2, ancho=2, alto=4, sentido=N))

    # Puerta en el borde inferior
    wh.add_puerta(Puerta("PU1", "OUTBOUND", x=2, y=0))

    # Zona de despacho arriba de la puerta
    wh.add_zona_despacho(
        ZonaDespacho("Z1", "PU1", x=1, y=1, ancho=4, alto=1, peso_max_kg=500)
    )

    # Todo lo vacio se vuelve pasillo AMBOS
    wh.rellenar_pasillos_implicitos()

    print(wh)
    print()
    wh.print_ascii()

    print("\n--- Verificaciones ---")
    print("Celdas transitables:", len(wh.celdas_transitables()))
    print("Celda (3,2) tipo:   ", wh.get_cell(3, 2).tipo)
    print("Celda (3,2) ref_id: ", wh.get_cell(3, 2).ref_id)
    print("Celda (2,5) sentido:", wh.get_cell(2, 5).sentido)