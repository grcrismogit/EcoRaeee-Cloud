import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ClipboardList, Inbox, PackageCheck } from 'lucide-react'
import { api } from '../api'
import { useAuth } from '../auth'
import { ESTADOS_SOLICITUD, MODALIDADES, OP } from '../catalogo'
import { Badge, etiqueta, fecha, num, useToast } from '../ui/feedback'
import { FormModal } from '../ui/Formulario'
import Recurso, { Encabezado } from '../ui/Recurso'

const hoy = () => new Date().toISOString().slice(0, 10)

export default function Recoleccion() {
  const { esAdmin, puede } = useAuth()
  const notificar = useToast()
  const [params] = useSearchParams()
  const [tab, setTab] = useState('solicitudes')
  const [recibir, setRecibir] = useState(null)
  const [version, setVersion] = useState(0)
  const loteInicial = params.get('lote')

  const camposRecepcion = [
    { name: 'peso_recibido_kg', label: 'Peso recibido (kg)', type: 'number', step: '0.01', gt: 0, help: 'Peso verificado en la báscula del centro.' },
    { name: 'id_operador', label: 'Operador que recibe', type: 'select', numeric: true, required: true, show: () => esAdmin, opciones: OP.usuarios('OPERADOR_CENTRO') },
    { name: 'observaciones', label: 'Observaciones', type: 'textarea', maxLength: 300, span: true },
  ]

  return (
    <>
      <Encabezado titulo="Recolección y recepción" descripcion="El generador solicita la recolección de un lote; el operador del centro lo recibe y los equipos quedan ubicados en el centro." />
      <div className="tabs">
        <button className={`tab ${tab === 'solicitudes' ? 'active' : ''}`} onClick={() => setTab('solicitudes')}><ClipboardList /> Solicitudes</button>
        <button className={`tab ${tab === 'recepciones' ? 'active' : ''}`} onClick={() => setTab('recepciones')}><Inbox /> Recepciones</button>
      </div>

      {tab === 'solicitudes' && (
        <Recurso
          embebido nombre="solicitud" femenino textoCrear="Nueva solicitud" endpoint="/solicitudes" idKey="id_solicitud"
          rolesEscritura={['GENERADOR', 'COORDINADOR_LOGISTICO']} recargaExterna={version}
          abrirAlIniciar={Boolean(loteInicial)} inicialCrear={loteInicial ? { id_lote: loteInicial } : {}}
          buscar={false}
          filtros={[{ name: 'estado', label: 'Todos los estados', options: ESTADOS_SOLICITUD }]}
          permitirEditar={(s) => ['PENDIENTE', 'PROGRAMADA'].includes(s.estado)}
          permitirEliminar={(s) => s.estado !== 'ATENDIDA'}
          columnas={[
            { key: 'id_solicitud', label: '#' },
            { key: 'codigo_lote', label: 'Lote', render: (s) => <b className="mono">{s.codigo_lote}</b> },
            { key: 'solicitante_nombre', label: 'Solicitante' },
            { key: 'centro_destino_nombre', label: 'Centro destino' },
            { key: 'modalidad', label: 'Modalidad', render: (s) => etiqueta(s.modalidad) },
            { key: 'fecha_programada', label: 'Programada', render: (s) => fecha(s.fecha_programada, false) },
            { key: 'estado', label: 'Estado', render: (s) => <Badge valor={s.estado} /> },
          ]}
          campos={[
            { name: 'id_lote', label: 'Lote', type: 'select', numeric: true, required: true, span: true,
              opciones: { ...OP.lotes, ruta: '/lotes?estado=REGISTRADO' }, help: 'Lotes registrados que aún no tienen solicitud activa.' },
            { name: 'id_centro_destino', label: 'Centro de acopio destino', type: 'select', numeric: true, required: true, opciones: OP.centros },
            { name: 'modalidad', label: 'Modalidad', type: 'select', required: true, options: MODALIDADES },
            { name: 'fecha_programada', label: 'Fecha programada', type: 'date', help: 'Si la indica, la solicitud queda PROGRAMADA.',
              validate: (v) => (v < hoy() ? 'No puede estar en el pasado' : null) },
            { name: 'id_solicitante', label: 'Solicitante', type: 'select', numeric: true, required: true, show: () => esAdmin, opciones: OP.usuarios('GENERADOR') },
          ]}
          camposEditar={[
            { name: 'id_centro_destino', label: 'Centro de acopio destino', type: 'select', numeric: true, required: true, opciones: OP.centros },
            { name: 'modalidad', label: 'Modalidad', type: 'select', required: true, options: MODALIDADES },
            { name: 'fecha_programada', label: 'Fecha programada', type: 'date', required: (v) => v.estado === 'PROGRAMADA' },
            { name: 'estado', label: 'Estado', type: 'select', required: true,
              options: ESTADOS_SOLICITUD.filter((e) => e.value !== 'ATENDIDA'), help: 'Pasa a ATENDIDA solo al registrar la recepción.' },
          ]}
          accionesFila={(s) => [{
            icon: <PackageCheck />, title: 'Registrar recepción',
            show: ['PENDIENTE', 'PROGRAMADA'].includes(s.estado) && puede('OPERADOR_CENTRO'),
            onClick: () => setRecibir(s),
          }]}
        />
      )}

      {tab === 'recepciones' && (
        <Recurso
          embebido nombre="recepción" femenino endpoint="/recepciones" idKey="id_recepcion" buscar={false}
          rolesEscritura={['OPERADOR_CENTRO']} permitirCrear={false} permitirEliminar={false}
          columnas={[
            { key: 'id_recepcion', label: '#' },
            { key: 'codigo_lote', label: 'Lote', render: (r) => <b className="mono">{r.codigo_lote}</b> },
            { key: 'centro_nombre', label: 'Centro' },
            { key: 'operador_nombre', label: 'Operador' },
            { key: 'fecha_recepcion', label: 'Fecha', render: (r) => fecha(r.fecha_recepcion) },
            { key: 'peso_recibido_kg', label: 'Peso (kg)', className: 'num', render: (r) => num(r.peso_recibido_kg) },
            { key: 'observaciones', label: 'Observaciones', render: (r) => <span className="small">{r.observaciones || '—'}</span> },
          ]}
          campos={camposRecepcion.filter((c) => c.name !== 'id_operador')}
          aFormulario={(r) => ({ peso_recibido_kg: r.peso_recibido_kg ?? '', observaciones: r.observaciones ?? '' })}
          avisoEditar="Una recepción no se elimina: forma parte de la trazabilidad. Solo se corrigen el peso y las observaciones."
        />
      )}

      {recibir && (
        <FormModal
          titulo={`Recepción del lote ${recibir.codigo_lote}`}
          aviso={`Se recibirá en ${recibir.centro_destino_nombre}. Todos los dispositivos del lote pasarán a RECIBIDO y se sumarán al inventario del centro.`}
          campos={camposRecepcion}
          textoBoton="Confirmar recepción"
          onClose={() => setRecibir(null)}
          onSubmit={(p) => api('/recepciones', { method: 'POST', body: { ...p, id_solicitud: recibir.id_solicitud } })}
          onExito={() => { notificar(`Lote ${recibir.codigo_lote} recibido en ${recibir.centro_destino_nombre}.`); setVersion((v) => v + 1) }}
        />
      )}
    </>
  )
}
