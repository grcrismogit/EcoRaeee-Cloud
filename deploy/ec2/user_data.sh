#!/bin/bash
# =====================================================================
#  EcoRAEE Cloud · Datos de usuario (user data) de la instancia EC2
#  Amazon Linux 2023. Se ejecuta UNA vez, como root, al crear la instancia.
#
#  Antes de pegarlo en "Advanced details → User data", cambie REPO_URL
#  por la URL de su repositorio de GitHub (debe ser público, o use la
#  opción B de la guía: subir el proyecto con scp).
# =====================================================================
set -euxo pipefail
exec > >(tee /var/log/ecoraee-user-data.log) 2>&1

REPO_URL="https://github.com/USUARIO/ecoraee-cloud.git"   # <-- cambiar
RAMA="main"

# 1) Docker (ejecuta la API), git y el cliente de PostgreSQL 16 (migración a RDS)
dnf install -y docker git postgresql16
systemctl enable --now docker
usermod -aG docker ec2-user

# 2) Código del proyecto en /opt/ecoraee
if [ ! -d /opt/ecoraee/.git ]; then
  git clone --depth 1 --branch "$RAMA" "$REPO_URL" /opt/ecoraee
fi

# 3) Lee la configuración de SSM Parameter Store y levanta la API
#    (si los parámetros todavía no existen, el script lo avisa en el log)
bash /opt/ecoraee/deploy/ec2/iniciar_api.sh || echo "Revise los parámetros /ecoraee/* y ejecute iniciar_api.sh de nuevo"
