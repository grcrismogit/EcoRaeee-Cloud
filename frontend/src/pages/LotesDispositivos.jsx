import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ListTree, ScanSearch, Truck } from 'lucide-react'
import { useAuth } from '../auth'
import { CLASIFICACIONES, ESTADOS_DISPOSITIVO, ESTADOS_LOTE, OP } from '../catalogo'
import { Badge, fecha, num } from '../ui/feedback'
import Recurso from '../ui/Recurso'
import { Icono3D, iconoCategoria } from '../ui/Efectos'

export function Lotes() {
  const { esAdmin } = useAuth()
  const navegar = useNavigate()
  return (
    <Recurso
      titulo="Lotes" nombre="lote" endpoint="/lotes" idKey="id_lote"
      descripcion="Conjunto de equipos que un generador entrega en un mismo evento. El código se genera automáticamente (RN-01)."
      rolesEscritura={['GENERADOR']}
      permitirEditar={(l) => l.estado !== 'CERRADO'}
      permitirEliminar={(l) => l.estado === 'REGISTRADO'}
      filtros={[{ name: 'estado', label: 'Todos los estados', options: ESTADOS_LOTE }]}
      columnas={[
        { key: 'codigo_lote', label: 'Código', render: (l) => <b className="mono">{l.codigo_lote}</b> },
        { key: 'descripcion', label: 'Descripción' },
        { key: 'generador_nombre', label: 'Generador' },
        { key: 'num_dispositivos', label: 'Equipos', className: 'num' },
        { key: 'peso_total_kg', label: 'Peso (kg)', className: 'num', render: (l) => num(l.peso_total_kg) },
        { key: 'fecha_registro', label: 'Registro', render: (l) => fecha(l.fecha_registro, false) },
        { key: 'estado', label: 'Estado', render: (l) => <Badge valor={l.estado} /> },
      ]}
      campos={[
        { name: 'descripcion', label: 'Descripción del lote', type: 'textarea', required: true, minLength: 5, maxLength: 250, span: true,
          placeholder: 'Ej.: Renovación del laboratorio de cómputo B-204' },
        { name: 'id_generador', label: 'Generador responsable', type: 'select', numeric: true, required: true, span: true,
          show: () => esAdmin, opciones: OP.usuarios('GENERADOR'), help: 'Como administrador debe indicar el generador (la base verifica su rol).' },
      ]}
      accionesFila={(l) => [
        { icon: <ListTree />, title: 'Ver dispositivos', onClick: () => navegar(`/dispositivos?id_lote=${l.id_lote}`) },
        { icon: <Truck />, title: 'Solicitar recolección', show: ['REGISTRADO'].includes(l.estado), onClick: () => navegar(`/recoleccion?lote=${l.id_lote}`) },
      ]}
    />
  )
}

export function Dispositivos() {
  const [params] = useSearchParams()
  const navegar = useNavigate()
  const filtrosIniciales = {}
  for (const k of ['id_lote', 'estado', 'id_centro']) if (params.get(k)) filtrosIniciales[k] = params.get(k)

  const campos = [
    { name: 'id_lote', label: 'Lote', type: 'select', numeric: true, required: true, span: true,
      opciones: { ...OP.lotes, ruta: '/lotes?estado=REGISTRADO,SOLICITADO' },
      help: 'Solo lotes que todavía no han sido recibidos.' },
    { name: 'id_categoria', label: 'Categoría', type: 'select', numeric: true, required: true, opciones: OP.categorias },
    { name: 'id_marca', label: 'Marca', type: 'select', numeric: true, opciones: OP.marcas, placeholder: 'Sin marca (opcional)' },
    { name: 'modelo', label: 'Modelo', maxLength: 80, placeholder: 'Ej.: Latitude 5490' },
    { name: 'numero_serie', label: 'Número de serie', maxLength: 60, pattern: '^[A-Za-z0-9\\-_/.]*$', patternMsg: 'Solo letras, números y - _ / .' },
    { name: 'peso_kg', label: 'Peso (kg)', type: 'number', step: '0.01', required: true, gt: 0, max: 99999.99 },
  ]

  // Al editar, el lote solo se puede cambiar mientras el equipo siga REGISTRADO
  const camposEditar = campos.map((c) => (c.name !== 'id_lote' ? c : {
    ...c, opciones: OP.lotes, help: 'El lote no cambia una vez recibido el equipo.',
    disabled: (v) => v.estado_actual !== 'REGISTRADO',
  }))

  return (
    <Recurso
      titulo="Dispositivos" nombre="dispositivo" endpoint="/dispositivos" idKey="id_dispositivo"
      descripcion="Equipos individuales. El estado, la clasificación y la ubicación los actualizan los procesos (triggers), no el usuario."
      rolesEscritura={['GENERADOR']}
      permitirEditar={(d) => d.estado_actual !== 'CERRADO'}
      permitirEliminar={(d) => d.estado_actual === 'REGISTRADO'}
      filtrosIniciales={filtrosIniciales}
      filtros={[
        { name: 'estado', label: 'Todos los estados', options: ESTADOS_DISPOSITIVO },
        { name: 'clasificacion', label: 'Toda clasificación', options: CLASIFICACIONES },
        { name: 'id_categoria', label: 'Todas las categorías', opciones: OP.categorias },
        { name: 'id_centro', label: 'Todos los centros', opciones: OP.centros },
        { name: 'id_lote', label: 'Todos los lotes', opciones: { ...OP.lotes, etiqueta: (l) => l.codigo_lote } },
      ]}
      inicialCrear={() => (params.get('id_lote') ? { id_lote: params.get('id_lote') } : {})}
      aFormulario={(d) => ({ ...d, id_marca: d.id_marca ?? '', modelo: d.modelo ?? '', numero_serie: d.numero_serie ?? '' })}
      columnas={[
        { key: 'codigo_unico', label: 'Código', render: (d) => <Link className="mono" to={`/trazabilidad/${d.codigo_unico}`}>{d.codigo_unico}</Link> },
        { key: 'categoria_nombre', label: 'Equipo', render: (d) => (
          <div className="equipo">
            <Icono3D {...iconoCategoria(d.categoria_nombre)} tamano={32} />
            <div className="stack"><span>{d.categoria_nombre}</span><span className="small muted">{[d.marca_nombre, d.modelo].filter(Boolean).join(' ') || '—'}</span></div>
          </div>
        ) },
        { key: 'codigo_lote', label: 'Lote', render: (d) => <span className="mono small nowrap">{d.codigo_lote}</span> },
        { key: 'peso_kg', label: 'Peso (kg)', className: 'num', render: (d) => num(d.peso_kg) },
        { key: 'centro_actual_nombre', label: 'Ubicación actual', render: (d) => d.centro_actual_nombre || <span className="muted">Con el generador</span> },
        { key: 'clasificacion', label: 'Clasificación', render: (d) => <Badge valor={d.clasificacion} /> },
        { key: 'estado_actual', label: 'Estado', render: (d) => <Badge valor={d.estado_actual} /> },
      ]}
      campos={campos}
      camposEditar={camposEditar}
      accionesFila={(d) => [{ icon: <ScanSearch />, title: 'Ver trazabilidad', onClick: () => navegar(`/trazabilidad/${d.codigo_unico}`) }]}
    />
  )
}
