# src/core/cell.py
# ---------------------------------------------------------------
# Una celda individual del grid del warehouse.
#
# El warehouse completo es una matriz de Cells: grid[y][x] -> Cell.
# Esta es la unidad mas chica del modelo fisico.
#
# Complejidad de las operaciones: O(1).
# ---------------------------------------------------------------


# --- Tipos posibles de celda (constantes de modulo) ---
VACIA     = "VACIA"       # celda sin asignar (deberia desaparecer al final)
PASILLO   = "PASILLO"     # por donde camina el picker
RACK      = "RACK"        # estanteria con productos
PUERTA    = "PUERTA"      # sobre el borde del warehouse
DESPACHO  = "DESPACHO"    # zona donde se consolidan pedidos


# --- Sentidos posibles de un pasillo ---
N     = "N"       # solo hacia +y (arriba)
S     = "S"       # solo hacia -y (abajo)
E     = "E"       # solo hacia +x (derecha)
O     = "O"       # solo hacia -x (izquierda)
AMBOS = "AMBOS"   # libre en las 4 direcciones


class Cell:
    """
    Una celda del grid del warehouse.

    Atributos publicos:
        x, y        : coordenadas enteras (esquina inferior izquierda).
        tipo        : PASILLO | RACK | PUERTA | DESPACHO | VACIA.
        sentido     : N | S | E | O | AMBOS  (solo aplica si tipo == PASILLO).
        ref_id      : id del elemento al que pertenece (rack_id, puerta_id, etc.),
                      o None si no tiene dueño (ej: pasillo implicito).
    """

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.tipo = VACIA
        self.sentido = AMBOS          # por defecto AMBOS (regla del PDF)
        self.ref_id = None

    def es_transitable(self):
        """
        True si el picker puede PARARSE en esta celda.
        Solo las celdas de PASILLO son transitables.
        Complejidad: O(1).
        """
        return self.tipo == PASILLO

    def es_adyacente_a_transitable(self):
        """
        True si la celda es accesible desde el costado.
        Racks, puertas y despachos se acceden desde un pasillo vecino.
        Complejidad: O(1).
        """
        return self.tipo in (RACK, PUERTA, DESPACHO)

    def __repr__(self):
        return "Cell(%d,%d,tipo=%s,sentido=%s)" % (
            self.x, self.y, self.tipo, self.sentido
        )


# =================================================================
# DEMO  (ejecutar con: python -m src.core.cell)
# =================================================================
if __name__ == "__main__":
    print("=== Prueba de Cell ===\n")

    # 1. Celda recien creada: tipo VACIA, sentido AMBOS
    c = Cell(3, 5)
    print("1) Celda creada:      ", c)

    # 2. Celda como pasillo con sentido N
    c.tipo = PASILLO
    c.sentido = N
    print("2) Celda pasillo N:   ", c)
    print("   Es transitable?    ", c.es_transitable())

    # 3. Celda como rack
    c.tipo = RACK
    c.ref_id = "R1"
    print("\n3) Celda rack R1:     ", c)
    print("   Es transitable?    ", c.es_transitable())
    print("   Es adyacente?      ", c.es_adyacente_a_transitable())

    # 4. Celda como puerta
    c.tipo = PUERTA
    print("\n4) Celda puerta:      ", c)
    print("   Es adyacente?      ", c.es_adyacente_a_transitable())

    print("\n=== Fin de la prueba ===")