import { useEffect, useState } from 'react'
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { LogOut, Search, ShieldCheck } from 'lucide-react'
import { api } from './api'
import { useAuth } from './auth'
import { MENU } from './menu'
import { etiqueta } from './ui/feedback'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Trazabilidad from './pages/Trazabilidad'
import { Dispositivos, Lotes } from './pages/LotesDispositivos'
import Recoleccion from './pages/Recoleccion'
import Evaluaciones from './pages/Evaluaciones'
import Transferencias from './pages/Transferencias'
import Destinos from './pages/Destinos'
import Evidencias from './pages/Evidencias'
import Red from './pages/Red'
import { Auditoria, Inventario } from './pages/Reportes'
import { Categorias, Centros, Marcas, Organizaciones, TiposCentro, Usuarios } from './pages/Admin'


function EstadoSistema() {
  const [salud, setSalud] = useState(null)
  useEffect(() => {
    const consultar = () => api('/salud').then(setSalud).catch(() => setSalud(false))
    consultar()
    const t = setInterval(consultar, 20000)
    return () => clearInterval(t)
  }, [])
  const punto = salud ? 'ok' : salud === false ? 'down' : ''
  return (
    <div className="sidebar-footer" title={salud ? salud.postgres : ''}>
      <div><span className={`status-dot ${punto}`} />API FastAPI {salud ? 'en línea' : salud === false ? 'sin conexión' : '…'}</div>
      <div style={{ marginTop: 4 }}><span className={`status-dot ${punto}`} />{salud ? `${salud.motor} · ${salud.tablas} tablas${salud.ssl ? ' · SSL' : ''}` : 'PostgreSQL'}</div>
      {salud && <div style={{ marginTop: 4 }}><span className="status-dot ok" />Evidencias en {salud.almacenamiento.startsWith('s3://') ? 'Amazon S3' : 'carpeta local'}</div>}
      <div style={{ marginTop: 8, color: '#6f9c87' }}>
        {salud?.region ? `AWS ${salud.region}${salud.notificaciones_sns ? ' · avisos SNS' : ''}` : 'Ejecución local'}
      </div>
    </div>
  )
}

function Layout({ children }) {
  const { usuario, salir, esAdmin } = useAuth()
  const navegar = useNavigate()
  const ubicacion = useLocation()
  const [codigo, setCodigo] = useState('')
  const iniciales = `${usuario.nombres[0]}${usuario.apellidos[0]}`
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <img src="/logo.svg" alt="" />
          <div><b>EcoRAEE Cloud</b><small>Trazabilidad de RAEE</small></div>
        </div>
        {MENU.filter((g) => !g.admin || esAdmin).map((g) => (
          <nav className="nav-group" key={g.grupo}>
            <span>{g.grupo}</span>
            {g.items.filter((i) => !i.admin || esAdmin).map(({ to, icono: Icono, texto, fin }) => (
              <NavLink key={to} to={to} end={fin} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                <Icono /> {texto}
              </NavLink>
            ))}
          </nav>
        ))}
        <EstadoSistema />
      </aside>
      <div className="main">
        <header className="topbar">
          <form className="search" onSubmit={(e) => { e.preventDefault(); if (codigo.trim()) navegar(`/trazabilidad/${codigo.trim().toUpperCase()}`) }}>
            <Search />
            <input className="input" aria-label="Rastrear dispositivo por código" spellCheck={false} placeholder="Rastrear dispositivo por código (ej. RAEE-2026-00002)…" value={codigo} onChange={(e) => setCodigo(e.target.value)} />
          </form>
          <div className="user-chip">
            <div className="avatar">{iniciales}</div>
            <div className="who">
              <b>{usuario.nombres} {usuario.apellidos}</b>
              <small><ShieldCheck style={{ width: 12, height: 12, verticalAlign: -2 }} /> {etiqueta(usuario.rol_codigo)} · {usuario.organizacion_nombre}</small>
            </div>
            <button className="icon-btn" title="Cerrar sesión" aria-label="Cerrar sesión" onClick={salir}><LogOut /></button>
          </div>
        </header>
        <main className="content">
          {/* key = ruta: cada cambio de pantalla vuelve a ejecutar la animación de entrada */}
          <div className="pagina" key={ubicacion.pathname}>{children}</div>
        </main>
      </div>
    </div>
  )
}

export default function App() {
  const { usuario, listo, esAdmin } = useAuth()
  if (!listo) return null
  if (!usuario) return <Routes><Route path="*" element={<Login />} /></Routes>
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/trazabilidad" element={<Trazabilidad />} />
        <Route path="/trazabilidad/:codigo" element={<Trazabilidad />} />
        <Route path="/lotes" element={<Lotes />} />
        <Route path="/dispositivos" element={<Dispositivos />} />
        <Route path="/recoleccion" element={<Recoleccion />} />
        <Route path="/evaluaciones" element={<Evaluaciones />} />
        <Route path="/transferencias" element={<Transferencias />} />
        <Route path="/destinos" element={<Destinos />} />
        <Route path="/evidencias" element={<Evidencias />} />
        <Route path="/red" element={<Red />} />
        <Route path="/inventario" element={<Inventario />} />
        {esAdmin && <Route path="/auditoria" element={<Auditoria />} />}
        {esAdmin && <>
          <Route path="/admin/organizaciones" element={<Organizaciones />} />
          <Route path="/admin/centros" element={<Centros />} />
          <Route path="/admin/tipos-centro" element={<TiposCentro />} />
          <Route path="/admin/usuarios" element={<Usuarios />} />
          <Route path="/admin/categorias" element={<Categorias />} />
          <Route path="/admin/marcas" element={<Marcas />} />
        </>}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}
