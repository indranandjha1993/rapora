-- Manual helper: create the non-superuser application role used for Row-Level
-- Security. PostgreSQL superusers (and roles with BYPASSRLS) skip RLS entirely,
-- so the application MUST connect as a plain, non-superuser role.
--
-- Run this against your external PostgreSQL after creating the database
-- (see RLS_SETUP.md). Adjust the role name and password to match your .env,
-- then run it while connected to the application database:
--
--   psql "postgresql://<admin>@<host>/<your-db>" -f docker/postgres/init-rls-user.sql

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'rapora') THEN
        CREATE ROLE rapora WITH LOGIN PASSWORD 'change-me' NOSUPERUSER NOBYPASSRLS;
    END IF;
END
$$;

-- Privileges on the current (application) database. Granting schema/table
-- privileges does NOT weaken RLS — only superuser status or BYPASSRLS does.
GRANT ALL ON SCHEMA public TO rapora;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO rapora;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO rapora;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO rapora;
