// Menú lateral: cada pantalla con su icono y el color de su icono 3D
import {
  ArrowLeftRight, Boxes, Building2, ClipboardCheck, FileCheck2, Flag, Gauge, History, Network,
  Package, Route as RutaIcono, ScanSearch, Shapes, Smartphone, Tags, Truck, Users, Warehouse,
} from 'lucide-react'

export const MENU = [
  { grupo: 'General', items: [
    { to: '/', icono: Gauge, texto: 'Tablero', fin: true, color: 'verde' },
    { to: '/trazabilidad', icono: ScanSearch, texto: 'Trazabilidad', color: 'teal' },
  ] },
  { grupo: 'Procesos RAEE', items: [
    { to: '/lotes', icono: Package, texto: 'Lotes', color: 'ambar' },
    { to: '/dispositivos', icono: Smartphone, texto: 'Dispositivos', color: 'azul' },
    { to: '/recoleccion', icono: Truck, texto: 'Recolección y recepción', color: 'teal' },
    { to: '/evaluaciones', icono: ClipboardCheck, texto: 'Evaluación técnica', color: 'violeta' },
    { to: '/transferencias', icono: ArrowLeftRight, texto: 'Transferencias', color: 'verde' },
    { to: '/destinos', icono: Flag, texto: 'Destino final', color: 'lima' },
    { to: '/evidencias', icono: FileCheck2, texto: 'Evidencias', color: 'azul' },
  ] },
  { grupo: 'Análisis', items: [
    { to: '/red', icono: Network, texto: 'Red y flujo máximo', color: 'violeta' },
    { to: '/inventario', icono: Warehouse, texto: 'Inventario', color: 'ambar' },
    { to: '/auditoria', icono: History, texto: 'Auditoría', admin: true, color: 'azul' },
  ] },
  { grupo: 'Administración', admin: true, items: [
    { to: '/admin/organizaciones', icono: Building2, texto: 'Organizaciones', color: 'teal' },
    { to: '/admin/centros', icono: Boxes, texto: 'Centros', color: 'verde' },
    { to: '/admin/tipos-centro', icono: RutaIcono, texto: 'Tipos de centro', color: 'lima' },
    { to: '/admin/usuarios', icono: Users, texto: 'Usuarios', color: 'violeta' },
    { to: '/admin/categorias', icono: Shapes, texto: 'Categorías', color: 'ambar' },
    { to: '/admin/marcas', icono: Tags, texto: 'Marcas', color: 'azul' },
  ] },
]

export const ITEMS = MENU.flatMap((g) => g.items)

// El ítem del menú que corresponde a una ruta (para el icono del encabezado)
export function itemDeRuta(ruta) {
  if (ruta === '/') return ITEMS[0]
  return ITEMS.filter((i) => i.to !== '/' && ruta.startsWith(i.to)).sort((a, b) => b.to.length - a.to.length)[0]
}
