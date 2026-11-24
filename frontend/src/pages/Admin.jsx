import { OP, PELIGROSIDAD, TIPOS_ORGANIZACION } from '../catalogo'
import { Badge, etiqueta, fecha, num } from '../ui/feedback'
import Recurso from '../ui/Recurso'

const ADMIN = []  // solo el ADMIN escribe en los catálogos

export function Organizaciones() {
  return (
    <Recurso
      titulo="Organizaciones" nombre="organización" femenino textoCrear="Nueva organización" endpoint="/organizaciones" idKey="id_organizacion"
      descripcion="Universidades, facultades, reacondicionadores, gestores de reciclaje y entidades beneficiarias de la red."
      rolesEscritura={ADMIN}
      filtros={[{ name: 'tipo_organizacion', label: 'Todos los tipos', options: TIPOS_ORGANIZACION }]}
      columnas={[
        { key: 'nombre', label: 'Nombre', render: (o) => <b>{o.nombre}</b> },
        { key: 'tipo_organizacion', label: 'Tipo', render: (o) => <span className="tag">{etiqueta(o.tipo_organizacion)}</span> },
        { key: 'identificacion', label: 'RUC / cédula', render: (o) => <span className="mono">{o.identificacion}</span> },
        { key: 'email_contacto', label: 'Contacto', render: (o) => <div className="stack"><span className="small">{o.email_contacto || '—'}</span><span className="small muted">{o.telefono || ''}</span></div> },
        { key: 'activo', label: 'Activa', render: (o) => (o.activo ? 'Sí' : <span className="muted">No</span>) },
      ]}
      campos={[
        { name: 'nombre', label: 'Nombre', required: true, minLength: 3, maxLength: 150, span: true },
        { name: 'tipo_organizacion', label: 'Tipo', type: 'select', required: true, options: TIPOS_ORGANIZACION },
        { name: 'identificacion', label: 'RUC o cédula', required: true, pattern: '^[0-9]{10}([0-9]{3})?$', patternMsg: '10 dígitos (cédula) o 13 dígitos (RUC)' },
        { name: 'email_contacto', label: 'Correo de contacto', type: 'email', maxLength: 120, pattern: '^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$', patternMsg: 'Correo no válido' },
        { name: 'telefono', label: 'Teléfono', pattern: '^\\+?[0-9 ]{7,20}$', patternMsg: 'Solo números (7 a 20 dígitos)' },
        { name: 'activo', label: 'Activa', type: 'checkbox', checkLabel: 'Organización activa', default: true },
      ]}
      inicialCrear={{ activo: true }}
      aFormulario={(o) => ({ ...o, email_contacto: o.email_contacto ?? '', telefono: o.telefono ?? '' })}
    />
  )
}

export function Centros() {
  return (
    <Recurso
      titulo="Centros" nombre="centro" endpoint="/centros" idKey="id_centro"
      descripcion="Puntos físicos de la red: acopio en campus, talleres, gestores de reciclaje y beneficiarios."
      rolesEscritura={ADMIN}
      filtros={[{ name: 'id_tipo_centro', label: 'Todos los tipos', opciones: OP.tiposCentro }]}
      columnas={[
        { key: 'nombre', label: 'Centro', render: (c) => <div className="stack"><b>{c.nombre}</b><span className="small muted">{c.direccion}, {c.ciudad}</span></div> },
        { key: 'tipo_centro_nombre', label: 'Tipo' },
        { key: 'organizacion_nombre', label: 'Organización' },
        { key: 'capacidad_unidades', label: 'Cap. unidades', className: 'num' },
        { key: 'capacidad_kg', label: 'Cap. kg', className: 'num', render: (c) => num(c.capacidad_kg) },
        { key: 'activo', label: 'Activo', render: (c) => (c.activo ? 'Sí' : <span className="muted">No</span>) },
      ]}
      campos={[
        { name: 'nombre', label: 'Nombre', required: true, minLength: 3, maxLength: 120, span: true },
        { name: 'id_organizacion', label: 'Organización', type: 'select', numeric: true, required: true, opciones: OP.organizaciones },
        { name: 'id_tipo_centro', label: 'Tipo de centro', type: 'select', numeric: true, required: true, opciones: OP.tiposCentro },
        { name: 'direccion', label: 'Dirección', required: true, minLength: 5, maxLength: 200, span: true },
        { name: 'ciudad', label: 'Ciudad', required: true, minLength: 3, maxLength: 60 },
        { name: 'capacidad_unidades', label: 'Capacidad (unidades)', type: 'number', integer: true, required: true, gt: 0 },
        { name: 'capacidad_kg', label: 'Capacidad (kg)', type: 'number', step: '0.01', required: true, gt: 0 },
        { name: 'activo', label: 'Activo', type: 'checkbox', checkLabel: 'Centro activo' },
      ]}
      inicialCrear={{ activo: true }}
    />
  )
}

export function TiposCentro() {
  return (
    <Recurso
      titulo="Tipos de centro" nombre="tipo de centro" textoCrear="Nuevo tipo" endpoint="/tipos-centro" idKey="id_tipo_centro"
      rolesEscritura={ADMIN} buscar={false}
      columnas={[{ key: 'nombre', label: 'Nombre', render: (t) => <b>{t.nombre}</b> }, { key: 'descripcion', label: 'Descripción' }]}
      campos={[
        { name: 'nombre', label: 'Nombre', required: true, minLength: 3, maxLength: 40, span: true },
        { name: 'descripcion', label: 'Descripción', type: 'textarea', maxLength: 200, span: true },
      ]}
      aFormulario={(t) => ({ ...t, descripcion: t.descripcion ?? '' })}
    />
  )
}

export function Usuarios() {
  const base = [
    { name: 'nombres', label: 'Nombres', required: true, minLength: 2, maxLength: 80 },
    { name: 'apellidos', label: 'Apellidos', required: true, minLength: 2, maxLength: 80 },
    { name: 'email', label: 'Correo', type: 'email', required: true, maxLength: 120, pattern: '^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$', patternMsg: 'Correo no válido', span: true },
    { name: 'id_organizacion', label: 'Organización', type: 'select', numeric: true, required: true, opciones: OP.organizaciones },
    { name: 'id_rol', label: 'Rol', type: 'select', numeric: true, required: true, opciones: OP.roles },
  ]
  const clave = (requerida) => ({
    name: 'password', label: requerida ? 'Contraseña' : 'Nueva contraseña (opcional)', type: 'password', required: requerida, minLength: 8, maxLength: 72,
    validate: (v) => (v && !(/[0-9]/.test(v) && /[A-Za-z]/.test(v)) ? 'Combine letras y números' : null),
    help: 'Mínimo 8 caracteres con letras y números. Se guarda cifrada con bcrypt.',
  })
  const activo = { name: 'activo', label: 'Activo', type: 'checkbox', checkLabel: 'Usuario activo' }
  return (
    <Recurso
      titulo="Usuarios" nombre="usuario" endpoint="/usuarios" idKey="id_usuario"
      descripcion="Especialización disjunta y parcial de USUARIO según su rol. Las contraseñas se almacenan como hash bcrypt."
      rolesEscritura={ADMIN}
      filtros={[{ name: 'rol', label: 'Todos los roles', opciones: { ...OP.roles, valor: 'codigo' } }]}
      columnas={[
        { key: 'nombre_completo', label: 'Nombre', render: (u) => <div className="stack"><b>{u.nombre_completo}</b><span className="small muted">{u.email}</span></div> },
        { key: 'rol_codigo', label: 'Rol', render: (u) => <span className="tag">{etiqueta(u.rol_codigo)}</span> },
        { key: 'organizacion_nombre', label: 'Organización' },
        { key: 'fecha_creacion', label: 'Alta', render: (u) => <span className="small">{fecha(u.fecha_creacion, false)}</span> },
        { key: 'activo', label: 'Estado', render: (u) => (u.activo ? <Badge valor="ACTIVO" /> : <span className="badge danger">INACTIVO</span>) },
      ]}
      campos={[...base, clave(true), activo]}
      camposEditar={[...base, clave(false), activo]}
      inicialCrear={{ activo: true }}
      aFormulario={(u) => ({ ...u, password: '' })}
    />
  )
}

export function Categorias() {
  return (
    <Recurso
      titulo="Categorías" nombre="categoría" femenino textoCrear="Nueva categoría" endpoint="/categorias" idKey="id_categoria"
      rolesEscritura={ADMIN}
      columnas={[
        { key: 'nombre', label: 'Nombre', render: (c) => <b>{c.nombre}</b> },
        { key: 'descripcion', label: 'Descripción' },
        { key: 'peligrosidad', label: 'Peligrosidad', render: (c) => <span className={`badge ${c.peligrosidad === 'ALTA' ? 'danger' : c.peligrosidad === 'MEDIA' ? 'warn' : ''}`}>{c.peligrosidad}</span> },
      ]}
      campos={[
        { name: 'nombre', label: 'Nombre', required: true, minLength: 3, maxLength: 60 },
        { name: 'peligrosidad', label: 'Peligrosidad', type: 'select', required: true, options: PELIGROSIDAD },
        { name: 'descripcion', label: 'Descripción', type: 'textarea', maxLength: 200, span: true },
      ]}
      aFormulario={(c) => ({ ...c, descripcion: c.descripcion ?? '' })}
    />
  )
}

export function Marcas() {
  return (
    <Recurso
      titulo="Marcas" nombre="marca" femenino textoCrear="Nueva marca" endpoint="/marcas" idKey="id_marca"
      rolesEscritura={ADMIN}
      columnas={[{ key: 'id_marca', label: '#' }, { key: 'nombre', label: 'Nombre', render: (m) => <b>{m.nombre}</b> }]}
      campos={[{ name: 'nombre', label: 'Nombre', required: true, minLength: 2, maxLength: 60, span: true }]}
    />
  )
}
