"""Modelos ORM: una clase por cada una de las 24 tablas de negocio del esquema ecoraee
(la tabla 25, correlativo, solo la usan los triggers que generan los códigos).

Las columnas que calcula la base (identidades, valores por defecto o campos
que mantienen los triggers) se marcan con FetchedValue para que SQLAlchemy
las lea de PostgreSQL en lugar de enviarlas.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (BigInteger, Boolean, CHAR, Date, FetchedValue, ForeignKey, Identity, Integer,
                        Numeric, SmallInteger, String)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .services import almacenamiento

TSTZ = TIMESTAMP(timezone=True)


def _pk_big():
    return mapped_column(BigInteger, Identity(always=True), primary_key=True)


def _pk_small():
    return mapped_column(SmallInteger, Identity(always=True), primary_key=True)


def _server(tipo, **kw):
    return mapped_column(tipo, server_default=FetchedValue(), **kw)


# --------------------------------------------------------------------- catálogos
class Organizacion(Base):
    __tablename__ = "organizacion"
    id_organizacion: Mapped[int] = _pk_big()
    nombre: Mapped[str] = mapped_column(String(150))
    tipo_organizacion: Mapped[str] = mapped_column(String(30))
    identificacion: Mapped[str] = mapped_column(String(20))
    email_contacto: Mapped[Optional[str]] = mapped_column(String(120))
    telefono: Mapped[Optional[str]] = mapped_column(String(20))
    activo: Mapped[bool] = _server(Boolean)
    fecha_creacion: Mapped[datetime] = _server(TSTZ)


class Rol(Base):
    __tablename__ = "rol"
    id_rol: Mapped[int] = _pk_small()
    codigo: Mapped[str] = mapped_column(String(30))
    descripcion: Mapped[str] = mapped_column(String(200))


class Usuario(Base):
    __tablename__ = "usuario"
    id_usuario: Mapped[int] = _pk_big()
    id_organizacion: Mapped[int] = mapped_column(ForeignKey("organizacion.id_organizacion"))
    id_rol: Mapped[int] = mapped_column(ForeignKey("rol.id_rol"))
    nombres: Mapped[str] = mapped_column(String(80))
    apellidos: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    activo: Mapped[bool] = _server(Boolean)
    fecha_creacion: Mapped[datetime] = _server(TSTZ)

    rol: Mapped[Rol] = relationship(lazy="joined")
    organizacion: Mapped[Organizacion] = relationship(lazy="joined")

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombres} {self.apellidos}"

    @property
    def rol_codigo(self) -> str:
        return self.rol.codigo

    @property
    def organizacion_nombre(self) -> str:
        return self.organizacion.nombre


class TipoCentro(Base):
    __tablename__ = "tipo_centro"
    id_tipo_centro: Mapped[int] = _pk_small()
    nombre: Mapped[str] = mapped_column(String(40))
    descripcion: Mapped[Optional[str]] = mapped_column(String(200))


class Centro(Base):
    __tablename__ = "centro"
    id_centro: Mapped[int] = _pk_big()
    id_organizacion: Mapped[int] = mapped_column(ForeignKey("organizacion.id_organizacion"))
    id_tipo_centro: Mapped[int] = mapped_column(ForeignKey("tipo_centro.id_tipo_centro"))
    nombre: Mapped[str] = mapped_column(String(120))
    direccion: Mapped[str] = mapped_column(String(200))
    ciudad: Mapped[str] = mapped_column(String(60))
    capacidad_unidades: Mapped[int] = mapped_column(Integer)
    capacidad_kg: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    activo: Mapped[bool] = _server(Boolean)

    organizacion: Mapped[Organizacion] = relationship(lazy="joined")
    tipo_centro: Mapped[TipoCentro] = relationship(lazy="joined")

    @property
    def organizacion_nombre(self) -> str:
        return self.organizacion.nombre

    @property
    def tipo_centro_nombre(self) -> str:
        return self.tipo_centro.nombre


class Categoria(Base):
    __tablename__ = "categoria"
    id_categoria: Mapped[int] = _pk_small()
    nombre: Mapped[str] = mapped_column(String(60))
    descripcion: Mapped[Optional[str]] = mapped_column(String(200))
    peligrosidad: Mapped[str] = mapped_column(String(10))


class Marca(Base):
    __tablename__ = "marca"
    id_marca: Mapped[int] = _pk_small()
    nombre: Mapped[str] = mapped_column(String(60))


# --------------------------------------------------------------------- operación
class Lote(Base):
    __tablename__ = "lote"
    id_lote: Mapped[int] = _pk_big()
    codigo_lote: Mapped[str] = _server(String(20))
    id_generador: Mapped[int] = mapped_column(ForeignKey("usuario.id_usuario"))
    fecha_registro: Mapped[datetime] = _server(TSTZ)
    descripcion: Mapped[Optional[str]] = mapped_column(String(250))
    estado: Mapped[str] = _server(String(20))

    generador: Mapped[Usuario] = relationship(lazy="joined")
    dispositivos: Mapped[list["Dispositivo"]] = relationship(
        back_populates="lote", lazy="selectin", order_by="Dispositivo.id_dispositivo",
        passive_deletes="all",  # la base decide (FK RESTRICT)
    )

    @property
    def generador_nombre(self) -> str:
        return self.generador.nombre_completo

    @property
    def num_dispositivos(self) -> int:
        return len(self.dispositivos)

    @property
    def peso_total_kg(self) -> float:
        return float(sum(d.peso_kg for d in self.dispositivos))


class Dispositivo(Base):
    __tablename__ = "dispositivo"
    id_dispositivo: Mapped[int] = _pk_big()
    codigo_unico: Mapped[str] = _server(String(25))
    id_lote: Mapped[int] = mapped_column(ForeignKey("lote.id_lote"))
    id_categoria: Mapped[int] = mapped_column(ForeignKey("categoria.id_categoria"))
    id_marca: Mapped[Optional[int]] = mapped_column(ForeignKey("marca.id_marca"))
    id_centro_actual: Mapped[Optional[int]] = _server(BigInteger, nullable=True)  # lo mantienen los procesos
    modelo: Mapped[Optional[str]] = mapped_column(String(80))
    numero_serie: Mapped[Optional[str]] = mapped_column(String(60))
    peso_kg: Mapped[Decimal] = mapped_column(Numeric(7, 2))
    estado_actual: Mapped[str] = _server(String(20))          # lo mantienen los triggers
    clasificacion: Mapped[Optional[str]] = _server(String(20), nullable=True)
    fecha_registro: Mapped[datetime] = _server(TSTZ)

    lote: Mapped[Lote] = relationship(back_populates="dispositivos", lazy="joined")
    categoria: Mapped[Categoria] = relationship(lazy="joined")
    marca: Mapped[Optional[Marca]] = relationship(lazy="joined")
    centro_actual: Mapped[Optional[Centro]] = relationship(
        lazy="joined", primaryjoin="Dispositivo.id_centro_actual == Centro.id_centro",
        foreign_keys="Dispositivo.id_centro_actual",
    )

    @property
    def codigo_lote(self) -> str:
        return self.lote.codigo_lote

    @property
    def categoria_nombre(self) -> str:
        return self.categoria.nombre

    @property
    def marca_nombre(self) -> Optional[str]:
        return self.marca.nombre if self.marca else None

    @property
    def centro_actual_nombre(self) -> Optional[str]:
        return self.centro_actual.nombre if self.centro_actual else None


class SolicitudRecoleccion(Base):
    __tablename__ = "solicitud_recoleccion"
    id_solicitud: Mapped[int] = _pk_big()
    id_lote: Mapped[int] = mapped_column(ForeignKey("lote.id_lote"))
    id_solicitante: Mapped[int] = mapped_column(ForeignKey("usuario.id_usuario"))
    id_centro_destino: Mapped[int] = mapped_column(ForeignKey("centro.id_centro"))
    modalidad: Mapped[str] = mapped_column(String(15))
    fecha_solicitud: Mapped[datetime] = _server(TSTZ)
    fecha_programada: Mapped[Optional[date]] = mapped_column(Date)
    estado: Mapped[str] = _server(String(15))

    lote: Mapped[Lote] = relationship(lazy="joined")
    solicitante: Mapped[Usuario] = relationship(lazy="joined")
    centro_destino: Mapped[Centro] = relationship(lazy="joined")

    @property
    def codigo_lote(self) -> str:
        return self.lote.codigo_lote

    @property
    def solicitante_nombre(self) -> str:
        return self.solicitante.nombre_completo

    @property
    def centro_destino_nombre(self) -> str:
        return self.centro_destino.nombre


class Recepcion(Base):
    __tablename__ = "recepcion"
    id_recepcion: Mapped[int] = _pk_big()
    id_solicitud: Mapped[int] = mapped_column(ForeignKey("solicitud_recoleccion.id_solicitud"))
    id_centro: Mapped[int] = mapped_column(ForeignKey("centro.id_centro"))
    id_operador: Mapped[int] = mapped_column(ForeignKey("usuario.id_usuario"))
    fecha_recepcion: Mapped[datetime] = _server(TSTZ)
    peso_recibido_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    observaciones: Mapped[Optional[str]] = mapped_column(String(300))

    solicitud: Mapped[SolicitudRecoleccion] = relationship(lazy="joined")
    centro: Mapped[Centro] = relationship(lazy="joined")
    operador: Mapped[Usuario] = relationship(lazy="joined")

    @property
    def codigo_lote(self) -> str:
        return self.solicitud.lote.codigo_lote

    @property
    def centro_nombre(self) -> str:
        return self.centro.nombre

    @property
    def operador_nombre(self) -> str:
        return self.operador.nombre_completo


class EvaluacionTecnica(Base):
    __tablename__ = "evaluacion_tecnica"
    id_evaluacion: Mapped[int] = _pk_big()
    id_dispositivo: Mapped[int] = mapped_column(ForeignKey("dispositivo.id_dispositivo"))
    id_tecnico: Mapped[int] = mapped_column(ForeignKey("usuario.id_usuario"))
    fecha_evaluacion: Mapped[datetime] = _server(TSTZ)
    condicion: Mapped[str] = mapped_column(String(15))
    clasificacion: Mapped[str] = mapped_column(String(20))
    borrado_datos: Mapped[bool] = mapped_column(Boolean)
    observaciones: Mapped[Optional[str]] = mapped_column(String(300))

    dispositivo: Mapped[Dispositivo] = relationship(lazy="joined")
    tecnico: Mapped[Usuario] = relationship(lazy="joined")

    @property
    def codigo_unico(self) -> str:
        return self.dispositivo.codigo_unico

    @property
    def dispositivo_descripcion(self) -> str:
        d = self.dispositivo
        return " ".join(x for x in [d.categoria.nombre, d.marca.nombre if d.marca else None, d.modelo] if x)

    @property
    def tecnico_nombre(self) -> str:
        return self.tecnico.nombre_completo


class HistorialEstado(Base):
    """Entidad débil: PK = (id_dispositivo, nro_cambio)."""
    __tablename__ = "historial_estado"
    id_dispositivo: Mapped[int] = mapped_column(ForeignKey("dispositivo.id_dispositivo"), primary_key=True)
    nro_cambio: Mapped[int] = mapped_column(Integer, primary_key=True)
    estado_anterior: Mapped[Optional[str]] = mapped_column(String(20))
    estado_nuevo: Mapped[str] = mapped_column(String(20))
    id_usuario: Mapped[Optional[int]] = mapped_column(ForeignKey("usuario.id_usuario"))
    fecha_cambio: Mapped[datetime] = _server(TSTZ)

    usuario: Mapped[Optional[Usuario]] = relationship(lazy="joined")
    dispositivo: Mapped[Dispositivo] = relationship(lazy="joined")

    @property
    def usuario_nombre(self) -> Optional[str]:
        return self.usuario.nombre_completo if self.usuario else None

    @property
    def codigo_unico(self) -> str:
        return self.dispositivo.codigo_unico


class Inventario(Base):
    __tablename__ = "inventario"
    id_centro: Mapped[int] = mapped_column(ForeignKey("centro.id_centro"), primary_key=True)
    id_categoria: Mapped[int] = mapped_column(ForeignKey("categoria.id_categoria"), primary_key=True)
    cantidad_unidades: Mapped[int] = mapped_column(Integer)
    peso_total_kg: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    fecha_actualizacion: Mapped[datetime] = _server(TSTZ)

    centro: Mapped[Centro] = relationship(lazy="joined")
    categoria: Mapped[Categoria] = relationship(lazy="joined")

    @property
    def centro_nombre(self) -> str:
        return self.centro.nombre

    @property
    def categoria_nombre(self) -> str:
        return self.categoria.nombre


# --------------------------------------------------------------------- red y transferencias
class EscenarioRed(Base):
    __tablename__ = "escenario_red"
    id_escenario: Mapped[int] = _pk_big()
    nombre: Mapped[str] = mapped_column(String(80))
    periodo_inicio: Mapped[date] = mapped_column(Date)
    periodo_fin: Mapped[date] = mapped_column(Date)
    unidad_medida: Mapped[str] = mapped_column(String(10))
    descripcion: Mapped[Optional[str]] = mapped_column(String(250))


class NodoRed(Base):
    __tablename__ = "nodo_red"
    id_nodo: Mapped[int] = _pk_big()
    id_escenario: Mapped[int] = mapped_column(ForeignKey("escenario_red.id_escenario"))
    id_centro: Mapped[Optional[int]] = mapped_column(ForeignKey("centro.id_centro"))
    etiqueta: Mapped[str] = mapped_column(String(20))
    tipo_nodo: Mapped[str] = mapped_column(String(12))

    centro: Mapped[Optional[Centro]] = relationship(lazy="joined")

    @property
    def centro_nombre(self) -> Optional[str]:
        return self.centro.nombre if self.centro else None


class AristaRed(Base):
    __tablename__ = "arista_red"
    id_arista: Mapped[int] = _pk_big()
    id_escenario: Mapped[int] = mapped_column(ForeignKey("escenario_red.id_escenario"))
    id_nodo_origen: Mapped[int] = mapped_column(BigInteger)
    id_nodo_destino: Mapped[int] = mapped_column(BigInteger)
    capacidad: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    nodo_origen: Mapped[NodoRed] = relationship(
        lazy="joined", primaryjoin="AristaRed.id_nodo_origen == NodoRed.id_nodo", foreign_keys="AristaRed.id_nodo_origen"
    )
    nodo_destino: Mapped[NodoRed] = relationship(
        lazy="joined", primaryjoin="AristaRed.id_nodo_destino == NodoRed.id_nodo", foreign_keys="AristaRed.id_nodo_destino"
    )
    escenario: Mapped[EscenarioRed] = relationship(lazy="joined")

    @property
    def origen_etiqueta(self) -> str:
        return self.nodo_origen.etiqueta

    @property
    def destino_etiqueta(self) -> str:
        return self.nodo_destino.etiqueta

    @property
    def descripcion(self) -> str:
        return f"{self.nodo_origen.etiqueta} → {self.nodo_destino.etiqueta} (cap. {float(self.capacidad):g} {self.escenario.unidad_medida.lower()})"


class Transferencia(Base):
    __tablename__ = "transferencia"
    id_transferencia: Mapped[int] = _pk_big()
    id_centro_origen: Mapped[int] = mapped_column(BigInteger)
    id_centro_destino: Mapped[int] = mapped_column(BigInteger)
    id_coordinador: Mapped[int] = mapped_column(BigInteger)
    id_responsable: Mapped[Optional[int]] = mapped_column(BigInteger)
    id_arista: Mapped[Optional[int]] = mapped_column(ForeignKey("arista_red.id_arista"))
    fecha_salida: Mapped[datetime] = _server(TSTZ)
    fecha_recepcion: Mapped[Optional[datetime]] = mapped_column(TSTZ)
    estado: Mapped[str] = _server(String(15))

    centro_origen: Mapped[Centro] = relationship(
        lazy="joined", primaryjoin="Transferencia.id_centro_origen == Centro.id_centro", foreign_keys="Transferencia.id_centro_origen")
    centro_destino: Mapped[Centro] = relationship(
        lazy="joined", primaryjoin="Transferencia.id_centro_destino == Centro.id_centro", foreign_keys="Transferencia.id_centro_destino")
    coordinador: Mapped[Usuario] = relationship(
        lazy="joined", primaryjoin="Transferencia.id_coordinador == Usuario.id_usuario", foreign_keys="Transferencia.id_coordinador")
    responsable: Mapped[Optional[Usuario]] = relationship(
        lazy="joined", primaryjoin="Transferencia.id_responsable == Usuario.id_usuario", foreign_keys="Transferencia.id_responsable")
    arista: Mapped[Optional[AristaRed]] = relationship(lazy="joined")
    detalles: Mapped[list["DetalleTransferencia"]] = relationship(
        lazy="selectin", back_populates="transferencia", passive_deletes="all")  # ON DELETE CASCADE en la base

    @property
    def centro_origen_nombre(self) -> str:
        return self.centro_origen.nombre

    @property
    def centro_destino_nombre(self) -> str:
        return self.centro_destino.nombre

    @property
    def coordinador_nombre(self) -> str:
        return self.coordinador.nombre_completo

    @property
    def responsable_nombre(self) -> Optional[str]:
        return self.responsable.nombre_completo if self.responsable else None

    @property
    def arista_descripcion(self) -> Optional[str]:
        return self.arista.descripcion if self.arista else None

    @property
    def dispositivos(self) -> list[Dispositivo]:
        return [d.dispositivo for d in self.detalles]

    @property
    def num_dispositivos(self) -> int:
        return len(self.detalles)


class DetalleTransferencia(Base):
    __tablename__ = "detalle_transferencia"
    id_transferencia: Mapped[int] = mapped_column(ForeignKey("transferencia.id_transferencia"), primary_key=True)
    id_dispositivo: Mapped[int] = mapped_column(ForeignKey("dispositivo.id_dispositivo"), primary_key=True)

    transferencia: Mapped[Transferencia] = relationship(back_populates="detalles")
    dispositivo: Mapped[Dispositivo] = relationship(lazy="joined")


class DestinoFinal(Base):
    __tablename__ = "destino_final"
    id_destino_final: Mapped[int] = _pk_big()
    id_dispositivo: Mapped[int] = mapped_column(ForeignKey("dispositivo.id_dispositivo"))
    id_centro: Mapped[int] = mapped_column(ForeignKey("centro.id_centro"))
    id_org_beneficiaria: Mapped[Optional[int]] = mapped_column(ForeignKey("organizacion.id_organizacion"))
    tipo_destino: Mapped[str] = mapped_column(String(25))
    fecha_confirmacion: Mapped[datetime] = _server(TSTZ)
    id_usuario_confirma: Mapped[int] = mapped_column(ForeignKey("usuario.id_usuario"))

    dispositivo: Mapped[Dispositivo] = relationship(lazy="joined")
    centro: Mapped[Centro] = relationship(lazy="joined")
    org_beneficiaria: Mapped[Optional[Organizacion]] = relationship(lazy="joined")
    usuario_confirma: Mapped[Usuario] = relationship(lazy="joined")

    @property
    def codigo_unico(self) -> str:
        return self.dispositivo.codigo_unico

    @property
    def clasificacion(self) -> Optional[str]:
        return self.dispositivo.clasificacion

    @property
    def centro_nombre(self) -> str:
        return self.centro.nombre

    @property
    def org_beneficiaria_nombre(self) -> Optional[str]:
        return self.org_beneficiaria.nombre if self.org_beneficiaria else None

    @property
    def usuario_confirma_nombre(self) -> str:
        return self.usuario_confirma.nombre_completo


class Evidencia(Base):
    __tablename__ = "evidencia"
    id_evidencia: Mapped[int] = _pk_big()
    tipo_evidencia: Mapped[str] = mapped_column(String(15))
    s3_key: Mapped[str] = mapped_column(String(300))
    hash_sha256: Mapped[str] = mapped_column(CHAR(64))
    id_usuario_carga: Mapped[int] = mapped_column(ForeignKey("usuario.id_usuario"))
    fecha_carga: Mapped[datetime] = _server(TSTZ)
    id_dispositivo: Mapped[Optional[int]] = mapped_column(ForeignKey("dispositivo.id_dispositivo"))
    id_evaluacion: Mapped[Optional[int]] = mapped_column(ForeignKey("evaluacion_tecnica.id_evaluacion"))
    id_transferencia: Mapped[Optional[int]] = mapped_column(ForeignKey("transferencia.id_transferencia"))
    id_destino_final: Mapped[Optional[int]] = mapped_column(ForeignKey("destino_final.id_destino_final"))

    usuario_carga: Mapped[Usuario] = relationship(lazy="joined")
    dispositivo: Mapped[Optional[Dispositivo]] = relationship(lazy="joined")
    evaluacion: Mapped[Optional[EvaluacionTecnica]] = relationship(lazy="joined")
    destino_final: Mapped[Optional[DestinoFinal]] = relationship(lazy="joined")

    @property
    def usuario_carga_nombre(self) -> str:
        return self.usuario_carga.nombre_completo

    @property
    def nombre_archivo(self) -> str:
        return self.s3_key.rsplit("/", 1)[-1]

    @property
    def vinculo(self) -> str:
        # Al usuario se le muestra el código único del equipo (RN-01), nunca el id interno
        if self.id_dispositivo:
            return f"Dispositivo {self.dispositivo.codigo_unico}"
        if self.id_evaluacion:
            return f"Evaluación de {self.evaluacion.codigo_unico}"
        if self.id_transferencia:
            return f"Transferencia #{self.id_transferencia}"
        return f"Destino final de {self.destino_final.codigo_unico}"

    @property
    def url(self) -> Optional[str]:
        """URL prefirmada de S3 para ver el archivo (None si se usa la carpeta local)."""
        return almacenamiento.url_temporal(self.s3_key, self.nombre_archivo)


class ResultadoFlujo(Base):
    __tablename__ = "resultado_flujo"
    id_resultado: Mapped[int] = _pk_big()
    id_escenario: Mapped[int] = mapped_column(ForeignKey("escenario_red.id_escenario"))
    algoritmo: Mapped[str] = mapped_column(String(30))
    flujo_maximo: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    fecha_ejecucion: Mapped[datetime] = _server(TSTZ)
    id_ejecutor: Mapped[Optional[int]] = mapped_column(ForeignKey("usuario.id_usuario"))

    flujos: Mapped[list["FlujoArista"]] = relationship(lazy="selectin", passive_deletes="all")
    ejecutor: Mapped[Optional[Usuario]] = relationship(lazy="joined")

    @property
    def ejecutor_nombre(self) -> Optional[str]:
        return self.ejecutor.nombre_completo if self.ejecutor else None


class FlujoArista(Base):
    __tablename__ = "flujo_arista"
    id_resultado: Mapped[int] = mapped_column(ForeignKey("resultado_flujo.id_resultado"), primary_key=True)
    id_arista: Mapped[int] = mapped_column(ForeignKey("arista_red.id_arista"), primary_key=True)
    flujo: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    saturada: Mapped[bool] = mapped_column(Boolean)
    en_corte_minimo: Mapped[bool] = mapped_column(Boolean)


class Auditoria(Base):
    __tablename__ = "auditoria"
    id_auditoria: Mapped[int] = _pk_big()
    tabla: Mapped[str] = mapped_column(String(40))
    operacion: Mapped[str] = mapped_column(CHAR(1))
    id_registro: Mapped[int] = mapped_column(BigInteger)
    id_usuario: Mapped[Optional[int]] = mapped_column(ForeignKey("usuario.id_usuario"))
    fecha: Mapped[datetime] = _server(TSTZ)
    datos_antes: Mapped[Optional[dict]] = mapped_column(JSONB)
    datos_despues: Mapped[Optional[dict]] = mapped_column(JSONB)

    usuario: Mapped[Optional[Usuario]] = relationship(lazy="joined")

    @property
    def usuario_nombre(self) -> Optional[str]:
        return self.usuario.nombre_completo if self.usuario else None
