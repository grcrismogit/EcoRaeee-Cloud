"""Crea (o reinicia) la base de datos de EcoRAEE Cloud ejecutando los scripts SQL.

Uso, desde la carpeta backend:
    python -m scripts.init_db            # modelo físico + datos sintéticos
    python -m scripts.init_db --sin-datos

Útil en la instalación manual (sin Docker) cuando psql no está en el PATH.
ATENCIÓN: borra y vuelve a crear el esquema ecoraee.
"""
import sys
from pathlib import Path

import psycopg

from app.config import settings

RAIZ = Path(__file__).resolve().parents[2]
SCRIPTS = [RAIZ / "database" / "01_modelo_fisico_ddl.sql", RAIZ / "database" / "02_datos_sinteticos.sql"]


def main() -> None:
    archivos = SCRIPTS[:1] if "--sin-datos" in sys.argv else SCRIPTS
    conninfo = settings.database_url.replace("postgresql+psycopg://", "postgresql://")
    with psycopg.connect(conninfo, autocommit=True) as conexion:
        for archivo in archivos:
            print(f"-> Ejecutando {archivo.name} ...")
            conexion.execute(archivo.read_text(encoding="utf-8"))
        tablas = conexion.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'ecoraee' AND table_type = 'BASE TABLE'"
        ).fetchone()[0]
        dispositivos = conexion.execute("SELECT count(*) FROM ecoraee.dispositivo").fetchone()[0]
    print(f"OK. Base lista: {tablas} tablas, {dispositivos} dispositivos de prueba.")


if __name__ == "__main__":
    main()
