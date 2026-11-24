"""Autenticación con JWT y control de acceso por rol.

Las contraseñas se guardan con bcrypt (extensión pgcrypto de PostgreSQL):
nunca viajan ni se almacenan en texto plano.
"""
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import Usuario

_bearer = HTTPBearer(auto_error=False)
ALGORITMO = "HS256"


def verificar_credenciales(db: Session, email: str, password: str) -> Usuario | None:
    fila = db.execute(
        text("""SELECT id_usuario FROM usuario
                 WHERE lower(email) = lower(:email) AND activo
                   AND password_hash = crypt(:password, password_hash)"""),
        {"email": email, "password": password},
    ).first()
    return db.get(Usuario, fila.id_usuario) if fila else None


def crear_token(usuario: Usuario) -> str:
    ahora = datetime.now(timezone.utc)
    datos = {
        "sub": str(usuario.id_usuario),
        "rol": usuario.rol_codigo,
        "iat": ahora,
        "exp": ahora + timedelta(minutes=settings.jwt_minutos),
    }
    return jwt.encode(datos, settings.jwt_secret, algorithm=ALGORITMO)


def usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    no_autorizado = HTTPException(status.HTTP_401_UNAUTHORIZED, "Sesión no válida o expirada. Inicie sesión de nuevo.")
    if credenciales is None:
        raise no_autorizado
    try:
        datos = jwt.decode(credenciales.credentials, settings.jwt_secret, algorithms=[ALGORITMO])
        id_usuario = int(datos["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise no_autorizado
    usuario = db.get(Usuario, id_usuario)
    if usuario is None or not usuario.activo:
        raise no_autorizado
    # Desde aquí PostgreSQL sabe quién opera (auditoría e historial de estados)
    db.info["id_usuario"] = usuario.id_usuario
    db.execute(text("SELECT set_config('ecoraee.id_usuario', :u, true)"), {"u": str(usuario.id_usuario)})
    return usuario


def requiere_rol(*roles: str):
    """Dependencia que deja pasar al ADMIN y a los roles indicados."""
    def _verificar(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
        if usuario.rol_codigo != "ADMIN" and usuario.rol_codigo not in roles:
            permitido = ", ".join(roles) if roles else "ADMIN"
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Su rol ({usuario.rol_codigo}) no puede realizar esta acción. Requiere: {permitido}.")
        return usuario
    return _verificar


def asignar_actor(datos: dict, campo: str, usuario: Usuario, etiqueta: str) -> dict:
    """El ADMIN elige al responsable de la acción; cualquier otro rol actúa en su propio nombre."""
    if usuario.rol_codigo == "ADMIN":
        if not datos.get(campo):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Seleccione el {etiqueta}.")
    else:
        datos[campo] = usuario.id_usuario
    return datos
