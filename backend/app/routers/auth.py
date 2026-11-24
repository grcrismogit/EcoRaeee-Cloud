"""Inicio de sesión."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Usuario
from ..schemas import LoginIn, TokenOut, UsuarioSesion
from ..security import crear_token, usuario_actual, verificar_credenciales

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=TokenOut, summary="Iniciar sesión")
def login(datos: LoginIn, db: Session = Depends(get_db)):
    usuario = verificar_credenciales(db, datos.email, datos.password)
    if usuario is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Correo o contraseña incorrectos, o usuario inactivo.")
    return TokenOut(access_token=crear_token(usuario), usuario=UsuarioSesion.model_validate(usuario))


@router.get("/me", response_model=UsuarioSesion, summary="Usuario de la sesión actual")
def me(usuario: Usuario = Depends(usuario_actual)):
    return usuario
