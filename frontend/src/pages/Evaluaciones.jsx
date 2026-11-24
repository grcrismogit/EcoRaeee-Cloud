import { Link } from 'react-router-dom'
import { Check, Minus } from 'lucide-react'
import { useAuth } from '../auth'
import { CLASIFICACIONES, CONDICIONES, OP, describirDispositivo } from '../catalogo'
import { Badge, etiqueta, fecha } from '../ui/feedback'
import Recurso from '../ui/Recurso'

const coherencia = (v, valores) => {
  if (valores.condicion === 'INSERVIBLE' && ['REUTILIZABLE', 'REPARABLE'].includes(v)) return 'Un equipo INSERVIBLE no puede ser reutilizable ni reparable'
  if (v === 'REUTILIZABLE' && valores.condicion && valores.condicion !== 'FUNCIONAL') return 'Solo un equipo FUNCIONAL puede ser REUTILIZABLE'
  return null
}

export default function Evaluaciones() {
  const { esAdmin } = useAuth()
  const comunes = [
    { name: 'condicion', label: 'Condición', type: 'select', required: true, options: CONDICIONES },
    { name: 'clasificacion', label: 'Clasificación', type: 'select', required: true, options: CLASIFICACIONES, validate: coherencia },
    { name: 'borrado_datos', label: 'Borrado seguro', type: 'checkbox', checkLabel: 'Se realizó el borrado seguro de datos', span: true },
    { name: 'observaciones', label: 'Observaciones / hallazgos', type: 'textarea', maxLength: 300, span: true },
  ]
  return (
    <Recurso
      titulo="Evaluación técnica" nombre="evaluación" femenino textoCrear="Nueva evaluación" endpoint="/evaluaciones" idKey="id_evaluacion"
      descripcion="Diagnóstico del técnico: condición, clasificación y borrado seguro de datos. Solo un TÉCNICO EVALUADOR activo puede evaluar (RN-02)."
      rolesEscritura={['TECNICO_EVALUADOR']}
      permitirEditar permitirEliminar
      filtros={[{ name: 'clasificacion', label: 'Toda clasificación', options: CLASIFICACIONES }]}
      buscar={false}
      columnas={[
        { key: 'fecha_evaluacion', label: 'Fecha', render: (e) => <span className="small">{fecha(e.fecha_evaluacion)}</span> },
        { key: 'codigo_unico', label: 'Dispositivo', render: (e) => <div className="stack"><Link className="mono" to={`/trazabilidad/${e.codigo_unico}`}>{e.codigo_unico}</Link><span className="small muted">{e.dispositivo_descripcion}</span></div> },
        { key: 'tecnico_nombre', label: 'Técnico' },
        { key: 'condicion', label: 'Condición', render: (e) => etiqueta(e.condicion) },
        { key: 'clasificacion', label: 'Clasificación', render: (e) => <Badge valor={e.clasificacion} /> },
        { key: 'borrado_datos', label: 'Borrado', render: (e) => (e.borrado_datos ? <span title="Sí"><Check size={16} color="var(--ok)" /> Sí</span> : <span className="muted"><Minus size={14} /> No</span>) },
        { key: 'observaciones', label: 'Observaciones', render: (e) => <span className="small">{e.observaciones || '—'}</span> },
      ]}
      campos={[
        { name: 'id_dispositivo', label: 'Dispositivo', type: 'select', numeric: true, required: true, span: true,
          opciones: { ruta: '/dispositivos?estado=RECIBIDO,EVALUADO,TRANSFERIDO', valor: 'id_dispositivo',
            etiqueta: (d) => `${describirDispositivo(d)} — ${d.centro_actual_nombre}` },
          help: 'Equipos que se encuentran en un centro (recibidos, evaluados o transferidos).' },
        ...comunes,
        { name: 'id_tecnico', label: 'Técnico evaluador', type: 'select', numeric: true, required: true, span: true, show: () => esAdmin,
          opciones: OP.usuarios('TECNICO_EVALUADOR'),
          help: 'Se listan todos los usuarios: si elige uno que no es técnico activo, la base de datos lo rechaza (RN-02).' },
      ]}
      camposEditar={comunes}
    />
  )
}
