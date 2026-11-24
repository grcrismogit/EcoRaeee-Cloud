#!/bin/bash
# =====================================================================
#  EcoRAEE Cloud · (Re)inicia la API en la instancia EC2
#
#  1. Lee la configuración de SSM Parameter Store (/ecoraee/...). Las
#     credenciales de AWS las da el rol IAM de la instancia: no hay claves
#     en el código ni en este script.
#  2. Descarga el certificado de Amazon RDS para validar la conexión SSL.
#  3. Construye la imagen Docker del backend y la ejecuta en el puerto 80.
#
#  Uso (por Session Manager o SSH):   sudo bash /opt/ecoraee/deploy/ec2/iniciar_api.sh
#  Tras cambiar el código:            cd /opt/ecoraee && sudo git pull && sudo bash deploy/ec2/iniciar_api.sh
# =====================================================================
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/../.." && pwd)"
CONF=/etc/ecoraee
mkdir -p "$CONF" && chmod 700 "$CONF"

# Región de la instancia (IMDSv2)
TOKEN=$(curl -sS -X PUT http://169.254.169.254/latest/api/token -H "X-aws-ec2-metadata-token-ttl-seconds: 300")
REGION=$(curl -sS -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/region)

echo "-> Leyendo /ecoraee/* de SSM Parameter Store ($REGION)"
aws ssm get-parameters-by-path --region "$REGION" --path /ecoraee/ --with-decryption \
  --query 'Parameters[].[Name,Value]' --output text \
  | awk -F'\t' '{ sub("^/ecoraee/", "", $1); print $1 "=" $2 }' > "$CONF/api.env.nuevo"

for clave in DATABASE_URL JWT_SECRET CORS_ORIGINS S3_BUCKET_EVIDENCIAS; do
  if ! grep -q "^$clave=" "$CONF/api.env.nuevo"; then
    echo "ERROR: falta el parámetro /ecoraee/$clave en SSM Parameter Store." >&2
    exit 1
  fi
done
echo "AWS_REGION=$REGION" >> "$CONF/api.env.nuevo"
echo "TZ=America/Guayaquil" >> "$CONF/api.env.nuevo"
mv "$CONF/api.env.nuevo" "$CONF/api.env" && chmod 600 "$CONF/api.env"

echo "-> Certificado raíz de Amazon RDS (SSL verify-full)"
curl -sSf -o "$CONF/rds-ca.pem" https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem
chmod 644 "$CONF/rds-ca.pem"

echo "-> Construyendo la imagen del backend"
docker build -t ecoraee-api "$RAIZ/backend"

echo "-> Iniciando el contenedor"
docker rm -f ecoraee-api >/dev/null 2>&1 || true
# Red del host: el contenedor llega a IMDSv2 (credenciales del rol) aunque la instancia
# limite los saltos a 1, y la API escucha directo en el puerto 80 de la instancia.
docker run -d --name ecoraee-api --restart unless-stopped --network host \
  --env-file "$CONF/api.env" \
  -v "$CONF/rds-ca.pem:/certs/rds-ca.pem:ro" \
  ecoraee-api uvicorn app.main:app --host 0.0.0.0 --port 80

sleep 4
if curl -sSf http://localhost/api/salud; then
  echo; echo "OK: la API responde en http://<IP-pública>/api/salud"
else
  echo "La API no respondió. Revise:  docker logs ecoraee-api" >&2
  exit 1
fi
