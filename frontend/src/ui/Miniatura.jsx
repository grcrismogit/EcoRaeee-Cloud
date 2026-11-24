import { FileText } from 'lucide-react'

const IMAGEN = /\.(png|jpe?g)$/i

// Vista previa servida directamente desde Amazon S3 con una URL prefirmada que expira en minutos.
// Con la carpeta local (Docker) no hay URL y se muestra solo el ícono.
export default function Miniatura({ ev }) {
  if (!ev.url) return <span className="miniatura" aria-hidden="true"><FileText /></span>
  return (
    <a className="miniatura" href={ev.url} target="_blank" rel="noopener noreferrer"
       title="Abrir desde Amazon S3" aria-label={`Abrir ${ev.nombre_archivo} desde Amazon S3`}>
      {IMAGEN.test(ev.nombre_archivo) ? <img src={ev.url} alt="" width="44" height="44" loading="lazy" /> : <FileText />}
    </a>
  )
}
