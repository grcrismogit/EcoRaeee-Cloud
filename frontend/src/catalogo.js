// Valores permitidos (coinciden con los CHECK de PostgreSQL) y cargadores de opciones reutilizables.
import { etiqueta } from './ui/feedback'

const lista = (...valores) => valores.map((v) => ({ value: v, label: etiqueta(v) }))

export const ESTADOS_DISPOSITIVO = lista('REGISTRADO', 'RECIBIDO', 'EVALUADO', 'EN_TRANSITO', 'TRANSFERIDO', 'CERRADO')
export const CLASIFICACIONES = lista('REUTILIZABLE', 'REPARABLE', 'RECICLABLE', 'NO_RECUPERABLE')
export const CONDICIONES = [
  { value: 'FUNCIONAL', label: 'Funcional' }, { value: 'CON_FALLAS', label: 'Con fallas' },
  { value: 'DANADO', label: 'Dañado' }, { value: 'INSERVIBLE', label: 'Inservible' },
]
export const TIPOS_DESTINO = lista('REUTILIZACION', 'REACONDICIONAMIENTO', 'RECICLAJE', 'DISPOSICION_FINAL', 'DONACION')
export const TIPOS_ORGANIZACION = lista('UNIVERSIDAD', 'FACULTAD', 'REACONDICIONADOR', 'GESTOR_RECICLAJE', 'BENEFICIARIA')
export const PELIGROSIDAD = lista('BAJA', 'MEDIA', 'ALTA')
export const MODALIDADES = [{ value: 'RECOLECCION', label: 'Recolección en sitio' }, { value: 'ENTREGA', label: 'Entrega en el centro' }]
export const ESTADOS_LOTE = lista('REGISTRADO', 'SOLICITADO', 'RECIBIDO', 'CERRADO')
export const ESTADOS_SOLICITUD = lista('PENDIENTE', 'PROGRAMADA', 'ATENDIDA', 'CANCELADA')
export const ESTADOS_TRANSFERENCIA = lista('PROGRAMADA', 'EN_TRANSITO', 'CERRADA', 'CANCELADA')
export const TIPOS_EVIDENCIA = lista('FOTO', 'ACTA', 'INFORME', 'CERTIFICADO')
export const TIPOS_NODO = lista('FUENTE', 'INTERMEDIO', 'SUMIDERO')
export const UNIDADES = [{ value: 'UNIDADES', label: 'Unidades' }, { value: 'KG', label: 'Kilogramos' }]

// Selects que leen datos de la API
export const OP = {
  centros: { ruta: '/centros', valor: 'id_centro', etiqueta: (c) => `${c.nombre} (${c.ciudad})` },
  categorias: { ruta: '/categorias', valor: 'id_categoria', etiqueta: (c) => c.nombre },
  marcas: { ruta: '/marcas', valor: 'id_marca', etiqueta: (m) => m.nombre },
  organizaciones: { ruta: '/organizaciones', valor: 'id_organizacion', etiqueta: (o) => o.nombre },
  beneficiarias: { ruta: '/organizaciones?tipo_organizacion=BENEFICIARIA', valor: 'id_organizacion', etiqueta: (o) => o.nombre },
  tiposCentro: { ruta: '/tipos-centro', valor: 'id_tipo_centro', etiqueta: (t) => t.nombre },
  roles: { ruta: '/roles', valor: 'id_rol', etiqueta: (r) => etiqueta(r.codigo) },
  lotes: { ruta: '/lotes', valor: 'id_lote', etiqueta: (l) => `${l.codigo_lote} · ${l.descripcion || ''}` },
  // Para que el ADMIN elija quién ejecuta una acción. Se listan TODOS los usuarios activos
  // a propósito: si elige uno sin el rol correcto, la base de datos lo rechaza (RN-02, etc.).
  usuarios: (rolSugerido) => ({
    ruta: '/usuarios?activo=true', valor: 'id_usuario',
    etiqueta: (u) => `${u.nombre_completo} · ${etiqueta(u.rol_codigo)}${u.rol_codigo === rolSugerido ? ' ✓' : ''}`,
  }),
}

export const describirDispositivo = (d) =>
  [d.codigo_unico, d.categoria_nombre, [d.marca_nombre, d.modelo].filter(Boolean).join(' ')].filter(Boolean).join(' · ')
