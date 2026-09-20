# 🚀 Guía de Git y Entorno de Desarrollo - Proyecto Algoritmos 2

Seguir esta guía paso a paso para tener todos exactamente las mismas versiones y dependencias configuradas[cite: 1, 5].

---

# ==========================================
# PARTE 1: CONFIGURACIÓN INICIAL (SOLO LA PRIMERA VEZ)
# ==========================================

# 1. Identificarse en Git (si nunca lo hicieron en su PC)
git config --global user.name "Tu Nombre o Usuario de GitHub"
git config --global user.email "tu_email@ejemplo.com"

# 2. Clonar el repositorio y entrar a la carpeta
git clone https://github.com/Matias-Funes/Algoritmos-2.git
cd Algoritmos-2

# 3. Crear el entorno virtual
python -m venv .venv

# 4. Activar el entorno virtual
# En Git Bash (o Mac / Linux):
source .venv/Scripts/activate
# En PowerShell (Windows):
# .venv\Scripts\Activate.ps1

# 5. Instalar las dependencias exactas del proyecto
pip install --upgrade pip
pip install -r requirements.txt


# ==========================================
# PARTE 2: FLUJO DE TRABAJO DEL DÍA A DÍA
# ==========================================
# REGLA: No programar directo en la rama main. Trabajar siempre en una rama propia.

# --- AL EMPEZAR A TRABAJAR ---

# 1. Activar el entorno virtual (siempre debe decir (.venv) en la terminal)
source .venv/Scripts/activate

# 2. Ir a la rama principal y descargar lo último que subió el equipo
git checkout main
git pull origin main

# 3. Crear y entrar a tu rama de trabajo (si es una tarea nueva)
git checkout -b nombre-de-tu-rama
# Ejemplo: git checkout -b julieta-algoritmo-dijkstra

# (Si la rama ya la habías creado antes y querés seguir trabajando en ella):
# git checkout nombre-de-tu-rama
# git merge main


# --- AL TERMINAR DE TRABAJAR Y SUBIR CAMBIOS ---

# 4. Ver qué archivos modificaste
git status

# 5. Agregar los cambios al área de preparación
git add .

# 6. Guardar los cambios con un mensaje claro
git commit -m "Explicacion corta de lo que hiciste"

# 7. Subir los cambios a tu rama en GitHub
git push origin nombre-de-tu-rama

# 8. Luego ir a GitHub en el navegador y crear el "Pull Request" para unirlo a main.


# ==========================================
# PARTE 3: COMANDOS ÚTILES Y CONSULTAS
# ==========================================

# Ver en qué rama estás parado
git branch

# Ver todas las ramas locales y remotas
git branch -a

# Descartar cambios locales no guardados en un archivo
git restore nombre_del_archivo.py

# Borrar una rama local (una vez que ya se subió y unió a main)
git branch -d nombre-de-tu-rama

# Borrar una rama remota en GitHub
git push origin --delete nombre-de-tu-rama