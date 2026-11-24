import { createContext, useCallback, useContext, useState } from 'react'
import { AlertTriangle, CheckCircle2, X } from 'lucide-react'

// ---------- Notificaciones (toasts) ----------
const ToastContext = createContext(() => {})

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const notificar = useCallback((mensaje, tipo = 'ok', titulo) => {
    const id = Math.random().toString(36).slice(2)
    setToasts((t) => [...t, { id, mensaje, tipo, titulo }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), tipo === 'error' ? 7000 : 3800)
  }, [])
  return (
    <ToastContext.Provider value={notificar}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.tipo}`}>
            {t.tipo === 'error' ? <AlertTriangle /> : <CheckCircle2 />}
            <div>
              <b>{t.titulo || (t.tipo === 'error' ? 'No se pudo completar' : 'Listo')}</b>
              {t.mensaje}
            </div>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export const useToast = () => useContext(ToastContext)

// ---------- Ventana modal ----------
export function Modal({ titulo, onClose, children, footer, size = '' }) {
  return (
    <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`modal ${size}`} role="dialog" aria-modal="true" aria-label={titulo}>
        <div className="modal-header">
          <h3>{titulo}</h3>
          <button className="icon-btn" onClick={onClose} aria-label="Cerrar"><X /></button>
        </div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-footer">{footer}</div>}
      </div>
    </div>
  )
}

// ---------- Confirmación ----------
export function Confirmar({ titulo, mensaje, textoBoton = 'Confirmar', peligro = false, onConfirm, onClose }) {
  const [ocupado, setOcupado] = useState(false)
  const [error, setError] = useState(null)
  const aceptar = async () => {
    setOcupado(true)
    setError(null)
    try {
      await onConfirm()
      onClose()
    } catch (e) {
      setError(e.message)
      setOcupado(false)
    }
  }
  return (
    <Modal titulo={titulo} onClose={onClose} size="sm" footer={<>
      <button className="btn" onClick={onClose}>Cancelar</button>
      <button className={`btn ${peligro ? 'danger solid' : 'primary'}`} onClick={aceptar} disabled={ocupado}>
        {ocupado ? 'Procesando…' : textoBoton}
      </button>
    </>}>
      {error && <div className="alert error"><AlertTriangle />{error}</div>}
      <div>{mensaje}</div>
    </Modal>
  )
}

// ---------- Etiquetas de estado (texto + color, nunca solo color) ----------
const COLORES = {
  // estados del dispositivo
  REGISTRADO: '', RECIBIDO: 'info', EVALUADO: 'violet', EN_TRANSITO: 'warn', TRANSFERIDO: 'teal', CERRADO: 'dark',
  // clasificación
  REUTILIZABLE: 'ok', REPARABLE: 'info', RECICLABLE: 'warn', NO_RECUPERABLE: 'danger',
  // lotes, solicitudes y transferencias
  SOLICITADO: 'info', PENDIENTE: '', PROGRAMADA: 'info', ATENDIDA: 'ok', CANCELADA: 'danger', CERRADA: 'ok',
  // destinos
  DONACION: 'ok', REUTILIZACION: 'ok', REACONDICIONAMIENTO: 'teal', RECICLAJE: 'warn', DISPOSICION_FINAL: 'danger',
  // nodos
  FUENTE: 'ok', SUMIDERO: 'violet', INTERMEDIO: '',
  // auditoría
  I: 'ok', U: 'info', D: 'danger',
  ACTIVO: 'ok',
}

const ETIQUETAS = {
  EN_TRANSITO: 'En tránsito', NO_RECUPERABLE: 'No recuperable', DISPOSICION_FINAL: 'Disposición final', DONACION: 'Donación',
  REUTILIZACION: 'Reutilización', RECOLECCION: 'Recolección', CON_FALLAS: 'Con fallas', DANADO: 'Dañado',
  COORDINADOR_LOGISTICO: 'Coordinador logístico', TECNICO_EVALUADOR: 'Técnico evaluador', OPERADOR_CENTRO: 'Operador de centro',
  GESTOR_RECICLAJE: 'Gestor de reciclaje', SIN_EVALUAR: 'Sin evaluar', ADMIN: 'Administrador', I: 'Alta', U: 'Cambio', D: 'Baja',
}

// Los valores de la base (EN_TRANSITO) se muestran como texto normal (En tránsito)
export const etiqueta = (valor) => {
  if (!valor) return '—'
  if (ETIQUETAS[valor]) return ETIQUETAS[valor]
  const t = String(valor).replaceAll('_', ' ').toLowerCase()
  return t.charAt(0).toUpperCase() + t.slice(1)
}

export function Badge({ valor }) {
  if (!valor) return <span className="muted">—</span>
  return <span className={`badge ${COLORES[valor] ?? ''}`}>{etiqueta(valor)}</span>
}

export function Cargando({ texto = 'Cargando…' }) {
  return (
    <div className="skeleton" role="status" aria-label={texto}>
      {Array.from({ length: 6 }, (_, i) => <i key={i} />)}
    </div>
  )
}

export function ErrorCaja({ error }) {
  if (!error) return null
  return <div className="alert error"><AlertTriangle />{error.message || String(error)}</div>
}

export const fecha = (v, conHora = true) => {
  if (!v) return '—'
  const d = new Date(v.length === 10 ? v + 'T00:00:00' : v)
  return d.toLocaleString('es-EC', conHora
    ? { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }
    : { day: '2-digit', month: 'short', year: 'numeric' })
}

export const num = (v, dec = 2) => (v === null || v === undefined ? '—'
  : Number(v).toLocaleString('es-EC', { minimumFractionDigits: 0, maximumFractionDigits: dec }))
