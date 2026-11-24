-- =====================================================================
--  EcoRAEE Cloud · Usuario de la aplicación en Amazon RDS (mínimo privilegio)
--
--  La API no se conecta con el usuario master de RDS: usa ecoraee_app, que
--  solo puede leer y escribir datos del esquema ecoraee. No puede crear ni
--  borrar tablas, ni administrar otros usuarios.
--
--  Lo ejecuta deploy/rds/migrar_a_rds.sh como usuario master:
--    psql ... -v clave_app='...' -f deploy/rds/usuario_app.sql
-- =====================================================================
\set ON_ERROR_STOP on

SELECT format('CREATE ROLE ecoraee_app LOGIN PASSWORD %L', :'clave_app')
 WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ecoraee_app') \gexec
ALTER ROLE ecoraee_app PASSWORD :'clave_app';

GRANT CONNECT ON DATABASE ecoraee TO ecoraee_app;
GRANT USAGE ON SCHEMA ecoraee TO ecoraee_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA ecoraee TO ecoraee_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA ecoraee TO ecoraee_app;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA ecoraee TO ecoraee_app;
GRANT EXECUTE ON ALL PROCEDURES IN SCHEMA ecoraee TO ecoraee_app;
ALTER ROLE ecoraee_app SET search_path = ecoraee, public;
ALTER ROLE ecoraee_app SET timezone = 'America/Guayaquil';

-- Nadie más que el master puede crear objetos en public
REVOKE CREATE ON SCHEMA public FROM PUBLIC;

\echo 'Usuario ecoraee_app listo (solo SELECT, INSERT, UPDATE y DELETE en el esquema ecoraee).'
