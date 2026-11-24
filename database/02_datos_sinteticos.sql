-- =====================================================================
--  EcoRAEE Cloud · Datos sintéticos de prueba
--  Escenario: red universitaria (UIDE) con puntos de acopio en campus,
--  un taller de reacondicionamiento, un gestor de reciclaje y una
--  escuela comunitaria beneficiaria. TODOS los datos son ficticios.
--
--  Los procesos se cargan en orden (lote → solicitud → recepción →
--  evaluación → transferencia → destino final) para que los triggers
--  generen solos el historial, el inventario y la auditoría.
--  Contraseña de todos los usuarios de prueba: Demo2026!
-- =====================================================================
SET search_path TO ecoraee, public;

-- ---------------------------------------------------------------------
-- Catálogos
-- ---------------------------------------------------------------------
INSERT INTO rol (codigo, descripcion) VALUES
 ('ADMIN',                 'Administra catálogos, usuarios y la configuración de la plataforma'),
 ('GENERADOR',             'Registra lotes y dispositivos que entrega a la red'),
 ('OPERADOR_CENTRO',       'Recibe lotes y transferencias en un centro'),
 ('TECNICO_EVALUADOR',     'Diagnostica, clasifica y certifica el borrado seguro de datos'),
 ('COORDINADOR_LOGISTICO', 'Autoriza transferencias, rutas y destinos finales'),
 ('BENEFICIARIO',          'Consulta los equipos recibidos por su organización');

INSERT INTO organizacion (nombre, tipo_organizacion, identificacion, email_contacto, telefono) VALUES
 ('UIDE – Sede Quito',                              'UNIVERSIDAD',      '1791234560001', 'sostenibilidad.quito@ecoraee.ec', '022985600'),
 ('UIDE – Sede Guayaquil',                          'UNIVERSIDAD',      '0991234560001', 'sostenibilidad.gye@ecoraee.ec',   '042593500'),
 ('Escuela de Ciencias de la Computación (UIDE)',   'FACULTAD',         '1791234560002', 'computacion@ecoraee.ec',          '022985700'),
 ('ReTech Reacondicionamiento S.A.',                'REACONDICIONADOR', '1792345670001', 'taller@retech-demo.ec',           '023301122'),
 ('EcoGestor Andino Cía. Ltda.',                    'GESTOR_RECICLAJE', '1793456780001', 'operaciones@ecogestor-demo.ec',   '022456789'),
 ('Escuela Comunitaria Nuevos Horizontes',          'BENEFICIARIA',     '1794567890001', 'direccion@nuevoshorizontes-demo.ec', '022334455'),
 ('Unidad Educativa Comunitaria Sembrando Futuro',  'BENEFICIARIA',     '1795678900001', NULL,                              NULL);

-- id_rol: 1 ADMIN · 2 GENERADOR · 3 OPERADOR_CENTRO · 4 TECNICO_EVALUADOR · 5 COORDINADOR_LOGISTICO · 6 BENEFICIARIO
INSERT INTO usuario (id_organizacion, id_rol, nombres, apellidos, email, password_hash, activo) VALUES
 (1, 1, 'Andrea',   'Salinas',  'admin@ecoraee.ec',        crypt('Demo2026!', gen_salt('bf', 8)), TRUE),  -- 1
 (1, 2, 'Daniel',   'Ortega',   'generador@ecoraee.ec',    crypt('Demo2026!', gen_salt('bf', 8)), TRUE),  -- 2
 (2, 2, 'Paula',    'Méndez',   'pmendez@ecoraee.ec',      crypt('Demo2026!', gen_salt('bf', 8)), TRUE),  -- 3
 (1, 3, 'Luis',     'Andrade',  'operador@ecoraee.ec',     crypt('Demo2026!', gen_salt('bf', 8)), TRUE),  -- 4
 (4, 3, 'Karla',    'Vega',     'kvega@ecoraee.ec',        crypt('Demo2026!', gen_salt('bf', 8)), TRUE),  -- 5
 (4, 4, 'Sofía',    'Herrera',  'tecnico@ecoraee.ec',      crypt('Demo2026!', gen_salt('bf', 8)), TRUE),  -- 6
 (1, 5, 'Marco',    'Paredes',  'coordinador@ecoraee.ec',  crypt('Demo2026!', gen_salt('bf', 8)), TRUE),  -- 7
 (6, 6, 'Rosa',     'Quishpe',  'beneficiario@ecoraee.ec', crypt('Demo2026!', gen_salt('bf', 8)), TRUE),  -- 8
 (4, 4, 'Jorge',    'Lema',     'jlema@ecoraee.ec',        crypt('Demo2026!', gen_salt('bf', 8)), FALSE), -- 9 (inactivo)
 (5, 3, 'Gabriela', 'Torres',   'gtorres@ecoraee.ec',      crypt('Demo2026!', gen_salt('bf', 8)), TRUE),  -- 10
 (2, 3, 'Andrés',   'Cevallos', 'acevallos@ecoraee.ec',    crypt('Demo2026!', gen_salt('bf', 8)), TRUE);  -- 11

INSERT INTO tipo_centro (nombre, descripcion) VALUES
 ('Punto de acopio',              'Recibe RAEE de la comunidad universitaria dentro del campus'),
 ('Taller de reacondicionamiento','Repara y reacondiciona equipos recuperables'),
 ('Gestor de reciclaje',          'Gestor ambiental autorizado para reciclaje de RAEE'),
 ('Disposición final',            'Disposición segura de residuos no recuperables'),
 ('Entidad beneficiaria',         'Organización que recibe equipos donados');

INSERT INTO centro (id_organizacion, id_tipo_centro, nombre, direccion, ciudad, capacidad_unidades, capacidad_kg) VALUES
 (1, 1, 'Punto de Acopio UIDE Quito',     'Campus Quito, bloque de servicios, planta baja', 'Quito',     300, 3000),
 (2, 1, 'Punto de Acopio UIDE Guayaquil', 'Campus Guayaquil, bodega 2',                     'Guayaquil', 200, 2000),
 (4, 2, 'Taller ReTech Quito',            'Calle Los Cedros N45-12',                        'Quito',     150, 1500),
 (5, 3, 'Planta EcoGestor Andino',        'Panamericana Norte km 12',                       'Quito',    1000, 20000),
 (6, 5, 'Escuela Nuevos Horizontes',      'Barrio La Forestal, calle principal',            'Quito',      80, 800);

INSERT INTO categoria (nombre, descripcion, peligrosidad) VALUES
 ('Laptop',                  'Computador portátil',                          'MEDIA'),  -- 1
 ('Computador de escritorio','CPU o equipo todo en uno',                     'MEDIA'),  -- 2
 ('Monitor',                 'Pantallas LCD/LED',                            'ALTA'),   -- 3
 ('Impresora',               'Impresoras y multifunción',                    'MEDIA'),  -- 4
 ('Teléfono móvil',          'Celulares y smartphones',                      'MEDIA'),  -- 5
 ('Tablet',                  'Tabletas',                                     'MEDIA'),  -- 6
 ('Periférico',              'Teclados, mouse, parlantes y similares',       'BAJA'),   -- 7
 ('Equipo de red',           'Switches, routers y puntos de acceso',         'BAJA'),   -- 8
 ('UPS y baterías',          'Sistemas de respaldo de energía y baterías',   'ALTA'),   -- 9
 ('Proyector',               'Proyectores multimedia',                       'MEDIA');  -- 10

INSERT INTO marca (nombre) VALUES
 ('Dell'), ('HP'), ('Lenovo'), ('Apple'), ('Samsung'), ('Epson'), ('Cisco'), ('Asus'), ('Acer'), ('LG');
-- 1 Dell · 2 HP · 3 Lenovo · 4 Apple · 5 Samsung · 6 Epson · 7 Cisco · 8 Asus · 9 Acer · 10 LG

-- ---------------------------------------------------------------------
-- Red de traslados (Matemáticas Discretas): G = (V, E), 6 nodos y 10 aristas
-- Capacidad = unidades por traslado
-- ---------------------------------------------------------------------
INSERT INTO escenario_red (nombre, periodo_inicio, periodo_fin, unidad_medida, descripcion) VALUES
 ('Red Quito · 4.º trimestre 2026', '2026-10-01', '2026-12-31', 'UNIDADES',
  'Capacidad de traslado entre centros de la red universitaria (unidades por viaje).');

INSERT INTO nodo_red (id_escenario, id_centro, etiqueta, tipo_nodo) VALUES
 (1, 1,    'ACQ',    'FUENTE'),      -- 1 Punto de Acopio UIDE Quito
 (1, 2,    'ACG',    'INTERMEDIO'),  -- 2 Punto de Acopio UIDE Guayaquil
 (1, NULL, 'TN',     'INTERMEDIO'),  -- 3 Punto de tránsito Norte (nodo lógico, sin centro)
 (1, NULL, 'TS',     'INTERMEDIO'),  -- 4 Punto de tránsito Sur (nodo lógico, sin centro)
 (1, 3,    'TALLER', 'INTERMEDIO'),  -- 5 Taller ReTech Quito
 (1, 4,    'GESTOR', 'SUMIDERO');    -- 6 Planta EcoGestor Andino

INSERT INTO arista_red (id_escenario, id_nodo_origen, id_nodo_destino, capacidad) VALUES
 (1, 1, 3, 30),   -- 1  ACQ → TN
 (1, 1, 4, 20),   -- 2  ACQ → TS
 (1, 1, 2, 10),   -- 3  ACQ → ACG
 (1, 1, 5,  8),   -- 4  ACQ → TALLER
 (1, 1, 6,  3),   -- 5  ACQ → GESTOR
 (1, 2, 4, 15),   -- 6  ACG → TS
 (1, 3, 5, 18),   -- 7  TN  → TALLER
 (1, 3, 6, 15),   -- 8  TN  → GESTOR
 (1, 4, 6, 18),   -- 9  TS  → GESTOR
 (1, 5, 6, 25);   -- 10 TALLER → GESTOR

-- ---------------------------------------------------------------------
-- Procesos de trazabilidad (fecha y usuario de cada evento)
-- ---------------------------------------------------------------------

-- Lote 1 · Laboratorio B-204 (generador: Daniel Ortega)
SELECT set_config('ecoraee.id_usuario', '2', false), set_config('ecoraee.fecha_evento', '2026-10-05 09:15-05', false);
INSERT INTO lote (id_generador, fecha_registro, descripcion)
VALUES (2, '2026-10-05 09:15-05', 'Renovación del laboratorio de cómputo B-204');
INSERT INTO dispositivo (id_lote, id_categoria, id_marca, modelo, numero_serie, peso_kg, fecha_registro) VALUES
 (1, 1, 1, 'Latitude 5490',  'DL5490-7731', 2.10, '2026-10-05 09:20-05'),   -- RAEE-2026-00001
 (1, 1, 3, 'ThinkPad T470',  'LT470-2209',  2.00, '2026-10-05 09:21-05'),   -- RAEE-2026-00002
 (1, 3, 5, 'S24F350',        'SM24-5512',   3.50, '2026-10-05 09:22-05'),   -- RAEE-2026-00003
 (1, 2, 2, 'ProDesk 600 G3', 'HP600-8821',  6.80, '2026-10-05 09:23-05'),   -- RAEE-2026-00004
 (1, 4, 6, 'L3150',          'EPL3150-341', 4.30, '2026-10-05 09:24-05'),   -- RAEE-2026-00005
 (1,10, 6, 'PowerLite X41',  'EPX41-0912',  3.10, '2026-10-05 09:25-05');   -- RAEE-2026-00006

SELECT set_config('ecoraee.fecha_evento', '2026-10-06 10:00-05', false);
INSERT INTO solicitud_recoleccion (id_lote, id_solicitante, id_centro_destino, modalidad, fecha_solicitud, fecha_programada, estado)
VALUES (1, 2, 1, 'ENTREGA', '2026-10-06 10:00-05', '2026-10-08', 'PROGRAMADA');

-- Lote 2 · Biblioteca
SELECT set_config('ecoraee.fecha_evento', '2026-10-12 14:00-05', false);
INSERT INTO lote (id_generador, fecha_registro, descripcion)
VALUES (2, '2026-10-12 14:00-05', 'Equipos administrativos de la Biblioteca');
INSERT INTO dispositivo (id_lote, id_categoria, id_marca, modelo, numero_serie, peso_kg, fecha_registro) VALUES
 (2, 2,    1, 'OptiPlex 7050',       'DO7050-1180', 7.50, '2026-10-12 14:05-05'),  -- RAEE-2026-00007
 (2, 3,   10, '22MK400H',            'LG22-7765',   3.20, '2026-10-12 14:06-05'),  -- RAEE-2026-00008
 (2, 9, NULL, 'UPS 1000VA',          NULL,         11.00, '2026-10-12 14:07-05'),  -- RAEE-2026-00009 (sin marca: FK opcional)
 (2, 7, NULL, 'Kit teclado y mouse', NULL,          0.90, '2026-10-12 14:08-05');  -- RAEE-2026-00010
SELECT set_config('ecoraee.fecha_evento', '2026-10-13 08:40-05', false);
INSERT INTO solicitud_recoleccion (id_lote, id_solicitante, id_centro_destino, modalidad, fecha_solicitud, fecha_programada, estado)
VALUES (2, 2, 1, 'RECOLECCION', '2026-10-13 08:40-05', '2026-10-15', 'PROGRAMADA');

-- Recepción del lote 1 en el acopio Quito (operador: Luis Andrade)
SELECT set_config('ecoraee.id_usuario', '4', false), set_config('ecoraee.fecha_evento', '2026-10-08 11:30-05', false);
INSERT INTO recepcion (id_solicitud, id_centro, id_operador, fecha_recepcion, peso_recibido_kg, observaciones)
VALUES (1, 1, 4, '2026-10-08 11:30-05', 21.80, 'Lote completo; embalaje en buen estado.');

-- Evaluaciones técnicas del lote 1 (técnica: Sofía Herrera)
SELECT set_config('ecoraee.id_usuario', '6', false), set_config('ecoraee.fecha_evento', '2026-10-09 09:00-05', false);
INSERT INTO evaluacion_tecnica (id_dispositivo, id_tecnico, fecha_evaluacion, condicion, clasificacion, borrado_datos, observaciones)
VALUES (1, 6, '2026-10-09 09:00-05', 'FUNCIONAL',  'REUTILIZABLE',  TRUE,  'Batería al 82 %; disco borrado con método NIST 800-88.');
SELECT set_config('ecoraee.fecha_evento', '2026-10-09 09:40-05', false);
INSERT INTO evaluacion_tecnica (id_dispositivo, id_tecnico, fecha_evaluacion, condicion, clasificacion, borrado_datos, observaciones)
VALUES (2, 6, '2026-10-09 09:40-05', 'CON_FALLAS', 'REPARABLE',     TRUE,  'Teclado dañado; se recomienda reemplazo.');
SELECT set_config('ecoraee.fecha_evento', '2026-10-09 10:15-05', false);
INSERT INTO evaluacion_tecnica (id_dispositivo, id_tecnico, fecha_evaluacion, condicion, clasificacion, borrado_datos, observaciones)
VALUES (3, 6, '2026-10-09 10:15-05', 'DANADO',     'RECICLABLE',    FALSE, 'Panel con líneas verticales permanentes.');
SELECT set_config('ecoraee.fecha_evento', '2026-10-09 11:00-05', false);
INSERT INTO evaluacion_tecnica (id_dispositivo, id_tecnico, fecha_evaluacion, condicion, clasificacion, borrado_datos, observaciones)
VALUES (4, 6, '2026-10-09 11:00-05', 'CON_FALLAS', 'RECICLABLE',    TRUE,  'Placa madre con capacitores inflados; disco borrado.');
SELECT set_config('ecoraee.fecha_evento', '2026-10-09 11:30-05', false);
INSERT INTO evaluacion_tecnica (id_dispositivo, id_tecnico, fecha_evaluacion, condicion, clasificacion, borrado_datos, observaciones)
VALUES (5, 6, '2026-10-09 11:30-05', 'INSERVIBLE', 'NO_RECUPERABLE', FALSE, 'Cabezal y tarjeta lógica quemados.');
SELECT set_config('ecoraee.fecha_evento', '2026-10-10 09:00-05', false);
INSERT INTO evaluacion_tecnica (id_dispositivo, id_tecnico, fecha_evaluacion, condicion, clasificacion, borrado_datos, observaciones)
VALUES (6, 6, '2026-10-10 09:00-05', 'CON_FALLAS', 'REPARABLE',     FALSE, 'Lámpara agotada; carcasa en buen estado.');

-- Transferencia 1: acopio Quito → taller (coordinador: Marco Paredes), ruta ACQ → TALLER
SELECT set_config('ecoraee.id_usuario', '7', false), set_config('ecoraee.fecha_evento', '2026-10-13 08:00-05', false);
INSERT INTO transferencia (id_centro_origen, id_centro_destino, id_coordinador, id_arista, fecha_salida)
VALUES (1, 3, 7, 4, '2026-10-13 09:00-05');
INSERT INTO detalle_transferencia (id_transferencia, id_dispositivo) VALUES (1, 1), (1, 2);
SELECT set_config('ecoraee.fecha_evento', '2026-10-13 09:00-05', false);
CALL sp_despachar_transferencia(1);
SELECT set_config('ecoraee.id_usuario', '5', false), set_config('ecoraee.fecha_evento', '2026-10-13 16:00-05', false);
CALL sp_recibir_transferencia(1, 5);

-- Transferencia 2: acopio Quito → gestor de reciclaje, ruta ACQ → GESTOR
SELECT set_config('ecoraee.id_usuario', '7', false), set_config('ecoraee.fecha_evento', '2026-10-14 08:00-05', false);
INSERT INTO transferencia (id_centro_origen, id_centro_destino, id_coordinador, id_arista, fecha_salida)
VALUES (1, 4, 7, 5, '2026-10-14 08:30-05');
INSERT INTO detalle_transferencia (id_transferencia, id_dispositivo) VALUES (2, 3), (2, 4);
SELECT set_config('ecoraee.fecha_evento', '2026-10-14 08:30-05', false);
CALL sp_despachar_transferencia(2);
SELECT set_config('ecoraee.id_usuario', '10', false), set_config('ecoraee.fecha_evento', '2026-10-14 13:00-05', false);
CALL sp_recibir_transferencia(2, 10);

-- Recepción del lote 2
SELECT set_config('ecoraee.id_usuario', '4', false), set_config('ecoraee.fecha_evento', '2026-10-15 15:10-05', false);
INSERT INTO recepcion (id_solicitud, id_centro, id_operador, fecha_recepcion, peso_recibido_kg, observaciones)
VALUES (2, 1, 4, '2026-10-15 15:10-05', 22.60, 'La UPS llega sin batería interna.');

SELECT set_config('ecoraee.id_usuario', '6', false), set_config('ecoraee.fecha_evento', '2026-10-16 10:00-05', false);
INSERT INTO evaluacion_tecnica (id_dispositivo, id_tecnico, fecha_evaluacion, condicion, clasificacion, borrado_datos, observaciones)
VALUES (7, 6, '2026-10-16 10:00-05', 'FUNCIONAL', 'REUTILIZABLE', TRUE,  'Disco borrado y sistema operativo reinstalado.');
SELECT set_config('ecoraee.fecha_evento', '2026-10-16 10:30-05', false);
INSERT INTO evaluacion_tecnica (id_dispositivo, id_tecnico, fecha_evaluacion, condicion, clasificacion, borrado_datos, observaciones)
VALUES (8, 6, '2026-10-16 10:30-05', 'DANADO',    'RECICLABLE',   FALSE, 'Fuente de poder averiada.');

-- Reevaluación en el taller: el ThinkPad reparado pasa a REUTILIZABLE
SELECT set_config('ecoraee.fecha_evento', '2026-10-20 14:00-05', false);
INSERT INTO evaluacion_tecnica (id_dispositivo, id_tecnico, fecha_evaluacion, condicion, clasificacion, borrado_datos, observaciones)
VALUES (2, 6, '2026-10-20 14:00-05', 'FUNCIONAL', 'REUTILIZABLE', TRUE,  'Teclado reemplazado en el taller ReTech; pruebas superadas.');

-- Destinos finales
SELECT set_config('ecoraee.id_usuario', '10', false), set_config('ecoraee.fecha_evento', '2026-10-20 11:00-05', false);
INSERT INTO destino_final (id_dispositivo, id_centro, tipo_destino, fecha_confirmacion, id_usuario_confirma)
VALUES (3, 4, 'RECICLAJE', '2026-10-20 11:00-05', 10);
SELECT set_config('ecoraee.id_usuario', '7', false), set_config('ecoraee.fecha_evento', '2026-10-22 10:00-05', false);
INSERT INTO destino_final (id_dispositivo, id_centro, id_org_beneficiaria, tipo_destino, fecha_confirmacion, id_usuario_confirma)
VALUES (1, 3, 6, 'DONACION', '2026-10-22 10:00-05', 7);

-- Lote 3 · Guayaquil (generadora: Paula Méndez) con solicitud programada
SELECT set_config('ecoraee.id_usuario', '3', false), set_config('ecoraee.fecha_evento', '2026-10-20 09:00-05', false);
INSERT INTO lote (id_generador, fecha_registro, descripcion)
VALUES (3, '2026-10-20 09:00-05', 'Baja de equipos del laboratorio de redes');
INSERT INTO dispositivo (id_lote, id_categoria, id_marca, modelo, numero_serie, peso_kg, fecha_registro) VALUES
 (3, 8, 7, 'Catalyst 2960',    'CS2960-A1', 3.60, '2026-10-20 09:05-05'),  -- RAEE-2026-00011
 (3, 8, 7, 'Catalyst 2960',    'CS2960-A2', 3.60, '2026-10-20 09:06-05'),  -- RAEE-2026-00012
 (3, 2, 3, 'ThinkCentre M720', 'LTC720-55', 6.50, '2026-10-20 09:07-05'),  -- RAEE-2026-00013
 (3, 3, 9, 'V226HQL',          'AC226-901', 3.00, '2026-10-20 09:08-05');  -- RAEE-2026-00014
SELECT set_config('ecoraee.fecha_evento', '2026-10-21 10:30-05', false);
INSERT INTO solicitud_recoleccion (id_lote, id_solicitante, id_centro_destino, modalidad, fecha_solicitud, fecha_programada, estado)
VALUES (3, 3, 2, 'RECOLECCION', '2026-10-21 10:30-05', '2026-11-05', 'PROGRAMADA');

-- Lote 4 · campaña estudiantil (aún sin solicitud)
SELECT set_config('ecoraee.id_usuario', '2', false), set_config('ecoraee.fecha_evento', '2026-10-28 12:00-05', false);
INSERT INTO lote (id_generador, fecha_registro, descripcion)
VALUES (2, '2026-10-28 12:00-05', 'Campaña estudiantil de celulares y tablets');
INSERT INTO dispositivo (id_lote, id_categoria, id_marca, modelo, numero_serie, peso_kg, fecha_registro) VALUES
 (4, 5, 5, 'Galaxy A52',          NULL, 0.19, '2026-10-28 12:05-05'),  -- RAEE-2026-00015
 (4, 6, 4, 'iPad 6.ª generación', NULL, 0.47, '2026-10-28 12:06-05'),  -- RAEE-2026-00016
 (4, 5, 4, 'iPhone 8',            NULL, 0.15, '2026-10-28 12:07-05');  -- RAEE-2026-00017

-- Transferencia 3: la impresora no recuperable va al gestor (queda EN_TRANSITO)
SELECT set_config('ecoraee.id_usuario', '7', false), set_config('ecoraee.fecha_evento', '2026-10-30 08:30-05', false);
INSERT INTO transferencia (id_centro_origen, id_centro_destino, id_coordinador, id_arista, fecha_salida)
VALUES (1, 4, 7, 5, '2026-10-30 09:00-05');
INSERT INTO detalle_transferencia (id_transferencia, id_dispositivo) VALUES (3, 5);
SELECT set_config('ecoraee.fecha_evento', '2026-10-30 09:00-05', false);
CALL sp_despachar_transferencia(3);

-- Transferencia 4: proyector reparable al taller (queda PROGRAMADA)
SELECT set_config('ecoraee.fecha_evento', '2026-11-02 16:00-05', false);
INSERT INTO transferencia (id_centro_origen, id_centro_destino, id_coordinador, id_arista, fecha_salida)
VALUES (1, 3, 7, 4, '2026-11-04 09:00-05');
INSERT INTO detalle_transferencia (id_transferencia, id_dispositivo) VALUES (4, 6);

-- Evidencias (archivos de ejemplo en backend/storage, simulan claves de S3)
SELECT set_config('ecoraee.id_usuario', '6', false), set_config('ecoraee.fecha_evento', '2026-10-09 11:45-05', false);
INSERT INTO evidencia (tipo_evidencia, s3_key, hash_sha256, id_usuario_carga, fecha_carga, id_evaluacion)
VALUES ('INFORME', 'evidencias/2026/10/informe-tecnico-RAEE-2026-00005.txt',
        '858b605883c2dac127281375ef6449bd8ec12244308ae4484e55080338b05b17', 6, '2026-10-09 11:45-05', 5);
SELECT set_config('ecoraee.id_usuario', '5', false), set_config('ecoraee.fecha_evento', '2026-10-13 16:10-05', false);
INSERT INTO evidencia (tipo_evidencia, s3_key, hash_sha256, id_usuario_carga, fecha_carga, id_transferencia)
VALUES ('ACTA', 'evidencias/2026/10/acta-transferencia-T1.txt',
        'ab68bc80ce0ff35749f51a8e3751930eff38b1dd8adc4c4bcb109a593b1be256', 5, '2026-10-13 16:10-05', 1);
SELECT set_config('ecoraee.id_usuario', '7', false), set_config('ecoraee.fecha_evento', '2026-10-22 10:15-05', false);
INSERT INTO evidencia (tipo_evidencia, s3_key, hash_sha256, id_usuario_carga, fecha_carga, id_destino_final)
VALUES ('CERTIFICADO', 'evidencias/2026/10/certificado-donacion-RAEE-2026-00001.txt',
        '4839213060aea89e51f69ea0f10b5dad362f4392395014ad2abb7969ddf93d2f', 7, '2026-10-22 10:15-05', 2);

-- Limpieza de variables de sesión
SELECT set_config('ecoraee.id_usuario', '', false), set_config('ecoraee.fecha_evento', '', false);
