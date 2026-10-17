from core.inventory import*

# constantes de estado

PENDIENTE       =  "PENDIENTE"
EN_WAVE         =  "EN_WAVE"
EN_PREPARACION  =  "EN_PREPARACION"
PREPARADO       =  "PREPARADO"

ESTADOS_VALIDOS = {PENDIENTE, EN_WAVE, EN_PREPARACION, PREPARADO}

class Orden:
    def __init__(self, orden_id, prioridad, items, estado = PENDIENTE):
        self.orden_id : str = orden_id
        self.prioridad : str = prioridad
        self.estado : str = estado
        self.items : list[tuple[str, int]] = items

    def peso_total(self, inventario : GestorInventario):
        """suma el peso de todos los items de la orden (peso_kg * cantidad pedida).
        Si algun producto no existe en el inventario, obtener_producto lanza KeyError, O(n) caso promedio"""
 
        total = 0.0
        for producto_id, cantidad in self.items:
            producto = inventario.obtener_producto(producto_id)
            total += producto.peso_kg * cantidad
        return total
        

    def cambiar_estado(self, nuevo_estado: str):
        """verifica si el estado pertenece a uno de los estados validos
        , en caso de que pertenesca a los estados retorna "None", sino 
        genera un error del tipo ValueError (me parece mejor devolver algo en caso de que
        no exista ese estado) , O(1) caso promedio
        """

        if nuevo_estado in ESTADOS_VALIDOS:
            self.estado = nuevo_estado
            return None
        else:
            raise ValueError(f"estado no valido")

    def esta_pendiente(self):
        """verifica se esta en pendiente y retorna true o false segun corresponda, O(1) caso promedio"""
        if self.estado == "PENDIENTE":
            return True
        else:
            return False
        

    def to_dict(self):
        """O(n) peor caso"""
        return{
            "orden_id"  : self.orden_id,
            "prioridad" : self.prioridad,
            "estado"    : self.estado,
            "items"     : self.items
        }

    @staticmethod
    def del_dict(d: dict):
        """O(n) peor caso"""

        return Orden(
            orden_id  = d["orden_id"],
            prioridad = d["prioridad"],
            estado    = d["estado"],
            items     = [tuple(item) for item in d["items"]]
        )

