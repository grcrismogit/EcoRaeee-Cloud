import { useState } from 'react'
import { useApi } from '../api'
import { OP } from '../catalogo'
import { Badge, Cargando, ErrorCaja, fecha, num } from '../ui/feedback'
import Recurso, { Encabezado } from '../ui/Recurso'

export function Inventario() {
  const { datos, cargando, error } = useApi('/dashboard')
  return (
    <>
      <Encabezado titulo="Inventario por centro" descripcion="Existencias por centro y categoría. Lo mantienen los triggers de la base: nadie lo edita a mano (RN-06)." />
      <ErrorCaja error={error} />
      {cargando && !datos ? <Cargando /> : datos && (
        <div className="kpis">
          {datos.ocupacion_centros.map((c) => (
            <div className="card kpi" key={c.id_centro}>
              <div className="label">{c.nombre}</div>
              <div className="value">{c.unidades} <span style={{ fontSize: 14, fontWeight: 500, color: 'var(--muted)' }}>/ {c.capacidad_unidades}</span></div>
              <div className="bar-track" style={{ margin: '8px 0 6px' }}><div className="bar-fill" style={{ width: `${Math.min(100, c.ocupacion_pct)}%` }} /></div>
              <div className="hint">{num(c.peso_kg)} kg · ocupación {num(c.ocupacion_pct, 1)} %</div>
            </div>
          ))}
        </div>
      )}
      <Recurso
        embebido nombre="existencia" femenino endpoint="/inventario" idKey={(i) => `${i.id_centro}-${i.id_categoria}`} buscar={false}
        filtros={[{ name: 'id_centro', label: 'Todos los centros', opciones: OP.centros }]}
        columnas={[
          { key: 'centro_nombre', label: 'Centro' },
          { key: 'categoria_nombre', label: 'Categoría' },
          { key: 'cantidad_unidades', label: 'Unidades', className: 'num' },
          { key: 'peso_total_kg', label: 'Peso (kg)', className: 'num', render: (i) => num(i.peso_total_kg) },
          { key: 'fecha_actualizacion', label: 'Actualizado', render: (i) => <span className="small">{fecha(i.fecha_actualizacion)}</span> },
        ]}
      />
    </>
  )
}

const TABLAS = ['usuario', 'centro', 'lote', 'dispositivo', 'recepcion', 'evaluacion_tecnica', 'transferencia', 'destino_final', 'evidencia']

function Cambios({ fila }) {
  const antes = fila.datos_antes || {}
  const despues = fila.datos_despues || {}
  if (fila.operacion === 'I') return <span className="small muted">Alta de registro</span>
  if (fila.operacion === 'D') return <span className="small muted">Registro eliminado</span>
  const campos = Object.keys(despues).filter((k) => JSON.stringify(antes[k]) !== JSON.stringify(despues[k]))
  return (
    <div className="diff">
      {campos.slice(0, 4).map((k) => (
        <div key={k}><b>{k}</b>: <span className="old">{String(antes[k] ?? '∅')}</span> → <span className="new">{String(despues[k] ?? '∅')}</span></div>
      ))}
      {campos.length > 4 && <div className="muted">+{campos.length - 4} campo(s) más</div>}
    </div>
  )
}

export function Auditoria() {
  const [abierto, setAbierto] = useState(null)
  return (
    <>
      <Recurso
        titulo="Auditoría" nombre="evento" endpoint="/auditoria" idKey="id_auditoria" buscar={false}
        descripcion="Bitácora de cambios sensibles generada por triggers: quién, qué, cuándo, antes y después."
        queryBase={{ limite: 150 }}
        filtros={[
          { name: 'tabla', label: 'Todas las tablas', options: TABLAS.map((t) => ({ value: t, label: t })) },
          { name: 'operacion', label: 'Toda operación', options: [{ value: 'I', label: 'Inserción' }, { value: 'U', label: 'Actualización' }, { value: 'D', label: 'Eliminación' }] },
        ]}
        columnas={[
          { key: 'id_auditoria', label: '#' },
          { key: 'fecha', label: 'Fecha', render: (a) => <span className="small">{fecha(a.fecha)}</span> },
          { key: 'tabla', label: 'Tabla', render: (a) => <span className="mono">{a.tabla}</span> },
          { key: 'operacion', label: 'Op.', render: (a) => <Badge valor={a.operacion} /> },
          { key: 'id_registro', label: 'Registro', className: 'num' },
          { key: 'usuario_nombre', label: 'Usuario', render: (a) => a.usuario_nombre || <span className="muted">sistema</span> },
          { key: 'cambios', label: 'Cambios', render: (a) => (
            <div>
              <Cambios fila={a} />
              <button className="btn ghost sm" onClick={() => setAbierto(abierto === a.id_auditoria ? null : a.id_auditoria)}>{abierto === a.id_auditoria ? 'Ocultar JSON' : 'Ver JSON'}</button>
              {abierto === a.id_auditoria && <pre className="mono small" style={{ whiteSpace: 'pre-wrap', maxWidth: 520, background: 'var(--surface-2)', padding: 8, borderRadius: 6 }}>{JSON.stringify({ antes: a.datos_antes, despues: a.datos_despues }, null, 2)}</pre>}
            </div>
          ) },
        ]}
      />
    </>
  )
}
