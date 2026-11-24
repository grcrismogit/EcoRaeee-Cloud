import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Ban, Eye, PackageCheck, Send } from 'lucide-react'
import { api } from '../api'
import { useAuth } from '../auth'
import { ESTADOS_TRANSFERENCIA, OP, describirDispositivo } from '../catalogo'
import { Badge, Cargando, Confirmar, Modal, fecha, num, useToast } from '../ui/feedback'
import { FormModal } from '../ui/Formulario'
import Recurso from '../ui/Recurso'

// datetime-local necesita "AAAA-MM-DDTHH:mm" en hora local
const aLocal = (d) => {
  const x = new Date(d)
  x.setMinutes(x.getMinutes() - x.getTimezoneOffset())
  return x.toISOString().slice(0, 16)
}

function Detalle({ id, onClose }) {
  const [t, setT] = useState(null)
  useEffect(() => { api(`/transferencias/${id}`).then(setT).catch(() => setT(null)) }, [id])
  return (
    <Modal titulo={`Transferencia #${id}`} onClose={onClose} size="lg">
      {!t ? <Cargando /> : (
        <>
          <dl className="dl" style={{ marginBottom: 16 }}>
            <dt>Ruta</dt><dd>{t.centro_origen_nombre} → {t.centro_destino_nombre} {t.arista_descripcion && <span className="tag">{t.arista_descripcion}</span>}</dd>
            <dt>Estado</dt><dd><Badge valor={t.estado} /></dd>
            <dt>Coordinador</dt><dd>{t.coordinador_nombre}</dd>
            <dt>Salida</dt><dd>{fecha(t.fecha_salida)}</dd>
            <dt>Recepción</dt><dd>{t.fecha_recepcion ? `${fecha(t.fecha_recepcion)} · ${t.responsable_nombre}` : '—'}</dd>
          </dl>
          <table className="data">
            <thead><tr><th>Código</th><th>Equipo</th><th>Peso</th><th>Clasificación</th><th>Estado actual</th></tr></thead>
            <tbody>
              {t.dispositivos.map((d) => (
                <tr key={d.id_dispositivo}>
                  <td><Link className="mono" to={`/trazabilidad/${d.codigo_unico}`}>{d.codigo_unico}</Link></td>
                  <td>{d.categoria_nombre} {[d.marca_nombre, d.modelo].filter(Boolean).join(' ')}</td>
                  <td className="num">{num(d.peso_kg)} kg</td>
                  <td><Badge valor={d.clasificacion} /></td>
                  <td><Badge valor={d.estado_actual} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </Modal>
  )
}

export default function Transferencias() {
  const { esAdmin, puede } = useAuth()
  const notificar = useToast()
  const [detalle, setDetalle] = useState(null)
  const [accion, setAccion] = useState(null) // {tipo, t}
  const [version, setVersion] = useState(0)
  const refrescar = (msg) => { notificar(msg); setVersion((v) => v + 1) }

  // Equipos del centro de origen que no están comprometidos en otra transferencia activa
  const rutaDispositivos = (v) => (v.id_centro_origen
    ? `/transferencias/disponibles?origen=${v.id_centro_origen}${v.id_transferencia ? `&transferencia=${v.id_transferencia}` : ''}` : null)
  const campoArista = {
    name: 'id_arista', label: 'Ruta en la red (arista)', type: 'select', numeric: true, span: true, placeholder: 'Sin ruta asignada (opcional)',
    esperando: 'Seleccione origen y destino',
    opciones: { ruta: (v) => (v.id_centro_origen && v.id_centro_destino ? `/transferencias/rutas?origen=${v.id_centro_origen}&destino=${v.id_centro_destino}` : null),
      valor: 'id_arista', etiqueta: (a) => a.descripcion },
    help: 'RN-05: la cantidad de equipos no puede superar la capacidad de la arista.',
  }
  const campoDispositivos = {
    name: 'dispositivos', label: 'Dispositivos a transferir', type: 'multiselect', required: true, span: true,
    esperando: 'Seleccione el centro de origen', sinOpciones: 'No hay equipos disponibles en ese centro',
    opciones: { ruta: rutaDispositivos, valor: 'id_dispositivo', etiqueta: (d) => `${describirDispositivo(d)} · ${d.clasificacion || 'sin evaluar'} · ${d.peso_kg} kg` },
    help: (v) => `${(v.dispositivos || []).length} seleccionado(s)`,
  }
  const campoFecha = { name: 'fecha_salida', label: 'Fecha y hora de salida', type: 'datetime', required: true }

  const campos = [
    { name: 'id_centro_origen', label: 'Centro de origen', type: 'select', numeric: true, required: true, opciones: OP.centros, reinicia: ['dispositivos', 'id_arista'] },
    { name: 'id_centro_destino', label: 'Centro de destino', type: 'select', numeric: true, required: true, opciones: OP.centros, reinicia: ['id_arista'],
      validate: (v, x) => (String(v) === String(x.id_centro_origen) ? 'Debe ser distinto del origen' : null) },
    campoArista, campoFecha,
    { name: 'id_coordinador', label: 'Coordinador logístico', type: 'select', numeric: true, required: true, show: () => esAdmin, opciones: OP.usuarios('COORDINADOR_LOGISTICO') },
    campoDispositivos,
  ]
  const camposEditar = [
    { name: 'id_centro_origen', label: 'Centro de origen', type: 'select', numeric: true, opciones: OP.centros, disabled: true, noEnviar: true },
    { ...campos[1] }, campoArista, campoFecha, campoDispositivos,
  ]

  return (
    <>
      <Recurso
        titulo="Transferencias" nombre="transferencia" femenino textoCrear="Programar transferencia" endpoint="/transferencias" idKey="id_transferencia"
        descripcion="Movimiento autorizado de equipos entre centros: PROGRAMADA → EN TRÁNSITO → CERRADA. Al recibir, el inventario de origen y destino cambia en una sola transacción (RN-06)."
        rolesEscritura={['COORDINADOR_LOGISTICO']} recargaExterna={version} buscar={false} tamanoModal="lg"
        filtros={[{ name: 'estado', label: 'Todos los estados', options: ESTADOS_TRANSFERENCIA }]}
        permitirEditar={(t) => t.estado === 'PROGRAMADA'}
        permitirEliminar={(t) => ['PROGRAMADA', 'CANCELADA'].includes(t.estado)}
        inicialCrear={() => ({ fecha_salida: aLocal(Date.now() + 3600e3) })}
        cargarParaEditar={(t) => api(`/transferencias/${t.id_transferencia}`)}
        aFormulario={(t) => ({
          id_transferencia: t.id_transferencia, id_centro_origen: t.id_centro_origen, id_centro_destino: t.id_centro_destino, id_arista: t.id_arista ?? '',
          fecha_salida: aLocal(t.fecha_salida), dispositivos: t.dispositivos.map((d) => String(d.id_dispositivo)),
        })}
        camposEditar={camposEditar}
        campos={campos}
        columnas={[
          { key: 'id_transferencia', label: '#' },
          { key: 'ruta', label: 'Origen → destino', render: (t) => <div className="stack"><span>{t.centro_origen_nombre} → {t.centro_destino_nombre}</span>{t.arista_descripcion && <span className="small muted">Ruta {t.arista_descripcion}</span>}</div> },
          { key: 'num_dispositivos', label: 'Equipos', className: 'num' },
          { key: 'fecha_salida', label: 'Salida', render: (t) => <span className="small">{fecha(t.fecha_salida)}</span> },
          { key: 'fecha_recepcion', label: 'Recepción', render: (t) => <span className="small">{t.fecha_recepcion ? `${fecha(t.fecha_recepcion)} · ${t.responsable_nombre}` : '—'}</span> },
          { key: 'coordinador_nombre', label: 'Coordinador' },
          { key: 'estado', label: 'Estado', render: (t) => <Badge valor={t.estado} /> },
        ]}
        accionesFila={(t) => [
          { icon: <Eye />, title: 'Ver equipos', onClick: () => setDetalle(t.id_transferencia) },
          { icon: <Send />, title: 'Despachar', show: t.estado === 'PROGRAMADA' && puede('COORDINADOR_LOGISTICO'), onClick: () => setAccion({ tipo: 'despachar', t }) },
          { icon: <PackageCheck />, title: 'Registrar recepción', show: t.estado === 'EN_TRANSITO' && puede('COORDINADOR_LOGISTICO', 'OPERADOR_CENTRO'), onClick: () => setAccion({ tipo: 'recibir', t }) },
          { icon: <Ban />, title: 'Cancelar', danger: true, show: t.estado === 'PROGRAMADA' && puede('COORDINADOR_LOGISTICO'), onClick: () => setAccion({ tipo: 'cancelar', t }) },
        ]}
      />

      {detalle && <Detalle id={detalle} onClose={() => setDetalle(null)} />}

      {accion?.tipo === 'despachar' && (
        <Confirmar titulo={`Despachar transferencia #${accion.t.id_transferencia}`} textoBoton="Despachar"
          mensaje={`Los ${accion.t.num_dispositivos} equipo(s) saldrán de ${accion.t.centro_origen_nombre} y quedarán EN TRÁNSITO hacia ${accion.t.centro_destino_nombre}.`}
          onClose={() => setAccion(null)}
          onConfirm={async () => { await api(`/transferencias/${accion.t.id_transferencia}/despachar`, { method: 'POST' }); refrescar('Transferencia despachada: equipos en tránsito.') }} />
      )}
      {accion?.tipo === 'cancelar' && (
        <Confirmar titulo={`Cancelar transferencia #${accion.t.id_transferencia}`} textoBoton="Cancelar transferencia" peligro
          mensaje="La transferencia quedará CANCELADA y los equipos seguirán en el centro de origen."
          onClose={() => setAccion(null)}
          onConfirm={async () => { await api(`/transferencias/${accion.t.id_transferencia}/cancelar`, { method: 'POST' }); refrescar('Transferencia cancelada.') }} />
      )}
      {accion?.tipo === 'recibir' && !esAdmin && (
        <Confirmar titulo={`Recibir transferencia #${accion.t.id_transferencia}`} textoBoton="Confirmar recepción"
          mensaje={`Usted firmará como responsable de la recepción en ${accion.t.centro_destino_nombre} (RN-03). El inventario se descontará del origen y se sumará al destino en una sola transacción (RN-06).`}
          onClose={() => setAccion(null)}
          onConfirm={async () => { await api(`/transferencias/${accion.t.id_transferencia}/recibir`, { method: 'POST', body: {} }); refrescar('Transferencia recibida y cerrada.') }} />
      )}
      {accion?.tipo === 'recibir' && esAdmin && (
        <FormModal titulo={`Recibir transferencia #${accion.t.id_transferencia}`} textoBoton="Confirmar recepción"
          aviso="RN-03: la transferencia se cierra con responsable y fecha de recepción. RN-06: origen y destino se actualizan en una sola transacción."
          campos={[{ name: 'id_responsable', label: 'Responsable que recibe', type: 'select', numeric: true, required: true, span: true, opciones: OP.usuarios('OPERADOR_CENTRO') }]}
          onClose={() => setAccion(null)}
          onSubmit={(p) => api(`/transferencias/${accion.t.id_transferencia}/recibir`, { method: 'POST', body: p })}
          onExito={() => refrescar('Transferencia recibida y cerrada.')} />
      )}
    </>
  )
}
