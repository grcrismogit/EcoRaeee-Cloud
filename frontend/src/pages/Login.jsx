import { Suspense, lazy, useState } from 'react'
import { AlertTriangle, LogIn } from 'lucide-react'
import { useAuth } from '../auth'

// El planeta 3D se carga aparte para que el inicio de sesión abra rápido
const Planeta = lazy(() => import('../three/Planeta'))

// Botones de cuentas de prueba: se ocultan con cuentasDemo: false en config.js (sitio público)
const MOSTRAR_CUENTAS = window.ECORAEE_CONFIG?.cuentasDemo !== false
const CUENTAS = [
  ['Administrador', 'admin@ecoraee.ec'],
  ['Generador', 'generador@ecoraee.ec'],
  ['Operador', 'operador@ecoraee.ec'],
  ['Técnico', 'tecnico@ecoraee.ec'],
  ['Coordinador', 'coordinador@ecoraee.ec'],
]


export default function Login() {
  const { entrar } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errores, setErrores] = useState({})
  const [error, setError] = useState(null)
  const [enviando, setEnviando] = useState(false)

  const enviar = async (e) => {
    e.preventDefault()
    const errs = {}
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim())) errs.email = 'Escribe un correo válido, por ejemplo nombre@ecoraee.ec'
    if (!password) errs.password = 'Escribe tu contraseña'
    setErrores(errs)
    if (Object.keys(errs).length) return
    setEnviando(true)
    setError(null)
    try {
      await entrar(email.trim(), password)
    } catch (err) {
      setError(err.message)
      setEnviando(false)
    }
  }

  return (
    <div className="login-page">
      <section className="login-hero">
        <div className="planeta">
          <Suspense fallback={<div className="planeta-respaldo" />}><Planeta /></Suspense>
        </div>
        <h1>Sigue cada equipo hasta su destino final.</h1>
        <p>EcoRAEE Cloud registra de dónde viene cada aparato electrónico de la red universitaria,
          quién lo evaluó, por dónde pasó y dónde terminó.</p>
        <p className="pie-login">Proyecto Integrador de Ingeniería en Sistemas de Información, UIDE.</p>
      </section>
      <section className="login-box">
        <form className="card" onSubmit={enviar} noValidate>
          <h2>Iniciar sesión</h2>
          <p className="muted" style={{ marginTop: 0 }}>Usa tu cuenta de la red EcoRAEE.</p>
          {error && <div className="alert error"><AlertTriangle />{error}</div>}
          <div className="field" style={{ marginBottom: 12 }}>
            <label htmlFor="email">Correo electrónico</label>
            <input id="email" className={`input ${errores.email ? 'invalid' : ''}`} value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" />
            {errores.email && <span className="error">{errores.email}</span>}
          </div>
          <div className="field" style={{ marginBottom: 16 }}>
            <label htmlFor="password">Contraseña</label>
            <input id="password" type="password" className={`input ${errores.password ? 'invalid' : ''}`} value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
            {errores.password && <span className="error">{errores.password}</span>}
          </div>
          <button className="btn primary" style={{ width: '100%', justifyContent: 'center' }} disabled={enviando}>
            <LogIn /> {enviando ? 'Verificando…' : 'Entrar'}
          </button>
          {MOSTRAR_CUENTAS && <div style={{ marginTop: 22 }}>
            <span className="small muted">Cuentas de prueba (contraseña <code>Demo2026!</code>):</span>
            <div className="demo-accounts">
              {CUENTAS.map(([rol, correo]) => (
                <button type="button" key={correo} className="btn sm" onClick={() => { setEmail(correo); setPassword('Demo2026!') }}>{rol}</button>
              ))}
            </div>
          </div>}
        </form>
      </section>
    </div>
  )
}
