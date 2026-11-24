"""Esquemas Pydantic: validan lo que llega del frontend y dan forma a las respuestas."""
from datetime import date, datetime
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

# ------------------------------------------------------------------ tipos reutilizables
def Texto(minimo: int = 1, maximo: int = 255):
    return Annotated[str, StringConstraints(strip_whitespace=True, min_length=minimo, max_length=maximo)]


Email = Annotated[str, StringConstraints(strip_whitespace=True, max_length=120,
                                         pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")]
Telefono = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^\+?[0-9 ]{7,20}$")]
Identificacion = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[0-9]{10}([0-9]{3})?$")]
Id = Annotated[int, Field(gt=0)]

TipoOrganizacion = Literal["UNIVERSIDAD", "FACULTAD", "REACONDICIONADOR", "GESTOR_RECICLAJE", "BENEFICIARIA"]
Peligrosidad = Literal["BAJA", "MEDIA", "ALTA"]
Modalidad = Literal["RECOLECCION", "ENTREGA"]
Condicion = Literal["FUNCIONAL", "CON_FALLAS", "DANADO", "INSERVIBLE"]
Clasificacion = Literal["REUTILIZABLE", "REPARABLE", "RECICLABLE", "NO_RECUPERABLE"]
TipoDestino = Literal["REUTILIZACION", "REACONDICIONAMIENTO", "RECICLAJE", "DISPOSICION_FINAL", "DONACION"]
TipoEvidencia = Literal["FOTO", "ACTA", "INFORME", "CERTIFICADO"]
TipoNodo = Literal["FUENTE", "INTERMEDIO", "SUMIDERO"]
UnidadMedida = Literal["UNIDADES", "KG"]


class Salida(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def _vacio_a_none(v):
    return None if isinstance(v, str) and not v.strip() else v


# ------------------------------------------------------------------ autenticación
class LoginIn(BaseModel):
    email: Email
    password: Texto(1, 128)


class UsuarioSesion(Salida):
    id_usuario: int
    nombres: str
    apellidos: str
    email: str
    rol_codigo: str
    organizacion_nombre: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioSesion


# ------------------------------------------------------------------ organizaciones
class OrganizacionIn(BaseModel):
    nombre: Texto(3, 150)
    tipo_organizacion: TipoOrganizacion
    identificacion: Identificacion
    email_contacto: Optional[Email] = None
    telefono: Optional[Telefono] = None
    activo: bool = True
    _limpiar = field_validator("email_contacto", "telefono", mode="before")(_vacio_a_none)


class OrganizacionOut(Salida):
    id_organizacion: int
    nombre: str
    tipo_organizacion: str
    identificacion: str
    email_contacto: Optional[str]
    telefono: Optional[str]
    activo: bool
    fecha_creacion: datetime


class RolOut(Salida):
    id_rol: int
    codigo: str
    descripcion: str


# ------------------------------------------------------------------ usuarios
class UsuarioCrear(BaseModel):
    id_organizacion: Id
    id_rol: Id
    nombres: Texto(2, 80)
    apellidos: Texto(2, 80)
    email: Email
    password: Texto(8, 72)
    activo: bool = True

    @field_validator("password")
    @classmethod
    def _password_segura(cls, v: str) -> str:
        if not any(c.isdigit() for c in v) or not any(c.isalpha() for c in v):
            raise ValueError("la contraseña debe combinar letras y números")
        return v


class UsuarioEditar(UsuarioCrear):
    password: Optional[Texto(8, 72)] = None  # vacío = no cambiar
    _limpiar = field_validator("password", mode="before")(_vacio_a_none)

    @field_validator("password")
    @classmethod
    def _password_segura(cls, v):
        if v is not None and (not any(c.isdigit() for c in v) or not any(c.isalpha() for c in v)):
            raise ValueError("la contraseña debe combinar letras y números")
        return v


class UsuarioOut(Salida):
    id_usuario: int
    id_organizacion: int
    organizacion_nombre: str
    id_rol: int
    rol_codigo: str
    nombres: str
    apellidos: str
    nombre_completo: str
    email: str
    activo: bool
    fecha_creacion: datetime


# ------------------------------------------------------------------ centros y catálogos
class TipoCentroIn(BaseModel):
    nombre: Texto(3, 40)
    descripcion: Optional[Texto(0, 200)] = None


class TipoCentroOut(Salida):
    id_tipo_centro: int
    nombre: str
    descripcion: Optional[str]


class CentroIn(BaseModel):
    id_organizacion: Id
    id_tipo_centro: Id
    nombre: Texto(3, 120)
    direccion: Texto(5, 200)
    ciudad: Texto(3, 60)
    capacidad_unidades: Annotated[int, Field(gt=0, le=1_000_000)]
    capacidad_kg: Annotated[float, Field(gt=0, le=99_999_999)]
    activo: bool = True


class CentroOut(Salida):
    id_centro: int
    id_organizacion: int
    organizacion_nombre: str
    id_tipo_centro: int
    tipo_centro_nombre: str
    nombre: str
    direccion: str
    ciudad: str
    capacidad_unidades: int
    capacidad_kg: float
    activo: bool


class CategoriaIn(BaseModel):
    nombre: Texto(3, 60)
    descripcion: Optional[Texto(0, 200)] = None
    peligrosidad: Peligrosidad


class CategoriaOut(Salida):
    id_categoria: int
    nombre: str
    descripcion: Optional[str]
    peligrosidad: str


class MarcaIn(BaseModel):
    nombre: Texto(2, 60)


class MarcaOut(Salida):
    id_marca: int
    nombre: str


# ------------------------------------------------------------------ lotes y dispositivos
class LoteIn(BaseModel):
    descripcion: Texto(5, 250)
    id_generador: Optional[Id] = None  # lo completa la API si quien registra es GENERADOR


class LoteOut(Salida):
    id_lote: int
    codigo_lote: str
    id_generador: int
    generador_nombre: str
    fecha_registro: datetime
    descripcion: Optional[str]
    estado: str
    num_dispositivos: int
    peso_total_kg: float


class DispositivoIn(BaseModel):
    id_lote: Id
    id_categoria: Id
    id_marca: Optional[Id] = None
    modelo: Optional[Texto(0, 80)] = None
    numero_serie: Optional[Annotated[str, StringConstraints(strip_whitespace=True, max_length=60,
                                                            pattern=r"^[A-Za-z0-9\-_/\.]*$")]] = None
    peso_kg: Annotated[float, Field(gt=0, le=99999.99)]
    _limpiar = field_validator("id_marca", "modelo", "numero_serie", mode="before")(_vacio_a_none)


class DispositivoOut(Salida):
    id_dispositivo: int
    codigo_unico: str
    id_lote: int
    codigo_lote: str
    id_categoria: int
    categoria_nombre: str
    id_marca: Optional[int]
    marca_nombre: Optional[str]
    id_centro_actual: Optional[int]
    centro_actual_nombre: Optional[str]
    modelo: Optional[str]
    numero_serie: Optional[str]
    peso_kg: float
    estado_actual: str
    clasificacion: Optional[str]
    fecha_registro: datetime


class LoteDetalleOut(LoteOut):
    dispositivos: list[DispositivoOut]


# ------------------------------------------------------------------ recolección y recepción
class SolicitudCrear(BaseModel):
    id_lote: Id
    id_centro_destino: Id
    modalidad: Modalidad
    fecha_programada: Optional[date] = None
    id_solicitante: Optional[Id] = None
    _limpiar = field_validator("fecha_programada", mode="before")(_vacio_a_none)

    @field_validator("fecha_programada")
    @classmethod
    def _no_pasada(cls, v):
        if v and v < date.today():
            raise ValueError("la fecha programada no puede estar en el pasado")
        return v


class SolicitudEditar(BaseModel):
    id_centro_destino: Id
    modalidad: Modalidad
    fecha_programada: Optional[date] = None
    estado: Literal["PENDIENTE", "PROGRAMADA", "CANCELADA"]
    _limpiar = field_validator("fecha_programada", mode="before")(_vacio_a_none)

    @model_validator(mode="after")
    def _programada_con_fecha(self):
        if self.estado == "PROGRAMADA" and not self.fecha_programada:
            raise ValueError("una solicitud PROGRAMADA necesita fecha programada")
        return self


class SolicitudOut(Salida):
    id_solicitud: int
    id_lote: int
    codigo_lote: str
    id_solicitante: int
    solicitante_nombre: str
    id_centro_destino: int
    centro_destino_nombre: str
    modalidad: str
    fecha_solicitud: datetime
    fecha_programada: Optional[date]
    estado: str


class RecepcionCrear(BaseModel):
    id_solicitud: Id
    peso_recibido_kg: Optional[Annotated[float, Field(gt=0, le=99_999_999)]] = None
    observaciones: Optional[Texto(0, 300)] = None
    id_operador: Optional[Id] = None
    _limpiar = field_validator("peso_recibido_kg", "observaciones", mode="before")(_vacio_a_none)


class RecepcionEditar(BaseModel):
    peso_recibido_kg: Optional[Annotated[float, Field(gt=0, le=99_999_999)]] = None
    observaciones: Optional[Texto(0, 300)] = None
    _limpiar = field_validator("peso_recibido_kg", "observaciones", mode="before")(_vacio_a_none)


class RecepcionOut(Salida):
    id_recepcion: int
    id_solicitud: int
    codigo_lote: str
    id_centro: int
    centro_nombre: str
    id_operador: int
    operador_nombre: str
    fecha_recepcion: datetime
    peso_recibido_kg: Optional[float]
    observaciones: Optional[str]


# ------------------------------------------------------------------ evaluación técnica
def _validar_coherencia(condicion: str, clasificacion: str) -> None:
    if condicion == "INSERVIBLE" and clasificacion in ("REUTILIZABLE", "REPARABLE"):
        raise ValueError("un equipo INSERVIBLE no puede clasificarse como REUTILIZABLE o REPARABLE")
    if clasificacion == "REUTILIZABLE" and condicion != "FUNCIONAL":
        raise ValueError("solo un equipo FUNCIONAL puede clasificarse como REUTILIZABLE")


class EvaluacionCrear(BaseModel):
    id_dispositivo: Id
    condicion: Condicion
    clasificacion: Clasificacion
    borrado_datos: bool = False
    observaciones: Optional[Texto(0, 300)] = None
    id_tecnico: Optional[Id] = None
    _limpiar = field_validator("observaciones", mode="before")(_vacio_a_none)

    @model_validator(mode="after")
    def _coherencia(self):
        _validar_coherencia(self.condicion, self.clasificacion)
        return self


class EvaluacionEditar(BaseModel):
    condicion: Condicion
    clasificacion: Clasificacion
    borrado_datos: bool = False
    observaciones: Optional[Texto(0, 300)] = None
    _limpiar = field_validator("observaciones", mode="before")(_vacio_a_none)

    @model_validator(mode="after")
    def _coherencia(self):
        _validar_coherencia(self.condicion, self.clasificacion)
        return self


class EvaluacionOut(Salida):
    id_evaluacion: int
    id_dispositivo: int
    codigo_unico: str
    dispositivo_descripcion: str
    id_tecnico: int
    tecnico_nombre: str
    fecha_evaluacion: datetime
    condicion: str
    clasificacion: str
    borrado_datos: bool
    observaciones: Optional[str]


class HistorialOut(Salida):
    id_dispositivo: int
    codigo_unico: str
    nro_cambio: int
    estado_anterior: Optional[str]
    estado_nuevo: str
    id_usuario: Optional[int]
    usuario_nombre: Optional[str]
    fecha_cambio: datetime


# ------------------------------------------------------------------ transferencias
class TransferenciaCrear(BaseModel):
    id_centro_origen: Id
    id_centro_destino: Id
    id_arista: Optional[Id] = None
    fecha_salida: datetime
    dispositivos: Annotated[list[Id], Field(min_length=1, max_length=500)]
    id_coordinador: Optional[Id] = None
    _limpiar = field_validator("id_arista", mode="before")(_vacio_a_none)

    @model_validator(mode="after")
    def _centros_distintos(self):
        if self.id_centro_origen == self.id_centro_destino:
            raise ValueError("el centro de origen y el de destino deben ser distintos")
        if len(set(self.dispositivos)) != len(self.dispositivos):
            raise ValueError("hay dispositivos repetidos en la transferencia")
        return self


class TransferenciaEditar(BaseModel):
    id_centro_destino: Id
    id_arista: Optional[Id] = None
    fecha_salida: datetime
    dispositivos: Annotated[list[Id], Field(min_length=1, max_length=500)]
    _limpiar = field_validator("id_arista", mode="before")(_vacio_a_none)


class RecibirIn(BaseModel):
    id_responsable: Optional[Id] = None


class TransferenciaOut(Salida):
    id_transferencia: int
    id_centro_origen: int
    centro_origen_nombre: str
    id_centro_destino: int
    centro_destino_nombre: str
    id_coordinador: int
    coordinador_nombre: str
    id_responsable: Optional[int]
    responsable_nombre: Optional[str]
    id_arista: Optional[int]
    arista_descripcion: Optional[str]
    fecha_salida: datetime
    fecha_recepcion: Optional[datetime]
    estado: str
    num_dispositivos: int


class TransferenciaDetalleOut(TransferenciaOut):
    dispositivos: list[DispositivoOut]


# ------------------------------------------------------------------ destino final
class DestinoCrear(BaseModel):
    id_dispositivo: Id
    tipo_destino: TipoDestino
    id_org_beneficiaria: Optional[Id] = None
    id_usuario_confirma: Optional[Id] = None
    _limpiar = field_validator("id_org_beneficiaria", mode="before")(_vacio_a_none)

    @model_validator(mode="after")
    def _donacion(self):
        if self.tipo_destino == "DONACION" and not self.id_org_beneficiaria:
            raise ValueError("una DONACION requiere la organización beneficiaria")
        return self


class DestinoOut(Salida):
    id_destino_final: int
    id_dispositivo: int
    codigo_unico: str
    clasificacion: Optional[str]
    id_centro: int
    centro_nombre: str
    id_org_beneficiaria: Optional[int]
    org_beneficiaria_nombre: Optional[str]
    tipo_destino: str
    fecha_confirmacion: datetime
    id_usuario_confirma: int
    usuario_confirma_nombre: str


# ------------------------------------------------------------------ evidencias
class EvidenciaOut(Salida):
    id_evidencia: int
    tipo_evidencia: str
    s3_key: str
    nombre_archivo: str
    hash_sha256: str
    id_usuario_carga: int
    usuario_carga_nombre: str
    fecha_carga: datetime
    id_dispositivo: Optional[int]
    id_evaluacion: Optional[int]
    id_transferencia: Optional[int]
    id_destino_final: Optional[int]
    vinculo: str
    url: Optional[str] = None  # URL prefirmada de S3 (expira en minutos)


# ------------------------------------------------------------------ red y flujo máximo
class EscenarioIn(BaseModel):
    nombre: Texto(3, 80)
    periodo_inicio: date
    periodo_fin: date
    unidad_medida: UnidadMedida
    descripcion: Optional[Texto(0, 250)] = None

    @model_validator(mode="after")
    def _periodo(self):
        if self.periodo_fin < self.periodo_inicio:
            raise ValueError("la fecha de fin debe ser igual o posterior a la de inicio")
        return self


class EscenarioOut(Salida):
    id_escenario: int
    nombre: str
    periodo_inicio: date
    periodo_fin: date
    unidad_medida: str
    descripcion: Optional[str]


class NodoIn(BaseModel):
    id_escenario: Id
    id_centro: Optional[Id] = None
    etiqueta: Annotated[str, StringConstraints(strip_whitespace=True, to_upper=True, min_length=1, max_length=20,
                                               pattern=r"^[A-Za-z0-9_\-]+$")]
    tipo_nodo: TipoNodo
    _limpiar = field_validator("id_centro", mode="before")(_vacio_a_none)


class NodoOut(Salida):
    id_nodo: int
    id_escenario: int
    id_centro: Optional[int]
    centro_nombre: Optional[str]
    etiqueta: str
    tipo_nodo: str


class AristaIn(BaseModel):
    id_escenario: Id
    id_nodo_origen: Id
    id_nodo_destino: Id
    capacidad: Annotated[float, Field(gt=0, le=99_999_999)]

    @model_validator(mode="after")
    def _sin_bucle(self):
        if self.id_nodo_origen == self.id_nodo_destino:
            raise ValueError("una arista no puede unir un nodo consigo mismo")
        return self


class AristaOut(Salida):
    id_arista: int
    id_escenario: int
    id_nodo_origen: int
    origen_etiqueta: str
    id_nodo_destino: int
    destino_etiqueta: str
    capacidad: float
    descripcion: str


class FlujoAristaOut(Salida):
    id_arista: int
    flujo: float
    saturada: bool
    en_corte_minimo: bool


class ResultadoOut(Salida):
    id_resultado: int
    id_escenario: int
    algoritmo: str
    flujo_maximo: float
    fecha_ejecucion: datetime
    id_ejecutor: Optional[int]
    ejecutor_nombre: Optional[str]
    flujos: list[FlujoAristaOut]


# ------------------------------------------------------------------ reportes
class InventarioOut(Salida):
    id_centro: int
    centro_nombre: str
    id_categoria: int
    categoria_nombre: str
    cantidad_unidades: int
    peso_total_kg: float
    fecha_actualizacion: datetime


class AuditoriaOut(Salida):
    id_auditoria: int
    tabla: str
    operacion: str
    id_registro: int
    id_usuario: Optional[int]
    usuario_nombre: Optional[str]
    fecha: datetime
    datos_antes: Optional[dict]
    datos_despues: Optional[dict]
