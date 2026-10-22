
from src.core.order import EN_WAVE
from src.core.wave import Wave


# no tengo muy claro porque pide la warehouse
def generar_waves(pedidos, inventory, warehouse, config):
    """Agrupa los pedidos PENDIENTES en waves, respetando los límites de configuración."""
    
    # 1. Filtrar solo los pedidos PENDIENTES que tengan items
    pendientes = [p for p in pedidos if p.esta_pendiente() and p.items]
    
    # 2. Ordenar por prioridad de mayor a menor, manteniendo un orden
    # .sort se puede reemplazar por algun metodo de ordenamiento de listas
    pendientes.sort(key=lambda p: int(p.prioridad), reverse=True)
    
    waves = []
    
    def nueva_wave():
        """ crea la wave segun la configuracion de max de pedidos, peso, productos"""
        return Wave(
            f"WAVE_{len(waves) + 1:03d}",
            config["max_pedidos"],
            config["max_productos"],
            config["peso_max_kg"],
        )
    
    # 3. Armar la primera wave
    wave = nueva_wave()
    
    # 4. Procesar cada pedido ordenado
    for pedido in pendientes:
        if wave.agregar_pedido(pedido, inventory):
            # 5a. Si entra en la wave actual, se marca como asignado
            pedido.cambiar_estado(EN_WAVE)
            continue
            
        # 5b. Si no entra, cerramos la wave actual y abrimos una nueva
        if len(wave) > 0:
            waves.append(wave)
            wave = nueva_wave()
            
        if wave.agregar_pedido(pedido, inventory):
            pedido.cambiar_estado(EN_WAVE)
        else:
            # Si el pedido es tan grande que no entra ni en una wave vacía,
            # lo dejamos pendiente para su revisión o manejo posterior.
            pass
            
    # Cerrar la última wave si quedó con pedidos acumulados
    if len(wave) > 0:
        waves.append(wave)
        
    return waves