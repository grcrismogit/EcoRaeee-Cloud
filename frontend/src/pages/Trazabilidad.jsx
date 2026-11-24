import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeftRight, ClipboardCheck, Download, Flag, Inbox, Package, Search, ShieldCheck } from 'lucide-react'
import { api, descargarArchivo } from '../api'
import { Badge, Cargando, ErrorCaja, etiqueta, fecha, num, useToast } from '../ui/feedback'
import { Encabezado } from '../ui/Recurso'
import { Icono3D, iconoCategoria } from '../ui/Efectos'
import Miniatura from '../ui/Miniatura'

const PASOS = [
  { icono: Package, texto: 'Registro', hecho: (t) => true },
  { icono: Inbox, texto: 'Recepción', hecho: (t) => Boolean(t.recepcion) },
  { icono: ClipboardCheck, texto: 'Evaluación', hecho: (t) => t.evaluaciones.length > 0 },
  { icono: ArrowLeftRight, texto: 'Transferencia', hecho: (t) => t.transferencias.some((x) => x.estado === 'CERRADA') },
  { icono: Flag, texto: 'Destino final', hecho: (t) => Boolean(t.destino_final) },
]

export default function Trazabilidad() {
  const { codigo } = useParams()
  const navegar = useNavigate()
  const notificar = useToast()
  const [texto, setTexto] = useState(codigo || '')
  const [traza, setTraza] = useState(null)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    setTexto(codigo || '')
    if (!codigo) { setTraza(null); return }
    setCargando(true)
    api(`/trazabilidad/${encodeURIComponent(codigo)}`)
      .then((r) => { setTraza(r); setError(null) })
      .catch((e) => { setTraza(null); setError(e) })
      .finally(() => setCargando(false))
  }, [codigo])

  const verificar = async (ev) => {
    try {
      const r = await api(`/evidencias/${ev.id_evidencia}/verificar`)
      notificar(r.mensaje, r.integra ? 'ok' : 'error', r.integra ? 'Integridad verificada (SHA-256)' : 'Integridad comprometida')
    } catch (e) { notificar(e.message, 'error') }
  }

  return (
    <>
      <Encabezado titulo="Trazabilidad" descripcion="Consulte de dónde vino un equipo, quién lo evaluó, por dónde pasó y dónde terminó." />
      <form className="card" style={{ padding: 16, display: 'flex', gap: 10, marginBottom: 16 }}
        onSubmit={(e) => { e.preventDefault(); if (texto.trim()) navegar(`/trazabilidad/${texto.trim().toUpperCase()}`) }}>
        <input className="input" placeholder="Código único del dispositivo, p. ej. RAEE-2026-00002" value={texto} onChange={(e) => setTexto(e.target.value)} />
        <button className="btn primary"><Search /> Rastrear</button>
      </form>

      {cargando && <Cargando />}
      <ErrorCaja error={error} />
      {!codigo && !cargando && <div className="card empty-state">Ingrese un código o abra un dispositivo desde la lista de <Link to="/dispositivos">Dispositivos</Link>.</div>}

      {traza && !cargando && (() => {
        const d = traza.dispositivo
        return (
          <>
            <div className="card" style={{ marginBottom: 16 }}>
              <div className="card-header">
                <Icono3D {...iconoCategoria(d.categoria_nombre)} tamano={42} />
                <h3 className="mono" style={{ fontSize: 17 }}>{d.codigo_unico}</h3>
                <Badge valor={d.estado_actual} />
                {d.clasificacion && <Badge valor={d.clasificacion} />}
                <span className="sub" style={{ marginLeft: 'auto' }}>{d.categoria_nombre} · {[d.marca_nombre, d.modelo].filter(Boolean).join(' ') || 'sin marca/modelo'}</span>
              </div>
              <div className="card-body">
                <div className="steps">
                  {PASOS.map(({ icono: Icono, texto: t, hecho }) => (
                    <div key={t} className={`step ${hecho(traza) ? 'done' : ''}`}><div className="circle"><Icono /></div>{t}</div>
                  ))}
                </div>
              </div>
            </div>

            <div className="grid grid-2">
              <div className="card">
                <div className="card-header"><h3>Historial de estados</h3><span className="sub">entidad débil · generado por trigger (RN-01)</span></div>
                <div className="card-body">
                  <div className="timeline">
                    {traza.historial.map((h) => (
                      <div className="tl-item" key={h.nro_cambio}>
                        <div className="tl-dot"><ShieldCheck /></div>
                        <div><b>#{h.nro_cambio}</b> {h.estado_anterior ? <>{etiqueta(h.estado_anterior)} → </> : 'Alta: '}<Badge valor={h.estado_nuevo} /></div>
                        <div className="when">{fecha(h.fecha_cambio)} · {h.usuario_nombre || 'sistema'}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="grid" style={{ alignContent: 'start' }}>
                <div className="card">
                  <div className="card-header"><h3>Origen</h3></div>
                  <div className="card-body">
                    <dl className="dl">
                      <dt>Lote</dt><dd><b>{traza.lote.codigo_lote}</b> · {traza.lote.descripcion}</dd>
                      <dt>Generador</dt><dd>{traza.lote.generador_nombre}</dd>
                      <dt>Peso / serie</dt><dd>{num(d.peso_kg)} kg · {d.numero_serie || 'sin serie'}</dd>
                      <dt>Recepción</dt><dd>{traza.recepcion ? `${traza.recepcion.centro_nombre} · ${fecha(traza.recepcion.fecha_recepcion)} · ${traza.recepcion.operador_nombre}` : 'Pendiente'}</dd>
                      <dt>Ubicación actual</dt><dd>{d.centro_actual_nombre || '—'}</dd>
                    </dl>
                  </div>
                </div>

                <div className="card">
                  <div className="card-header"><h3>Evaluaciones técnicas</h3></div>
                  <div className="card-body">
                    {traza.evaluaciones.length === 0 ? <span className="muted">Sin evaluaciones.</span> : traza.evaluaciones.map((e) => (
                      <div key={e.id_evaluacion} style={{ marginBottom: 10 }}>
                        <Badge valor={e.clasificacion} /> <span className="tag">{etiqueta(e.condicion)}</span>{' '}
                        {e.borrado_datos && <span className="tag">datos borrados</span>}
                        <div className="small muted">{fecha(e.fecha_evaluacion)} · {e.tecnico_nombre}</div>
                        {e.observaciones && <div className="small">{e.observaciones}</div>}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="card">
                  <div className="card-header"><h3>Transferencias</h3></div>
                  <div className="card-body">
                    {traza.transferencias.length === 0 ? <span className="muted">No ha sido transferido.</span> : traza.transferencias.map((x) => (
                      <div key={x.id_transferencia} style={{ marginBottom: 10 }}>
                        <b>#{x.id_transferencia}</b> {x.centro_origen_nombre} → {x.centro_destino_nombre} <Badge valor={x.estado} />
                        <div className="small muted">Salida {fecha(x.fecha_salida)}{x.fecha_recepcion ? ` · recibida ${fecha(x.fecha_recepcion)} por ${x.responsable_nombre}` : ''}{x.arista_descripcion ? ` · ruta ${x.arista_descripcion}` : ''}</div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="card">
                  <div className="card-header"><h3>Destino final</h3></div>
                  <div className="card-body">
                    {traza.destino_final ? (
                      <dl className="dl">
                        <dt>Tipo</dt><dd><Badge valor={traza.destino_final.tipo_destino} /></dd>
                        <dt>Centro</dt><dd>{traza.destino_final.centro_nombre}</dd>
                        {traza.destino_final.org_beneficiaria_nombre && <><dt>Beneficiaria</dt><dd>{traza.destino_final.org_beneficiaria_nombre}</dd></>}
                        <dt>Confirmado</dt><dd>{fecha(traza.destino_final.fecha_confirmacion)} · {traza.destino_final.usuario_confirma_nombre}</dd>
                      </dl>
                    ) : <span className="muted">Aún abierto.</span>}
                  </div>
                </div>

                <div className="card">
                  <div className="card-header"><h3>Evidencias</h3><span className="sub">RN-07</span></div>
                  <div className="card-body">
                    {traza.evidencias.length === 0 ? <span className="muted">Sin evidencias.</span> : traza.evidencias.map((ev) => (
                      <div key={ev.id_evidencia} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                        <Miniatura ev={ev} />
                        <span className="tag">{ev.tipo_evidencia}</span>
                        <span className="small">{ev.nombre_archivo}</span>
                        <span className="small muted">({ev.vinculo})</span>
                        <button className="icon-btn" title="Verificar integridad" aria-label="Verificar integridad" onClick={() => verificar(ev)} style={{ marginLeft: 'auto' }}><ShieldCheck /></button>
                        <button className="icon-btn" title="Descargar" aria-label="Descargar" onClick={() => descargarArchivo(`/evidencias/${ev.id_evidencia}/archivo`, ev.nombre_archivo).catch((e) => notificar(e.message, 'error'))}><Download /></button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </>
        )
      })()}
    </>
  )
}
