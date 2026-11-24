// Página CRUD genérica: tabla + filtros + búsqueda + formularios de crear/editar + eliminar.
import { useEffect, useMemo, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { ArrowLeftRight, ChevronRight, ClipboardCheck, Flag, Inbox, Package, Pencil, Plus, RefreshCw, Search, Trash2, Truck } from 'lucide-react'
import { itemDeRuta } from '../menu'
import { Icono3D } from './Efectos'
import { api, construirQuery } from '../api'
import { useAuth } from '../auth'
import { Cargando, Confirmar, ErrorCaja, useToast } from './feedback'
import { Campo, FormModal } from './Formulario'

// Ciclo RAEE: orienta al usuario sobre en qué paso del proceso está
const PASOS = [
  { to: '/lotes', rutas: ['/lotes', '/dispositivos'], texto: 'Registro', detalle: 'Lotes y dispositivos', icono: Package },
  { to: '/recoleccion', rutas: ['/recoleccion'], texto: 'Recolección', detalle: 'Solicitud y recepción', icono: Truck },
  { to: '/evaluaciones', rutas: ['/evaluaciones'], texto: 'Evaluación', detalle: 'Diagnóstico técnico', icono: ClipboardCheck },
  { to: '/transferencias', rutas: ['/transferencias'], texto: 'Transferencia', detalle: 'Entre centros', icono: ArrowLeftRight },
  { to: '/destinos', rutas: ['/destinos'], texto: 'Destino final', detalle: 'Cierre de trazabilidad', icono: Flag },
]

function CicloRAEE({ ruta }) {
  if (!PASOS.some((p) => p.rutas.includes(ruta))) return null
  return (
    <nav className="proceso" aria-label="Ciclo de trazabilidad RAEE">
      <span className="rotulo">Ciclo RAEE</span>
      {PASOS.map((p, i) => (
        <span key={p.to} style={{ display: 'contents' }}>
          {i > 0 && <ChevronRight className="sep" />}
          <NavLink to={p.to} className={`paso ${p.rutas.includes(ruta) ? 'activo' : ''}`} title={p.detalle}>
            <span className="num">{i + 1}</span>
            <span><b>{p.texto}</b><small>{p.detalle}</small></span>
          </NavLink>
        </span>
      ))}
    </nav>
  )
}

export function Encabezado({ titulo, descripcion, children }) {
  const ruta = useLocation().pathname
  const item = itemDeRuta(ruta)
  return (
    <>
    <div className="page-header">
      <div className="titulo">
        {item && <Icono3D icono={item.icono} color={item.color} tamano={52} />}
        <div>
          <h1>{titulo}</h1>
          {descripcion && <p>{descripcion}</p>}
        </div>
      </div>
      <div className="actions">{children}</div>
    </div>
    <CicloRAEE ruta={ruta} />
    </>
  )
}

export default function Recurso({
  titulo, descripcion, nombre = 'registro', endpoint, idKey, columnas, campos, camposEditar,
  rolesEscritura, permitirCrear = true, permitirEditar = true, permitirEliminar = true,
  filtros = [], buscar = true, queryBase = {}, filtrosIniciales = {}, inicialCrear = {}, aFormulario,
  cargarParaEditar, accionesFila, enviarCrear, enviarEditar, avisoCrear, avisoEditar, textoCrear,
  onCambio, embebido = false, extraAcciones, tamanoModal, recargaExterna, abrirAlIniciar = false, femenino = false,
}) {
  const { puede } = useAuth()
  const notificar = useToast()
  const [filas, setFilas] = useState([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState(null)
  const [valoresFiltro, setValoresFiltro] = useState(filtrosIniciales)
  const [texto, setTexto] = useState('')
  const [q, setQ] = useState('')
  const [modal, setModal] = useState(null) // {modo, fila, inicial}
  const [borrar, setBorrar] = useState(null)

  const escribe = rolesEscritura !== undefined && puede(...rolesEscritura)
  const idDe = typeof idKey === 'function' ? idKey : (f) => f[idKey]
  const Nombre = nombre[0].toUpperCase() + nombre.slice(1)
  const o = femenino ? 'a' : 'o'
  const nuevo = textoCrear || `${femenino ? 'Nueva' : 'Nuevo'} ${nombre}`
  const query = useMemo(() => construirQuery({ ...queryBase, ...valoresFiltro, q }), [queryBase, valoresFiltro, q])

  useEffect(() => { const t = setTimeout(() => setQ(texto), 300); return () => clearTimeout(t) }, [texto])

  const recargar = async () => {
    setCargando(true)
    try {
      setFilas(await api(endpoint + query))
      setError(null)
    } catch (e) {
      setError(e)
    } finally {
      setCargando(false)
    }
  }
  useEffect(() => { recargar() }, [endpoint, query, recargaExterna]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (abrirAlIniciar && escribe) setModal({ modo: 'crear', inicial: typeof inicialCrear === 'function' ? inicialCrear() : inicialCrear })
  }, [abrirAlIniciar, escribe]) // eslint-disable-line react-hooks/exhaustive-deps

  const despues = (mensaje) => { notificar(mensaje); recargar(); onCambio?.() }

  const abrirEditar = async (fila) => {
    try {
      const completa = cargarParaEditar ? await cargarParaEditar(fila) : fila
      setModal({ modo: 'editar', fila, inicial: aFormulario ? aFormulario(completa) : completa })
    } catch (e) {
      notificar(e.message, 'error')
    }
  }

  const puedeFila = (regla, fila) => (typeof regla === 'function' ? regla(fila) : regla)

  return (
    <>
      {!embebido && (
        <Encabezado titulo={titulo} descripcion={descripcion}>
          {extraAcciones}
          {escribe && permitirCrear && (
            <button className="btn primary" onClick={() => setModal({ modo: 'crear', inicial: typeof inicialCrear === 'function' ? inicialCrear() : inicialCrear })}>
              <Plus /> {nuevo}
            </button>
          )}
        </Encabezado>
      )}

      <div className="card">
        <div className="toolbar">
          {buscar && (
            <div className="grow" style={{ position: 'relative' }}>
              <Search style={{ position: 'absolute', left: 9, top: 9, width: 16, color: 'var(--muted)' }} />
              <input className="input" style={{ paddingLeft: 32 }} placeholder="Buscar…" value={texto} onChange={(e) => setTexto(e.target.value)} />
            </div>
          )}
          {filtros.map((f) => (
            <div key={f.name} style={{ minWidth: 170 }}>
              <Campo campo={{ ...f, type: 'select', placeholder: f.label }} valores={valoresFiltro}
                setValor={(n, v) => setValoresFiltro((x) => ({ ...x, [n]: v }))} modo="filtro" />
            </div>
          ))}
          <button className="icon-btn" title="Recargar" aria-label="Recargar" onClick={recargar}><RefreshCw /></button>
          {embebido && escribe && permitirCrear && (
            <button className="btn primary sm" onClick={() => setModal({ modo: 'crear', inicial: typeof inicialCrear === 'function' ? inicialCrear() : inicialCrear })}>
              <Plus /> {nuevo}
            </button>
          )}
          <span className="count">{filas.length} registro(s)</span>
        </div>
        <ErrorCaja error={error} />
        {cargando && !filas.length ? <Cargando /> : filas.length === 0 ? (
          <div className="empty-state"><Icono3D icono={Inbox} color="teal" tamano={48} />No hay registros que coincidan.</div>
        ) : (
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  {columnas.map((c) => <th key={c.key} className={c.className}>{c.label}</th>)}
                  <th />
                </tr>
              </thead>
              <tbody>
                {filas.map((f) => (
                  <tr key={idDe(f)}>
                    {columnas.map((c) => <td key={c.key} className={c.className}>{c.render ? c.render(f) : (f[c.key] ?? '—')}</td>)}
                    <td className="actions">
                      {(accionesFila?.(f, { recargar: () => despues('Operación realizada.'), notificar }) || [])
                        .filter((a) => a && a.show !== false)
                        .map((a) => (
                          <button key={a.title} className={`icon-btn ${a.danger ? 'danger' : ''}`} title={a.title} aria-label={a.title} onClick={a.onClick}>{a.icon}</button>
                        ))}
                      {escribe && puedeFila(permitirEditar, f) && (
                        <button className="icon-btn" title="Editar" aria-label="Editar" onClick={() => abrirEditar(f)}><Pencil /></button>
                      )}
                      {escribe && puedeFila(permitirEliminar, f) && (
                        <button className="icon-btn danger" title="Eliminar" aria-label="Eliminar" onClick={() => setBorrar(f)}><Trash2 /></button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {modal && (
        <FormModal
          titulo={modal.modo === 'crear' ? nuevo : `Editar ${nombre}`}
          campos={modal.modo === 'editar' && camposEditar ? camposEditar : campos}
          modo={modal.modo}
          inicial={modal.inicial}
          aviso={modal.modo === 'crear' ? avisoCrear : avisoEditar}
          size={tamanoModal}
          onClose={() => setModal(null)}
          onSubmit={(payload, valores) => (modal.modo === 'crear'
            ? (enviarCrear ? enviarCrear(payload, valores) : api(endpoint, { method: 'POST', body: payload }))
            : (enviarEditar ? enviarEditar(idDe(modal.fila), payload, valores) : api(`${endpoint}/${idDe(modal.fila)}`, { method: 'PUT', body: payload })))}
          onExito={() => despues(modal.modo === 'crear' ? `${Nombre} registrad${o} correctamente.` : 'Cambios guardados.')}
        />
      )}

      {borrar && (
        <Confirmar
          titulo={`Eliminar ${nombre}`}
          mensaje={<>¿Seguro que desea eliminar est{femenino ? 'a' : 'e'} {nombre}? La base de datos verificará que no esté en uso.</>}
          textoBoton="Eliminar" peligro
          onClose={() => setBorrar(null)}
          onConfirm={async () => { await api(`${endpoint}/${idDe(borrar)}`, { method: 'DELETE' }); despues(`${Nombre} eliminad${o}.`) }}
        />
      )}
    </>
  )
}
