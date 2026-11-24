#!/bin/bash
# =====================================================================
#  EcoRAEE Cloud · Publica el frontend React en el bucket S3 (sitio web)
#
#  Se ejecuta en AWS CloudShell (ya trae AWS CLI, Node.js y npm) con el
#  repositorio clonado, y con un usuario del grupo G-Datos:
#    git clone https://github.com/grcrismogit/EcoRaeee-Cloud.git && cd EcoRaeee-Cloud
#    bash deploy/frontend/desplegar_frontend.sh <bucket-frontend> http://<IP-elástica-de-EC2> [sin-demo]
#    bash deploy/frontend/desplegar_frontend.sh <bucket-frontend> cloudfront [sin-demo]
#
#  "cloudfront": la app y la API se sirven desde el mismo dominio HTTPS de CloudFront
#  (/api/* va a EC2), así que config.js queda con apiUrl vacío.
#  Con "sin-demo" se ocultan los botones de cuentas de prueba del login (sitio público).
#
#  La URL de la API no se compila: va en config.js, que se sube sin caché.
#  Si la IP de EC2 cambia, basta con volver a ejecutar este script.
# =====================================================================
set -euo pipefail

BUCKET="${1:?Indique el nombre del bucket del frontend}"
API="${2:?Indique la URL pública de la API (p. ej. http://3.90.12.34) o la palabra cloudfront}"
[ "$API" = "cloudfront" ] && API=""
DEMO=true; [ "${3:-}" = "sin-demo" ] && DEMO=false
cd "$(dirname "$0")/../../frontend"

echo "-> Compilando la aplicación"
npm ci --no-audit --no-fund
npm run build
printf "window.ECORAEE_CONFIG = { apiUrl: '%s', cuentasDemo: %s }\n" "${API%/}" "$DEMO" > dist/config.js

echo "-> Subiendo a s3://$BUCKET"
# Los archivos con hash en el nombre se cachean un año; index.html y config.js nunca
aws s3 sync dist "s3://$BUCKET" --delete --exclude index.html --exclude config.js \
  --cache-control "public, max-age=31536000, immutable"
aws s3 cp dist/index.html "s3://$BUCKET/index.html" --cache-control "no-cache"
aws s3 cp dist/config.js "s3://$BUCKET/config.js" --cache-control "no-cache" --content-type "application/javascript"

REGION=$(aws s3api get-bucket-location --bucket "$BUCKET" --query LocationConstraint --output text)
[ "$REGION" = "None" ] && REGION=us-east-1
echo
echo "OK. Aplicación publicada en: http://$BUCKET.s3-website-$REGION.amazonaws.com"
if [ -z "$API" ]; then
  echo "Con CloudFront: cree una invalidación de /* para que tome el config.js nuevo."
else
  echo "Recuerde que esa URL debe estar en /ecoraee/CORS_ORIGINS."
fi
