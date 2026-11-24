-- =====================================================================
--  EcoRAEE Cloud · Modelo físico
--  Motor: PostgreSQL 16 (compatible con Amazon RDS for PostgreSQL)
--  Proyecto Integrador · Ingeniería en Sistemas de Información · UIDE
--
--  Contenido:
--    1. Esquema y extensiones
--    2. Tablas (25) con PK, FK, UNIQUE y CHECK
--    3. Índices
--    4. Funciones auxiliares
--    5. Triggers de reglas de negocio (RN-01 … RN-08) y auditoría
--    6. Procedimientos almacenados (transferencias, RN-06)
--    7. Vistas de consulta
--
--  Cambios respecto al primer avance (observaciones de la docente):
--    * historial_estado es entidad débil: PK (id_dispositivo, nro_cambio),
--      donde nro_cambio es la clave parcial.
--    * Claves secundarias declaradas como UNIQUE: codigo_unico,
--      codigo_lote y email (insensible a mayúsculas).
--    * FK opcionales explícitas: dispositivo.id_marca y
--      dispositivo.id_centro_actual admiten NULL.
--
--  Cambios de la Parte III (códigos RAEE-AAAA-NNNNN y LOT-AAAA-NNNN):
--    * El año sale de fecha_registro (hora de Ecuador) y no del momento
--      del INSERT, y el correlativo vuelve a 1 cada año (tabla correlativo).
--    * Ya no se usan secuencias: un INSERT rechazado no deja huecos y el
--      número no se trunca al pasar de 99 999 (lpad cortaba el texto).
--    * Un mismo equipo físico (marca + número de serie) no puede estar
--      activo dos veces (índice único uq_dispositivo_serie).
--    * La base usa la zona horaria America/Guayaquil también en RDS.
-- =====================================================================

SET client_min_messages = warning;
DROP SCHEMA IF EXISTS ecoraee CASCADE;
CREATE SCHEMA ecoraee;
SET search_path TO ecoraee, public;

-- pgcrypto: hash bcrypt de contraseñas (crypt / gen_salt)
CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;

-- La base usa el esquema ecoraee por defecto (útil para psql, pgAdmin o Adminer)
-- y la hora de Ecuador (Amazon RDS trabaja en UTC si no se indica)
DO $$
BEGIN
  EXECUTE format('ALTER DATABASE %I SET search_path = ecoraee, public', current_database());
  EXECUTE format('ALTER DATABASE %I SET timezone = %L', current_database(), 'America/Guayaquil');
END $$;
SET timezone = 'America/Guayaquil';

-- =====================================================================
-- 2. TABLAS
-- =====================================================================

-- 1. organizacion -----------------------------------------------------
CREATE TABLE organizacion (
  id_organizacion   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  nombre            VARCHAR(150) NOT NULL,
  tipo_organizacion VARCHAR(30)  NOT NULL
    CONSTRAINT ck_organizacion_tipo CHECK (tipo_organizacion IN
      ('UNIVERSIDAD','FACULTAD','REACONDICIONADOR','GESTOR_RECICLAJE','BENEFICIARIA')),
  identificacion    VARCHAR(20)  NOT NULL,
  email_contacto    VARCHAR(120),
  telefono          VARCHAR(20),
  activo            BOOLEAN      NOT NULL DEFAULT TRUE,
  fecha_creacion    TIMESTAMPTZ  NOT NULL DEFAULT now(),
  CONSTRAINT uq_organizacion_identificacion UNIQUE (identificacion),
  CONSTRAINT ck_organizacion_email CHECK (email_contacto IS NULL OR email_contacto ~* '^[^@\s]+@[^@\s]+\.[^@\s]+$')
);

-- 2. rol (base de la especialización disjunta y parcial de USUARIO) ----
CREATE TABLE rol (
  id_rol      SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  codigo      VARCHAR(30)  NOT NULL,
  descripcion VARCHAR(200) NOT NULL,
  CONSTRAINT uq_rol_codigo UNIQUE (codigo)
);

-- 3. usuario ----------------------------------------------------------
CREATE TABLE usuario (
  id_usuario      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id_organizacion BIGINT      NOT NULL REFERENCES organizacion (id_organizacion),
  id_rol          SMALLINT    NOT NULL REFERENCES rol (id_rol),
  nombres         VARCHAR(80) NOT NULL,
  apellidos       VARCHAR(80) NOT NULL,
  email           VARCHAR(120) NOT NULL,
  password_hash   VARCHAR(255) NOT NULL,
  activo          BOOLEAN     NOT NULL DEFAULT TRUE,
  fecha_creacion  TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT ck_usuario_email CHECK (email ~* '^[^@\s]+@[^@\s]+\.[^@\s]+$')
);
-- Clave secundaria: email único sin importar mayúsculas
CREATE UNIQUE INDEX uq_usuario_email ON usuario (lower(email));

-- 4. tipo_centro ------------------------------------------------------
CREATE TABLE tipo_centro (
  id_tipo_centro SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  nombre         VARCHAR(40)  NOT NULL,
  descripcion    VARCHAR(200),
  CONSTRAINT uq_tipo_centro_nombre UNIQUE (nombre)
);

-- 5. centro -----------------------------------------------------------
CREATE TABLE centro (
  id_centro          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id_organizacion    BIGINT        NOT NULL REFERENCES organizacion (id_organizacion),
  id_tipo_centro     SMALLINT      NOT NULL REFERENCES tipo_centro (id_tipo_centro),
  nombre             VARCHAR(120)  NOT NULL,
  direccion          VARCHAR(200)  NOT NULL,
  ciudad             VARCHAR(60)   NOT NULL,
  capacidad_unidades INT           NOT NULL CONSTRAINT ck_centro_capacidad_unidades CHECK (capacidad_unidades > 0),
  capacidad_kg       NUMERIC(10,2) NOT NULL CONSTRAINT ck_centro_capacidad_kg CHECK (capacidad_kg > 0),
  activo             BOOLEAN       NOT NULL DEFAULT TRUE,
  CONSTRAINT uq_centro_nombre UNIQUE (nombre)
);

-- 6. categoria --------------------------------------------------------
CREATE TABLE categoria (
  id_categoria SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  nombre       VARCHAR(60)  NOT NULL,
  descripcion  VARCHAR(200),
  peligrosidad VARCHAR(10)  NOT NULL
    CONSTRAINT ck_categoria_peligrosidad CHECK (peligrosidad IN ('BAJA','MEDIA','ALTA')),
  CONSTRAINT uq_categoria_nombre UNIQUE (nombre)
);

-- 7. marca ------------------------------------------------------------
CREATE TABLE marca (
  id_marca SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  nombre   VARCHAR(60) NOT NULL,
  CONSTRAINT uq_marca_nombre UNIQUE (nombre)
);

-- 8. lote -------------------------------------------------------------
CREATE TABLE lote (
  id_lote        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  codigo_lote    VARCHAR(20)  NOT NULL,   -- lo asigna trg_lote_reglas (RN-01)
  id_generador   BIGINT       NOT NULL REFERENCES usuario (id_usuario),
  fecha_registro TIMESTAMPTZ  NOT NULL DEFAULT now(),
  descripcion    VARCHAR(250),
  estado         VARCHAR(20)  NOT NULL DEFAULT 'REGISTRADO'
    CONSTRAINT ck_lote_estado CHECK (estado IN ('REGISTRADO','SOLICITADO','RECIBIDO','CERRADO')),
  CONSTRAINT uq_lote_codigo UNIQUE (codigo_lote),                       -- clave secundaria (RN-01)
  CONSTRAINT ck_lote_codigo_formato CHECK (codigo_lote ~ '^LOT-[0-9]{4}-[0-9]{4,}$')
);

-- 9. dispositivo ------------------------------------------------------
CREATE TABLE dispositivo (
  id_dispositivo   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  codigo_unico     VARCHAR(25)  NOT NULL,   -- lo asigna trg_dispositivo_reglas (RN-01)
  id_lote          BIGINT       NOT NULL REFERENCES lote (id_lote),
  id_categoria     SMALLINT     NOT NULL REFERENCES categoria (id_categoria),
  id_marca         SMALLINT              REFERENCES marca (id_marca),       -- FK opcional
  id_centro_actual BIGINT                REFERENCES centro (id_centro),     -- FK opcional (NULL hasta la recepción)
  modelo           VARCHAR(80),
  numero_serie     VARCHAR(60),
  peso_kg          NUMERIC(7,2) NOT NULL CONSTRAINT ck_dispositivo_peso CHECK (peso_kg > 0),
  estado_actual    VARCHAR(20)  NOT NULL DEFAULT 'REGISTRADO'
    CONSTRAINT ck_dispositivo_estado CHECK (estado_actual IN
      ('REGISTRADO','RECIBIDO','EVALUADO','EN_TRANSITO','TRANSFERIDO','CERRADO')),
  clasificacion    VARCHAR(20)
    CONSTRAINT ck_dispositivo_clasificacion CHECK (clasificacion IN
      ('REUTILIZABLE','REPARABLE','RECICLABLE','NO_RECUPERABLE')),
  fecha_registro   TIMESTAMPTZ  NOT NULL DEFAULT now(),
  CONSTRAINT uq_dispositivo_codigo UNIQUE (codigo_unico),               -- clave secundaria (RN-01)
  CONSTRAINT ck_dispositivo_codigo_formato CHECK (codigo_unico ~ '^RAEE-[0-9]{4}-[0-9]{5,}$')
);

-- 10. solicitud_recoleccion ------------------------------------------
CREATE TABLE solicitud_recoleccion (
  id_solicitud      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id_lote           BIGINT      NOT NULL REFERENCES lote (id_lote),
  id_solicitante    BIGINT      NOT NULL REFERENCES usuario (id_usuario),
  id_centro_destino BIGINT      NOT NULL REFERENCES centro (id_centro),
  modalidad         VARCHAR(15) NOT NULL
    CONSTRAINT ck_solicitud_modalidad CHECK (modalidad IN ('RECOLECCION','ENTREGA')),
  fecha_solicitud   TIMESTAMPTZ NOT NULL DEFAULT now(),
  fecha_programada  DATE,
  estado            VARCHAR(15) NOT NULL DEFAULT 'PENDIENTE'
    CONSTRAINT ck_solicitud_estado CHECK (estado IN ('PENDIENTE','PROGRAMADA','ATENDIDA','CANCELADA')),
  CONSTRAINT ck_solicitud_programada CHECK (estado <> 'PROGRAMADA' OR fecha_programada IS NOT NULL)
);
-- Un lote solo puede tener una solicitud activa a la vez (las reprogramaciones cancelan la anterior)
CREATE UNIQUE INDEX uq_solicitud_lote_activa ON solicitud_recoleccion (id_lote)
  WHERE estado IN ('PENDIENTE','PROGRAMADA');

-- 11. recepcion -------------------------------------------------------
CREATE TABLE recepcion (
  id_recepcion     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id_solicitud     BIGINT        NOT NULL REFERENCES solicitud_recoleccion (id_solicitud),
  id_centro        BIGINT        NOT NULL REFERENCES centro (id_centro),
  id_operador      BIGINT        NOT NULL REFERENCES usuario (id_usuario),
  fecha_recepcion  TIMESTAMPTZ   NOT NULL DEFAULT now(),
  peso_recibido_kg NUMERIC(10,2) CONSTRAINT ck_recepcion_peso CHECK (peso_recibido_kg > 0),
  observaciones    VARCHAR(300),
  CONSTRAINT uq_recepcion_solicitud UNIQUE (id_solicitud)               -- relación 1:1
);

-- 12. evaluacion_tecnica ---------------------------------------------
CREATE TABLE evaluacion_tecnica (
  id_evaluacion    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id_dispositivo   BIGINT      NOT NULL REFERENCES dispositivo (id_dispositivo),
  id_tecnico       BIGINT      NOT NULL REFERENCES usuario (id_usuario),
  fecha_evaluacion TIMESTAMPTZ NOT NULL DEFAULT now(),
  condicion        VARCHAR(15) NOT NULL
    CONSTRAINT ck_evaluacion_condicion CHECK (condicion IN ('FUNCIONAL','CON_FALLAS','DANADO','INSERVIBLE')),
  clasificacion    VARCHAR(20) NOT NULL
    CONSTRAINT ck_evaluacion_clasificacion CHECK (clasificacion IN
      ('REUTILIZABLE','REPARABLE','RECICLABLE','NO_RECUPERABLE')),
  borrado_datos    BOOLEAN     NOT NULL DEFAULT FALSE,
  observaciones    VARCHAR(300)
);

-- 13. historial_estado (ENTIDAD DÉBIL, dueño: dispositivo) -------------
--     Se identifica por la PK del dueño + la clave parcial nro_cambio.
CREATE TABLE historial_estado (
  id_dispositivo  BIGINT      NOT NULL REFERENCES dispositivo (id_dispositivo) ON DELETE CASCADE,
  nro_cambio      INT         NOT NULL CONSTRAINT ck_historial_nro CHECK (nro_cambio > 0),
  estado_anterior VARCHAR(20),
  estado_nuevo    VARCHAR(20) NOT NULL,
  id_usuario      BIGINT      REFERENCES usuario (id_usuario) ON DELETE SET NULL,
  fecha_cambio    TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT pk_historial_estado PRIMARY KEY (id_dispositivo, nro_cambio)
);

-- 14. inventario (asociativa N:M centro–categoría) ----------------------
CREATE TABLE inventario (
  id_centro           BIGINT        NOT NULL REFERENCES centro (id_centro) ON DELETE CASCADE,
  id_categoria        SMALLINT      NOT NULL REFERENCES categoria (id_categoria),
  cantidad_unidades   INT           NOT NULL DEFAULT 0 CONSTRAINT ck_inventario_cantidad CHECK (cantidad_unidades >= 0),
  peso_total_kg       NUMERIC(10,2) NOT NULL DEFAULT 0 CONSTRAINT ck_inventario_peso CHECK (peso_total_kg >= 0),
  fecha_actualizacion TIMESTAMPTZ   NOT NULL DEFAULT now(),
  CONSTRAINT pk_inventario PRIMARY KEY (id_centro, id_categoria)
);

-- 19. escenario_red ----------------------------------------------------
CREATE TABLE escenario_red (
  id_escenario   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  nombre         VARCHAR(80)  NOT NULL,
  periodo_inicio DATE         NOT NULL,
  periodo_fin    DATE         NOT NULL,
  unidad_medida  VARCHAR(10)  NOT NULL
    CONSTRAINT ck_escenario_unidad CHECK (unidad_medida IN ('UNIDADES','KG')),
  descripcion    VARCHAR(250),
  CONSTRAINT ck_escenario_periodo CHECK (periodo_fin >= periodo_inicio)
);

-- 20. nodo_red ---------------------------------------------------------
CREATE TABLE nodo_red (
  id_nodo      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id_escenario BIGINT      NOT NULL REFERENCES escenario_red (id_escenario) ON DELETE CASCADE,
  id_centro    BIGINT               REFERENCES centro (id_centro),        -- NULL: nodo lógico (p. ej. punto de tránsito)
  etiqueta     VARCHAR(20) NOT NULL,
  tipo_nodo    VARCHAR(12) NOT NULL
    CONSTRAINT ck_nodo_tipo CHECK (tipo_nodo IN ('FUENTE','INTERMEDIO','SUMIDERO')),
  CONSTRAINT uq_nodo_escenario UNIQUE (id_nodo, id_escenario),          -- destino de la FK compuesta
  CONSTRAINT uq_nodo_etiqueta UNIQUE (id_escenario, etiqueta)
);
CREATE UNIQUE INDEX uq_nodo_centro_escenario ON nodo_red (id_escenario, id_centro) WHERE id_centro IS NOT NULL;

-- 21. arista_red (grafo dirigido G = (V, E)) ---------------------------
CREATE TABLE arista_red (
  id_arista       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id_escenario    BIGINT        NOT NULL REFERENCES escenario_red (id_escenario) ON DELETE CASCADE,
  id_nodo_origen  BIGINT        NOT NULL,
  id_nodo_destino BIGINT        NOT NULL,
  capacidad       NUMERIC(10,2) NOT NULL CONSTRAINT ck_arista_capacidad CHECK (capacidad > 0),
  -- FK compuestas: impiden unir nodos de escenarios distintos
  CONSTRAINT fk_arista_origen  FOREIGN KEY (id_nodo_origen,  id_escenario) REFERENCES nodo_red (id_nodo, id_escenario) ON DELETE CASCADE,
  CONSTRAINT fk_arista_destino FOREIGN KEY (id_nodo_destino, id_escenario) REFERENCES nodo_red (id_nodo, id_escenario) ON DELETE CASCADE,
  CONSTRAINT ck_arista_sin_bucle CHECK (id_nodo_origen <> id_nodo_destino),
  CONSTRAINT uq_arista UNIQUE (id_escenario, id_nodo_origen, id_nodo_destino)
);

-- 15. transferencia ---------------------------------------------------
CREATE TABLE transferencia (
  id_transferencia  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id_centro_origen  BIGINT      NOT NULL REFERENCES centro (id_centro),
  id_centro_destino BIGINT      NOT NULL REFERENCES centro (id_centro),
  id_coordinador    BIGINT      NOT NULL REFERENCES usuario (id_usuario),
  id_responsable    BIGINT               REFERENCES usuario (id_usuario),
  id_arista         BIGINT               REFERENCES arista_red (id_arista) ON DELETE SET NULL,
  fecha_salida      TIMESTAMPTZ NOT NULL DEFAULT now(),
  fecha_recepcion   TIMESTAMPTZ,
  estado            VARCHAR(15) NOT NULL DEFAULT 'PROGRAMADA'
    CONSTRAINT ck_transferencia_estado CHECK (estado IN ('PROGRAMADA','EN_TRANSITO','CERRADA','CANCELADA')),
  CONSTRAINT ck_transferencia_centros CHECK (id_centro_origen <> id_centro_destino),
  -- RN-03: una transferencia solo se cierra con responsable y fecha de recepción
  CONSTRAINT ck_transferencia_cierre CHECK (estado <> 'CERRADA' OR (id_responsable IS NOT NULL AND fecha_recepcion IS NOT NULL)),
  CONSTRAINT ck_transferencia_fechas CHECK (fecha_recepcion IS NULL OR fecha_recepcion >= fecha_salida)
);

-- 16. detalle_transferencia (asociativa N:M) ---------------------------
CREATE TABLE detalle_transferencia (
  id_transferencia BIGINT NOT NULL REFERENCES transferencia (id_transferencia) ON DELETE CASCADE,
  id_dispositivo   BIGINT NOT NULL REFERENCES dispositivo (id_dispositivo),
  CONSTRAINT pk_detalle_transferencia PRIMARY KEY (id_transferencia, id_dispositivo)
);

-- 17. destino_final ---------------------------------------------------
CREATE TABLE destino_final (
  id_destino_final    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id_dispositivo      BIGINT      NOT NULL REFERENCES dispositivo (id_dispositivo),
  id_centro           BIGINT      NOT NULL REFERENCES centro (id_centro),
  id_org_beneficiaria BIGINT               REFERENCES organizacion (id_organizacion),
  tipo_destino        VARCHAR(25) NOT NULL
    CONSTRAINT ck_destino_tipo CHECK (tipo_destino IN
      ('REUTILIZACION','REACONDICIONAMIENTO','RECICLAJE','DISPOSICION_FINAL','DONACION')),
  fecha_confirmacion  TIMESTAMPTZ NOT NULL DEFAULT now(),
  id_usuario_confirma BIGINT      NOT NULL REFERENCES usuario (id_usuario),
  CONSTRAINT uq_destino_dispositivo UNIQUE (id_dispositivo),            -- RN-08: un único cierre por equipo
  CONSTRAINT ck_destino_beneficiaria CHECK (tipo_destino <> 'DONACION' OR id_org_beneficiaria IS NOT NULL)
);

-- 18. evidencia (arco exclusivo) ---------------------------------------
CREATE TABLE evidencia (
  id_evidencia     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  tipo_evidencia   VARCHAR(15)  NOT NULL
    CONSTRAINT ck_evidencia_tipo CHECK (tipo_evidencia IN ('FOTO','ACTA','INFORME','CERTIFICADO')),
  s3_key           VARCHAR(300) NOT NULL,
  hash_sha256      CHAR(64)     NOT NULL CONSTRAINT ck_evidencia_hash CHECK (hash_sha256 ~ '^[0-9a-f]{64}$'),
  id_usuario_carga BIGINT       NOT NULL REFERENCES usuario (id_usuario),
  fecha_carga      TIMESTAMPTZ  NOT NULL DEFAULT now(),
  id_dispositivo   BIGINT REFERENCES dispositivo (id_dispositivo),
  id_evaluacion    BIGINT REFERENCES evaluacion_tecnica (id_evaluacion),
  id_transferencia BIGINT REFERENCES transferencia (id_transferencia),
  id_destino_final BIGINT REFERENCES destino_final (id_destino_final),
  CONSTRAINT uq_evidencia_s3_key UNIQUE (s3_key),
  -- RN-07: cada evidencia respalda exactamente un hecho
  CONSTRAINT ck_evidencia_arco CHECK (num_nonnulls(id_dispositivo, id_evaluacion, id_transferencia, id_destino_final) = 1)
);

-- 22. resultado_flujo --------------------------------------------------
CREATE TABLE resultado_flujo (
  id_resultado    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  id_escenario    BIGINT        NOT NULL REFERENCES escenario_red (id_escenario) ON DELETE CASCADE,
  algoritmo       VARCHAR(30)   NOT NULL,
  flujo_maximo    NUMERIC(12,2) NOT NULL CONSTRAINT ck_resultado_flujo CHECK (flujo_maximo >= 0),
  fecha_ejecucion TIMESTAMPTZ   NOT NULL DEFAULT now(),
  id_ejecutor     BIGINT        REFERENCES usuario (id_usuario) ON DELETE SET NULL
);

-- 23. flujo_arista (asociativa N:M resultado–arista) ---------------------
CREATE TABLE flujo_arista (
  id_resultado    BIGINT        NOT NULL REFERENCES resultado_flujo (id_resultado) ON DELETE CASCADE,
  id_arista       BIGINT        NOT NULL REFERENCES arista_red (id_arista) ON DELETE CASCADE,
  flujo           NUMERIC(10,2) NOT NULL CONSTRAINT ck_flujo_no_negativo CHECK (flujo >= 0),
  saturada        BOOLEAN       NOT NULL,
  en_corte_minimo BOOLEAN       NOT NULL,
  CONSTRAINT pk_flujo_arista PRIMARY KEY (id_resultado, id_arista)
);

-- 24. auditoria --------------------------------------------------------
CREATE TABLE auditoria (
  id_auditoria  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  tabla         VARCHAR(40) NOT NULL,
  operacion     CHAR(1)     NOT NULL CONSTRAINT ck_auditoria_operacion CHECK (operacion IN ('I','U','D')),
  id_registro   BIGINT      NOT NULL,
  id_usuario    BIGINT      REFERENCES usuario (id_usuario) ON DELETE SET NULL,
  fecha         TIMESTAMPTZ NOT NULL DEFAULT now(),
  datos_antes   JSONB,
  datos_despues JSONB
);

-- 25. correlativo (contador anual de los códigos legibles, RN-01) -------
-- Reemplaza a las secuencias: se actualiza dentro de la misma transacción
-- del INSERT, así que un registro rechazado no consume número.
CREATE TABLE correlativo (
  entidad VARCHAR(15) NOT NULL CONSTRAINT ck_correlativo_entidad CHECK (entidad IN ('LOTE','DISPOSITIVO')),
  anio    SMALLINT    NOT NULL CONSTRAINT ck_correlativo_anio CHECK (anio BETWEEN 2000 AND 2999),
  ultimo  INT         NOT NULL CONSTRAINT ck_correlativo_ultimo CHECK (ultimo > 0),
  CONSTRAINT pk_correlativo PRIMARY KEY (entidad, anio)
);

-- =====================================================================
-- 3. ÍNDICES (claves foráneas y búsquedas frecuentes)
-- =====================================================================
-- RN-01: un mismo equipo físico (marca + número de serie) no puede estar activo
-- dos veces. Un equipo CERRADO sí puede volver a ingresar como un RAEE nuevo.
CREATE UNIQUE INDEX uq_dispositivo_serie ON dispositivo (COALESCE(id_marca, 0), upper(numero_serie))
  WHERE numero_serie IS NOT NULL AND estado_actual <> 'CERRADO';
CREATE INDEX ix_usuario_organizacion       ON usuario (id_organizacion);
CREATE INDEX ix_usuario_rol                ON usuario (id_rol);
CREATE INDEX ix_centro_organizacion        ON centro (id_organizacion);
CREATE INDEX ix_lote_generador             ON lote (id_generador);
CREATE INDEX ix_dispositivo_lote           ON dispositivo (id_lote);
CREATE INDEX ix_dispositivo_centro_estado  ON dispositivo (id_centro_actual, estado_actual);
CREATE INDEX ix_dispositivo_categoria      ON dispositivo (id_categoria);
CREATE INDEX ix_dispositivo_clasificacion  ON dispositivo (clasificacion);
CREATE INDEX ix_solicitud_lote             ON solicitud_recoleccion (id_lote);
CREATE INDEX ix_solicitud_centro_estado    ON solicitud_recoleccion (id_centro_destino, estado);
CREATE INDEX ix_recepcion_centro           ON recepcion (id_centro);
CREATE INDEX ix_evaluacion_dispositivo     ON evaluacion_tecnica (id_dispositivo, fecha_evaluacion DESC);
CREATE INDEX ix_evaluacion_tecnico         ON evaluacion_tecnica (id_tecnico);
CREATE INDEX ix_historial_fecha            ON historial_estado (fecha_cambio DESC);
CREATE INDEX ix_transferencia_origen       ON transferencia (id_centro_origen, estado);
CREATE INDEX ix_transferencia_destino      ON transferencia (id_centro_destino, estado);
CREATE INDEX ix_detalle_dispositivo        ON detalle_transferencia (id_dispositivo);
CREATE INDEX ix_destino_centro             ON destino_final (id_centro);
CREATE INDEX ix_evidencia_dispositivo      ON evidencia (id_dispositivo)   WHERE id_dispositivo   IS NOT NULL;
CREATE INDEX ix_evidencia_evaluacion       ON evidencia (id_evaluacion)    WHERE id_evaluacion    IS NOT NULL;
CREATE INDEX ix_evidencia_transferencia    ON evidencia (id_transferencia) WHERE id_transferencia IS NOT NULL;
CREATE INDEX ix_evidencia_destino          ON evidencia (id_destino_final) WHERE id_destino_final IS NOT NULL;
CREATE INDEX ix_arista_escenario           ON arista_red (id_escenario);
CREATE INDEX ix_resultado_escenario        ON resultado_flujo (id_escenario, fecha_ejecucion DESC);
CREATE INDEX ix_auditoria_tabla_registro   ON auditoria (tabla, id_registro);
CREATE INDEX ix_auditoria_fecha            ON auditoria (fecha DESC);

-- =====================================================================
-- 4. FUNCIONES AUXILIARES
-- =====================================================================

-- Usuario que realiza la operación (lo fija la API con set_config en cada transacción)
CREATE OR REPLACE FUNCTION fn_usuario_actual() RETURNS BIGINT
LANGUAGE sql STABLE SET search_path = ecoraee, public AS $$
  SELECT NULLIF(current_setting('ecoraee.id_usuario', true), '')::BIGINT
$$;

-- Fecha del evento: now() en operación normal; los datos sintéticos pueden fijar otra fecha
CREATE OR REPLACE FUNCTION fn_fecha_evento() RETURNS TIMESTAMPTZ
LANGUAGE sql STABLE SET search_path = ecoraee, public AS $$
  SELECT COALESCE(NULLIF(current_setting('ecoraee.fecha_evento', true), '')::TIMESTAMPTZ, now())
$$;

-- Siguiente código legible (RN-01): PREFIJO-AAAA-NNNNN, con el año de la fecha de
-- registro en hora de Ecuador y un correlativo que vuelve a 1 cada año.
CREATE OR REPLACE FUNCTION fn_siguiente_codigo(p_entidad TEXT, p_prefijo TEXT, p_fecha TIMESTAMPTZ, p_digitos INT)
RETURNS TEXT LANGUAGE plpgsql SET search_path = ecoraee, public AS $$
DECLARE
  v_anio INT := EXTRACT(YEAR FROM p_fecha AT TIME ZONE 'America/Guayaquil');
  v_n    INT;
BEGIN
  INSERT INTO correlativo (entidad, anio, ultimo) VALUES (p_entidad, v_anio, 1)
  ON CONFLICT (entidad, anio) DO UPDATE SET ultimo = correlativo.ultimo + 1
  RETURNING ultimo INTO v_n;
  -- lpad corta el texto si es más largo que el ancho: por eso el ancho crece con el número
  RETURN p_prefijo || '-' || v_anio || '-' || lpad(v_n::text, greatest(p_digitos, length(v_n::text)), '0');
END $$;

-- ¿El usuario existe, está activo y tiene el rol indicado?
CREATE OR REPLACE FUNCTION fn_tiene_rol(p_usuario BIGINT, p_roles TEXT[]) RETURNS BOOLEAN
LANGUAGE sql STABLE SET search_path = ecoraee, public AS $$
  SELECT EXISTS (
    SELECT 1 FROM usuario u JOIN rol r ON r.id_rol = u.id_rol
     WHERE u.id_usuario = p_usuario AND u.activo AND r.codigo = ANY (p_roles)
  )
$$;

-- Suma/resta existencias de un centro y valida su capacidad (RN-06)
CREATE OR REPLACE FUNCTION fn_ajustar_inventario(p_centro BIGINT, p_categoria SMALLINT, p_unidades INT, p_kg NUMERIC)
RETURNS void LANGUAGE plpgsql SET search_path = ecoraee, public AS $$
DECLARE
  v_total_u INT; v_total_kg NUMERIC; v_centro centro%ROWTYPE;
BEGIN
  IF p_unidades < 0 THEN
    -- Salida: descuenta (el CHECK >= 0 impide existencias negativas)
    UPDATE inventario
       SET cantidad_unidades   = cantidad_unidades + p_unidades,
           peso_total_kg       = peso_total_kg + p_kg,
           fecha_actualizacion = now()
     WHERE id_centro = p_centro AND id_categoria = p_categoria;
    IF NOT FOUND THEN
      RAISE EXCEPTION 'Inventario inconsistente: no hay existencias de la categoría % en el centro %.', p_categoria, p_centro;
    END IF;
  ELSE
    -- Entrada: crea la fila centro–categoría si aún no existe
    INSERT INTO inventario AS i (id_centro, id_categoria, cantidad_unidades, peso_total_kg, fecha_actualizacion)
    VALUES (p_centro, p_categoria, p_unidades, p_kg, now())
    ON CONFLICT (id_centro, id_categoria) DO UPDATE
       SET cantidad_unidades   = i.cantidad_unidades + EXCLUDED.cantidad_unidades,
           peso_total_kg       = i.peso_total_kg + EXCLUDED.peso_total_kg,
           fecha_actualizacion = now();
  END IF;

  IF p_unidades > 0 THEN
    SELECT * INTO v_centro FROM centro WHERE id_centro = p_centro;
    SELECT COALESCE(SUM(cantidad_unidades), 0), COALESCE(SUM(peso_total_kg), 0)
      INTO v_total_u, v_total_kg FROM inventario WHERE id_centro = p_centro;
    IF v_total_u > v_centro.capacidad_unidades OR v_total_kg > v_centro.capacidad_kg THEN
      RAISE EXCEPTION 'El centro "%" superaría su capacidad (% de % unidades; % de % kg).',
        v_centro.nombre, v_total_u, v_centro.capacidad_unidades, v_total_kg, v_centro.capacidad_kg;
    END IF;
  END IF;
END $$;

-- =====================================================================
-- 5. TRIGGERS DE REGLAS DE NEGOCIO
-- =====================================================================

-- ---------- RN-01: historial automático de estados -------------------
CREATE OR REPLACE FUNCTION fn_trg_historial_estado() RETURNS trigger
LANGUAGE plpgsql SET search_path = ecoraee, public AS $$
BEGIN
  IF TG_OP = 'INSERT' OR NEW.estado_actual IS DISTINCT FROM OLD.estado_actual THEN
    INSERT INTO historial_estado (id_dispositivo, nro_cambio, estado_anterior, estado_nuevo, id_usuario, fecha_cambio)
    VALUES (NEW.id_dispositivo,
            COALESCE((SELECT MAX(nro_cambio) FROM historial_estado WHERE id_dispositivo = NEW.id_dispositivo), 0) + 1,
            CASE WHEN TG_OP = 'UPDATE' THEN OLD.estado_actual END,
            NEW.estado_actual,
            fn_usuario_actual(),
            fn_fecha_evento());
  END IF;
  RETURN NULL;
END $$;
CREATE TRIGGER trg_historial_estado
  AFTER INSERT OR UPDATE OF estado_actual ON dispositivo
  FOR EACH ROW EXECUTE FUNCTION fn_trg_historial_estado();

-- ---------- Dispositivo: reglas de alta, cambios y bajas -------------
CREATE OR REPLACE FUNCTION fn_trg_dispositivo_reglas() RETURNS trigger
LANGUAGE plpgsql SET search_path = ecoraee, public AS $$
DECLARE v_estado_lote TEXT;
BEGIN
  IF TG_OP = 'INSERT' THEN
    SELECT estado INTO v_estado_lote FROM lote WHERE id_lote = NEW.id_lote;
    IF v_estado_lote NOT IN ('REGISTRADO','SOLICITADO') THEN
      RAISE EXCEPTION 'Solo se agregan dispositivos a lotes que aún no han sido recibidos (el lote está %).', v_estado_lote;
    END IF;
    NEW.codigo_unico := fn_siguiente_codigo('DISPOSITIVO', 'RAEE', NEW.fecha_registro, 5);  -- RN-01
    RETURN NEW;
  END IF;

  -- RN-08: un equipo cerrado ya no admite cambios
  IF OLD.estado_actual = 'CERRADO' THEN
    RAISE EXCEPTION 'RN-08: el dispositivo % ya cerró su trazabilidad y no admite cambios.', OLD.codigo_unico;
  END IF;

  IF TG_OP = 'DELETE' THEN
    IF OLD.estado_actual <> 'REGISTRADO' THEN
      RAISE EXCEPTION 'Solo se eliminan dispositivos en estado REGISTRADO; el dispositivo % ya forma parte de la trazabilidad (%).',
        OLD.codigo_unico, OLD.estado_actual;
    END IF;
    RETURN OLD;
  END IF;

  IF NEW.id_lote <> OLD.id_lote AND OLD.estado_actual <> 'REGISTRADO' THEN
    RAISE EXCEPTION 'No se puede cambiar el lote de un dispositivo que ya fue recibido.';
  END IF;
  IF NEW.codigo_unico <> OLD.codigo_unico THEN
    RAISE EXCEPTION 'RN-01: el código único % no se puede modificar.', OLD.codigo_unico;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_dispositivo_reglas
  BEFORE INSERT OR UPDATE OR DELETE ON dispositivo
  FOR EACH ROW EXECUTE FUNCTION fn_trg_dispositivo_reglas();

-- ---------- RN-06: inventario siempre sincronizado ---------------------
-- Cuenta en el inventario de su centro todo equipo recibido que no esté cerrado.
CREATE OR REPLACE FUNCTION fn_trg_inventario_dispositivo() RETURNS trigger
LANGUAGE plpgsql SET search_path = ecoraee, public AS $$
DECLARE v_old BOOLEAN := FALSE; v_new BOOLEAN := FALSE;
BEGIN
  IF TG_OP IN ('UPDATE','DELETE') THEN
    v_old := OLD.id_centro_actual IS NOT NULL AND OLD.estado_actual NOT IN ('REGISTRADO','CERRADO');
  END IF;
  IF TG_OP IN ('INSERT','UPDATE') THEN
    v_new := NEW.id_centro_actual IS NOT NULL AND NEW.estado_actual NOT IN ('REGISTRADO','CERRADO');
  END IF;
  IF TG_OP = 'UPDATE' AND v_old AND v_new
     AND OLD.id_centro_actual = NEW.id_centro_actual
     AND OLD.id_categoria = NEW.id_categoria AND OLD.peso_kg = NEW.peso_kg THEN
    RETURN NULL;  -- nada cambió para el inventario
  END IF;
  IF v_old THEN PERFORM fn_ajustar_inventario(OLD.id_centro_actual, OLD.id_categoria, -1, -OLD.peso_kg); END IF;
  IF v_new THEN PERFORM fn_ajustar_inventario(NEW.id_centro_actual, NEW.id_categoria,  1,  NEW.peso_kg); END IF;
  RETURN NULL;
END $$;
CREATE TRIGGER trg_inventario_dispositivo
  AFTER INSERT OR UPDATE OF id_centro_actual, estado_actual, id_categoria, peso_kg OR DELETE ON dispositivo
  FOR EACH ROW EXECUTE FUNCTION fn_trg_inventario_dispositivo();

-- ---------- Lote: solo se elimina mientras no avance -------------------
CREATE OR REPLACE FUNCTION fn_trg_lote_reglas() RETURNS trigger
LANGUAGE plpgsql SET search_path = ecoraee, public AS $$
BEGIN
  IF TG_OP = 'DELETE' AND OLD.estado <> 'REGISTRADO' THEN
    RAISE EXCEPTION 'El lote % no se puede eliminar porque ya está en estado %.', OLD.codigo_lote, OLD.estado;
  END IF;
  IF TG_OP = 'UPDATE' AND NEW.codigo_lote <> OLD.codigo_lote THEN
    RAISE EXCEPTION 'RN-01: el código de lote % no se puede modificar.', OLD.codigo_lote;
  END IF;
  IF TG_OP = 'UPDATE' AND NEW.id_generador <> OLD.id_generador AND NOT fn_tiene_rol(NEW.id_generador, ARRAY['GENERADOR']) THEN
    RAISE EXCEPTION 'El usuario % no es un generador activo.', NEW.id_generador;
  END IF;
  IF TG_OP = 'INSERT' AND NOT fn_tiene_rol(NEW.id_generador, ARRAY['GENERADOR']) THEN
    RAISE EXCEPTION 'Solo los usuarios GENERADOR activos registran lotes (usuario %).', NEW.id_generador;
  END IF;
  IF TG_OP = 'INSERT' THEN
    NEW.codigo_lote := fn_siguiente_codigo('LOTE', 'LOT', NEW.fecha_registro, 4);  -- RN-01
  END IF;
  RETURN COALESCE(NEW, OLD);
END $$;
CREATE TRIGGER trg_lote_reglas
  BEFORE INSERT OR UPDATE OR DELETE ON lote
  FOR EACH ROW EXECUTE FUNCTION fn_trg_lote_reglas();

-- ---------- Solicitudes de recolección ---------------------------------
CREATE OR REPLACE FUNCTION fn_trg_solicitud_reglas() RETURNS trigger
LANGUAGE plpgsql SET search_path = ecoraee, public AS $$
DECLARE v_lote lote%ROWTYPE; v_n INT;
BEGIN
  IF TG_OP = 'INSERT' THEN
    SELECT * INTO v_lote FROM lote WHERE id_lote = NEW.id_lote;
    IF v_lote.estado NOT IN ('REGISTRADO','SOLICITADO') THEN
      RAISE EXCEPTION 'El lote % ya fue recibido; no admite nuevas solicitudes.', v_lote.codigo_lote;
    END IF;
    SELECT count(*) INTO v_n FROM dispositivo WHERE id_lote = NEW.id_lote;
    IF v_n = 0 THEN
      RAISE EXCEPTION 'El lote % no tiene dispositivos registrados.', v_lote.codigo_lote;
    END IF;
    IF NOT fn_tiene_rol(NEW.id_solicitante, ARRAY['GENERADOR','COORDINADOR_LOGISTICO']) THEN
      RAISE EXCEPTION 'El usuario % no puede solicitar recolecciones (requiere GENERADOR o COORDINADOR_LOGISTICO activo).', NEW.id_solicitante;
    END IF;
    RETURN NEW;
  END IF;

  IF OLD.estado IN ('ATENDIDA','CANCELADA') AND TG_OP = 'UPDATE' THEN
    RAISE EXCEPTION 'La solicitud % ya está % y no se puede modificar.', OLD.id_solicitud, OLD.estado;
  END IF;
  IF TG_OP = 'UPDATE' AND NEW.estado = 'ATENDIDA' AND current_setting('ecoraee.origen_recepcion', true) IS DISTINCT FROM 'si' THEN
    RAISE EXCEPTION 'Una solicitud pasa a ATENDIDA solo al registrar su recepción.';
  END IF;
  IF TG_OP = 'DELETE' AND OLD.estado = 'ATENDIDA' THEN
    RAISE EXCEPTION 'La solicitud % ya fue atendida y forma parte de la trazabilidad.', OLD.id_solicitud;
  END IF;
  RETURN COALESCE(NEW, OLD);
END $$;
CREATE TRIGGER trg_solicitud_reglas
  BEFORE INSERT OR UPDATE OR DELETE ON solicitud_recoleccion
  FOR EACH ROW EXECUTE FUNCTION fn_trg_solicitud_reglas();

-- Mantiene el estado del lote según sus solicitudes activas
CREATE OR REPLACE FUNCTION fn_trg_solicitud_estado_lote() RETURNS trigger
LANGUAGE plpgsql SET search_path = ecoraee, public AS $$
DECLARE v_lote BIGINT := COALESCE(NEW.id_lote, OLD.id_lote);
BEGIN
  UPDATE lote l
     SET estado = CASE WHEN EXISTS (SELECT 1 FROM solicitud_recoleccion s
                                     WHERE s.id_lote = l.id_lote AND s.estado IN ('PENDIENTE','PROGRAMADA'))
                       THEN 'SOLICITADO' ELSE 'REGISTRADO' END
   WHERE l.id_lote = v_lote AND l.estado IN ('REGISTRADO','SOLICITADO');
  RETURN NULL;
END $$;
CREATE TRIGGER trg_solicitud_estado_lote
  AFTER INSERT OR UPDATE OF estado OR DELETE ON solicitud_recoleccion
  FOR EACH ROW EXECUTE FUNCTION fn_trg_solicitud_estado_lote();

-- ---------- Recepción física del lote ----------------------------------
CREATE OR REPLACE FUNCTION fn_trg_recepcion_reglas() RETURNS trigger
LANGUAGE plpgsql SET search_path = ecoraee, public AS $$
DECLARE v_sol solicitud_recoleccion%ROWTYPE;
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'Una recepción registrada no se elimina: forma parte de la trazabilidad (corrija con observaciones).';
  END IF;
  IF TG_OP = 'UPDATE' THEN
    IF NEW.id_solicitud <> OLD.id_solicitud OR NEW.id_centro <> OLD.id_centro THEN
      RAISE EXCEPTION 'No se puede cambiar la solicitud ni el centro de una recepción ya registrada.';
    END IF;
    RETURN NEW;
  END IF;

  SELECT * INTO v_sol FROM solicitud_recoleccion WHERE id_solicitud = NEW.id_solicitud;
  IF v_sol.estado NOT IN ('PENDIENTE','PROGRAMADA') THEN
    RAISE EXCEPTION 'La solicitud % está % y no se puede recibir.', NEW.id_solicitud, v_sol.estado;
  END IF;
  IF NEW.id_centro <> v_sol.id_centro_destino THEN
    RAISE EXCEPTION 'El lote debe recibirse en el centro destino de la solicitud (centro %).', v_sol.id_centro_destino;
  END IF;
  IF NOT fn_tiene_rol(NEW.id_operador, ARRAY['OPERADOR_CENTRO']) THEN
    RAISE EXCEPTION 'El usuario % no es un operador de centro activo; solo ellos firman recepciones.', NEW.id_operador;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_recepcion_reglas
  BEFORE INSERT OR UPDATE OR DELETE ON recepcion
  FOR EACH ROW EXECUTE FUNCTION fn_trg_recepcion_reglas();

-- Al recibir: solicitud ATENDIDA, lote RECIBIDO y dispositivos ubicados en el centro
CREATE OR REPLACE FUNCTION fn_trg_recepcion_aplicar() RETURNS trigger
LANGUAGE plpgsql SET search_path = ecoraee, public AS $$
DECLARE v_lote BIGINT;
BEGIN
  PERFORM set_config('ecoraee.origen_recepcion', 'si', true);
  UPDATE solicitud_recoleccion SET estado = 'ATENDIDA' WHERE id_solicitud = NEW.id_solicitud
  RETURNING id_lote INTO v_lote;
  PERFORM set_config('ecoraee.origen_recepcion', '', true);

  UPDATE lote SET estado = 'RECIBIDO' WHERE id_lote = v_lote;
  UPDATE dispositivo
     SET id_centro_actual = NEW.id_centro, estado_actual = 'RECIBIDO'
   WHERE id_lote = v_lote AND estado_actual = 'REGISTRADO';
  RETURN NULL;
END $$;
CREATE TRIGGER trg_recepcion_aplicar
  AFTER INSERT ON recepcion
  FOR EACH ROW EXECUTE FUNCTION fn_trg_recepcion_aplicar();

-- ---------- RN-02: solo un técnico autorizado evalúa -------------------
CREATE OR REPLACE FUNCTION fn_trg_valida_evaluacion() RETURNS trigger
LANGUAGE plpgsql SET search_path = ecoraee, public AS $$
DECLARE v_disp dispositivo%ROWTYPE;
BEGIN
  SELECT * INTO v_disp FROM dispositivo WHERE id_dispositivo = COALESCE(NEW.id_dispositivo, OLD.id_dispositivo);
  IF v_disp.estado_actual = 'CERRADO' THEN
    RAISE EXCEPTION 'RN-08: el dispositivo % ya cerró su trazabilidad; sus evaluaciones no se modifican.', v_disp.codigo_unico;
  END IF;
  IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;

  IF TG_OP = 'UPDATE' AND NEW.id_dispositivo <> OLD.id_dispositivo THEN
    RAISE EXCEPTION 'No se puede mover una evaluación a otro dispositivo.';
  END IF;
  IF NOT fn_tiene_rol(NEW.id_tecnico, ARRAY['TECNICO_EVALUADOR']) THEN
    RAISE EXCEPTION 'RN-02: el usuario % no es un técnico evaluador autorizado.', NEW.id_tecnico;
  END IF;
  IF TG_OP = 'INSERT' AND v_disp.estado_actual NOT IN ('RECIBIDO','EVALUADO','TRANSFERIDO') THEN
    RAISE EXCEPTION 'El dispositivo % está %; solo se evalúan equipos que se encuentran en un centro.',
      v_disp.codigo_unico, v_disp.estado_actual;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_valida_evaluacion
  BEFORE INSERT OR UPDATE OR DELETE ON evaluacion_tecnica
  FOR EACH ROW EXECUTE FUNCTION fn_trg_valida_evaluacion();

-- Redundancia controlada: la clasificación del dispositivo = la de su última evaluación
CREATE OR REPLACE FUNCTION fn_trg_sincroniza_clasificacion() RETURNS trigger
LANGUAGE plpgsql SET search_path = ecoraee, public AS $$
DECLARE v_id BIGINT := COALESCE(NEW.id_dispositivo, OLD.id_dispositivo); v_clasif TEXT;
BEGIN
  SELECT clasificacion INTO v_clasif FROM evaluacion_tecnica
   WHERE id_dispositivo = v_id ORDER BY fecha_evaluacion DESC, id_evaluacion DESC LIMIT 1;

  UPDATE dispositivo d
     SET clasificacion = v_clasif,
         estado_actual = CASE
           WHEN v_clasif IS NULL AND d.estado_actual = 'EVALUADO' THEN 'RECIBIDO'
           WHEN v_clasif IS NOT NULL AND TG_OP = 'INSERT' THEN 'EVALUADO'
           ELSE d.estado_actual END
   WHERE d.id_dispositivo = v_id;
  RETURN NULL;
END $$;
CREATE TRIGGER trg_sincroniza_clasificacion
  AFTER INSERT OR UPDATE OF clasificacion, fecha_evaluacion OR DELETE ON evaluacion_tecnica
  FOR EACH ROW EXECUTE FUNCTION fn_trg_sincroniza_clasificacion();

-- ---------- Transferencias: estados permitidos y ruta (arista) ---------
CREATE OR REPLACE FUNCTION fn_trg_transferencia_reglas() RETURNS trigger
LANGUAGE plpgsql SET search_path = ecoraee, public AS $$
DECLARE v_ok BOOLEAN; v_carga NUMERIC; v_cap NUMERIC; v_unidad TEXT;
BEGIN
  IF TG_OP = 'DELETE' THEN
    IF OLD.estado NOT IN ('PROGRAMADA','CANCELADA') THEN
      RAISE EXCEPTION 'Solo se eliminan transferencias PROGRAMADAS o CANCELADAS (esta está %).', OLD.estado;
    END IF;
    RETURN OLD;
  END IF;

  IF TG_OP = 'INSERT' AND NEW.estado <> 'PROGRAMADA' THEN
    RAISE EXCEPTION 'Toda transferencia nace PROGRAMADA; luego se despacha y se recibe.';
  END IF;

  IF TG_OP = 'UPDATE' THEN
    IF OLD.estado IN ('CERRADA','CANCELADA') THEN
      RAISE EXCEPTION 'La transferencia % ya está % y no se puede modificar.', OLD.id_transferencia, OLD.estado;
    END IF;
    IF NOT ( NEW.estado = OLD.estado
          OR (OLD.estado = 'PROGRAMADA'  AND NEW.estado IN ('EN_TRANSITO','CANCELADA'))
          OR (OLD.estado = 'EN_TRANSITO' AND NEW.estado = 'CERRADA') ) THEN
      RAISE EXCEPTION 'Cambio de estado no permitido: % → %.', OLD.estado, NEW.estado;
    END IF;
    IF OLD.estado <> 'PROGRAMADA' AND (NEW.id_centro_origen <> OLD.id_centro_origen
        OR NEW.id_centro_destino <> OLD.id_centro_destino OR NEW.id_arista IS DISTINCT FROM OLD.id_arista) THEN
      RAISE EXCEPTION 'Solo se cambian centros o ruta mientras la transferencia está PROGRAMADA.';
    END IF;
    IF NEW.id_centro_origen <> OLD.id_centro_origen
       AND EXISTS (SELECT 1 FROM detalle_transferencia WHERE id_transferencia = OLD.id_transferencia) THEN
      RAISE EXCEPTION 'Quite los dispositivos antes de cambiar el centro de origen.';
    END IF;
  END IF;

  IF NOT fn_tiene_rol(NEW.id_coordinador, ARRAY['COORDINADOR_LOGISTICO']) THEN
    RAISE EXCEPTION 'El usuario % no es un coordinador logístico activo; solo ellos autorizan transferencias.', NEW.id_coordinador;
  END IF;

  -- La ruta (arista) debe unir el centro origen con el centro destino
  IF NEW.id_arista IS NOT NULL THEN
    SELECT TRUE INTO v_ok
      FROM arista_red a
      JOIN nodo_red o ON o.id_nodo = a.id_nodo_origen
      JOIN nodo_red d ON d.id_nodo = a.id_nodo_destino
     WHERE a.id_arista = NEW.id_arista
       AND o.id_centro = NEW.id_centro_origen AND d.id_centro = NEW.id_centro_destino;
    IF v_ok IS NULL THEN
      RAISE EXCEPTION 'La arista % no conecta el centro origen con el centro destino.', NEW.id_arista;
    END IF;
    -- RN-05 al cambiar la ruta de una transferencia que ya tiene equipos
    IF TG_OP = 'UPDATE' AND NEW.id_arista IS DISTINCT FROM OLD.id_arista THEN
      SELECT a.capacidad, e.unidad_medida INTO v_cap, v_unidad
        FROM arista_red a JOIN escenario_red e ON e.id_escenario = a.id_escenario WHERE a.id_arista = NEW.id_arista;
      SELECT CASE WHEN v_unidad = 'KG' THEN COALESCE(SUM(d.peso_kg), 0) ELSE count(*) END INTO v_carga
        FROM detalle_transferencia dt JOIN dispositivo d ON d.id_dispositivo = dt.id_dispositivo
       WHERE dt.id_transferencia = NEW.id_transferencia;
      IF v_carga > v_cap THEN
        RAISE EXCEPTION 'RN-05: la carga (% %) supera la capacidad de la arista (% %).', v_carga, v_unidad, v_cap, v_unidad;
      END IF;
    END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_transferencia_reglas
  BEFORE INSERT OR UPDATE OR DELETE ON transferencia
  FOR EACH ROW EXECUTE FUNCTION fn_trg_transferencia_reglas();

-- ---------- RN-05: cantidad ≤ capacidad de la arista -------------------
CREATE OR REPLACE FUNCTION fn_trg_valida_capacidad_arista() RETURNS trigger
LANGUAGE plpgsql SET search_path = ecoraee, public AS $$
DECLARE
  v_t transferencia%ROWTYPE; v_d dispositivo%ROWTYPE;
  v_cap NUMERIC; v_unidad TEXT; v_carga NUMERIC;
BEGIN
  IF TG_OP = 'DELETE' THEN
    SELECT * INTO v_t FROM transferencia WHERE id_transferencia = OLD.id_transferencia;
    IF FOUND AND v_t.estado <> 'PROGRAMADA' THEN
      RAISE EXCEPTION 'Solo se quitan dispositivos de transferencias PROGRAMADAS.';
    END IF;
    RETURN OLD;
  END IF;

  SELECT * INTO v_t FROM transferencia WHERE id_transferencia = NEW.id_transferencia;
  SELECT * INTO v_d FROM dispositivo   WHERE id_dispositivo   = NEW.id_dispositivo;

  IF v_t.estado <> 'PROGRAMADA' THEN
    RAISE EXCEPTION 'Solo se agregan dispositivos a transferencias PROGRAMADAS.';
  END IF;
  IF v_d.id_centro_actual IS DISTINCT FROM v_t.id_centro_origen THEN
    RAISE EXCEPTION 'El dispositivo % no se encuentra en el centro de origen.', v_d.codigo_unico;
  END IF;
  IF v_d.estado_actual NOT IN ('RECIBIDO','EVALUADO','TRANSFERIDO') THEN
    RAISE EXCEPTION 'El dispositivo % está % y no puede transferirse.', v_d.codigo_unico, v_d.estado_actual;
  END IF;
  IF EXISTS (SELECT 1 FROM detalle_transferencia dt JOIN transferencia t ON t.id_transferencia = dt.id_transferencia
              WHERE dt.id_dispositivo = NEW.id_dispositivo AND t.id_transferencia <> NEW.id_transferencia
                AND t.estado IN ('PROGRAMADA','EN_TRANSITO')) THEN
    RAISE EXCEPTION 'El dispositivo % ya está incluido en otra transferencia activa.', v_d.codigo_unico;
  END IF;

  IF v_t.id_arista IS NOT NULL THEN
    SELECT a.capacidad, e.unidad_medida INTO v_cap, v_unidad
      FROM arista_red a JOIN escenario_red e ON e.id_escenario = a.id_escenario
     WHERE a.id_arista = v_t.id_arista;
    SELECT CASE WHEN v_unidad = 'KG' THEN COALESCE(SUM(d.peso_kg), 0) ELSE count(*) END INTO v_carga
      FROM detalle_transferencia dt JOIN dispositivo d ON d.id_dispositivo = dt.id_dispositivo
     WHERE dt.id_transferencia = NEW.id_transferencia;
    v_carga := v_carga + CASE WHEN v_unidad = 'KG' THEN v_d.peso_kg ELSE 1 END;
    IF v_carga > v_cap THEN
      RAISE EXCEPTION 'RN-05: la carga (% %) supera la capacidad de la arista (% %).', v_carga, v_unidad, v_cap, v_unidad;
    END IF;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_valida_capacidad_arista
  BEFORE INSERT OR DELETE ON detalle_transferencia
  FOR EACH ROW EXECUTE FUNCTION fn_trg_valida_capacidad_arista();

-- ---------- RN-04 / RN-08: destino final -------------------------------
CREATE OR REPLACE FUNCTION fn_trg_valida_destino() RETURNS trigger
LANGUAGE plpgsql SET search_path = ecoraee, public AS $$
DECLARE v_d dispositivo%ROWTYPE; v_tipo_org TEXT;
BEGIN
  IF TG_OP IN ('UPDATE','DELETE') THEN
    RAISE EXCEPTION 'RN-08: el cierre de trazabilidad es definitivo; no se puede modificar ni eliminar.';
  END IF;

  SELECT * INTO v_d FROM dispositivo WHERE id_dispositivo = NEW.id_dispositivo;
  IF v_d.estado_actual IN ('REGISTRADO','EN_TRANSITO','CERRADO') THEN
    RAISE EXCEPTION 'El dispositivo % está % y no puede cerrarse.', v_d.codigo_unico, v_d.estado_actual;
  END IF;
  IF v_d.clasificacion IS NULL THEN
    RAISE EXCEPTION 'El dispositivo % necesita una evaluación técnica antes de su destino final.', v_d.codigo_unico;
  END IF;
  IF v_d.id_centro_actual IS DISTINCT FROM NEW.id_centro THEN
    RAISE EXCEPTION 'El destino final se registra en el centro donde está el dispositivo.';
  END IF;
  -- RN-04: lo no recuperable no va a beneficiarios
  IF v_d.clasificacion = 'NO_RECUPERABLE' AND NEW.tipo_destino IN ('DONACION','REUTILIZACION') THEN
    RAISE EXCEPTION 'RN-04: un dispositivo NO_RECUPERABLE no puede asignarse a %.', NEW.tipo_destino;
  END IF;
  IF NEW.id_org_beneficiaria IS NOT NULL THEN
    SELECT tipo_organizacion INTO v_tipo_org FROM organizacion WHERE id_organizacion = NEW.id_org_beneficiaria;
    IF v_tipo_org <> 'BENEFICIARIA' THEN
      RAISE EXCEPTION 'La organización receptora debe ser de tipo BENEFICIARIA.';
    END IF;
  END IF;
  IF NOT fn_tiene_rol(NEW.id_usuario_confirma, ARRAY['COORDINADOR_LOGISTICO','OPERADOR_CENTRO']) THEN
    RAISE EXCEPTION 'El usuario % no puede confirmar destinos finales.', NEW.id_usuario_confirma;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_valida_destino
  BEFORE INSERT OR UPDATE OR DELETE ON destino_final
  FOR EACH ROW EXECUTE FUNCTION fn_trg_valida_destino();

-- RN-08: al confirmar el destino el equipo pasa a CERRADO (y el lote, si ya cerró todo)
CREATE OR REPLACE FUNCTION fn_trg_cierra_dispositivo() RETURNS trigger
LANGUAGE plpgsql SET search_path = ecoraee, public AS $$
DECLARE v_lote BIGINT;
BEGIN
  UPDATE dispositivo SET estado_actual = 'CERRADO'
   WHERE id_dispositivo = NEW.id_dispositivo RETURNING id_lote INTO v_lote;
  UPDATE lote SET estado = 'CERRADO'
   WHERE id_lote = v_lote
     AND NOT EXISTS (SELECT 1 FROM dispositivo WHERE id_lote = v_lote AND estado_actual <> 'CERRADO');
  RETURN NULL;
END $$;
CREATE TRIGGER trg_cierra_dispositivo
  AFTER INSERT ON destino_final
  FOR EACH ROW EXECUTE FUNCTION fn_trg_cierra_dispositivo();

-- ---------- Flujo asignado ≤ capacidad --------------------------------
CREATE OR REPLACE FUNCTION fn_trg_valida_flujo() RETURNS trigger
LANGUAGE plpgsql SET search_path = ecoraee, public AS $$
DECLARE v_cap NUMERIC;
BEGIN
  SELECT capacidad INTO v_cap FROM arista_red WHERE id_arista = NEW.id_arista;
  IF NEW.flujo > v_cap THEN
    RAISE EXCEPTION 'El flujo % supera la capacidad % de la arista %.', NEW.flujo, v_cap, NEW.id_arista;
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER trg_valida_flujo
  BEFORE INSERT OR UPDATE ON flujo_arista
  FOR EACH ROW EXECUTE FUNCTION fn_trg_valida_flujo();

-- ---------- Auditoría de cambios sensibles -----------------------------
CREATE OR REPLACE FUNCTION fn_trg_auditoria() RETURNS trigger
LANGUAGE plpgsql SET search_path = ecoraee, public AS $$
DECLARE v_antes JSONB; v_despues JSONB;
BEGIN
  IF TG_OP IN ('UPDATE','DELETE') THEN v_antes   := to_jsonb(OLD) - 'password_hash'; END IF;
  IF TG_OP IN ('INSERT','UPDATE') THEN v_despues := to_jsonb(NEW) - 'password_hash'; END IF;
  IF TG_OP = 'UPDATE' AND v_antes = v_despues THEN RETURN NULL; END IF;
  INSERT INTO auditoria (tabla, operacion, id_registro, id_usuario, fecha, datos_antes, datos_despues)
  VALUES (TG_TABLE_NAME, left(TG_OP, 1),
          (COALESCE(v_despues, v_antes) ->> TG_ARGV[0])::BIGINT,
          fn_usuario_actual(), fn_fecha_evento(), v_antes, v_despues);
  RETURN NULL;
END $$;

CREATE TRIGGER trg_auditoria_usuario       AFTER INSERT OR UPDATE OR DELETE ON usuario            FOR EACH ROW EXECUTE FUNCTION fn_trg_auditoria('id_usuario');
CREATE TRIGGER trg_auditoria_centro        AFTER INSERT OR UPDATE OR DELETE ON centro             FOR EACH ROW EXECUTE FUNCTION fn_trg_auditoria('id_centro');
CREATE TRIGGER trg_auditoria_lote          AFTER INSERT OR UPDATE OR DELETE ON lote               FOR EACH ROW EXECUTE FUNCTION fn_trg_auditoria('id_lote');
CREATE TRIGGER trg_auditoria_dispositivo   AFTER INSERT OR UPDATE OR DELETE ON dispositivo        FOR EACH ROW EXECUTE FUNCTION fn_trg_auditoria('id_dispositivo');
CREATE TRIGGER trg_auditoria_recepcion     AFTER INSERT OR UPDATE OR DELETE ON recepcion          FOR EACH ROW EXECUTE FUNCTION fn_trg_auditoria('id_recepcion');
CREATE TRIGGER trg_auditoria_evaluacion    AFTER INSERT OR UPDATE OR DELETE ON evaluacion_tecnica FOR EACH ROW EXECUTE FUNCTION fn_trg_auditoria('id_evaluacion');
CREATE TRIGGER trg_auditoria_transferencia AFTER INSERT OR UPDATE OR DELETE ON transferencia      FOR EACH ROW EXECUTE FUNCTION fn_trg_auditoria('id_transferencia');
CREATE TRIGGER trg_auditoria_destino       AFTER INSERT OR UPDATE OR DELETE ON destino_final      FOR EACH ROW EXECUTE FUNCTION fn_trg_auditoria('id_destino_final');
CREATE TRIGGER trg_auditoria_evidencia     AFTER INSERT OR UPDATE OR DELETE ON evidencia          FOR EACH ROW EXECUTE FUNCTION fn_trg_auditoria('id_evidencia');

-- =====================================================================
-- 6. PROCEDIMIENTOS ALMACENADOS (RN-06: todo o nada)
-- =====================================================================

-- Despacho: la transferencia sale y sus equipos quedan EN_TRANSITO
CREATE OR REPLACE PROCEDURE sp_despachar_transferencia(p_id BIGINT)
LANGUAGE plpgsql SET search_path = ecoraee, public AS $$
DECLARE v_estado TEXT; v_n INT;
BEGIN
  SELECT estado INTO v_estado FROM transferencia WHERE id_transferencia = p_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'La transferencia % no existe.', p_id; END IF;
  IF v_estado <> 'PROGRAMADA' THEN
    RAISE EXCEPTION 'Solo se despachan transferencias PROGRAMADAS (estado actual: %).', v_estado;
  END IF;
  SELECT count(*) INTO v_n FROM detalle_transferencia WHERE id_transferencia = p_id;
  IF v_n = 0 THEN RAISE EXCEPTION 'La transferencia % no tiene dispositivos asignados.', p_id; END IF;

  UPDATE transferencia SET estado = 'EN_TRANSITO', fecha_salida = fn_fecha_evento() WHERE id_transferencia = p_id;
  UPDATE dispositivo d SET estado_actual = 'EN_TRANSITO'
    FROM detalle_transferencia dt
   WHERE dt.id_dispositivo = d.id_dispositivo AND dt.id_transferencia = p_id;
END $$;

-- Recepción: en UNA transacción se descuenta del origen, se suma al destino,
-- se ubican los equipos y se cierra la transferencia (RN-03, RN-06).
CREATE OR REPLACE PROCEDURE sp_recibir_transferencia(p_id BIGINT, p_responsable BIGINT)
LANGUAGE plpgsql SET search_path = ecoraee, public AS $$
DECLARE v_t transferencia%ROWTYPE;
BEGIN
  SELECT * INTO v_t FROM transferencia WHERE id_transferencia = p_id FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'La transferencia % no existe.', p_id; END IF;
  IF v_t.estado <> 'EN_TRANSITO' THEN
    RAISE EXCEPTION 'Solo se reciben transferencias EN_TRANSITO (estado actual: %).', v_t.estado;
  END IF;
  IF NOT fn_tiene_rol(p_responsable, ARRAY['OPERADOR_CENTRO','COORDINADOR_LOGISTICO']) THEN
    RAISE EXCEPTION 'RN-03: el responsable % debe ser un operador de centro o coordinador activo.', p_responsable;
  END IF;

  UPDATE dispositivo d
     SET id_centro_actual = v_t.id_centro_destino, estado_actual = 'TRANSFERIDO'
    FROM detalle_transferencia dt
   WHERE dt.id_dispositivo = d.id_dispositivo AND dt.id_transferencia = p_id;

  UPDATE transferencia
     SET estado = 'CERRADA', id_responsable = p_responsable, fecha_recepcion = fn_fecha_evento()
   WHERE id_transferencia = p_id;
END $$;

-- =====================================================================
-- 7. VISTAS
-- =====================================================================

-- Trazabilidad resumida de cada dispositivo
CREATE OR REPLACE VIEW v_trazabilidad_dispositivo AS
SELECT d.id_dispositivo, d.codigo_unico, l.codigo_lote, c.nombre AS categoria, m.nombre AS marca, d.modelo,
       d.peso_kg, d.estado_actual, d.clasificacion, ce.nombre AS centro_actual,
       (SELECT count(*) FROM historial_estado h WHERE h.id_dispositivo = d.id_dispositivo) AS cambios_estado,
       (SELECT max(e.fecha_evaluacion) FROM evaluacion_tecnica e WHERE e.id_dispositivo = d.id_dispositivo) AS ultima_evaluacion,
       df.tipo_destino, df.fecha_confirmacion
  FROM dispositivo d
  JOIN lote l       ON l.id_lote = d.id_lote
  JOIN categoria c  ON c.id_categoria = d.id_categoria
  LEFT JOIN marca m ON m.id_marca = d.id_marca
  LEFT JOIN centro ce ON ce.id_centro = d.id_centro_actual
  LEFT JOIN destino_final df ON df.id_dispositivo = d.id_dispositivo;

-- Ocupación de cada centro frente a su capacidad
CREATE OR REPLACE VIEW v_ocupacion_centro AS
SELECT c.id_centro, c.nombre, tc.nombre AS tipo_centro, c.capacidad_unidades, c.capacidad_kg,
       COALESCE(SUM(i.cantidad_unidades), 0)::INT AS unidades,
       COALESCE(SUM(i.peso_total_kg), 0)          AS peso_kg,
       ROUND(100.0 * COALESCE(SUM(i.cantidad_unidades), 0) / c.capacidad_unidades, 1) AS ocupacion_pct
  FROM centro c
  JOIN tipo_centro tc ON tc.id_tipo_centro = c.id_tipo_centro
  LEFT JOIN inventario i ON i.id_centro = c.id_centro
 GROUP BY c.id_centro, tc.nombre;

-- Red de un escenario lista para el módulo de flujo máximo (RF-INT-04)
CREATE OR REPLACE VIEW v_red_flujo AS
SELECT a.id_escenario, a.id_arista, o.etiqueta AS origen, d.etiqueta AS destino, a.capacidad,
       o.tipo_nodo AS tipo_origen, d.tipo_nodo AS tipo_destino
  FROM arista_red a
  JOIN nodo_red o ON o.id_nodo = a.id_nodo_origen
  JOIN nodo_red d ON d.id_nodo = a.id_nodo_destino;
