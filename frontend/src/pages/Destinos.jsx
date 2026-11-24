import { Link } from 'react-router-dom'
import { useAuth } from '../auth'
import { OP, TIPOS_DESTINO, describirDispositivo } from '../catalogo'
import { Badge, fecha } from '../ui/feedback'
import Recurso from '../ui/Recurso'

export default function Destinos() {
  const { esAdmin } = useAuth()
  return (
    <Recurso
      titulo="Destino final" nombre="destino final" textoCrear="Registrar destino final" endpoint="/destinos" idKey="id_destino_final"
      descripcion="Cierre de la trazabilidad: reutilización, reacondicionamiento, reciclaje, disposición o donación. Es definitivo (RN-08) y lo no recuperable no se dona (RN-04)."
      rolesEscritura={['COORDINADOR_LOGISTICO', 'OPERADOR_CENTRO']}
      permitirEditar={false} permitirEliminar={false} buscar={false}
      filtros={[{ name: 'tipo_destino', label: 'Todos los destinos', options: TIPOS_DESTINO }]}
      avisoCrear="Al confirmar, el dispositivo pasa a CERRADO y ya no admite cambios. El cierre se registra en el centro donde está el equipo."
      columnas={[
        { key: 'fecha_confirmacion', label: 'Fecha', render: (d) => <span className="small">{fecha(d.fecha_confirmacion)}</span> },
        { key: 'codigo_unico', label: 'Dispositivo', render: (d) => <Link className="mono" to={`/trazabilidad/${d.codigo_unico}`}>{d.codigo_unico}</Link> },
        { key: 'clasificacion', label: 'Clasificación', render: (d) => <Badge valor={d.clasificacion} /> },
        { key: 'tipo_destino', label: 'Destino', render: (d) => <Badge valor={d.tipo_destino} /> },
        { key: 'centro_nombre', label: 'Centro' },
        { key: 'org_beneficiaria_nombre', label: 'Beneficiaria', render: (d) => d.org_beneficiaria_nombre || '—' },
        { key: 'usuario_confirma_nombre', label: 'Confirmó' },
      ]}
      campos={[
        { name: 'id_dispositivo', label: 'Dispositivo evaluado', type: 'select', numeric: true, required: true, span: true,
          opciones: { ruta: '/dispositivos?estado=RECIBIDO,EVALUADO,TRANSFERIDO', valor: 'id_dispositivo', filtro: (d) => Boolean(d.clasificacion),
            etiqueta: (d) => `${describirDispositivo(d)} — ${d.clasificacion} — ${d.centro_actual_nombre}` },
          help: 'Solo equipos con evaluación técnica que estén en un centro.' },
        { name: 'tipo_destino', label: 'Tipo de destino', type: 'select', required: true, options: TIPOS_DESTINO, reinicia: ['id_org_beneficiaria'] },
        { name: 'id_org_beneficiaria', label: 'Organización beneficiaria', type: 'select', numeric: true, required: true,
          show: (v) => v.tipo_destino === 'DONACION', opciones: OP.beneficiarias },
        { name: 'id_usuario_confirma', label: 'Usuario que confirma', type: 'select', numeric: true, required: true, span: true,
          show: () => esAdmin, opciones: OP.usuarios('COORDINADOR_LOGISTICO') },
      ]}
    />
  )
}
