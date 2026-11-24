"""Catálogos y administración: organizaciones, roles, tipos de centro, centros,
categorías, marcas y usuarios."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..crud import crear_router_crud, obtener_o_404
from ..database import get_db
from ..models import Categoria, Centro, Marca, Organizacion, Rol, TipoCentro, Usuario
from ..schemas import (CategoriaIn, CategoriaOut, CentroIn, CentroOut, MarcaIn, MarcaOut, OrganizacionIn,
                       OrganizacionOut, RolOut, TipoCentroIn, TipoCentroOut, UsuarioCrear, UsuarioEditar, UsuarioOut)
from ..security import requiere_rol, usuario_actual

organizaciones = crear_router_crud(
    prefijo="/organizaciones", etiqueta="Organizaciones", nombre="Organización", modelo=Organizacion,
    esquema_crear=OrganizacionIn, esquema_salida=OrganizacionOut, orden=Organizacion.nombre,
    filtros={"tipo_organizacion": (Organizacion.tipo_organizacion, str)},
    busqueda=[Organizacion.nombre, Organizacion.identificacion],
)

tipos_centro = crear_router_crud(
    prefijo="/tipos-centro", etiqueta="Tipos de centro", nombre="Tipo de centro", modelo=TipoCentro,
    esquema_crear=TipoCentroIn, esquema_salida=TipoCentroOut, orden=TipoCentro.id_tipo_centro,
)

centros = crear_router_crud(
    prefijo="/centros", etiqueta="Centros", nombre="Centro", modelo=Centro,
    esquema_crear=CentroIn, esquema_salida=CentroOut, orden=Centro.id_centro,
    filtros={"id_tipo_centro": (Centro.id_tipo_centro, int), "id_organizacion": (Centro.id_organizacion, int)},
    busqueda=[Centro.nombre, Centro.ciudad],
)

categorias = crear_router_crud(
    prefijo="/categorias", etiqueta="Categorías", nombre="Categoría", modelo=Categoria,
    esquema_crear=CategoriaIn, esquema_salida=CategoriaOut, orden=Categoria.id_categoria,
    busqueda=[Categoria.nombre],
)

marcas = crear_router_crud(
    prefijo="/marcas", etiqueta="Marcas", nombre="Marca", modelo=Marca,
    esquema_crear=MarcaIn, esquema_salida=MarcaOut, orden=Marca.nombre, busqueda=[Marca.nombre],
)

# --------------------------------------------------------------------- roles (solo lectura)
roles = APIRouter(prefix="/roles", tags=["Roles"])


@roles.get("", response_model=list[RolOut], summary="Listar roles")
def listar_roles(db: Session = Depends(get_db), _: Usuario = Depends(usuario_actual)):
    return db.scalars(select(Rol).order_by(Rol.id_rol)).all()


# --------------------------------------------------------------------- usuarios
usuarios = APIRouter(prefix="/usuarios", tags=["Usuarios"])
solo_admin = requiere_rol()


@usuarios.get("", response_model=list[UsuarioOut], summary="Listar usuarios")
def listar_usuarios(rol: Optional[str] = None, activo: Optional[bool] = None, q: Optional[str] = None,
                    db: Session = Depends(get_db), _: Usuario = Depends(usuario_actual)):
    consulta = select(Usuario).join(Rol).order_by(Usuario.id_usuario)
    if rol:
        consulta = consulta.where(Rol.codigo.in_(rol.split(",")))
    if activo is not None:
        consulta = consulta.where(Usuario.activo == activo)
    if q:
        p = f"%{q.strip()}%"
        consulta = consulta.where(or_(Usuario.nombres.ilike(p), Usuario.apellidos.ilike(p), Usuario.email.ilike(p)))
    return db.scalars(consulta).unique().all()


@usuarios.get("/{id_}", response_model=UsuarioOut, summary="Obtener usuario")
def obtener_usuario(id_: int, db: Session = Depends(get_db), _: Usuario = Depends(usuario_actual)):
    return obtener_o_404(db, Usuario, id_, "Usuario")


@usuarios.post("", response_model=UsuarioOut, status_code=201, summary="Crear usuario")
def crear_usuario(datos: UsuarioCrear, db: Session = Depends(get_db), _: Usuario = Depends(solo_admin)):
    valores = datos.model_dump(exclude={"password"})
    usuario = Usuario(**valores)
    # bcrypt calculado por PostgreSQL (pgcrypto): la contraseña nunca se guarda en texto plano
    usuario.password_hash = func.crypt(datos.password, func.gen_salt("bf", 8))
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@usuarios.put("/{id_}", response_model=UsuarioOut, summary="Actualizar usuario")
def actualizar_usuario(id_: int, datos: UsuarioEditar, db: Session = Depends(get_db),
                       actual: Usuario = Depends(solo_admin)):
    usuario = obtener_o_404(db, Usuario, id_, "Usuario")
    if usuario.id_usuario == actual.id_usuario and not datos.activo:
        raise HTTPException(409, "No puede desactivar su propio usuario.")
    for campo, valor in datos.model_dump(exclude={"password"}).items():
        setattr(usuario, campo, valor)
    if datos.password:
        usuario.password_hash = func.crypt(datos.password, func.gen_salt("bf", 8))
    db.commit()
    db.refresh(usuario)
    return usuario


@usuarios.delete("/{id_}", status_code=204, summary="Eliminar usuario")
def eliminar_usuario(id_: int, db: Session = Depends(get_db), actual: Usuario = Depends(solo_admin)):
    usuario = obtener_o_404(db, Usuario, id_, "Usuario")
    if usuario.id_usuario == actual.id_usuario:
        raise HTTPException(409, "No puede eliminar su propio usuario.")
    db.delete(usuario)
    db.commit()  # si ya participó en procesos, la FK lo impide y se sugiere desactivarlo
    return Response(status_code=204)


routers = [organizaciones, roles, usuarios, tipos_centro, centros, categorias, marcas]
