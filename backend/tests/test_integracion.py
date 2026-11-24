"""Pruebas de integración: API (FastAPI) + base de datos real (PostgreSQL).

Reinicia la base con los datos sintéticos y recorre el ciclo completo de
trazabilidad, además de las reglas de negocio que deben rechazarse.

Ejecutar desde la carpeta backend:   python -m pytest -v
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from scripts import init_db

PASSWORD = "Demo2026!"


@pytest.fixture(scope="module")
def client():
    init_db.main()  # base limpia y con datos de prueba
    with TestClient(app) as c:
        yield c


def _token(client, email):
    r = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def h(client):
    return {rol: _token(client, email) for rol, email in {
        "admin": "admin@ecoraee.ec", "generador": "generador@ecoraee.ec", "operador": "operador@ecoraee.ec",
        "tecnico": "tecnico@ecoraee.ec", "coordinador": "coordinador@ecoraee.ec", "beneficiario": "beneficiario@ecoraee.ec",
    }.items()}


# ------------------------------------------------------------------ 1. conexión y seguridad
def test_salud_api_y_base(client):
    r = client.get("/api/salud")
    assert r.status_code == 200 and r.json()["tablas"] == 25


def test_login_incorrecto_y_sin_token(client):
    assert client.post("/api/auth/login", json={"email": "admin@ecoraee.ec", "password": "x"}).status_code == 401
    assert client.get("/api/lotes").status_code == 401


def test_usuario_inactivo_no_inicia_sesion(client):
    r = client.post("/api/auth/login", json={"email": "jlema@ecoraee.ec", "password": PASSWORD})
    assert r.status_code == 401


def test_permiso_por_rol(client, h):
    r = client.post("/api/lotes", json={"descripcion": "Lote no autorizado"}, headers=h["beneficiario"])
    assert r.status_code == 403


# ------------------------------------------------------------------ 2. CRUD y validaciones
def test_crud_marca(client, h):
    r = client.post("/api/marcas", json={"nombre": "Toshiba"}, headers=h["admin"])
    assert r.status_code == 201
    id_ = r.json()["id_marca"]
    assert client.put(f"/api/marcas/{id_}", json={"nombre": "Toshiba Corp"}, headers=h["admin"]).json()["nombre"] == "Toshiba Corp"
    dup = client.post("/api/marcas", json={"nombre": "Dell"}, headers=h["admin"])
    assert dup.status_code == 409 and "Ya existe una marca" in dup.json()["detail"]
    assert client.delete(f"/api/marcas/{id_}", headers=h["admin"]).status_code == 204
    assert client.get(f"/api/marcas/{id_}", headers=h["admin"]).status_code == 404


def test_validacion_en_espanol(client, h):
    r = client.post("/api/centros", json={"nombre": "X", "capacidad_unidades": -3}, headers=h["admin"])
    assert r.status_code == 422
    campos = {e["campo"] for e in r.json()["errores"]}
    assert {"nombre", "capacidad_unidades", "id_organizacion"} <= campos


def test_email_duplicado_sin_importar_mayusculas(client, h):
    datos = {"id_organizacion": 1, "id_rol": 2, "nombres": "Ana", "apellidos": "Prueba",
             "email": "GENERADOR@ecoraee.ec", "password": "Clave2026"}
    r = client.post("/api/usuarios", json=datos, headers=h["admin"])
    assert r.status_code == 409 and "correo" in r.json()["detail"]


def test_no_se_elimina_registro_en_uso(client, h):
    r = client.delete("/api/categorias/1", headers=h["admin"])
    assert r.status_code == 409 and "usado" in r.json()["detail"]


# ------------------------------------------------------------------ 3. ciclo completo de trazabilidad
def test_ciclo_completo(client, h):
    # Generador registra lote y dispositivos (códigos generados por la base, RN-01)
    lote = client.post("/api/lotes", json={"descripcion": "Prueba de integración"}, headers=h["generador"]).json()
    assert lote["codigo_lote"].startswith("LOT-") and lote["estado"] == "REGISTRADO"
    d1 = client.post("/api/dispositivos", json={"id_lote": lote["id_lote"], "id_categoria": 1, "id_marca": 2,
                                                 "modelo": "EliteBook 840", "peso_kg": 1.6}, headers=h["generador"]).json()
    d2 = client.post("/api/dispositivos", json={"id_lote": lote["id_lote"], "id_categoria": 3,
                                                 "peso_kg": 3.4}, headers=h["generador"]).json()
    assert d1["codigo_unico"].startswith("RAEE-") and d2["marca_nombre"] is None

    # Solicitud y recepción en el acopio Quito
    sol = client.post("/api/solicitudes", json={"id_lote": lote["id_lote"], "id_centro_destino": 1,
                                                 "modalidad": "ENTREGA"}, headers=h["generador"]).json()
    assert sol["estado"] == "PENDIENTE"
    antes = {i["id_categoria"]: i["cantidad_unidades"] for i in client.get("/api/inventario?id_centro=1", headers=h["admin"]).json()}
    rec = client.post("/api/recepciones", json={"id_solicitud": sol["id_solicitud"], "peso_recibido_kg": 5.0},
                      headers=h["operador"])
    assert rec.status_code == 201, rec.text
    disp = client.get(f"/api/dispositivos/{d1['id_dispositivo']}", headers=h["admin"]).json()
    assert disp["estado_actual"] == "RECIBIDO" and disp["id_centro_actual"] == 1
    despues = {i["id_categoria"]: i["cantidad_unidades"] for i in client.get("/api/inventario?id_centro=1", headers=h["admin"]).json()}
    assert despues[1] == antes.get(1, 0) + 1  # inventario actualizado por trigger

    # Evaluación técnica (RN-02)
    ev = client.post("/api/evaluaciones", json={"id_dispositivo": d1["id_dispositivo"], "condicion": "FUNCIONAL",
                                                 "clasificacion": "REUTILIZABLE", "borrado_datos": True}, headers=h["tecnico"])
    assert ev.status_code == 201 and ev.json()["tecnico_nombre"] == "Sofía Herrera"
    assert client.get(f"/api/dispositivos/{d1['id_dispositivo']}", headers=h["admin"]).json()["clasificacion"] == "REUTILIZABLE"

    # Transferencia acopio Quito → taller con ruta ACQ → TALLER
    t = client.post("/api/transferencias", json={"id_centro_origen": 1, "id_centro_destino": 3, "id_arista": 4,
                                                  "fecha_salida": "2026-11-10T09:00:00-05:00",
                                                  "dispositivos": [d1["id_dispositivo"]]}, headers=h["coordinador"])
    assert t.status_code == 201, t.text
    id_t = t.json()["id_transferencia"]
    assert client.post(f"/api/transferencias/{id_t}/despachar", headers=h["coordinador"]).json()["estado"] == "EN_TRANSITO"
    inv_taller_antes = sum(i["cantidad_unidades"] for i in client.get("/api/inventario?id_centro=3", headers=h["admin"]).json())
    recibida = client.post(f"/api/transferencias/{id_t}/recibir", json={}, headers=h["operador"]).json()
    assert recibida["estado"] == "CERRADA" and recibida["responsable_nombre"] == "Luis Andrade"
    inv_taller = sum(i["cantidad_unidades"] for i in client.get("/api/inventario?id_centro=3", headers=h["admin"]).json())
    assert inv_taller == inv_taller_antes + 1  # RN-06: origen y destino en la misma transacción

    # Destino final y cierre (RN-08)
    dest = client.post("/api/destinos", json={"id_dispositivo": d1["id_dispositivo"], "tipo_destino": "DONACION",
                                              "id_org_beneficiaria": 7}, headers=h["coordinador"])
    assert dest.status_code == 201, dest.text
    traza = client.get(f"/api/dispositivos/{d1['id_dispositivo']}/trazabilidad", headers=h["admin"]).json()
    assert traza["dispositivo"]["estado_actual"] == "CERRADO"
    assert [x["estado_nuevo"] for x in traza["historial"]] == [
        "REGISTRADO", "RECIBIDO", "EVALUADO", "EN_TRANSITO", "TRANSFERIDO", "CERRADO"]
    assert traza["recepcion"] and len(traza["transferencias"]) == 1 and traza["destino_final"]["tipo_destino"] == "DONACION"
    # Equipo cerrado: ya no admite cambios
    r = client.put(f"/api/dispositivos/{d1['id_dispositivo']}", json={"id_lote": lote["id_lote"], "id_categoria": 1,
                                                                      "peso_kg": 2}, headers=h["generador"])
    assert r.status_code == 409 and "RN-08" in r.json()["detail"]
    # Auditoría registra quién lo hizo
    aud = client.get(f"/api/auditoria?tabla=destino_final&id_registro={dest.json()['id_destino_final']}", headers=h["admin"]).json()
    assert aud[0]["usuario_nombre"] == "Marco Paredes"


# ------------------------------------------------------------------ 4. reglas de negocio rechazadas
def test_rn01_codigos_sin_huecos_y_serie_unica(client, h):
    lote = client.post("/api/lotes", json={"descripcion": "Prueba de códigos"}, headers=h["generador"]).json()

    def nuevo(**kw):
        return client.post("/api/dispositivos", json={"id_lote": lote["id_lote"], "id_categoria": 1, "peso_kg": 1, **kw},
                           headers=h["generador"])

    a = nuevo(id_marca=1, numero_serie="ser-777").json()["codigo_unico"]
    # Dos rechazos (equipo ya activo con la misma marca y serie, y lote ya recibido) que no consumen número
    dup = nuevo(id_marca=1, numero_serie="SER-777")
    assert dup.status_code == 409 and "serie" in dup.json()["detail"]
    r = client.post("/api/dispositivos", json={"id_lote": 1, "id_categoria": 1, "peso_kg": 1}, headers=h["admin"])
    assert r.status_code == 409
    b = nuevo().json()["codigo_unico"]
    _, anio, n = a.split("-")
    assert b == f"RAEE-{anio}-{int(n) + 1:05d}"


def test_rn01_anio_de_registro_y_sin_truncar(client):
    import psycopg
    from app.config import settings
    with psycopg.connect(settings.database_url.replace("postgresql+psycopg://", "postgresql://")) as cx:
        # 2031-01-01 03:00 UTC todavía es 31 de diciembre de 2030 en Ecuador
        fila = cx.execute("SELECT ecoraee.fn_siguiente_codigo('LOTE', 'LOT', '2031-01-01 03:00+00', 4)").fetchone()
        assert fila[0] == "LOT-2030-0001"
        cx.execute("INSERT INTO ecoraee.correlativo VALUES ('DISPOSITIVO', 2031, 99999)")
        fila = cx.execute("SELECT ecoraee.fn_siguiente_codigo('DISPOSITIVO', 'RAEE', '2031-06-01', 5)").fetchone()
        assert fila[0] == "RAEE-2031-100000"  # antes lpad lo cortaba a RAEE-2031-10000
        cx.rollback()


def test_rn02_solo_tecnico_evalua(client, h):
    r = client.post("/api/evaluaciones", json={"id_dispositivo": 9, "condicion": "FUNCIONAL", "clasificacion": "RECICLABLE",
                                               "id_tecnico": 2}, headers=h["admin"])
    assert r.status_code == 409 and "RN-02" in r.json()["detail"]


def test_rn04_no_recuperable_no_se_dona(client, h):
    client.post("/api/transferencias/3/recibir", json={}, headers=h["coordinador"])  # la impresora llega al gestor
    r = client.post("/api/destinos", json={"id_dispositivo": 5, "tipo_destino": "DONACION", "id_org_beneficiaria": 6},
                    headers=h["coordinador"])
    assert r.status_code == 409 and "RN-04" in r.json()["detail"]
    ok = client.post("/api/destinos", json={"id_dispositivo": 5, "tipo_destino": "DISPOSICION_FINAL"}, headers=h["coordinador"])
    assert ok.status_code == 201


def test_rn05_capacidad_de_la_arista(client, h):
    r = client.post("/api/transferencias", json={"id_centro_origen": 1, "id_centro_destino": 4, "id_arista": 5,
                                                  "fecha_salida": "2026-11-12T09:00:00-05:00",
                                                  "dispositivos": [7, 8, 9, 10]}, headers=h["coordinador"])
    assert r.status_code == 409 and "RN-05" in r.json()["detail"]
    assert all(t["fecha_salida"] != "2026-11-12T14:00:00Z" for t in client.get("/api/transferencias", headers=h["admin"]).json())


def test_rn07_y_evidencias(client, h):
    archivo = {"archivo": ("foto.png", b"\x89PNG\r\n\x1a\nprueba", "image/png")}
    r = client.post("/api/evidencias", data={"tipo_evidencia": "FOTO", "vinculo": "dispositivo", "id_vinculo": "9"},
                    files=archivo, headers=h["operador"])
    assert r.status_code == 201, r.text
    id_e = r.json()["id_evidencia"]
    assert client.get(f"/api/evidencias/{id_e}/verificar", headers=h["admin"]).json()["integra"] is True
    assert client.get(f"/api/evidencias/{id_e}/archivo", headers=h["admin"]).content.endswith(b"prueba")
    malo = client.post("/api/evidencias", data={"tipo_evidencia": "FOTO", "vinculo": "dispositivo", "id_vinculo": "9"},
                       files={"archivo": ("virus.exe", b"MZ", "application/octet-stream")}, headers=h["operador"])
    assert malo.status_code == 422
    assert client.delete(f"/api/evidencias/{id_e}", headers=h["operador"]).status_code == 204


def test_dispositivo_en_proceso_no_se_elimina(client, h):
    r = client.delete("/api/dispositivos/7", headers=h["admin"])
    assert r.status_code == 409 and "REGISTRADO" in r.json()["detail"]


# ------------------------------------------------------------------ 5. red y flujo máximo
def test_flujo_maximo(client, h):
    r = client.post("/api/escenarios/1/flujo-maximo", headers=h["coordinador"])
    assert r.status_code == 201, r.text
    res = r.json()
    assert res["flujo_maximo"] == 59
    corte = {f["id_arista"] for f in res["flujos"] if f["en_corte_minimo"]}
    assert corte == {1, 4, 5, 9}  # ACQ→TN, ACQ→TALLER, ACQ→GESTOR, TS→GESTOR = 30+8+3+18
    capacidades = {a["id_arista"]: a["capacidad"] for a in client.get("/api/aristas?id_escenario=1", headers=h["admin"]).json()}
    assert sum(capacidades[i] for i in corte) == res["flujo_maximo"]  # teorema flujo máximo = corte mínimo
