import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { alExpirarSesion, api, guardarToken, hayToken } from './api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null)
  const [listo, setListo] = useState(false)

  const salir = useCallback(() => {
    guardarToken(null)
    setUsuario(null)
  }, [])

  useEffect(() => {
    alExpirarSesion(salir)
    if (!hayToken()) { setListo(true); return }
    api('/auth/me')
      .then(setUsuario)
      .catch(() => guardarToken(null))
      .finally(() => setListo(true))
  }, [salir])

  const entrar = async (email, password) => {
    const r = await api('/auth/login', { method: 'POST', body: { email, password } })
    guardarToken(r.access_token)
    setUsuario(r.usuario)
  }

  // El ADMIN puede todo; los demás según su rol
  const puede = useCallback((...roles) => {
    if (!usuario) return false
    return usuario.rol_codigo === 'ADMIN' || roles.includes(usuario.rol_codigo)
  }, [usuario])

  const esAdmin = usuario?.rol_codigo === 'ADMIN'

  return (
    <AuthContext.Provider value={{ usuario, listo, entrar, salir, puede, esAdmin }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
