# inventory.py — solo la parte de Product para que veas como encaja la z

class Product:
    """
    Producto del catalogo.

    - product_id : identificador unico (ej: "P001").
    - name       : nombre del producto.
    - location   : posicion 3D <x,y,z>.
                   <x,y> = donde esta parado el picker en el piso.
                   z     = altura del estante (1, 2, 3...).
    - stock      : cantidad disponible.
    """

    def __init__(self, product_id, name, location, stock=0):
        self.product_id = product_id
        self.name = name
        self.location = location #recibe instancia 
        self.stock = stock

    def __repr__(self):
        return "Product(%s, %s @ %s, stock=%d)" % (
            self.product_id, self.name, self.location, self.stock
            )








