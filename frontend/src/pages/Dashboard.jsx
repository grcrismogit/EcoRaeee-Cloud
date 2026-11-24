import { Suspense, lazy } from 'react'
import { Link } from 'react-router-dom'
import { CheckCircle2, ClipboardList, Code2, Database, Leaf, Route, Server, Smartphone, Boxes } from 'lucide-react'
import { useApi } from '../api'
import { useAuth } from '../auth'
import { Badge, Cargando, ErrorCaja, etiqueta, fecha, num } from '../ui/feedback'

// El globo 3D se carga aparte para que el tablero abra rápido
const Planeta = lazy(() => import('../three/Planeta'))

// Barras horizontales de una sola serie: un solo color, valor rotulado y detalle al pasar el mouse
function Barras({ datos, campo, valor = 'cantidad', total }) {
  const max = Math.max(1, ...datos.map((d) => d[valor]))
  return (
    <div className="bars">
      {datos.map((d) => (
        <div className="bar-row tooltip-host" key={d[campo]}>
          <span className="lbl">{etiqueta(d[campo])}</span>
          <div className="bar-track">
            <div className="bar-fill" style={{ width: `${(d[valor] / max) * 100}%` }} />
          </div>
          <span className="val">{d[valor]}</span>
          <span className="tip">{etiqueta(d[campo])}: {d[valor]} dispositivo(s){total ? `, ${Math.round((d[valor] / total) * 100)} %` : ''}</span>
        </div>
      ))}
    </div>
  )
}

export default function Dashboard() {
  const { usuario } = useAuth()
  const { datos, cargando, error } = useApi('/dashboard')
  if (cargando && !datos) return <Cargando />
  if (error) return <ErrorCaja error={error} />
  const t = datos.totales

  const kpis = [
    { icono: Smartphone, label: 'Dispositivos registrados', valor: num(t.dispositivos), hint: `en ${t.lotes} lotes · ${num(t.kg_total, 1)} kg` },
    { icono: Leaf, label: 'Kilos recuperados', valor: num(t.kg_recuperados, 1), hint: 'donados, reusados o reciclados' },
    { icono: CheckCircle2, label: 'Trazabilidad cerrada', valor: num(t.cerrados), hint: 'equipos con destino final' },
    { icono: ClipboardList, label: 'Por evaluar', valor: num(t.por_evaluar), hint: `${t.transferencias_activas} transferencia(s) activa(s)` },
  ]

  return (
    <>
      <section className="hero">
        <div>
          <h1>Hola, {usuario.nombres}</h1>
          <p>Así va hoy el ciclo de los equipos electrónicos en la red universitaria, desde el registro hasta su destino final.</p>
          <div className="acciones-hero">
            <Link to="/trazabilidad" className="btn primary"><Route /> Consultar trazabilidad</Link>
            <Link to="/lotes" className="btn"><Boxes /> Ver lotes</Link>
          </div>
          <div className="pie-hero">
            <span><Code2 /> React en Amazon S3</span>
            <span><Server /> FastAPI en EC2</span>
            <span><Database /> PostgreSQL 16 en RDS</span>
          </div>
        </div>
        <div className="planeta" aria-hidden="true">
          <Suspense fallback={<div className="planeta-respaldo" />}><Planeta /></Suspense>
        </div>
      </section>

      <div className="kpis">
        {kpis.map(({ icono: Icono, label, valor, hint }) => (
          <div className="kpi" key={label}>
            <div className="label"><span className="ico"><Icono /></span>{label}</div>
            <div className="value">{valor}</div>
            <div className="hint">{hint}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-3">
        <div className="card">
          <div className="card-header"><h3>Dispositivos por estado</h3><span className="sub">estado actual</span></div>
          <div className="card-body"><Barras datos={datos.por_estado} campo="estado" total={t.dispositivos} /></div>
        </div>
        <div className="card">
          <div className="card-header"><h3>Clasificación técnica</h3><span className="sub">última evaluación</span></div>
          <div className="card-body"><Barras datos={datos.por_clasificacion} campo="clasificacion" total={t.dispositivos} /></div>
        </div>
        <div className="card">
          <div className="card-header"><h3>Ocupación de centros</h3><span className="sub">uso de capacidad</span></div>
          <div className="card-body">
            {datos.ocupacion_centros.map((c) => (
              <div className="meter tooltip-host" key={c.id_centro}>
                <div className="meter-top"><span>{c.nombre}</span><span>{num(c.ocupacion_pct, 1)} %</span></div>
                <div className="bar-track"><div className="bar-fill" style={{ width: `${Math.min(100, c.ocupacion_pct)}%` }} /></div>
                <span className="tip">{c.unidades} de {c.capacidad_unidades} unidades · {num(c.peso_kg)} de {num(c.capacidad_kg)} kg</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 18 }}>
        <div className="card-header"><h3>Últimos movimientos</h3><span className="sub">historial de estados (RN-01)</span></div>
        <div className="table-wrap">
          <table className="data">
            <thead><tr><th>Dispositivo</th><th>Cambio</th><th>Usuario</th><th>Fecha</th></tr></thead>
            <tbody>
              {datos.ultimos_movimientos.slice(0, 6).map((h) => (
                <tr key={`${h.id_dispositivo}-${h.nro_cambio}`}>
                  <td><Link to={`/trazabilidad/${h.codigo_unico}`} className="mono">{h.codigo_unico}</Link></td>
                  <td className="nowrap">{h.estado_anterior ? <><Badge valor={h.estado_anterior} /> → </> : null}<Badge valor={h.estado_nuevo} /></td>
                  <td>{h.usuario_nombre || '—'}</td>
                  <td className="small muted nowrap">{fecha(h.fecha_cambio)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}
