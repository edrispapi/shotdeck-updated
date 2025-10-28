--
-- PostgreSQL database cluster dump
--

\restrict dL9lEx8XeS95OslfZf4BfhIsnEDgRbs5rvgebYWRZMb6vq3YL1305IGruRbD0Nh

SET default_transaction_read_only = off;

SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;

--
-- Roles
--

CREATE ROLE postgres;
ALTER ROLE postgres WITH SUPERUSER INHERIT CREATEROLE CREATEDB LOGIN REPLICATION BYPASSRLS PASSWORD 'md5a8418ef54ed61d4890c0a3c848049e53';






\unrestrict dL9lEx8XeS95OslfZf4BfhIsnEDgRbs5rvgebYWRZMb6vq3YL1305IGruRbD0Nh

--
-- PostgreSQL database cluster dump complete
--

