"""Manejo centralizado de errores: toda respuesta de error tiene la forma
{"detail": "mensaje legible", "codigo": "...", "errores": [...]}.
"""
import logging

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError, OperationalError

log = logging.getLogger("ecoraee")

# Mensajes legibles para las restricciones declaradas en el modelo físico
RESTRICCIONES = {
    "uq_usuario_email": "Ya existe un usuario con ese correo electrónico.",
    "uq_organizacion_identificacion": "Ya existe una organización con esa identificación (RUC/cédula).",
    "uq_centro_nombre": "Ya existe un centro con ese nombre.",
    "uq_categoria_nombre": "Ya existe una categoría con ese nombre.",
    "uq_marca_nombre": "Ya existe una marca con ese nombre.",
    "uq_tipo_centro_nombre": "Ya existe un tipo de centro con ese nombre.",
    "uq_rol_codigo": "Ya existe un rol con ese código.",
    "uq_lote_codigo": "RN-01: el código de lote ya existe.",
    "uq_dispositivo_codigo": "RN-01: el código único del dispositivo ya existe.",
    "uq_dispositivo_serie": "RN-01: ya hay un dispositivo activo con esa marca y ese número de serie.",
    "uq_recepcion_solicitud": "Esta solicitud ya tiene una recepción registrada (relación 1:1).",
    "uq_destino_dispositivo": "RN-08: el dispositivo ya tiene un destino final registrado.",
    "uq_solicitud_lote_activa": "El lote ya tiene una solicitud activa; cancélela antes de crear otra.",
    "uq_nodo_etiqueta": "Ya existe un nodo con esa etiqueta en el escenario.",
    "uq_nodo_centro_escenario": "Ese centro ya está representado por otro nodo del escenario.",
    "uq_arista": "Ya existe una arista entre esos dos nodos.",
    "uq_evidencia_s3_key": "Ya existe una evidencia con esa clave de almacenamiento.",
    "pk_detalle_transferencia": "El dispositivo ya está incluido en la transferencia.",
    "ck_evidencia_arco": "RN-07: la evidencia debe vincularse exactamente a un hecho (dispositivo, evaluación, transferencia o destino).",
    "ck_transferencia_cierre": "RN-03: una transferencia solo se cierra con responsable y fecha de recepción.",
    "ck_transferencia_centros": "El centro de origen y el de destino deben ser distintos.",
    "ck_transferencia_fechas": "La fecha de recepción no puede ser anterior a la de salida.",
    "ck_destino_beneficiaria": "Una DONACION requiere la organización beneficiaria.",
    "ck_inventario_cantidad": "RN-06: el inventario de un centro no puede quedar negativo.",
    "ck_inventario_peso": "RN-06: el inventario de un centro no puede quedar negativo.",
    "ck_arista_sin_bucle": "Una arista no puede unir un nodo consigo mismo.",
    "ck_escenario_periodo": "La fecha de fin debe ser igual o posterior a la de inicio.",
    "ck_solicitud_programada": "Una solicitud PROGRAMADA necesita fecha programada.",
    "ck_dispositivo_peso": "El peso del dispositivo debe ser mayor que cero.",
    "ck_centro_capacidad_unidades": "La capacidad en unidades debe ser mayor que cero.",
    "ck_centro_capacidad_kg": "La capacidad en kg debe ser mayor que cero.",
    "ck_usuario_email": "El correo electrónico no tiene un formato válido.",
    "fk_arista_origen": "El nodo de origen no pertenece al escenario de la arista.",
    "fk_arista_destino": "El nodo de destino no pertenece al escenario de la arista.",
}

TABLAS = {
    "dispositivo": "dispositivos", "lote": "lotes", "usuario": "usuarios", "centro": "centros",
    "evaluacion_tecnica": "evaluaciones", "transferencia": "transferencias", "evidencia": "evidencias",
    "solicitud_recoleccion": "solicitudes", "recepcion": "recepciones", "destino_final": "destinos finales",
    "nodo_red": "nodos de red", "arista_red": "aristas de red", "inventario": "inventario",
    "detalle_transferencia": "transferencias", "historial_estado": "historial", "resultado_flujo": "resultados de flujo",
}

# Traducción de los errores de validación de Pydantic
VALIDACION = {
    "missing": "es obligatorio",
    "string_too_short": "debe tener al menos {min_length} caracteres",
    "string_too_long": "debe tener como máximo {max_length} caracteres",
    "string_pattern_mismatch": "tiene un formato no válido",
    "greater_than": "debe ser mayor que {gt}",
    "greater_than_equal": "debe ser mayor o igual que {ge}",
    "less_than_equal": "debe ser menor o igual que {le}",
    "int_parsing": "debe ser un número entero",
    "int_type": "debe ser un número entero",
    "float_parsing": "debe ser un número",
    "float_type": "debe ser un número",
    "bool_parsing": "debe ser verdadero o falso",
    "date_from_datetime_parsing": "debe ser una fecha válida",
    "date_parsing": "debe ser una fecha válida",
    "datetime_parsing": "debe ser una fecha y hora válidas",
    "datetime_from_date_parsing": "debe ser una fecha y hora válidas",
    "literal_error": "debe ser uno de: {expected}",
    "too_short": "debe tener al menos {min_length} elemento(s)",
    "too_long": "tiene demasiados elementos",
    "list_type": "debe ser una lista",
    "json_invalid": "el cuerpo de la petición no es un JSON válido",
}


def _respuesta(codigo_http: int, detalle: str, codigo: str, errores: list | None = None) -> JSONResponse:
    return JSONResponse(status_code=codigo_http, content={"detail": detalle, "codigo": codigo, "errores": errores or []})


def registrar_manejadores(app: FastAPI) -> None:

    @app.exception_handler(RequestValidationError)
    async def _validacion(request: Request, exc: RequestValidationError):
        errores = []
        for e in exc.errors():
            campo = ".".join(str(p) for p in e.get("loc", []) if p not in ("body", "query", "path"))
            plantilla = VALIDACION.get(e.get("type", ""))
            if plantilla:
                try:
                    mensaje = plantilla.format(**(e.get("ctx") or {}))
                except (KeyError, IndexError):
                    mensaje = plantilla
            else:
                mensaje = str(e.get("msg", "valor no válido")).replace("Value error, ", "")
            errores.append({"campo": campo or "formulario", "mensaje": mensaje})
        resumen = "; ".join(f"{x['campo']}: {x['mensaje']}" if x["campo"] != "formulario" else x["mensaje"] for x in errores)
        return _respuesta(422, f"Revise los datos: {resumen}", "VALIDACION", errores)

    @app.exception_handler(OperationalError)
    async def _sin_bd(request: Request, exc: OperationalError):
        log.error("Base de datos no disponible: %s", exc)
        return _respuesta(503, "No hay conexión con la base de datos. Verifique que PostgreSQL esté encendido.", "BD_NO_DISPONIBLE")

    @app.exception_handler(DBAPIError)
    async def _base_datos(request: Request, exc: DBAPIError):
        orig = exc.orig
        sqlstate = getattr(orig, "sqlstate", None)
        diag = getattr(orig, "diag", None)
        primario = getattr(diag, "message_primary", None) or str(orig)
        restriccion = getattr(diag, "constraint_name", None)
        detalle_pg = getattr(diag, "message_detail", "") or ""

        if sqlstate == "P0001":  # RAISE EXCEPTION de un trigger o procedimiento: regla de negocio
            return _respuesta(409, primario, "REGLA_NEGOCIO")
        if sqlstate == "23505":
            return _respuesta(409, RESTRICCIONES.get(restriccion, "Ya existe un registro con esos datos."), "DUPLICADO")
        if sqlstate == "23503":
            if restriccion in RESTRICCIONES:
                return _respuesta(409, RESTRICCIONES[restriccion], "REFERENCIA")
            if "still referenced" in detalle_pg:
                tabla = detalle_pg.rsplit('"', 2)[-2] if '"' in detalle_pg else ""
                return _respuesta(409, f"No se puede eliminar: el registro está siendo usado en {TABLAS.get(tabla, tabla)}.", "EN_USO")
            return _respuesta(422, "El registro relacionado que seleccionó no existe.", "REFERENCIA")
        if sqlstate == "23514":
            return _respuesta(422, RESTRICCIONES.get(restriccion, f"Los datos no cumplen la restricción {restriccion}."), "RESTRICCION")
        if sqlstate == "23502":
            columna = getattr(diag, "column_name", "un campo")
            return _respuesta(422, f"Falta el campo obligatorio {columna}.", "OBLIGATORIO")
        if sqlstate and sqlstate.startswith("22"):
            return _respuesta(422, "Uno de los valores enviados no es válido para la base de datos.", "DATO_INVALIDO")
        log.exception("Error de base de datos no controlado")
        return _respuesta(500, "Error inesperado en la base de datos.", "ERROR_BD")

    @app.exception_handler(ClientError)
    @app.exception_handler(BotoCoreError)
    async def _aws(request: Request, exc: Exception):
        codigo = exc.response.get("Error", {}).get("Code", "") if isinstance(exc, ClientError) else type(exc).__name__
        log.error("Error de AWS (%s): %s", codigo, exc)
        return _respuesta(502, f"No se pudo usar el servicio de AWS ({codigo}). Revise el rol IAM de la instancia "
                               "y los parámetros /ecoraee/* (nombre del bucket y del tópico).", "ERROR_AWS")

    @app.middleware("http")
    async def _general(request: Request, call_next):
        # Middleware (no exception_handler): así la respuesta 500 pasa por CORS
        try:
            return await call_next(request)
        except Exception:
            log.exception("Error no controlado")
            return _respuesta(500, "Ocurrió un error inesperado en el servidor.", "ERROR_INTERNO")
