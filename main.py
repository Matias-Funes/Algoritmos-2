import pygame
import constants

pygame.init()



#creo la ventana
window = pygame.display.set_mode((constants.WIDTH, constants.HEIGHT))
#Nombre de la ventana
pygame.display.set_caption("WAREHOUSE")

run = True
while run:
    # Manejo de eventos como tocar una tecla o cerrar la ventana
    for event in pygame.event.get():
        # Procesa el evento para cerrar la ventana
        if event.type == pygame.QUIT:
            run = False

    window.fill((0, 50, 50))  # Rellena la ventana con color negro
    pygame.display.flip()  # Actualiza la pantalla

pygame.quit()  # Cierra Pygame