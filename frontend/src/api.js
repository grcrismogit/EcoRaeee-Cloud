// Cliente HTTP del frontend: toda la comunicación con el backend (FastAPI) pasa por aquí.
import { useCallback, useEffect, useState } from 'react'

// URL de la API: la define public/config.js (en AWS apunta a la instancia EC2)
const BASE = (window.ECORAEE_CONFIG?.apiUrl || '').replace(/\/+$/, '') + '/api'
const CLAVE_TOKEN = 'ecoraee_token'

let token = null
try { token = localStorage.getItem(CLAVE_TOKEN) } catch { token = null }
let alExpirar = () => {}

export class ApiError extends Error {
  constructor(mensaje, estado, errores = []) {
    super(mensaje)
    this.estado = estado
    this.errores = errores
  }
}

export function guardarToken(nuevo) {
  token = nuevo
  try {
    if (nuevo) localStorage.setItem(CLAVE_TOKEN, nuevo)
    else localStorage.removeItem(CLAVE_TOKEN)
  } catch { /* almacenamiento no disponible */ }
}

export const hayToken = () => Boolean(token)
export const alExpirarSesion = (fn) => { alExpirar = fn }

export async function api(ruta, { method = 'GET', body, form, blob = false } = {}) {
  const headers = {}
  if (token) headers.Authorization = `Bearer ${token}`
  let carga
  if (form) carga = form
  else if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    carga = JSON.stringify(body)
  }
  let res
  try {
    res = await fetch(BASE + ruta, { method, headers, body: carga })
  } catch {
    throw new ApiError('No se pudo conectar con la API. Revise que el servidor esté encendido y que config.js tenga la URL correcta.', 0)
  }
  if (res.status === 204) return null
  const esJson = (res.headers.get('content-type') || '').includes('json')
  const datos = esJson ? await res.json() : (blob ? await res.blob() : await res.text())
  if (!res.ok) {
    if (res.status === 401 && ruta !== '/auth/login') alExpirar()
    const mensaje = (esJson && datos?.detail) || `Error ${res.status}`
    throw new ApiError(typeof mensaje === 'string' ? mensaje : 'Solicitud no válida', res.status, datos?.errores || [])
  }
  return datos
}

export function construirQuery(params = {}) {
  const q = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')
  return q.length ? '?' + new URLSearchParams(q).toString() : ''
}

// Hook para leer datos con recarga manual
export function useApi(ruta, deps = []) {
  const [datos, setDatos] = useState(null)
  const [cargando, setCargando] = useState(Boolean(ruta))
  const [error, setError] = useState(null)

  const recargar = useCallback(async () => {
    if (!ruta) return
    setCargando(true)
    try {
      setDatos(await api(ruta))
      setError(null)
    } catch (e) {
      setError(e)
    } finally {
      setCargando(false)
    }
  }, [ruta])

  useEffect(() => { recargar() }, [recargar, ...deps]) // eslint-disable-line react-hooks/exhaustive-deps
  return { datos, cargando, error, recargar, setDatos }
}

export async function descargarArchivo(ruta, nombre) {
  const archivo = await api(ruta, { blob: true })
  const url = URL.createObjectURL(archivo)
  const a = document.createElement('a')
  a.href = url
  a.download = nombre
  a.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
