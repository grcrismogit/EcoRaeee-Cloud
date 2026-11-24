import { useEffect, useMemo, useState } from 'react'
import { Calculator, CircleDot, GitBranch, Map as MapIcon } from 'lucide-react'
import { api } from '../api'
import { useAuth } from '../auth'
import { OP, TIPOS_NODO, UNIDADES } from '../catalogo'
import { Badge, ErrorCaja, fecha, num, useToast } from '../ui/feedback'
import Recurso, { Encabezado } from '../ui/Recurso'

// Capas por camino más largo desde la fuente (orden topológico), para dibujar el grafo de izquierda a derecha
function calcularPosiciones(nodos, aristas, ancho, alto) {
  const capa = Object.fromEntries(nodos.map((n) => [n.id_nodo, 0]))
  for (let i = 0; i < nodos.length; i++) {
    for (const a of aristas) capa[a.id_nodo_destino] = Math.max(capa[a.id_nodo_destino], Math.min(capa[a.id_nodo_origen] + 1, nodos.length))
  }
  for (const n of nodos) if (n.tipo_nodo === 'FUENTE') capa[n.id_nodo] = 0
  const maxCapa = Math.max(...nodos.map((n) => (n.tipo_nodo === 'SUMIDERO' ? 0 : capa[n.id_nodo])), 0) + 1
  for (const n of nodos) if (n.tipo_nodo === 'SUMIDERO') capa[n.id_nodo] = maxCapa
  const grupos = {}
  for (const n of nodos) (grupos[capa[n.id_nodo]] ||= []).push(n)
  const columnas = Object.keys(grupos).map(Number).sort((a, b) => a - b)
  const pos = {}
  columnas.forEach((c, i) => {
    const x = 60 + (i * (ancho - 120)) / Math.max(1, columnas.length - 1)
    grupos[c].forEach((n, j) => {
      const k = grupos[c].length
      pos[n.id_nodo] = { x, y: alto / 2 + (j - (k - 1) / 2) * Math.min(220, (alto - 110) / Math.max(1, k - 1)) }
    })
  })
  return pos
}

function Grafo({ nodos, aristas, resultado, unidad }) {
  const ancho = 820
  const alto = 400
  const pos = useMemo(() => calcularPosiciones(nodos, aristas, ancho, alto), [nodos, aristas])
  const flujos = Object.fromEntries((resultado?.flujos || []).map((f) => [f.id_arista, f]))
  if (!nodos.length) return <div className="empty-state">El escenario no tiene nodos.</div>
  return (
    <div className="graph">
      <svg viewBox={`0 0 ${ancho} ${alto}`} role="img" aria-label="Grafo dirigido de la red de traslados">
        <defs>
          {[['FUENTE', '#a7f3d0', '#059669', '#064e3b'], ['SUMIDERO', '#ddd6fe', '#7c3aed', '#3b0764'], ['INTERMEDIO', '#ffffff', '#e2ebe6', '#9fb3aa']].map(([k, c1, c2, c3]) => (
            <radialGradient key={k} id={`esfera-${k}`} cx="35%" cy="30%" r="75%">
              <stop offset="0%" stopColor={c1} /><stop offset="55%" stopColor={c2} /><stop offset="100%" stopColor={c3} />
            </radialGradient>
          ))}
          {['base', 'corte', 'idle'].map((k) => (
            <marker key={k} id={`flecha-${k}`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M0,0 L10,5 L0,10 z" fill={k === 'corte' ? 'var(--danger)' : k === 'idle' ? '#b8c2bd' : 'var(--brand-600)'} />
            </marker>
          ))}
        </defs>
        {aristas.map((a) => {
          const o = pos[a.id_nodo_origen]
          const d = pos[a.id_nodo_destino]
          if (!o || !d) return null
          const f = flujos[a.id_arista]
          const dx = d.x - o.x
          const dy = d.y - o.y
          const L = Math.hypot(dx, dy) || 1
          const r = 27
          const x1 = o.x + (dx / L) * r
          const y1 = o.y + (dy / L) * r
          const x2 = d.x - (dx / L) * (r + 3)
          const y2 = d.y - (dy / L) * (r + 3)
          const cx = (x1 + x2) / 2 - (dy / L) * 22
          const cy = (y1 + y2) / 2 + (dx / L) * 22
          const tipo = f?.en_corte_minimo ? 'corte' : f && f.flujo === 0 ? 'idle' : 'base'
          const color = tipo === 'corte' ? 'var(--danger)' : tipo === 'idle' ? '#b8c2bd' : 'var(--brand-600)'
          const texto = f ? `${num(f.flujo)}/${num(a.capacidad)}` : num(a.capacidad)
          return (
            <g key={a.id_arista}>
              <title>{`${a.origen_etiqueta} → ${a.destino_etiqueta}: ${f ? `flujo ${f.flujo} de ` : 'capacidad '}${a.capacidad} ${unidad}${f?.saturada ? ' · saturada' : ''}${f?.en_corte_minimo ? ' · en el corte mínimo' : ''}`}</title>
              <path className={f && f.flujo > 0 ? `arista-flujo ${tipo === 'corte' ? 'arista-corte' : ''}` : ''}
                d={`M${x1},${y1} Q${cx},${cy} ${x2},${y2}`} fill="none" stroke={color}
                strokeWidth={f?.saturada ? 3.5 : 2} strokeDasharray={tipo === 'corte' ? '7 5' : undefined} markerEnd={`url(#flecha-${tipo})`} />
              <rect x={(x1 + 2 * cx + x2) / 4 - 22} y={(y1 + 2 * cy + y2) / 4 - 10} width="44" height="19" rx="5" fill="#fff" stroke={color} strokeWidth="1" />
              <text x={(x1 + 2 * cx + x2) / 4} y={(y1 + 2 * cy + y2) / 4 + 4} textAnchor="middle" fontSize="11.5" fontWeight="600" fill="var(--text)">{texto}</text>
            </g>
          )
        })}
        {nodos.map((n, i) => {
          const p = pos[n.id_nodo]
          const relleno = `url(#esfera-${n.tipo_nodo})`
          const tinta = n.tipo_nodo === 'INTERMEDIO' ? 'var(--text)' : '#fff'
          return (
            <g key={n.id_nodo} className="nodo" style={{ animationDelay: `${i * 0.08}s` }}>
              <title>{`${n.etiqueta} · ${n.tipo_nodo}${n.centro_nombre ? ` · ${n.centro_nombre}` : ' · nodo lógico'}`}</title>
              <circle cx={p.x} cy={p.y} r="27" fill={relleno} stroke="rgba(6,34,25,.25)" strokeWidth="1" />
              <ellipse cx={p.x - 8} cy={p.y - 12} rx="9" ry="5" fill="rgba(255,255,255,.55)" />
              <text x={p.x} y={p.y + 4} textAnchor="middle" fontSize={n.etiqueta.length > 4 ? 10 : 12} fontWeight="700" fill={tinta}>{n.etiqueta}</text>
              <text x={p.x} y={p.y + 44} textAnchor="middle" fontSize="10.5" fill="var(--text-2)">{n.centro_nombre ? n.centro_nombre.replace('Punto de Acopio ', 'Acopio ') : 'nodo lógico'}</text>
            </g>
          )
        })}
      </svg>
      <div className="legend">
        <span><i /> arista con flujo, en movimiento (gruesa = saturada)</span>
        <span><i className="cut" /> arista del corte mínimo</span>
        <span><i className="idle" /> sin flujo</span>
        <span>Etiqueta: flujo / capacidad ({unidad.toLowerCase()})</span>
      </div>
    </div>
  )
}

export default function Red() {
  const { puede } = useAuth()
  const notificar = useToast()
  const [escenarios, setEscenarios] = useState([])
  const [idEsc, setIdEsc] = useState('')
  const [nodos, setNodos] = useState([])
  const [aristas, setAristas] = useState([])
  const [resultados, setResultados] = useState([])
  const [error, setError] = useState(null)
  const [calculando, setCalculando] = useState(false)
  const [tab, setTab] = useState('nodos')
  const [version, setVersion] = useState(0)

  const cargarEscenarios = () => api('/escenarios').then((e) => {
    setEscenarios(e)
    setIdEsc((actual) => actual || (e[0] ? String(e[0].id_escenario) : ''))
  }).catch(setError)
  useEffect(() => { cargarEscenarios() }, [])

  useEffect(() => {
    if (!idEsc) return
    Promise.all([api(`/nodos?id_escenario=${idEsc}`), api(`/aristas?id_escenario=${idEsc}`), api(`/escenarios/${idEsc}/resultados`)])
      .then(([n, a, r]) => { setNodos(n); setAristas(a); setResultados(r); setError(null) })
      .catch(setError)
  }, [idEsc, version])

  const escenario = escenarios.find((e) => String(e.id_escenario) === idEsc)
  const resultado = resultados[0]
  // El resultado solo se dibuja si corresponde a la red actual (mismas aristas)
  const vigente = resultado && resultado.flujos.length === aristas.length && resultado.flujos.every((f) => aristas.some((a) => a.id_arista === f.id_arista))
  const corte = vigente ? aristas.filter((a) => resultado.flujos.find((f) => f.id_arista === a.id_arista)?.en_corte_minimo) : []

  const calcular = async () => {
    setCalculando(true)
    try {
      const r = await api(`/escenarios/${idEsc}/flujo-maximo`, { method: 'POST' })
      notificar(`Flujo máximo = ${num(r.flujo_maximo)} ${escenario.unidad_medida.toLowerCase()}`, 'ok', 'Edmonds-Karp ejecutado')
      setVersion((v) => v + 1)
    } catch (e) {
      notificar(e.message, 'error')
    } finally {
      setCalculando(false)
    }
  }

  return (
    <>
      <Encabezado titulo="Red de traslados y flujo máximo" descripcion="Grafo dirigido G = (V, E) con capacidades por escenario (Matemáticas Discretas). El cálculo se guarda en resultado_flujo y flujo_arista.">
        <select className="input" style={{ width: 280 }} value={idEsc} onChange={(e) => setIdEsc(e.target.value)}>
          {escenarios.map((e) => <option key={e.id_escenario} value={e.id_escenario}>{e.nombre}</option>)}
        </select>
        {puede('COORDINADOR_LOGISTICO') && (
          <button className="btn primary" onClick={calcular} disabled={!idEsc || calculando}><Calculator /> {calculando ? 'Calculando…' : 'Calcular flujo máximo'}</button>
        )}
      </Encabezado>
      <ErrorCaja error={error} />

      {escenario && (
        <div className="grid" style={{ gridTemplateColumns: 'minmax(0, 2fr) minmax(280px, 1fr)', marginBottom: 16 }}>
          <div className="card">
            <div className="card-header"><h3>{escenario.nombre}</h3><span className="sub">{fecha(escenario.periodo_inicio, false)} – {fecha(escenario.periodo_fin, false)} · {nodos.length} nodos · {aristas.length} aristas</span></div>
            <div className="card-body"><Grafo nodos={nodos} aristas={aristas} resultado={vigente ? resultado : null} unidad={escenario.unidad_medida} /></div>
          </div>
          <div className="card">
            <div className="card-header"><h3>Resultado</h3></div>
            <div className="card-body">
              {!vigente ? (
                <p className="muted">{resultado ? 'La red cambió desde el último cálculo. ' : ''}Presione «Calcular flujo máximo» para ejecutar Edmonds-Karp sobre la red actual.</p>
              ) : (
                <>
                  <div className="small muted">Flujo máximo de la fuente al sumidero</div>
                  <div className="big-number">{num(resultado.flujo_maximo)} <span style={{ fontSize: 16, fontWeight: 500 }}>{escenario.unidad_medida.toLowerCase()}</span></div>
                  <div className="small muted" style={{ marginBottom: 14 }}>{resultado.algoritmo} · {fecha(resultado.fecha_ejecucion)} · {resultado.ejecutor_nombre}</div>
                  <b>Corte mínimo</b>
                  <table className="data" style={{ marginTop: 6 }}>
                    <tbody>
                      {corte.map((a) => <tr key={a.id_arista}><td>{a.origen_etiqueta} → {a.destino_etiqueta}</td><td className="num">{num(a.capacidad)}</td></tr>)}
                      <tr><td><b>Capacidad del corte</b></td><td className="num"><b>{num(corte.reduce((s, a) => s + a.capacidad, 0))}</b></td></tr>
                    </tbody>
                  </table>
                  <div className="alert ok" style={{ marginTop: 12, marginBottom: 0 }}>Teorema flujo máximo = corte mínimo: {num(resultado.flujo_maximo)} = {num(corte.reduce((s, a) => s + a.capacidad, 0))}</div>
                </>
              )}
              {resultados.length > 1 && <p className="small muted" style={{ marginTop: 12 }}>{resultados.length} cálculos guardados para este escenario.</p>}
            </div>
          </div>
        </div>
      )}

      <div className="tabs">
        <button className={`tab ${tab === 'nodos' ? 'active' : ''}`} onClick={() => setTab('nodos')}><CircleDot /> Nodos (V)</button>
        <button className={`tab ${tab === 'aristas' ? 'active' : ''}`} onClick={() => setTab('aristas')}><GitBranch /> Aristas (E)</button>
        <button className={`tab ${tab === 'escenarios' ? 'active' : ''}`} onClick={() => setTab('escenarios')}><MapIcon /> Escenarios</button>
      </div>

      {tab === 'nodos' && idEsc && (
        <Recurso embebido nombre="nodo" endpoint="/nodos" idKey="id_nodo" buscar={false} rolesEscritura={['COORDINADOR_LOGISTICO']}
          queryBase={{ id_escenario: idEsc }} inicialCrear={{ id_escenario: idEsc }} onCambio={() => setVersion((v) => v + 1)}
          columnas={[
            { key: 'etiqueta', label: 'Etiqueta', render: (n) => <b>{n.etiqueta}</b> },
            { key: 'tipo_nodo', label: 'Tipo', render: (n) => <Badge valor={n.tipo_nodo} /> },
            { key: 'centro_nombre', label: 'Centro que representa', render: (n) => n.centro_nombre || <span className="muted">Nodo lógico (sin centro)</span> },
          ]}
          campos={[
            { name: 'id_escenario', label: 'Escenario', type: 'select', numeric: true, required: true, disabled: true, options: escenarios.map((e) => ({ value: e.id_escenario, label: e.nombre })) },
            { name: 'etiqueta', label: 'Etiqueta', required: true, maxLength: 20, pattern: '^[A-Za-z0-9_-]+$', patternMsg: 'Solo letras, números, - y _' },
            { name: 'tipo_nodo', label: 'Tipo de nodo', type: 'select', required: true, options: TIPOS_NODO },
            { name: 'id_centro', label: 'Centro', type: 'select', numeric: true, opciones: OP.centros, placeholder: 'Ninguno (nodo lógico)' },
          ]}
          aFormulario={(n) => ({ ...n, id_centro: n.id_centro ?? '' })}
        />
      )}
      {tab === 'aristas' && idEsc && (
        <Recurso embebido nombre="arista" femenino endpoint="/aristas" idKey="id_arista" buscar={false} rolesEscritura={['COORDINADOR_LOGISTICO']}
          queryBase={{ id_escenario: idEsc }} inicialCrear={{ id_escenario: idEsc }} onCambio={() => setVersion((v) => v + 1)}
          columnas={[
            { key: 'id_arista', label: '#' },
            { key: 'ruta', label: 'Origen → destino', render: (a) => <b>{a.origen_etiqueta} → {a.destino_etiqueta}</b> },
            { key: 'capacidad', label: `Capacidad (${escenario?.unidad_medida.toLowerCase() || ''})`, className: 'num', render: (a) => num(a.capacidad) },
            { key: 'flujo', label: 'Último flujo', className: 'num', render: (a) => { const f = vigente && resultado.flujos.find((x) => x.id_arista === a.id_arista); return f ? `${num(f.flujo)}${f.saturada ? ' (saturada)' : ''}` : '—' } },
          ]}
          campos={[
            { name: 'id_escenario', label: 'Escenario', type: 'select', numeric: true, required: true, disabled: true, span: true, options: escenarios.map((e) => ({ value: e.id_escenario, label: e.nombre })) },
            { name: 'id_nodo_origen', label: 'Nodo origen', type: 'select', numeric: true, required: true, options: nodos.map((n) => ({ value: n.id_nodo, label: n.etiqueta })) },
            { name: 'id_nodo_destino', label: 'Nodo destino', type: 'select', numeric: true, required: true, options: nodos.map((n) => ({ value: n.id_nodo, label: n.etiqueta })),
              validate: (v, x) => (String(v) === String(x.id_nodo_origen) ? 'No puede ser el mismo nodo (sin bucles)' : null) },
            { name: 'capacidad', label: 'Capacidad', type: 'number', step: '0.01', required: true, gt: 0 },
          ]}
        />
      )}
      {tab === 'escenarios' && (
        <Recurso embebido nombre="escenario" endpoint="/escenarios" idKey="id_escenario" buscar={false} rolesEscritura={['COORDINADOR_LOGISTICO']}
          onCambio={cargarEscenarios}
          columnas={[
            { key: 'nombre', label: 'Nombre', render: (e) => <b>{e.nombre}</b> },
            { key: 'periodo', label: 'Periodo', render: (e) => `${fecha(e.periodo_inicio, false)} – ${fecha(e.periodo_fin, false)}` },
            { key: 'unidad_medida', label: 'Unidad' },
            { key: 'descripcion', label: 'Descripción', render: (e) => <span className="small">{e.descripcion || '—'}</span> },
          ]}
          campos={[
            { name: 'nombre', label: 'Nombre', required: true, minLength: 3, maxLength: 80, span: true },
            { name: 'periodo_inicio', label: 'Inicio', type: 'date', required: true },
            { name: 'periodo_fin', label: 'Fin', type: 'date', required: true, validate: (v, x) => (x.periodo_inicio && v < x.periodo_inicio ? 'Debe ser posterior al inicio' : null) },
            { name: 'unidad_medida', label: 'Unidad de capacidad', type: 'select', required: true, options: UNIDADES },
            { name: 'descripcion', label: 'Descripción', type: 'textarea', maxLength: 250, span: true },
          ]}
        />
      )}
    </>
  )
}
