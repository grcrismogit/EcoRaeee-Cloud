// Configuración que se lee al abrir la aplicación (no hace falta recompilar para cambiarla).
// En AWS, deploy/desplegar_frontend.sh reemplaza este archivo en el bucket S3 con la URL
// pública de la API en EC2. Vacío = mismo origen (Vite o Nginx reenvían /api al backend).
// cuentasDemo: muestra en el login los botones con las cuentas de prueba. En un sitio público
// cualquiera podría entrar como administrador: pónganlo en false cuando terminen de grabar.
window.ECORAEE_CONFIG = { apiUrl: '', cuentasDemo: true }
