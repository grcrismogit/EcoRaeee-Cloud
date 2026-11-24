// Iconos de la interfaz: un estilo único y el icono de cada categoría de equipo
import {
  BatteryCharging, Box, Keyboard, Laptop, Monitor, PcCase, Printer, Projector, Router, Smartphone, Tablet,
} from 'lucide-react'

// ---------- Icono en recuadro ----------
export function Icono3D({ icono: Icono, color = 'verde', tamano = 40, className = '' }) {
  return (
    <span className={`icono3d ${color} ${className}`} style={{ width: tamano, height: tamano }} aria-hidden="true">
      <Icono />
    </span>
  )
}

// Icono según la categoría del dispositivo
const POR_CATEGORIA = [
  [/laptop/i, Laptop, 'azul'], [/escritorio|computador/i, PcCase, 'violeta'], [/monitor/i, Monitor, 'teal'],
  [/impresora/i, Printer, 'ambar'], [/tel[eé]fono|m[oó]vil|celular/i, Smartphone, 'verde'], [/tablet/i, Tablet, 'lima'],
  [/perif/i, Keyboard, 'azul'], [/red/i, Router, 'teal'], [/ups|bater/i, BatteryCharging, 'ambar'], [/proyector/i, Projector, 'violeta'],
]
export function iconoCategoria(nombre = '') {
  const m = POR_CATEGORIA.find(([re]) => re.test(nombre))
  return m ? { icono: m[1], color: m[2] } : { icono: Box, color: 'verde' }
}
