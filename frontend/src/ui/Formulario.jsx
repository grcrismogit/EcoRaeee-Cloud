// Formularios declarativos con validación en el cliente.
// Cada página describe sus campos; este módulo los dibuja, valida y arma el JSON para la API.
import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, Info } from 'lucide-react'
import { api } from '../api'
import { Modal } from './feedback'

const vacio = (v) => v === undefined || v === null || v === '' || (Array.isArray(v) && v.length === 0)

export const visible = (campo, valores, modo) =>
  !(campo.show && !campo.show(valores, modo)) &&
  !(campo.soloCrear && modo === 'editar') &&
  !(campo.soloEditar && modo === 'crear')

export function validar(campos, valores, modo) {
  const errores = {}
  for (const c of campos) {
    if (!visible(c, valores, modo)) continue
    const v = valores[c.name]
    const requerido = typeof c.required === 'function' ? c.required(valores, modo) : c.required
    if (requerido && vacio(v)) { errores[c.name] = 'Este campo es obligatorio'; continue }
    if (vacio(v)) continue
    if (c.type === 'number') {
      const n = Number(v)
      if (Number.isNaN(n)) { errores[c.name] = 'Debe ser un número'; continue }
      if (c.integer && !Number.isInteger(n)) { errores[c.name] = 'Debe ser un número entero'; continue }
      if (c.gt !== undefined && n <= c.gt) { errores[c.name] = `Debe ser mayor que ${c.gt}`; continue }
      if (c.min !== undefined && n < c.min) { errores[c.name] = `Debe ser mayor o igual que ${c.min}`; continue }
      if (c.max !== undefined && n > c.max) { errores[c.name] = `Debe ser menor o igual que ${c.max}`; continue }
    }
    if (typeof v === 'string') {
      const t = v.trim()
      if (c.minLength && t.length < c.minLength) { errores[c.name] = `Mínimo ${c.minLength} caracteres`; continue }
      if (c.maxLength && t.length > c.maxLength) { errores[c.name] = `Máximo ${c.maxLength} caracteres`; continue }
      if (c.pattern && !new RegExp(c.pattern).test(t)) { errores[c.name] = c.patternMsg || 'Formato no válido'; continue }
    }
    if (c.validate) {
      const m = c.validate(v, valores, modo)
      if (m) errores[c.name] = m
    }
  }
  return errores
}

export function armarPayload(campos, valores, modo) {
  const salida = {}
  for (const c of campos) {
    if (!visible(c, valores, modo) || c.noEnviar) continue
    let v = valores[c.name]
    if (c.type === 'checkbox') v = Boolean(v)
    else if (c.type === 'multiselect') v = (v || []).map((x) => (c.numeric === false ? x : Number(x)))
    else if (c.type === 'file') v = v || null
    else if (vacio(v)) v = null
    else if (c.type === 'number' || c.numeric) v = Number(v)
    else if (c.type === 'datetime') v = new Date(v).toISOString()
    else if (typeof v === 'string') v = v.trim()
    salida[c.name] = v
  }
  return salida
}

// Carga opciones de un select desde la API (pueden depender de otros campos)
function useOpciones(campo, valores) {
  // opciones puede ser un objeto {ruta, valor, etiqueta, filtro} o una función de los valores del formulario
  const cfg = typeof campo.opciones === 'function' ? campo.opciones(valores) : campo.opciones
  const ruta = cfg ? (typeof cfg.ruta === 'function' ? cfg.ruta(valores) : cfg.ruta) : null
  const [filas, setFilas] = useState([])
  const [cargando, setCargando] = useState(false)
  useEffect(() => {
    let vivo = true
    if (!ruta) { setFilas([]); return }
    setCargando(true)
    api(ruta).then((r) => vivo && setFilas(r)).catch(() => vivo && setFilas([])).finally(() => vivo && setCargando(false))
    return () => { vivo = false }
  }, [ruta])
  return useMemo(() => {
    if (campo.options) return { lista: campo.options, cargando: false, sinRuta: false }
    if (!campo.opciones) return { lista: [], cargando: false, sinRuta: false }
    if (!cfg) return { lista: [], cargando: false, sinRuta: true }
    const { valor, etiqueta, filtro } = cfg
    const lista = filas.filter((f) => !filtro || filtro(f, valores))
      .map((f) => ({ value: f[valor], label: etiqueta(f), fila: f }))
    return { lista, cargando, sinRuta: !ruta }
  }, [campo, cfg, filas, cargando, ruta, valores])
}

export function Campo({ campo, valores, setValor, error, modo }) {
  const { lista, cargando, sinRuta } = useOpciones(campo, valores)
  const v = valores[campo.name]
  const requerido = typeof campo.required === 'function' ? campo.required(valores, modo) : campo.required
  const deshabilitado = typeof campo.disabled === 'function' ? campo.disabled(valores, modo) : campo.disabled
  const clase = `input ${error ? 'invalid' : ''}`
  const esFiltro = modo === 'filtro'
  const id = `${esFiltro ? 'flt' : 'f'}-${campo.name}`
  let control

  switch (campo.type) {
    case 'textarea':
      control = <textarea id={id} className={clase} value={v ?? ''} maxLength={campo.maxLength}
        placeholder={campo.placeholder} disabled={deshabilitado} onChange={(e) => setValor(campo.name, e.target.value)} />
      break
    case 'select':
      control = (
        <select id={id} className={clase} value={v ?? ''} disabled={deshabilitado || sinRuta} aria-label={campo.label}
          onChange={(e) => setValor(campo.name, e.target.value)}>
          <option value="">{sinRuta ? (campo.esperando || 'Complete el campo anterior') : cargando ? 'Cargando…' : (campo.placeholder || 'Seleccione…')}</option>
          {lista.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      )
      break
    case 'multiselect': {
      const sel = (v || []).map(String)
      const alternar = (val) => setValor(campo.name, sel.includes(String(val)) ? sel.filter((x) => x !== String(val)) : [...sel, String(val)])
      control = (
        <div className={`multi ${error ? 'invalid' : ''}`}>
          {sinRuta && <div className="empty">{campo.esperando || 'Complete el campo anterior'}</div>}
          {!sinRuta && cargando && <div className="empty">Cargando…</div>}
          {!sinRuta && !cargando && lista.length === 0 && <div className="empty">{campo.sinOpciones || 'No hay opciones disponibles'}</div>}
          {!sinRuta && lista.map((o) => (
            <label key={o.value}>
              <input type="checkbox" checked={sel.includes(String(o.value))} onChange={() => alternar(o.value)} />
              <span>{o.label}</span>
            </label>
          ))}
        </div>
      )
      break
    }
    case 'checkbox':
      control = (
        <label className="check">
          <input id={id} type="checkbox" checked={Boolean(v)} disabled={deshabilitado}
            onChange={(e) => setValor(campo.name, e.target.checked)} />
          {campo.checkLabel || campo.label}
        </label>
      )
      break
    case 'file':
      control = <input id={id} type="file" className={clase} accept={campo.accept}
        onChange={(e) => setValor(campo.name, e.target.files?.[0] || null)} />
      break
    default: {
      const tipo = { datetime: 'datetime-local', number: 'number', date: 'date', email: 'email', password: 'password' }[campo.type] || 'text'
      control = <input id={id} type={tipo} className={clase} value={v ?? ''} placeholder={campo.placeholder}
        step={campo.step} maxLength={campo.maxLength} disabled={deshabilitado} autoComplete="off"
        onChange={(e) => setValor(campo.name, e.target.value)} />
    }
  }

  return (
    <div className={`field ${campo.span ? 'span-2' : ''}`}>
      {campo.type !== 'checkbox' && !esFiltro && (
        <label htmlFor={id}>{campo.label}{requerido && <span className="req">*</span>}</label>
      )}
      {control}
      {error ? <span className="error">{error}</span> : campo.help && <span className="help">
        {typeof campo.help === 'function' ? campo.help(valores, lista) : campo.help}</span>}
    </div>
  )
}

export function FormModal({ titulo, campos, inicial = {}, modo = 'crear', onSubmit, onClose, onExito, textoBoton, aviso, size }) {
  const [valores, setValores] = useState(() => {
    const base = {}
    for (const c of campos) base[c.name] = c.default ?? (c.type === 'multiselect' ? [] : c.type === 'checkbox' ? false : '')
    return { ...base, ...inicial }
  })
  const [errores, setErrores] = useState({})
  const [errorGeneral, setErrorGeneral] = useState(null)
  const [enviando, setEnviando] = useState(false)

  const setValor = (nombre, valor) => {
    setValores((prev) => {
      const nuevo = { ...prev, [nombre]: valor }
      const campo = campos.find((c) => c.name === nombre)
      for (const dep of campo?.reinicia || []) {
        const c = campos.find((x) => x.name === dep)
        nuevo[dep] = c?.type === 'multiselect' ? [] : ''
      }
      return nuevo
    })
    setErrores((e) => ({ ...e, [nombre]: undefined }))
  }

  const enviar = async (e) => {
    e.preventDefault()
    const errs = validar(campos, valores, modo)
    setErrores(errs)
    if (Object.keys(errs).length) {
      setErrorGeneral('Corrija los campos marcados en rojo.')
      return
    }
    setEnviando(true)
    setErrorGeneral(null)
    try {
      const r = await onSubmit(armarPayload(campos, valores, modo), valores)
      onExito?.(r)
      onClose()
    } catch (err) {
      // Errores del backend: se marcan en el campo correspondiente cuando es posible
      const porCampo = {}
      for (const x of err.errores || []) {
        const nombre = String(x.campo).split('.')[0]
        if (campos.some((c) => c.name === nombre)) porCampo[nombre] = x.mensaje
      }
      setErrores(porCampo)
      setErrorGeneral(err.message)
      setEnviando(false)
    }
  }

  return (
    <Modal titulo={titulo} onClose={onClose} size={size} footer={<>
      <button className="btn" type="button" onClick={onClose}>Cancelar</button>
      <button className="btn primary" type="submit" form="form-modal" disabled={enviando}>
        {enviando ? 'Guardando…' : (textoBoton || (modo === 'crear' ? 'Registrar' : 'Guardar cambios'))}
      </button>
    </>}>
      {aviso && <div className="alert info"><Info />{aviso}</div>}
      {errorGeneral && <div className="alert error"><AlertTriangle /><span>{errorGeneral}</span></div>}
      <form id="form-modal" className="form-grid" onSubmit={enviar} noValidate>
        {campos.filter((c) => visible(c, valores, modo)).map((c) => (
          <Campo key={c.name} campo={c} valores={valores} setValor={setValor} error={errores[c.name]} modo={modo} />
        ))}
      </form>
    </Modal>
  )
}
