import sys
import os
from cx_Freeze import setup, Executable

# Nom de ton application
app_name = "VMaster"

# Récupère tous les fichiers et dossiers du répertoire courant
current_dir = os.getcwd()

# Exclure certains dossiers inutiles
excluded_dirs = ["build", "__pycache__", "venv"]

# Liste des fichiers à inclure
include_files = []

for item in os.listdir(current_dir):
    # Ignorer les dossiers exclus
    if item in excluded_dirs:
        continue
    # Ignorer le fichier setup.py lui-même
    if item == "setup.py":
        continue
    # Ajouter tout le reste
    include_files.append(item)

# Options cx_Freeze
build_exe_options = {
    "packages": ["flask", "os", "sys", "jinja2"],
    "include_files": include_files,
    "include_msvcr": True,
}

# Configuration principale
setup(
    name=app_name,
    version="1.0",
    description="Application Flask VMaster",
    options={"build_exe": build_exe_options},
    executables=[
        Executable(
            script="app.py",
            base=None,  # Pour une app console Flask
            icon="vmaster.ico",
            target_name="VMaster.exe"
        )
    ]
)
