# EcoRAEE Cloud · Parte II (local) y Parte III (AWS)

**EcoRAEE Cloud** es la plataforma para gestionar y rastrear Residuos de Aparatos Eléctricos y Electrónicos (RAEE) en la red universitaria. Tiene frontend, backend y base de datos integrados. El mismo código **se ejecuta en local con Docker** (secciones 1 a 8) y **se despliega en Amazon Web Services** (sección 9): frontend en S3, API en EC2, base en RDS, evidencias en S3, notificaciones con SNS y permisos con IAM.

| Capa | Tecnología | Carpeta |
|---|---|---|
| Frontend | React 18 + Vite | `frontend/` |
| Backend (API REST) | Python · FastAPI · SQLAlchemy 2 · Pydantic | `backend/` |
| Base de datos | PostgreSQL 16 (el mismo motor que se usará en Amazon RDS) | `database/` |

Proyecto Integrador · Ingeniería en Sistemas de Información · UIDE. Integrantes: Cristopher Grados y Cristian Curipallo.

---

## 1. Opción A: con Docker (recomendada)

Requisito: tener instalado **Docker Desktop** y abierto.

```powershell
cd ecoraee-cloud
docker compose up --build
```

La primera vez tarda unos minutos porque descarga las imágenes y crea la base con los scripts de `database/`. Cuando termine, abre:

| Servicio | URL |
|---|---|
| Aplicación (frontend) | http://localhost:5173 |
| API y documentación interactiva (Swagger) | http://localhost:8000/docs |
| Estado de la API y de la base | http://localhost:8000/api/salud |
| Adminer, para ver las tablas | http://localhost:8081 (Sistema: PostgreSQL · Servidor: `db` · Usuario: `ecoraee` · Contraseña: `ecoraee_local` · Base: `ecoraee`) |

Comandos útiles:

```powershell
docker compose ps                                   # ver que los 4 contenedores estén arriba
docker compose logs -f api                          # ver las peticiones que llegan al backend
docker compose exec api python -m scripts.init_db   # reiniciar la base con los datos de prueba
docker compose down                                 # apagar (los datos se conservan)
docker compose down -v                              # apagar y BORRAR la base (se recrea al volver a subir)
```

> PostgreSQL queda expuesto en tu PC en el puerto **5433**, para no chocar con un PostgreSQL que ya tengas instalado. Desde pgAdmin conéctate a `localhost:5433`.

## 2. Opción B: instalación manual en Windows

Requisitos: **PostgreSQL 16**, **Python 3.12 o 3.13** y **Node.js 20 o superior**.

### 2.1 Base de datos

Abre **SQL Shell (psql)** o la Query Tool de pgAdmin como usuario `postgres` y ejecuta:

```sql
CREATE USER ecoraee WITH PASSWORD 'ecoraee_local';
CREATE DATABASE ecoraee OWNER ecoraee;
```

Luego crea las tablas y carga los datos. Puedes hacerlo con psql:

```powershell
psql -U ecoraee -d ecoraee -f database/01_modelo_fisico_ddl.sql
psql -U ecoraee -d ecoraee -f database/02_datos_sinteticos.sql
```

O, si psql no está en el PATH, usa el script de Python después de instalar el backend (paso 2.2):

```powershell
cd backend
python -m scripts.init_db
```

### 2.2 Backend (terminal 1)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Si tu PostgreSQL usa otro usuario, contraseña o puerto, copia `backend/.env.example` como `backend/.env` y ajusta `DATABASE_URL`.

### 2.3 Frontend (terminal 2)

```powershell
cd frontend
npm install
npm run dev
```

Abre http://localhost:5173. En desarrollo, Vite reenvía las llamadas `/api` al backend del puerto 8000.

---

## 3. Usuarios de prueba

Todos usan la contraseña **`Demo2026!`**. En la pantalla de inicio de sesión hay botones para rellenarlos con un clic.

| Rol | Correo | Qué puede hacer |
|---|---|---|
| Administrador | admin@ecoraee.ec | Todo, incluidos catálogos, usuarios y auditoría |
| Generador | generador@ecoraee.ec | Registrar lotes y dispositivos, y solicitar la recolección |
| Operador de centro | operador@ecoraee.ec | Recibir lotes y transferencias |
| Técnico evaluador | tecnico@ecoraee.ec | Hacer evaluaciones técnicas |
| Coordinador logístico | coordinador@ecoraee.ec | Transferencias, destino final y red/flujo máximo |
| Técnico **inactivo** | jlema@ecoraee.ec | No puede iniciar sesión (sirve para probar la regla RN-02) |

## 4. Módulos y procesos de trazabilidad

```
Lote ─► Dispositivos ─► Solicitud de recolección ─► Recepción en el centro ─► Evaluación técnica
                                                                               │
          Destino final (CERRADO) ◄── Transferencias entre centros ◄───────────┘
```

| Módulo | Operaciones |
|---|---|
| Lotes y dispositivos | CRUD completo. Los códigos `LOT-AAAA-NNNN` y `RAEE-AAAA-NNNNN` los genera la base (RN-01) |
| Recolección y recepción | Solicitar, programar o cancelar; registrar la recepción (relación 1:1) |
| Evaluación técnica | CRUD. Solo un técnico evaluador activo puede evaluar (RN-02) |
| Transferencias | Programar, editar, despachar, recibir o cancelar; ruta por arista con capacidad (RN-03, RN-05, RN-06) |
| Destino final | Cierre definitivo de la trazabilidad (RN-04, RN-08) |
| Evidencias | Subida de archivos con hash SHA-256 a Amazon S3 (o a una carpeta local con Docker) y vista previa con URL prefirmada (RN-07) |
| Red y flujo máximo | Grafo dirigido, algoritmo de Edmonds-Karp, corte mínimo |
| Trazabilidad | Línea de tiempo completa de un equipo a partir de su código |
| Inventario y auditoría | Generados por triggers; solo se consultan |
| Administración | CRUD de organizaciones, centros, tipos de centro, usuarios, categorías y marcas |

## 5. Base de datos

- `database/01_modelo_fisico_ddl.sql`: esquema `ecoraee` con **25 tablas** (24 del modelo y `correlativo`, que numera los códigos), PK, FK, UNIQUE y CHECK, 26 índices de consulta (más 4 índices únicos), 24 triggers (15 de reglas de negocio y 9 de auditoría), 2 procedimientos almacenados y 3 vistas.
- `database/02_datos_sinteticos.sql`: datos ficticios (7 organizaciones, 11 usuarios, 5 centros, 4 lotes, 17 dispositivos y una red de 6 nodos y 10 aristas). Los procesos se cargan en orden para que los triggers generen solos el historial, el inventario y la auditoría.

Cambios respecto al primer avance, según las observaciones de la docente:

- `historial_estado` quedó como **entidad débil**: su PK es `(id_dispositivo, nro_cambio)`, donde `nro_cambio` es la clave parcial.
- `codigo_unico`, `codigo_lote` y `email` se declaran como **claves secundarias** (UNIQUE). El correo es único sin importar mayúsculas.
- `id_marca` e `id_centro_actual` son **FK opcionales** (admiten NULL).

Cambios de la Parte III en los códigos `RAEE-AAAA-NNNNN` y `LOT-AAAA-NNNN`:

- El año sale de `fecha_registro` (hora de Ecuador) y no del momento del INSERT; el correlativo vuelve a 1 cada año.
- Se reemplazaron las secuencias por la tabla `correlativo`: un registro rechazado ya no deja huecos y el número no se trunca después de 99 999 (`lpad` cortaba el texto y el código chocaba con uno anterior).
- Un mismo equipo físico (marca + número de serie) no puede estar activo dos veces (`uq_dispositivo_serie`).
- La interfaz muestra el código único del equipo, no su id interno (por ejemplo, en "Respalda a" de las evidencias).

Reglas de negocio implementadas en la base:

| Regla | Implementación |
|---|---|
| RN-01 Código único e historial | UNIQUE + secuencias + `trg_historial_estado` |
| RN-02 Solo técnicos evalúan | `trg_valida_evaluacion` (rol TECNICO_EVALUADOR y usuario activo) |
| RN-03 Cierre con responsable | `CHECK ck_transferencia_cierre` + `sp_recibir_transferencia` |
| RN-04 No recuperable no se dona | `trg_valida_destino` |
| RN-05 Capacidad de la arista | `trg_valida_capacidad_arista` |
| RN-06 Inventario atómico | `trg_inventario_dispositivo` + procedimientos almacenados en una sola transacción |
| RN-07 Evidencia de un solo hecho | `CHECK num_nonnulls(...) = 1` |
| RN-08 Cierre único y definitivo | `UNIQUE(id_dispositivo)` + `trg_cierra_dispositivo` |

## 6. Backend

- API REST con prefijo `/api`, documentada en `/docs`.
- Validación de datos con Pydantic. Los mensajes de error están en español e indican el campo.
- Manejo de errores centralizado (`app/errors.py`). Las violaciones de restricciones y triggers se traducen a respuestas 409/422 con un mensaje claro.
- Autenticación con JWT y control de acceso por rol. Las contraseñas se guardan con bcrypt (pgcrypto).
- Cada transacción informa a PostgreSQL qué usuario opera (`set_config`), para que la auditoría y el historial registren quién hizo cada cambio.

## 7. Pruebas automáticas

```powershell
# Con Docker (con los contenedores encendidos)
docker compose exec api python -m pytest -v

# Instalación manual (con el entorno virtual activado)
cd backend
python -m pytest -v
```

Son 22 pruebas: 17 de integración contra la base real (el ciclo completo de trazabilidad, las validaciones, los permisos por rol, las reglas RN-01, RN-02, RN-04, RN-05, RN-07 y RN-08, y el flujo máximo de 59 unidades) y 5 de la integración con AWS (`tests/test_aws.py`), que usan moto para simular S3 y SNS sin necesidad de cuenta (incluida una que comprueba que los errores de AWS llegan al navegador con CORS y un mensaje claro).

> ⚠️ Las pruebas **reinician la base** con los datos sintéticos. No las ejecutes justo después de preparar datos para el video.

## 8. Estructura

```
ecoraee-cloud/
├── docker-compose.yml
├── database/            01_modelo_fisico_ddl.sql · 02_datos_sinteticos.sql
├── deploy/              scripts y políticas para AWS (sección 9)
├── backend/
│   ├── app/             main.py · models.py · schemas.py · security.py · errors.py · crud.py
│   │   ├── routers/     auth · catalogos · operacion · transferencias · evidencias · red · reportes
│   │   └── services/    flujo_maximo.py (Edmonds-Karp) · almacenamiento.py (S3) · notificaciones.py (SNS)
│   ├── scripts/         init_db.py
│   ├── tests/           test_integracion.py
│   └── storage/         evidencias (simulación local de S3)
└── frontend/
    └── src/             App.jsx · api.js · auth.jsx · ui/ · pages/
```

## 9. Despliegue en AWS (Parte III)

La guía paso a paso (consola de AWS) está en [`docs/Guia_despliegue_AWS_Parte_III.pdf`](docs/Guia_despliegue_AWS_Parte_III.pdf) y el diagrama corregido en Lucid (**Arquitectura y organización AWS v2**). Resumen:

| Componente | Servicio | Archivos |
|---|---|---|
| Frontend React | Bucket S3 con sitio web estático; la URL de la API va en `config.js` | `deploy/frontend/desplegar_frontend.sh`, `deploy/s3/politica_bucket_frontend.json` |
| Evidencias | Bucket S3 privado (cifrado, versionado, solo HTTPS); vista con URL prefirmada | `backend/app/services/almacenamiento.py`, `deploy/s3/politica_bucket_evidencias.json` |
| Backend | EC2 t3.micro (Amazon Linux 2023) con Docker; configuración en SSM Parameter Store | `deploy/ec2/user_data.sh`, `deploy/ec2/iniciar_api.sh` |
| Base de datos | RDS PostgreSQL 16 Single-AZ, sin acceso público, SSL verify-full, usuario `ecoraee_app` | `deploy/rds/migrar_a_rds.sh`, `deploy/rds/usuario_app.sql` |
| Notificaciones | SNS `ecoraee-eventos`: lote recibido, transferencia en tránsito y recibida, destino final | `backend/app/services/notificaciones.py` |
| Permisos | 4 grupos, políticas AWS y propias, rol `EcoRAEE-EC2-AppRole` (sin access keys) | `deploy/iam/*.json` |
| HTTPS (paso 9) | CloudFront: `/` va al bucket del frontend y `/api/*` a la EC2, en el mismo dominio `https://<id>.cloudfront.net` | `deploy/frontend/desplegar_frontend.sh <bucket> cloudfront` |
| Monitoreo (paso 10) | 3 alarmas de CloudWatch (estado de la EC2, CPU y disco de RDS) que avisan por el tópico SNS | Guía, paso 10 |
| Validación | Recorre la arquitectura completa y marca cada punto con OK o FALLA (también en modo CloudFront) | `deploy/verificar_despliegue.py` |

En `config.js`, `cuentasDemo: false` oculta los botones de cuentas de prueba del login; úsenlo cuando el sitio quede público después de grabar.

Variables que lee la API en AWS (parámetros `/ecoraee/*`): `DATABASE_URL`, `JWT_SECRET`, `CORS_ORIGINS`, `S3_BUCKET_EVIDENCIAS` y `SNS_TOPIC_ARN`. Sin `S3_BUCKET_EVIDENCIAS` las evidencias vuelven a la carpeta local, así que `docker compose up` sigue funcionando igual que en la Parte II.

> Al terminar las pruebas, apague o elimine la instancia EC2 y la base RDS para no consumir créditos (lista completa en la guía).
