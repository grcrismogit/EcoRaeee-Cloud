"""EcoRAEE Cloud · Verificación del despliegue en AWS (Parte 6 del enunciado).

Recorre la arquitectura completa contra la nube real y marca cada punto con OK o FALLA:
frontend en S3, API en EC2, base en RDS (con SSL), CORS, CRUD, evidencias en S3 con URL
prefirmada e integridad SHA-256. Solo usa la biblioteca estándar de Python 3.

Uso:
    python deploy/verificar_despliegue.py --web http://<bucket>.s3-website-us-east-1.amazonaws.com --api http://<IP-EC2>
    python deploy/verificar_despliegue.py --web https://<id>.cloudfront.net --api https://<id>.cloudfront.net   (con CloudFront)

Crea un lote, un dispositivo, una marca y una evidencia de prueba, y los borra al final.
"""
import argparse
import json
import time
import urllib.error
import urllib.request
import uuid

PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
       b"\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0\xf0\x1f\x00\x05\x00\x01\xff\x89\x99=\x1d\x00\x00\x00\x00IEND\xaeB`\x82")
resultados = []


def pedir(metodo, url, cuerpo=None, token=None, cabeceras=None, tipo="application/json"):
    datos = None
    h = dict(cabeceras or {})
    if cuerpo is not None:
        datos = cuerpo if isinstance(cuerpo, bytes) else json.dumps(cuerpo).encode()
        h["Content-Type"] = tipo
    if token:
        h["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=datos, method=metodo, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()
    except (urllib.error.URLError, OSError) as e:  # sin conexión: se informa como FALLA, no como error
        return 0, {}, str(e).encode()


class _SinRedireccion(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None  # se quiere ver la respuesta 301 en sí, no seguirla


def sin_redireccion(url):
    """Estado y cabecera Location de una petición, sin seguir redirecciones."""
    try:
        r = urllib.request.build_opener(_SinRedireccion).open(url, timeout=20)
        return r.status, r.headers.get("Location", "")
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Location", "")
    except (urllib.error.URLError, OSError):
        return 0, ""


def js(contenido):
    return json.loads(contenido or b"null")


def comprobar(nombre, condicion, detalle=""):
    resultados.append(bool(condicion))
    print(f"[{'OK   ' if condicion else 'FALLA'}] {nombre}" + (f" · {detalle}" if detalle else ""))
    return condicion


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--web", required=True, help="URL del sitio web del bucket S3 del frontend")
    p.add_argument("--api", required=True, help="URL pública de la API en EC2 (http://IP-elástica)")
    p.add_argument("--email", default="admin@ecoraee.ec")
    p.add_argument("--password", default="Demo2026!")
    a = p.parse_args()
    web, api = a.web.rstrip("/"), a.api.rstrip("/") + "/api"
    origen = web.split("/", 3)[0] + "//" + web.split("/", 3)[2]
    mismo_origen = a.api.rstrip("/").startswith(origen)  # CloudFront: app y API en el mismo dominio

    print("\n== 1. Frontend en Amazon S3 ==")
    s, _, c = pedir("GET", web + "/")
    comprobar("La aplicación web responde desde internet", s == 200 and b"EcoRAEE" in c, f"HTTP {s}")
    s, _, c = pedir("GET", web + "/config.js")
    esperado = b"apiUrl: ''" if mismo_origen else a.api.rstrip("/").encode()
    comprobar("config.js apunta a la API" + (" (mismo dominio)" if mismo_origen else " de EC2"), s == 200 and esperado in c,
              c.decode(errors="ignore").strip()[-80:])
    if web.startswith("https://"):
        s, loc = sin_redireccion("http://" + web[len("https://"):] + "/")
        comprobar("Quien entra por HTTP es enviado a HTTPS", s in (301, 302, 307, 308) and loc.startswith("https://"),
                  f"HTTP {s} → {loc or 'sin redirección'}")
    s, _, c = pedir("GET", web + "/trazabilidad/RAEE-2026-00001")
    # S3 responde 404 pero con index.html (documento de error); lo que importa es que llegue la app
    comprobar("Las rutas de React cargan (documento de error = index.html)", b"EcoRAEE" in c, f"HTTP {s}")

    print("\n== 2. Backend en Amazon EC2 y base en Amazon RDS ==")
    s, _, c = pedir("GET", api + "/salud")
    salud = js(c) if s == 200 else {}
    comprobar("La API responde en EC2", s == 200, f"HTTP {s}")
    comprobar("La base de datos es Amazon RDS", salud.get("motor") == "Amazon RDS", salud.get("postgres", ""))
    comprobar("La conexión con RDS va cifrada (SSL)", salud.get("ssl") is True)
    comprobar("Las evidencias se guardan en S3", str(salud.get("almacenamiento", "")).startswith("s3://"), salud.get("almacenamiento", ""))
    comprobar("SNS está configurado", salud.get("notificaciones_sns") is True)

    if mismo_origen:
        comprobar("Frontend y API en el mismo dominio: no necesitan CORS", True)
    else:
        s, h, _ = pedir("OPTIONS", api + "/auth/login", cabeceras={
            "Origin": origen, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"})
        permitido = {k.lower(): v for k, v in h.items()}.get("access-control-allow-origin")
        comprobar("CORS permite al frontend llamar a la API", permitido == origen, f"permitido: {permitido}")

    print("\n== 3. Funcionalidad (registrar, consultar, actualizar y eliminar) ==")
    s, _, c = pedir("POST", api + "/auth/login", {"email": a.email, "password": a.password})
    if not comprobar("Inicio de sesión (JWT)", s == 200, f"HTTP {s}"):
        return resumen()
    token = js(c)["access_token"]
    marca = f"Prueba AWS {int(time.time())}"
    s, _, c = pedir("POST", api + "/marcas", {"nombre": marca}, token)
    id_marca = js(c).get("id_marca") if s == 201 else None
    comprobar("Registrar (marca)", s == 201, f"HTTP {s}")
    if id_marca:
        s, _, c = pedir("PUT", api + f"/marcas/{id_marca}", {"nombre": marca + " editada"}, token)
        comprobar("Actualizar", s == 200 and js(c)["nombre"].endswith("editada"), f"HTTP {s}")
        s, _, c = pedir("GET", api + f"/marcas/{id_marca}", token=token)
        comprobar("Consultar", s == 200, f"HTTP {s}")
        s, _, _ = pedir("DELETE", api + f"/marcas/{id_marca}", token=token)
        comprobar("Eliminar", s == 204, f"HTTP {s}")

    s, _, c = pedir("GET", api + "/usuarios", token=token)
    generador = next((u["id_usuario"] for u in js(c) or [] if u.get("rol_codigo") == "GENERADOR" and u.get("activo")), None)
    s, _, c = pedir("POST", api + "/lotes", {"descripcion": "Lote de verificación AWS", "id_generador": generador}, token)
    lote = js(c) if s == 201 else {}
    s, _, c = pedir("POST", api + "/dispositivos", {"id_lote": lote.get("id_lote"), "id_categoria": 1, "peso_kg": 1.5,
                                                    "modelo": "Verificación"}, token)
    disp = js(c) if s == 201 else {}
    comprobar("RDS genera el código único del dispositivo (RN-01)", str(disp.get("codigo_unico", "")).startswith("RAEE-"),
              disp.get("codigo_unico", f"HTTP {s}"))

    print("\n== 4. Evidencias en Amazon S3 ==")
    if disp:
        limite = uuid.uuid4().hex
        partes = []
        for campo, valor in {"tipo_evidencia": "FOTO", "vinculo": "dispositivo", "id_vinculo": str(disp["id_dispositivo"])}.items():
            partes.append(f'--{limite}\r\nContent-Disposition: form-data; name="{campo}"\r\n\r\n{valor}\r\n'.encode())
        partes.append(f'--{limite}\r\nContent-Disposition: form-data; name="archivo"; filename="verificacion.png"\r\n'
                      f"Content-Type: image/png\r\n\r\n".encode() + PNG + b"\r\n")
        partes.append(f"--{limite}--\r\n".encode())
        s, _, c = pedir("POST", api + "/evidencias", b"".join(partes), token, tipo=f"multipart/form-data; boundary={limite}")
        ev = js(c) if s == 201 else {}
        comprobar("Subir evidencia (EC2 → S3 con el rol IAM)", s == 201, ev.get("s3_key", f"HTTP {s}"))
        if ev:
            url = ev.get("url") or ""
            comprobar("La API entrega una URL prefirmada", "X-Amz-Signature" in url)
            s, _, c = pedir("GET", url) if url else (0, {}, b"")
            comprobar("El navegador descarga la evidencia directo de S3", s == 200 and c == PNG, f"HTTP {s}")
            s, _, c = pedir("GET", api + f"/evidencias/{ev['id_evidencia']}/verificar", token=token)
            comprobar("Integridad SHA-256 verificada", s == 200 and js(c).get("integra") is True)
            s, _, _ = pedir("DELETE", api + f"/evidencias/{ev['id_evidencia']}", token=token)
            comprobar("Eliminar evidencia (también se borra de S3)", s == 204, f"HTTP {s}")
        pedir("DELETE", api + f"/dispositivos/{disp['id_dispositivo']}", token=token)
    if lote:
        pedir("DELETE", api + f"/lotes/{lote['id_lote']}", token=token)
    return resumen()


def resumen():
    ok = sum(resultados)
    print(f"\nResultado: {ok} de {len(resultados)} comprobaciones correctas.")
    return 0 if ok == len(resultados) else 1


if __name__ == "__main__":
    raise SystemExit(main())
