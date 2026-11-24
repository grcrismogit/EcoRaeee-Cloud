import { Download, ShieldCheck } from 'lucide-react'
import { api, descargarArchivo } from '../api'
import { TIPOS_EVIDENCIA } from '../catalogo'
import { fecha } from '../ui/feedback'
import Miniatura from '../ui/Miniatura'
import Recurso from '../ui/Recurso'

const VINCULOS = [
  { value: 'dispositivo', label: 'Dispositivo' },
  { value: 'evaluacion', label: 'Evaluación técnica' },
  { value: 'transferencia', label: 'Transferencia' },
  { value: 'destino_final', label: 'Destino final' },
]

const OPCIONES_VINCULO = {
  dispositivo: { ruta: '/dispositivos', valor: 'id_dispositivo', etiqueta: (d) => `${d.codigo_unico} · ${d.categoria_nombre} ${d.modelo || ''}` },
  evaluacion: { ruta: '/evaluaciones', valor: 'id_evaluacion', etiqueta: (e) => `#${e.id_evaluacion} · ${e.codigo_unico} · ${e.clasificacion}` },
  transferencia: { ruta: '/transferencias', valor: 'id_transferencia', etiqueta: (t) => `#${t.id_transferencia} · ${t.centro_origen_nombre} → ${t.centro_destino_nombre}` },
  destino_final: { ruta: '/destinos', valor: 'id_destino_final', etiqueta: (d) => `#${d.id_destino_final} · ${d.codigo_unico} · ${d.tipo_destino}` },
}

export default function Evidencias() {
  return (
    <Recurso
      titulo="Evidencias" nombre="evidencia" femenino textoCrear="Subir evidencia" endpoint="/evidencias" idKey="id_evidencia"
      descripcion="Fotos, actas, informes y certificados. Los archivos se guardan cifrados en un bucket privado de Amazon S3; la base registra la clave y el hash SHA-256. Las vistas previas usan enlaces temporales."
      rolesEscritura={['GENERADOR', 'OPERADOR_CENTRO', 'TECNICO_EVALUADOR', 'COORDINADOR_LOGISTICO']}
      permitirEditar={false} buscar={false}
      filtros={[{ name: 'tipo_evidencia', label: 'Todos los tipos', options: TIPOS_EVIDENCIA }]}
      avisoCrear="RN-07: cada evidencia respalda exactamente un hecho. Formatos: PDF, JPG, PNG o TXT (máx. 10 MB)."
      columnas={[
        { key: 'vista', label: 'Vista', render: (e) => <Miniatura ev={e} /> },
        { key: 'fecha_carga', label: 'Fecha', render: (e) => <span className="small">{fecha(e.fecha_carga)}</span> },
        { key: 'tipo_evidencia', label: 'Tipo', render: (e) => <span className="tag">{e.tipo_evidencia}</span> },
        { key: 'nombre_archivo', label: 'Archivo', render: (e) => <div className="stack"><span>{e.nombre_archivo}</span><span className="small muted mono">{e.s3_key}</span></div> },
        { key: 'vinculo', label: 'Respalda a' },
        { key: 'usuario_carga_nombre', label: 'Cargó' },
        { key: 'hash_sha256', label: 'SHA-256', render: (e) => <span className="mono small" title={e.hash_sha256}>{e.hash_sha256.slice(0, 12)}…</span> },
      ]}
      campos={[
        { name: 'tipo_evidencia', label: 'Tipo de evidencia', type: 'select', required: true, options: TIPOS_EVIDENCIA },
        { name: 'vinculo', label: 'Respalda a', type: 'select', required: true, options: VINCULOS, reinicia: ['id_vinculo'] },
        { name: 'id_vinculo', label: 'Registro', type: 'select', numeric: true, required: true, span: true,
          esperando: 'Elija primero qué respalda', opciones: (v) => OPCIONES_VINCULO[v.vinculo] || null },
        { name: 'archivo', label: 'Archivo', type: 'file', required: true, span: true, accept: '.pdf,.jpg,.jpeg,.png,.txt',
          validate: (f) => {
            if (!f) return null
            if (!/\.(pdf|jpe?g|png|txt)$/i.test(f.name)) return 'Formato no permitido'
            if (f.size > 10 * 1024 * 1024) return 'El archivo supera 10 MB'
            return null
          } },
      ]}
      enviarCrear={(p) => {
        const form = new FormData()
        form.append('tipo_evidencia', p.tipo_evidencia)
        form.append('vinculo', p.vinculo)
        form.append('id_vinculo', p.id_vinculo)
        form.append('archivo', p.archivo)
        return api('/evidencias', { method: 'POST', form })
      }}
      accionesFila={(e, { notificar }) => [
        { icon: <ShieldCheck />, title: 'Verificar integridad (SHA-256)', onClick: async () => {
          try {
            const r = await api(`/evidencias/${e.id_evidencia}/verificar`)
            notificar(r.mensaje, r.integra ? 'ok' : 'error', r.integra ? 'Integridad verificada' : 'Integridad comprometida')
          } catch (err) { notificar(err.message, 'error') }
        } },
        { icon: <Download />, title: 'Descargar', onClick: () => descargarArchivo(`/evidencias/${e.id_evidencia}/archivo`, e.nombre_archivo).catch((err) => notificar(err.message, 'error')) },
      ]}
    />
  )
}
