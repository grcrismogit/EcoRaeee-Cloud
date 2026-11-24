"""EcoRAEE Cloud · API REST (FastAPI).

Ejecutar en local:  uvicorn app.main:app --reload --port 8000
Documentación interactiva: http://localhost:8000/docs
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .errors import registrar_manejadores
from .routers import auth, catalogos, evidencias, operacion, red, reportes, transferencias

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="EcoRAEE Cloud API",
    version="1.0.0",
    description="Gestión y trazabilidad de Residuos de Aparatos Eléctricos y Electrónicos (RAEE). "
                "Proyecto Integrador (UIDE): versión local con Docker y despliegue en AWS.",
)

# Primero los manejadores de error y después CORS: así CORS envuelve también las respuestas 500
# (si no, el navegador las ve como "error de CORS" y no muestra el mensaje real).
registrar_manejadores(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PREFIJO = "/api"
app.include_router(reportes.router, prefix=PREFIJO)
app.include_router(auth.router, prefix=PREFIJO)
for grupo in (catalogos.routers, operacion.routers, red.routers):
    for r in grupo:
        app.include_router(r, prefix=PREFIJO)
app.include_router(transferencias.router, prefix=PREFIJO)
app.include_router(evidencias.router, prefix=PREFIJO)


@app.get("/", include_in_schema=False)
def inicio():
    return {"servicio": "EcoRAEE Cloud API", "documentacion": "/docs", "salud": "/api/salud"}
