"""
Stub temporal de las clases de Integrante A.
Usar SOLO mientras src/core/warehouse.py no esté reescrito.
Cuando A entregue, borrar este archivo y ajustar el import en
tests/test_scenario_loader.py.
"""


class Rectangulo:
    def __init__(self, elem_id, x, y, ancho, alto):
        self.id = elem_id
        self.x = x
        self.y = y
        self.ancho = ancho
        self.alto = alto

    def celdas(self):
        return [
            (x, y)
            for x in range(self.x, self.x + self.ancho)
            for y in range(self.y, self.y + self.alto)
        ]


class Rack(Rectangulo):
    def __init__(self, rack_id, x, y, ancho, alto):
        if not (ancho == 2 or alto == 2):
            raise ValueError("Un lado del rack debe ser 2")
        super().__init__(rack_id, x, y, ancho, alto)


class Pasillo(Rectangulo):
    def __init__(self, pas_id, x, y, ancho, alto, sentido):
        if sentido not in ("N", "S", "E", "O", "AMBOS"):
            raise ValueError("Sentido inválido: %s" % sentido)
        super().__init__(pas_id, x, y, ancho, alto)
        self.sentido = sentido


class Puerta:
    def __init__(self, puerta_id, tipo, x, y):
        self.id = puerta_id
        self.tipo = tipo
        self.x = x
        self.y = y


class ZonaDespacho(Rectangulo):
    def __init__(self, zona_id, puerta_id, x, y, ancho, alto, peso_max_kg):
        super().__init__(zona_id, x, y, ancho, alto)
        self.puerta_id = puerta_id
        self.peso_max_kg = peso_max_kg


class Warehouse:
    def __init__(self, ancho_x, largo_y):
        self.ancho_x = ancho_x
        self.largo_y = largo_y
        self.racks = {}
        self.pasillos = {}
        self.puertas = {}
        self.zonas = {}

    def add_rack(self, rack):
        self.racks[rack.id] = rack

    def add_pasillo(self, pasillo):
        self.pasillos[pasillo.id] = pasillo

    def add_puerta(self, puerta):
        self.puertas[puerta.id] = puerta

    def add_zona_despacho(self, zona):
        self.zonas[zona.id] = zona

    def rellenar_pasillos_implicitos(self):
        pass

    def print_ascii(self):
        print(
            "[stub] %dx%d con %d racks" % (self.ancho_x, self.largo_y, len(self.racks))
        )
