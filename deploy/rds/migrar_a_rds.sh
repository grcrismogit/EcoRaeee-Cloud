#!/bin/bash
# =====================================================================
#  EcoRAEE Cloud · Migración de la base local a Amazon RDS for PostgreSQL
#
#  Se ejecuta en la instancia EC2 (RDS no es público: solo EC2 llega a él).
#
#  Uso:
#    export PGPASSWORD='<contraseña master de RDS>'
#    bash deploy/rds/migrar_a_rds.sh <endpoint-rds> [ecoraee_local.dump]
#
#  - Con un archivo .dump (pg_dump -Fc de la base local): restaura esos datos.
#  - Sin archivo: crea el modelo físico y carga los datos sintéticos del repo.
#  En ambos casos crea el usuario ecoraee_app (mínimo privilegio) y muestra
#  la DATABASE_URL que debe guardarse en SSM Parameter Store.
# =====================================================================
set -euo pipefail

ENDPOINT="${1:?Indique el endpoint de RDS, p. ej. ecoraee-db.xxxx.us-east-1.rds.amazonaws.com}"
DUMP="${2:-}"
MASTER="${PGUSER:-postgres}"
RAIZ="$(cd "$(dirname "$0")/../.." && pwd)"
: "${PGPASSWORD:?Exporte PGPASSWORD con la contraseña master de RDS}"
export PGSSLMODE=require PGCONNECT_TIMEOUT=10 PGOPTIONS="-c client_min_messages=warning"

psql_master() { psql -h "$ENDPOINT" -U "$MASTER" -v ON_ERROR_STOP=1 "$@"; }

echo "-> Conexión con RDS ($ENDPOINT) por SSL"
psql_master -d postgres -tAc "SELECT version()"

echo "-> Base de datos ecoraee"
if [ "$(psql_master -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = 'ecoraee'")" != "1" ]; then
  psql_master -d postgres -c "CREATE DATABASE ecoraee"
fi

if [ -n "$DUMP" ]; then
  echo "-> Restaurando $DUMP (datos migrados desde el entorno local)"
  psql_master -d ecoraee -c "CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public" \
                         -c "DROP SCHEMA IF EXISTS ecoraee CASCADE" \
                         -c "ALTER DATABASE ecoraee SET search_path = ecoraee, public" \
                         -c "ALTER DATABASE ecoraee SET timezone = 'America/Guayaquil'"
  pg_restore -h "$ENDPOINT" -U "$MASTER" -d ecoraee --no-owner --no-privileges --exit-on-error "$DUMP"
else
  echo "-> Creando el modelo físico y cargando los datos sintéticos"
  psql_master -d ecoraee -q -f "$RAIZ/database/01_modelo_fisico_ddl.sql"
  psql_master -d ecoraee -q -f "$RAIZ/database/02_datos_sinteticos.sql"
fi

echo "-> Usuario de la aplicación (ecoraee_app)"
CLAVE_APP="${CLAVE_APP:-$(openssl rand -hex 16)}"   # solo letras y números: segura dentro de una URL
psql_master -d ecoraee -q -v clave_app="$CLAVE_APP" -f "$RAIZ/deploy/rds/usuario_app.sql"

echo "-> Verificación"
psql_master -d ecoraee -tA <<'SQL'
SELECT 'Tablas:        ' || count(*) FROM information_schema.tables WHERE table_schema = 'ecoraee' AND table_type = 'BASE TABLE';
SELECT 'Dispositivos:  ' || count(*) FROM ecoraee.dispositivo;
SELECT 'Lotes:         ' || count(*) FROM ecoraee.lote;
SELECT 'Usuarios:      ' || count(*) FROM ecoraee.usuario;
SELECT 'Historial:     ' || count(*) FROM ecoraee.historial_estado;
SQL

cat <<EOF

=====================================================================
 Migración terminada. Guarde este valor en SSM Parameter Store como
 /ecoraee/DATABASE_URL (tipo SecureString):

 postgresql+psycopg://ecoraee_app:${CLAVE_APP}@${ENDPOINT}:5432/ecoraee?sslmode=verify-full&sslrootcert=/certs/rds-ca.pem

 Luego reinicie la API:  sudo bash $RAIZ/deploy/ec2/iniciar_api.sh
=====================================================================
EOF
