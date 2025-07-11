

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


CREATE SCHEMA IF NOT EXISTS "dev";


ALTER SCHEMA "dev" OWNER TO "postgres";


CREATE EXTENSION IF NOT EXISTS "pg_net" WITH SCHEMA "extensions";






COMMENT ON SCHEMA "public" IS 'standard public schema';



CREATE SCHEMA IF NOT EXISTS "vector";


ALTER SCHEMA "vector" OWNER TO "postgres";


CREATE EXTENSION IF NOT EXISTS "hypopg" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "index_advisor" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pg_graphql" WITH SCHEMA "graphql";






CREATE EXTENSION IF NOT EXISTS "pg_stat_statements" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pgjwt" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "supabase_vault" WITH SCHEMA "vault";






CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "vector" WITH SCHEMA "vector";






CREATE EXTENSION IF NOT EXISTS "wrappers" WITH SCHEMA "public";






CREATE TYPE "public"."integration_type_enum" AS ENUM (
    'QUICKBOOKS',
    'XERO',
    'SAGE',
    'NETSUITE'
);


ALTER TYPE "public"."integration_type_enum" OWNER TO "postgres";


CREATE TYPE "public"."integrationstatus" AS ENUM (
    'Connected',
    'Disconnected',
    'Error',
    'Pending'
);


ALTER TYPE "public"."integrationstatus" OWNER TO "postgres";


CREATE TYPE "public"."integrationtype" AS ENUM (
    'QuickBooks'
);


ALTER TYPE "public"."integrationtype" OWNER TO "postgres";


CREATE TYPE "public"."leasestatus" AS ENUM (
    'DRAFT',
    'PENDING',
    'ACTIVE',
    'EXPIRED',
    'TERMINATED',
    'RENEWED'
);


ALTER TYPE "public"."leasestatus" OWNER TO "postgres";


CREATE TYPE "public"."maintenance_priority" AS ENUM (
    'Low',
    'Medium',
    'High'
);


ALTER TYPE "public"."maintenance_priority" OWNER TO "postgres";


CREATE TYPE "public"."maintenance_status" AS ENUM (
    'Pending',
    'In Progress',
    'Scheduled',
    'Completed',
    'Cancelled'
);


ALTER TYPE "public"."maintenance_status" OWNER TO "postgres";


CREATE TYPE "public"."messagetype" AS ENUM (
    'DIRECT',
    'ANNOUNCEMENT',
    'SYSTEM'
);


ALTER TYPE "public"."messagetype" OWNER TO "postgres";


CREATE TYPE "public"."paymentmethod" AS ENUM (
    'Credit Card',
    'Bank Transfer',
    'Cash',
    'Check',
    'Other'
);


ALTER TYPE "public"."paymentmethod" OWNER TO "postgres";


CREATE TYPE "public"."paymentstatus" AS ENUM (
    'Pending',
    'Paid',
    'Partial',
    'Overdue',
    'Cancelled',
    'Refunded',
    'Draft',
    'Void',
    'Uncollectible'
);


ALTER TYPE "public"."paymentstatus" OWNER TO "postgres";


CREATE TYPE "public"."property_type_enum" AS ENUM (
    'Residential',
    'Commercial',
    'Industrial',
    'Land',
    'Special Purpose',
    'Mixed-Use',
    'Apartment Complex',
    'Other'
);


ALTER TYPE "public"."property_type_enum" OWNER TO "postgres";


CREATE TYPE "public"."propertystatus" AS ENUM (
    'ACTIVE',
    'INACTIVE',
    'DRAFT',
    'ARCHIVED'
);


ALTER TYPE "public"."propertystatus" OWNER TO "postgres";


CREATE TYPE "public"."tenantstatus" AS ENUM (
    'ACTIVE',
    'INACTIVE',
    'PENDING',
    'EVICTED',
    'MOVED_OUT'
);


ALTER TYPE "public"."tenantstatus" OWNER TO "postgres";


CREATE TYPE "public"."tenanttype" AS ENUM (
    'INDIVIDUAL',
    'COMPANY'
);


ALTER TYPE "public"."tenanttype" OWNER TO "postgres";


CREATE TYPE "public"."vendorstatus" AS ENUM (
    'PENDING',
    'APPROVED',
    'DENIED',
    'INACTIVE'
);


ALTER TYPE "public"."vendorstatus" OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_current_app_user_id"() RETURNS "uuid"
    LANGUAGE "plpgsql" STABLE
    SET "search_path" TO 'public'
    AS $$
BEGIN
  RETURN auth.uid();
END;
$$;


ALTER FUNCTION "public"."get_current_app_user_id"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."is_current_user_landlord"() RETURNS boolean
    LANGUAGE "plpgsql" STABLE
    SET "search_path" TO 'public'
    AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM public.users
    WHERE auth_provider_id = auth.uid() AND user_type = 'LANDLORD'
  );
END;
$$;


ALTER FUNCTION "public"."is_current_user_landlord"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."is_expense_owner"("p_expense_id" integer, "p_user_id" "uuid") RETURNS boolean
    LANGUAGE "sql" STABLE SECURITY DEFINER
    AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.expenses e
    JOIN public.properties p ON e.property_id = p.id
    WHERE e.id = p_expense_id AND p.user_id = p_user_id
  );
$$;


ALTER FUNCTION "public"."is_expense_owner"("p_expense_id" integer, "p_user_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."update_updated_at_column"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO ''
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."update_updated_at_column"() OWNER TO "postgres";

SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "public"."alembic_version" (
    "version_num" character varying(32) NOT NULL
);


ALTER TABLE "public"."alembic_version" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."expense_tax_details" (
    "id" integer NOT NULL,
    "tax_name" character varying NOT NULL,
    "tax_rate" numeric(5,2) NOT NULL,
    "tax_amount" numeric(12,2) NOT NULL,
    "expense_id" integer,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL
);


ALTER TABLE "public"."expense_tax_details" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."expense_tax_details_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "public"."expense_tax_details_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."expense_tax_details_id_seq" OWNED BY "public"."expense_tax_details"."id";



CREATE TABLE IF NOT EXISTS "public"."expenses" (
    "id" integer NOT NULL,
    "category" character varying NOT NULL,
    "description" character varying,
    "expense_date" timestamp with time zone NOT NULL,
    "receipt_url" character varying,
    "property_id" integer NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "subtotal_amount" numeric(12,2) NOT NULL,
    "total_tax_amount" numeric(12,2) DEFAULT '0'::double precision NOT NULL,
    "quickbooks_id" character varying(64),
    "last_synced_at" timestamp with time zone
);


ALTER TABLE "public"."expenses" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."expenses_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "public"."expenses_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."expenses_id_seq" OWNED BY "public"."expenses"."id";



CREATE TABLE IF NOT EXISTS "public"."integrations" (
    "id" integer NOT NULL,
    "user_id" "uuid" NOT NULL,
    "integration_type" "public"."integration_type_enum" NOT NULL,
    "status" "public"."integrationstatus" DEFAULT 'Disconnected'::"public"."integrationstatus" NOT NULL,
    "apideck_consumer_id" character varying,
    "apideck_service_id" character varying,
    "connected_at" timestamp with time zone,
    "last_sync_at" timestamp with time zone,
    "connection_metadata" "jsonb",
    "last_error" character varying(255),
    "error_count" integer DEFAULT 0 NOT NULL,
    "created_at" timestamp with time zone DEFAULT "now"() NOT NULL,
    "updated_at" timestamp with time zone DEFAULT "now"() NOT NULL
);


ALTER TABLE "public"."integrations" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."integrations_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "public"."integrations_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."integrations_id_seq" OWNED BY "public"."integrations"."id";



CREATE TABLE IF NOT EXISTS "public"."invoices" (
    "id" integer NOT NULL,
    "invoice_number" character varying NOT NULL,
    "amount" numeric(12,2) NOT NULL,
    "description" character varying NOT NULL,
    "issue_date" timestamp with time zone NOT NULL,
    "due_date" timestamp with time zone NOT NULL,
    "property_id" integer,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "status" "public"."paymentstatus" DEFAULT 'Pending'::"public"."paymentstatus",
    "tenant_id" integer,
    "quickbooks_id" character varying(64),
    "last_synced_at" timestamp with time zone
);


ALTER TABLE "public"."invoices" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."invoices_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "public"."invoices_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."invoices_id_seq" OWNED BY "public"."invoices"."id";



CREATE TABLE IF NOT EXISTS "public"."lease_documents" (
    "id" integer NOT NULL,
    "name" character varying NOT NULL,
    "file_path" character varying NOT NULL,
    "document_type" character varying NOT NULL,
    "upload_date" timestamp with time zone NOT NULL,
    "lease_id" integer,
    "uploaded_by_id" "uuid"
);


ALTER TABLE "public"."lease_documents" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."lease_documents_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "public"."lease_documents_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."lease_documents_id_seq" OWNED BY "public"."lease_documents"."id";



CREATE TABLE IF NOT EXISTS "public"."leases" (
    "id" integer NOT NULL,
    "start_date" "date" NOT NULL,
    "end_date" "date" NOT NULL,
    "monthly_rent" numeric(12,2) NOT NULL,
    "security_deposit" numeric(12,2) NOT NULL,
    "status" "public"."leasestatus" NOT NULL,
    "is_renewable" boolean NOT NULL,
    "auto_renew" boolean NOT NULL,
    "rent_due_day" integer NOT NULL,
    "late_fee_amount" numeric(12,2),
    "late_fee_after_days" integer,
    "special_terms" character varying,
    "property_id" integer NOT NULL,
    "unit_id" integer,
    "tenant_id" integer NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL
);


ALTER TABLE "public"."leases" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."leases_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "public"."leases_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."leases_id_seq" OWNED BY "public"."leases"."id";



CREATE TABLE IF NOT EXISTS "public"."maintenance_requests" (
    "id" integer NOT NULL,
    "issue_title" character varying(255) NOT NULL,
    "description" "text",
    "property_id" integer NOT NULL,
    "unit_id" integer,
    "tenant_id" integer,
    "user_id" "uuid",
    "request_date" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "priority" "public"."maintenance_priority" NOT NULL,
    "status" "public"."maintenance_status" DEFAULT 'Pending'::"public"."maintenance_status" NOT NULL,
    "scheduled_date" "date",
    "estimated_cost" numeric(10,2),
    "actual_cost" numeric(10,2),
    "photos" "json",
    "created_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "updated_at" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    "assigned_to" character varying(255)
);


ALTER TABLE "public"."maintenance_requests" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."maintenance_requests_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "public"."maintenance_requests_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."maintenance_requests_id_seq" OWNED BY "public"."maintenance_requests"."id";



CREATE TABLE IF NOT EXISTS "public"."payments" (
    "id" integer NOT NULL,
    "amount" numeric(12,2) NOT NULL,
    "payment_date" timestamp with time zone NOT NULL,
    "lease_id" integer,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "description" character varying,
    "status" "public"."paymentstatus" DEFAULT 'Pending'::"public"."paymentstatus",
    "payment_method" "public"."paymentmethod" NOT NULL,
    "transaction_reference" character varying,
    "receipt_url" character varying,
    "tenant_id" integer,
    "quickbooks_id" character varying(64),
    "last_synced_at" timestamp with time zone
);


ALTER TABLE "public"."payments" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."payments_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "public"."payments_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."payments_id_seq" OWNED BY "public"."payments"."id";



CREATE TABLE IF NOT EXISTS "public"."properties" (
    "id" integer NOT NULL,
    "name" character varying,
    "address" character varying,
    "city" character varying,
    "province" character varying,
    "postal_code" character varying,
    "property_type" character varying(50),
    "year_built" integer,
    "description" character varying,
    "status" "public"."propertystatus" NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "user_id" "uuid" NOT NULL
);


ALTER TABLE "public"."properties" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."properties_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "public"."properties_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."properties_id_seq" OWNED BY "public"."properties"."id";



CREATE TABLE IF NOT EXISTS "public"."property_units" (
    "id" integer NOT NULL,
    "property_id" integer,
    "tenant_id" integer,
    "name" character varying NOT NULL,
    "description" character varying,
    "size" double precision,
    "monthly_rent" numeric(12,2),
    "is_rented" boolean NOT NULL,
    "bedrooms" integer,
    "bathrooms" double precision,
    "floor" integer,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL
);


ALTER TABLE "public"."property_units" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."property_units_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "public"."property_units_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."property_units_id_seq" OWNED BY "public"."property_units"."id";



CREATE TABLE IF NOT EXISTS "public"."tenant_unit_link" (
    "tenant_id" integer NOT NULL,
    "unit_id" integer NOT NULL,
    "start_date" timestamp without time zone,
    "end_date" timestamp without time zone
);


ALTER TABLE "public"."tenant_unit_link" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."tenants" (
    "id" integer NOT NULL,
    "user_id" "uuid",
    "first_name" character varying(100),
    "last_name" character varying(100),
    "phone" character varying,
    "email" character varying,
    "status" "public"."tenantstatus" NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "current_property_id" integer,
    "landlord_id" "uuid" NOT NULL,
    "quickbooks_id" character varying,
    "last_synced_at" timestamp with time zone,
    "profile_image_url" character varying,
    "tenant_type" "public"."tenanttype" NOT NULL,
    "company_name" character varying(200),
    "contact_person" character varying(200)
);


ALTER TABLE "public"."tenants" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."tenants_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "public"."tenants_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."tenants_id_seq" OWNED BY "public"."tenants"."id";



CREATE TABLE IF NOT EXISTS "public"."user_agent_threads" (
    "id" "uuid" NOT NULL,
    "user_id" "uuid" NOT NULL,
    "thread_id" character varying NOT NULL,
    "title" character varying,
    "created_at" timestamp with time zone NOT NULL,
    "last_active" timestamp with time zone NOT NULL,
    "is_active" boolean NOT NULL,
    "conversation_metadata" "json"
);


ALTER TABLE "public"."user_agent_threads" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."users" (
    "id" "uuid" DEFAULT "gen_random_uuid"() NOT NULL,
    "email" character varying NOT NULL,
    "first_name" character varying,
    "last_name" character varying,
    "user_type" character varying,
    "phone" character varying,
    "address" character varying,
    "city" character varying,
    "province" character varying,
    "postal_code" character varying,
    "profile_image_url" character varying,
    "is_active" boolean NOT NULL,
    "is_admin" boolean NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "is_email_verified" boolean NOT NULL
);


ALTER TABLE "public"."users" OWNER TO "postgres";


CREATE SEQUENCE IF NOT EXISTS "public"."users_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE "public"."users_id_seq" OWNER TO "postgres";


ALTER SEQUENCE "public"."users_id_seq" OWNED BY "public"."users"."id";



ALTER TABLE ONLY "public"."expense_tax_details" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."expense_tax_details_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."expenses" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."expenses_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."integrations" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."integrations_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."invoices" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."invoices_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."lease_documents" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."lease_documents_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."leases" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."leases_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."maintenance_requests" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."maintenance_requests_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."payments" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."payments_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."properties" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."properties_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."property_units" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."property_units_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."tenants" ALTER COLUMN "id" SET DEFAULT "nextval"('"public"."tenants_id_seq"'::"regclass");



ALTER TABLE ONLY "public"."alembic_version"
    ADD CONSTRAINT "alembic_version_pkc" PRIMARY KEY ("version_num");



ALTER TABLE ONLY "public"."expense_tax_details"
    ADD CONSTRAINT "expense_tax_details_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."expenses"
    ADD CONSTRAINT "expenses_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."integrations"
    ADD CONSTRAINT "integrations_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."invoices"
    ADD CONSTRAINT "invoices_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."lease_documents"
    ADD CONSTRAINT "lease_documents_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."leases"
    ADD CONSTRAINT "leases_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."maintenance_requests"
    ADD CONSTRAINT "maintenance_requests_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."payments"
    ADD CONSTRAINT "payments_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."properties"
    ADD CONSTRAINT "properties_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."property_units"
    ADD CONSTRAINT "property_units_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."tenant_unit_link"
    ADD CONSTRAINT "tenant_unit_link_pkey" PRIMARY KEY ("tenant_id", "unit_id");



ALTER TABLE ONLY "public"."tenants"
    ADD CONSTRAINT "tenants_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."integrations"
    ADD CONSTRAINT "unique_user_integration" UNIQUE ("user_id", "integration_type");



ALTER TABLE ONLY "public"."invoices"
    ADD CONSTRAINT "uq_invoices_invoice_number" UNIQUE ("invoice_number");



ALTER TABLE ONLY "public"."invoices"
    ADD CONSTRAINT "uq_invoices_quickbooks_id" UNIQUE ("quickbooks_id");



ALTER TABLE ONLY "public"."payments"
    ADD CONSTRAINT "uq_payments_quickbooks_id" UNIQUE ("quickbooks_id");



ALTER TABLE ONLY "public"."user_agent_threads"
    ADD CONSTRAINT "user_agent_threads_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."users"
    ADD CONSTRAINT "users_pkey" PRIMARY KEY ("id");



CREATE INDEX "idx_integration_type" ON "public"."integrations" USING "btree" ("integration_type");



CREATE INDEX "idx_integration_user_id" ON "public"."integrations" USING "btree" ("user_id");



CREATE INDEX "idx_integration_user_type" ON "public"."integrations" USING "btree" ("user_id", "integration_type");



CREATE UNIQUE INDEX "idx_tenant_email_unique_per_landlord" ON "public"."tenants" USING "btree" ("landlord_id", "lower"(("email")::"text")) WHERE ("email" IS NOT NULL);



COMMENT ON INDEX "public"."idx_tenant_email_unique_per_landlord" IS 'Ensures each landlord cannot have duplicate tenant emails (case-insensitive). NULL emails are allowed.';



CREATE INDEX "idx_tenants_email_lower" ON "public"."tenants" USING "btree" ("lower"(("email")::"text")) WHERE ("email" IS NOT NULL);



CREATE INDEX "idx_tenants_landlord_id" ON "public"."tenants" USING "btree" ("landlord_id");



CREATE INDEX "ix_expense_tax_details_expense_id" ON "public"."expense_tax_details" USING "btree" ("expense_id");



CREATE INDEX "ix_expenses_property_id" ON "public"."expenses" USING "btree" ("property_id");



CREATE UNIQUE INDEX "ix_expenses_quickbooks_id" ON "public"."expenses" USING "btree" ("quickbooks_id");



CREATE INDEX "ix_invoices_last_synced_at" ON "public"."invoices" USING "btree" ("last_synced_at");



CREATE INDEX "ix_invoices_property_id" ON "public"."invoices" USING "btree" ("property_id");



CREATE INDEX "ix_invoices_tenant_id" ON "public"."invoices" USING "btree" ("tenant_id");



CREATE INDEX "ix_lease_documents_lease_id" ON "public"."lease_documents" USING "btree" ("lease_id");



CREATE INDEX "ix_lease_documents_uploaded_by_id" ON "public"."lease_documents" USING "btree" ("uploaded_by_id");



CREATE INDEX "ix_leases_property_id" ON "public"."leases" USING "btree" ("property_id");



CREATE INDEX "ix_leases_status" ON "public"."leases" USING "btree" ("status");



CREATE INDEX "ix_leases_tenant_id" ON "public"."leases" USING "btree" ("tenant_id");



CREATE INDEX "ix_leases_unit_id" ON "public"."leases" USING "btree" ("unit_id");



CREATE INDEX "ix_maintenance_requests_property_id" ON "public"."maintenance_requests" USING "btree" ("property_id");



CREATE INDEX "ix_maintenance_requests_tenant_id" ON "public"."maintenance_requests" USING "btree" ("tenant_id");



CREATE INDEX "ix_maintenance_requests_unit_id" ON "public"."maintenance_requests" USING "btree" ("unit_id");



CREATE INDEX "ix_maintenance_requests_user_id" ON "public"."maintenance_requests" USING "btree" ("user_id");



CREATE INDEX "ix_payments_lease_id" ON "public"."payments" USING "btree" ("lease_id");



CREATE INDEX "ix_payments_tenant_id" ON "public"."payments" USING "btree" ("tenant_id");



CREATE INDEX "ix_properties_user_id" ON "public"."properties" USING "btree" ("user_id");



CREATE INDEX "ix_property_units_name" ON "public"."property_units" USING "btree" ("name");



CREATE INDEX "ix_property_units_property_tenant" ON "public"."property_units" USING "btree" ("property_id", "tenant_id");



CREATE INDEX "ix_tenant_unit_link_unit_id" ON "public"."tenant_unit_link" USING "btree" ("unit_id");



CREATE INDEX "ix_tenants_current_property_id" ON "public"."tenants" USING "btree" ("current_property_id");



CREATE INDEX "ix_tenants_status" ON "public"."tenants" USING "btree" ("status");



CREATE INDEX "ix_tenants_tenant_type" ON "public"."tenants" USING "btree" ("tenant_type");



CREATE INDEX "ix_tenants_user_id" ON "public"."tenants" USING "btree" ("user_id");



CREATE INDEX "ix_user_agent_threads_thread_id" ON "public"."user_agent_threads" USING "btree" ("thread_id");



CREATE INDEX "ix_user_agent_threads_user_id" ON "public"."user_agent_threads" USING "btree" ("user_id");



CREATE UNIQUE INDEX "ix_users_email" ON "public"."users" USING "btree" ("email");



CREATE OR REPLACE TRIGGER "update_maintenance_requests_updated_at" BEFORE UPDATE ON "public"."maintenance_requests" FOR EACH ROW EXECUTE FUNCTION "public"."update_updated_at_column"();



ALTER TABLE ONLY "public"."expense_tax_details"
    ADD CONSTRAINT "expense_tax_details_expense_id_fkey" FOREIGN KEY ("expense_id") REFERENCES "public"."expenses"("id");



ALTER TABLE ONLY "public"."expenses"
    ADD CONSTRAINT "expenses_property_id_fkey" FOREIGN KEY ("property_id") REFERENCES "public"."properties"("id");



ALTER TABLE ONLY "public"."integrations"
    ADD CONSTRAINT "integrations_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id");



ALTER TABLE ONLY "public"."invoices"
    ADD CONSTRAINT "invoices_property_id_fkey" FOREIGN KEY ("property_id") REFERENCES "public"."properties"("id");



ALTER TABLE ONLY "public"."invoices"
    ADD CONSTRAINT "invoices_tenant_id_fkey" FOREIGN KEY ("tenant_id") REFERENCES "public"."tenants"("id");



ALTER TABLE ONLY "public"."lease_documents"
    ADD CONSTRAINT "lease_documents_lease_id_fkey_corrected" FOREIGN KEY ("lease_id") REFERENCES "public"."leases"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."lease_documents"
    ADD CONSTRAINT "lease_documents_uploaded_by_id_fkey" FOREIGN KEY ("uploaded_by_id") REFERENCES "public"."users"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."leases"
    ADD CONSTRAINT "leases_property_id_fkey" FOREIGN KEY ("property_id") REFERENCES "public"."properties"("id");



ALTER TABLE ONLY "public"."leases"
    ADD CONSTRAINT "leases_tenant_id_fkey" FOREIGN KEY ("tenant_id") REFERENCES "public"."tenants"("id");



ALTER TABLE ONLY "public"."leases"
    ADD CONSTRAINT "leases_unit_id_fkey" FOREIGN KEY ("unit_id") REFERENCES "public"."property_units"("id");



ALTER TABLE ONLY "public"."maintenance_requests"
    ADD CONSTRAINT "maintenance_requests_property_id_fkey" FOREIGN KEY ("property_id") REFERENCES "public"."properties"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."maintenance_requests"
    ADD CONSTRAINT "maintenance_requests_tenant_id_fkey" FOREIGN KEY ("tenant_id") REFERENCES "public"."tenants"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."maintenance_requests"
    ADD CONSTRAINT "maintenance_requests_unit_id_fkey" FOREIGN KEY ("unit_id") REFERENCES "public"."property_units"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."maintenance_requests"
    ADD CONSTRAINT "maintenance_requests_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."payments"
    ADD CONSTRAINT "payments_lease_id_fkey" FOREIGN KEY ("lease_id") REFERENCES "public"."leases"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."payments"
    ADD CONSTRAINT "payments_tenant_id_fkey" FOREIGN KEY ("tenant_id") REFERENCES "public"."tenants"("id");



ALTER TABLE ONLY "public"."properties"
    ADD CONSTRAINT "properties_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."property_units"
    ADD CONSTRAINT "property_units_property_id_fkey_corrected" FOREIGN KEY ("property_id") REFERENCES "public"."properties"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."property_units"
    ADD CONSTRAINT "property_units_tenant_id_fkey" FOREIGN KEY ("tenant_id") REFERENCES "public"."tenants"("id");



ALTER TABLE ONLY "public"."tenant_unit_link"
    ADD CONSTRAINT "tenant_unit_link_tenant_id_fkey" FOREIGN KEY ("tenant_id") REFERENCES "public"."tenants"("id");



ALTER TABLE ONLY "public"."tenant_unit_link"
    ADD CONSTRAINT "tenant_unit_link_unit_id_fkey" FOREIGN KEY ("unit_id") REFERENCES "public"."property_units"("id");



ALTER TABLE ONLY "public"."tenants"
    ADD CONSTRAINT "tenants_current_property_id_fkey_corrected" FOREIGN KEY ("current_property_id") REFERENCES "public"."properties"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."tenants"
    ADD CONSTRAINT "tenants_landlord_id_fkey" FOREIGN KEY ("landlord_id") REFERENCES "public"."users"("id");



ALTER TABLE ONLY "public"."tenants"
    ADD CONSTRAINT "tenants_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."user_agent_threads"
    ADD CONSTRAINT "user_agent_threads_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id");



CREATE POLICY "Allow authenticated read access to alembic version" ON "public"."alembic_version" FOR SELECT TO "authenticated" USING (true);



CREATE POLICY "Expense Tax Details Delete Access Control" ON "public"."expense_tax_details" FOR DELETE TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("expense_id" IN ( SELECT "exp"."id"
   FROM "public"."expenses" "exp"
  WHERE ("exp"."property_id" IN ( SELECT "prop"."id"
           FROM "public"."properties" "prop"
          WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))))));



CREATE POLICY "Expense Tax Details Insert Access Control" ON "public"."expense_tax_details" FOR INSERT TO "authenticated" WITH CHECK (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("expense_id" IN ( SELECT "exp"."id"
   FROM "public"."expenses" "exp"
  WHERE ("exp"."property_id" IN ( SELECT "prop"."id"
           FROM "public"."properties" "prop"
          WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))))));



CREATE POLICY "Expense Tax Details Select Access Control" ON "public"."expense_tax_details" FOR SELECT TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("expense_id" IN ( SELECT "exp"."id"
   FROM "public"."expenses" "exp"
  WHERE ("exp"."property_id" IN ( SELECT "prop"."id"
           FROM "public"."properties" "prop"
          WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))))));



CREATE POLICY "Expense Tax Details Update Access Control" ON "public"."expense_tax_details" FOR UPDATE TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("expense_id" IN ( SELECT "exp"."id"
   FROM "public"."expenses" "exp"
  WHERE ("exp"."property_id" IN ( SELECT "prop"."id"
           FROM "public"."properties" "prop"
          WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid"))))))))) WITH CHECK (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("expense_id" IN ( SELECT "exp"."id"
   FROM "public"."expenses" "exp"
  WHERE ("exp"."property_id" IN ( SELECT "prop"."id"
           FROM "public"."properties" "prop"
          WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))))));



CREATE POLICY "Expenses Delete Access Control" ON "public"."expenses" FOR DELETE TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("property_id" IN ( SELECT "prop"."id"
   FROM "public"."properties" "prop"
  WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))));



CREATE POLICY "Expenses Insert Access Control" ON "public"."expenses" FOR INSERT TO "authenticated" WITH CHECK (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("property_id" IN ( SELECT "prop"."id"
   FROM "public"."properties" "prop"
  WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))));



CREATE POLICY "Expenses Select Access Control" ON "public"."expenses" FOR SELECT TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("property_id" IN ( SELECT "prop"."id"
   FROM "public"."properties" "prop"
  WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))));



CREATE POLICY "Expenses Update Access Control" ON "public"."expenses" FOR UPDATE TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("property_id" IN ( SELECT "prop"."id"
   FROM "public"."properties" "prop"
  WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid"))))))) WITH CHECK (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("property_id" IN ( SELECT "prop"."id"
   FROM "public"."properties" "prop"
  WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))));



CREATE POLICY "Integrations Delete Access Control" ON "public"."integrations" FOR DELETE TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ("user_id" = ( SELECT "auth"."uid"() AS "uid"))));



CREATE POLICY "Integrations Insert Access Control" ON "public"."integrations" FOR INSERT TO "authenticated" WITH CHECK (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ("user_id" = ( SELECT "auth"."uid"() AS "uid"))));



CREATE POLICY "Integrations Select Access Control" ON "public"."integrations" FOR SELECT TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ("user_id" = ( SELECT "auth"."uid"() AS "uid"))));



CREATE POLICY "Integrations Update Access Control" ON "public"."integrations" FOR UPDATE TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ("user_id" = ( SELECT "auth"."uid"() AS "uid")))) WITH CHECK (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ("user_id" = ( SELECT "auth"."uid"() AS "uid"))));



CREATE POLICY "Invoices Delete Access Control" ON "public"."invoices" FOR DELETE TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("property_id" IN ( SELECT "prop"."id"
   FROM "public"."properties" "prop"
  WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))));



CREATE POLICY "Invoices Insert Access Control" ON "public"."invoices" FOR INSERT TO "authenticated" WITH CHECK (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("property_id" IN ( SELECT "prop"."id"
   FROM "public"."properties" "prop"
  WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))));



CREATE POLICY "Invoices Select Access Control" ON "public"."invoices" FOR SELECT TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("property_id" IN ( SELECT "prop"."id"
   FROM "public"."properties" "prop"
  WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))));



CREATE POLICY "Invoices Update Access Control" ON "public"."invoices" FOR UPDATE TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("property_id" IN ( SELECT "prop"."id"
   FROM "public"."properties" "prop"
  WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid"))))))) WITH CHECK (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("property_id" IN ( SELECT "prop"."id"
   FROM "public"."properties" "prop"
  WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))));



CREATE POLICY "Lease Documents Delete Access Control" ON "public"."lease_documents" FOR DELETE TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("lease_id" IN ( SELECT "l"."id"
   FROM "public"."leases" "l"
  WHERE ("l"."property_id" IN ( SELECT "prop"."id"
           FROM "public"."properties" "prop"
          WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))))));



CREATE POLICY "Lease Documents Insert Access Control" ON "public"."lease_documents" FOR INSERT TO "authenticated" WITH CHECK (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("lease_id" IN ( SELECT "l"."id"
   FROM "public"."leases" "l"
  WHERE ("l"."property_id" IN ( SELECT "prop"."id"
           FROM "public"."properties" "prop"
          WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))))));



CREATE POLICY "Lease Documents Select Access Control" ON "public"."lease_documents" FOR SELECT TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("lease_id" IN ( SELECT "l"."id"
   FROM "public"."leases" "l"
  WHERE ("l"."property_id" IN ( SELECT "prop"."id"
           FROM "public"."properties" "prop"
          WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))))));



CREATE POLICY "Lease Documents Update Access Control" ON "public"."lease_documents" FOR UPDATE TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("lease_id" IN ( SELECT "l"."id"
   FROM "public"."leases" "l"
  WHERE ("l"."property_id" IN ( SELECT "prop"."id"
           FROM "public"."properties" "prop"
          WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid"))))))))) WITH CHECK (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("lease_id" IN ( SELECT "l"."id"
   FROM "public"."leases" "l"
  WHERE ("l"."property_id" IN ( SELECT "prop"."id"
           FROM "public"."properties" "prop"
          WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))))));



CREATE POLICY "Leases Delete Access Control" ON "public"."leases" FOR DELETE TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("property_id" IN ( SELECT "prop"."id"
   FROM "public"."properties" "prop"
  WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))));



CREATE POLICY "Leases Insert Access Control" ON "public"."leases" FOR INSERT TO "authenticated" WITH CHECK (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("property_id" IN ( SELECT "prop"."id"
   FROM "public"."properties" "prop"
  WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))));



CREATE POLICY "Leases Select Access Control" ON "public"."leases" FOR SELECT TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("property_id" IN ( SELECT "prop"."id"
   FROM "public"."properties" "prop"
  WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))));



CREATE POLICY "Leases Update Access Control" ON "public"."leases" FOR UPDATE TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("property_id" IN ( SELECT "prop"."id"
   FROM "public"."properties" "prop"
  WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid"))))))) WITH CHECK (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("property_id" IN ( SELECT "prop"."id"
   FROM "public"."properties" "prop"
  WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))));



CREATE POLICY "Maintenance Requests Delete Access Control" ON "public"."maintenance_requests" FOR DELETE TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("property_id" IN ( SELECT "prop"."id"
   FROM "public"."properties" "prop"
  WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))));



CREATE POLICY "Maintenance Requests Insert Access Control" ON "public"."maintenance_requests" FOR INSERT TO "authenticated" WITH CHECK (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("property_id" IN ( SELECT "prop"."id"
   FROM "public"."properties" "prop"
  WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))));



CREATE POLICY "Maintenance Requests Select Access Control" ON "public"."maintenance_requests" FOR SELECT TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("property_id" IN ( SELECT "prop"."id"
   FROM "public"."properties" "prop"
  WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))));



CREATE POLICY "Maintenance Requests Update Access Control" ON "public"."maintenance_requests" FOR UPDATE TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("property_id" IN ( SELECT "prop"."id"
   FROM "public"."properties" "prop"
  WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid"))))))) WITH CHECK (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("property_id" IN ( SELECT "prop"."id"
   FROM "public"."properties" "prop"
  WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))));



CREATE POLICY "Payments Delete Access Control" ON "public"."payments" FOR DELETE TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("lease_id" IN ( SELECT "l"."id"
   FROM "public"."leases" "l"
  WHERE ("l"."property_id" IN ( SELECT "prop"."id"
           FROM "public"."properties" "prop"
          WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))))));



CREATE POLICY "Payments Insert Access Control" ON "public"."payments" FOR INSERT TO "authenticated" WITH CHECK (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("lease_id" IN ( SELECT "l"."id"
   FROM "public"."leases" "l"
  WHERE ("l"."property_id" IN ( SELECT "prop"."id"
           FROM "public"."properties" "prop"
          WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))))));



CREATE POLICY "Payments Select Access Control" ON "public"."payments" FOR SELECT TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("lease_id" IN ( SELECT "l"."id"
   FROM "public"."leases" "l"
  WHERE ("l"."property_id" IN ( SELECT "prop"."id"
           FROM "public"."properties" "prop"
          WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))))));



CREATE POLICY "Payments Update Access Control" ON "public"."payments" FOR UPDATE TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("lease_id" IN ( SELECT "l"."id"
   FROM "public"."leases" "l"
  WHERE ("l"."property_id" IN ( SELECT "prop"."id"
           FROM "public"."properties" "prop"
          WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid"))))))))) WITH CHECK (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("lease_id" IN ( SELECT "l"."id"
   FROM "public"."leases" "l"
  WHERE ("l"."property_id" IN ( SELECT "prop"."id"
           FROM "public"."properties" "prop"
          WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))))));



CREATE POLICY "Properties Delete Access Control" ON "public"."properties" FOR DELETE TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("user_id" = ( SELECT "auth"."uid"() AS "uid")))));



CREATE POLICY "Properties Insert Access Control" ON "public"."properties" FOR INSERT TO "authenticated" WITH CHECK (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("user_id" = ( SELECT "auth"."uid"() AS "uid")))));



CREATE POLICY "Properties Select Access Control" ON "public"."properties" FOR SELECT TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("user_id" = ( SELECT "auth"."uid"() AS "uid")))));



CREATE POLICY "Properties Update Access Control" ON "public"."properties" FOR UPDATE TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("user_id" = ( SELECT "auth"."uid"() AS "uid"))))) WITH CHECK (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("user_id" = ( SELECT "auth"."uid"() AS "uid")))));



CREATE POLICY "Property Units Delete Access Control" ON "public"."property_units" FOR DELETE TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("property_id" IN ( SELECT "prop"."id"
   FROM "public"."properties" "prop"
  WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))));



CREATE POLICY "Property Units Insert Access Control" ON "public"."property_units" FOR INSERT TO "authenticated" WITH CHECK (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("property_id" IN ( SELECT "prop"."id"
   FROM "public"."properties" "prop"
  WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))));



CREATE POLICY "Property Units Select Access Control" ON "public"."property_units" FOR SELECT TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("property_id" IN ( SELECT "prop"."id"
   FROM "public"."properties" "prop"
  WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))));



CREATE POLICY "Property Units Update Access Control" ON "public"."property_units" FOR UPDATE TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("property_id" IN ( SELECT "prop"."id"
   FROM "public"."properties" "prop"
  WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid"))))))) WITH CHECK (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("property_id" IN ( SELECT "prop"."id"
   FROM "public"."properties" "prop"
  WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))));



CREATE POLICY "Tenant Delete Access Control" ON "public"."tenants" FOR DELETE TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ((EXISTS ( SELECT 1
   FROM "public"."properties" "p"
  WHERE (("p"."user_id" = ( SELECT "auth"."uid"() AS "uid")) AND ("tenants"."current_property_id" = "p"."id")))) OR (EXISTS ( SELECT 1
   FROM ("public"."properties" "p"
     JOIN "public"."leases" "l" ON (("l"."property_id" = "p"."id")))
  WHERE (("p"."user_id" = ( SELECT "auth"."uid"() AS "uid")) AND ("l"."tenant_id" = "tenants"."id"))))))));



CREATE POLICY "Tenant Insert Access Control" ON "public"."tenants" FOR INSERT TO "authenticated" WITH CHECK (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND (("current_property_id" IS NULL) OR (EXISTS ( SELECT 1
   FROM "public"."properties" "p"
  WHERE (("p"."id" = "tenants"."current_property_id") AND ("p"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))))));



CREATE POLICY "Tenant Select Access Control" ON "public"."tenants" FOR SELECT TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ((EXISTS ( SELECT 1
   FROM "public"."properties" "p"
  WHERE (("p"."user_id" = ( SELECT "auth"."uid"() AS "uid")) AND ("tenants"."current_property_id" = "p"."id")))) OR (EXISTS ( SELECT 1
   FROM ("public"."properties" "p"
     JOIN "public"."leases" "l" ON (("l"."property_id" = "p"."id")))
  WHERE (("p"."user_id" = ( SELECT "auth"."uid"() AS "uid")) AND ("l"."tenant_id" = "tenants"."id"))))))));



CREATE POLICY "Tenant Unit Link Delete Access Control" ON "public"."tenant_unit_link" FOR DELETE TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("unit_id" IN ( SELECT "pu"."id"
   FROM "public"."property_units" "pu"
  WHERE ("pu"."property_id" IN ( SELECT "prop"."id"
           FROM "public"."properties" "prop"
          WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))))));



CREATE POLICY "Tenant Unit Link Insert Access Control" ON "public"."tenant_unit_link" FOR INSERT TO "authenticated" WITH CHECK (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("unit_id" IN ( SELECT "pu"."id"
   FROM "public"."property_units" "pu"
  WHERE ("pu"."property_id" IN ( SELECT "prop"."id"
           FROM "public"."properties" "prop"
          WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))))));



CREATE POLICY "Tenant Unit Link Select Access Control" ON "public"."tenant_unit_link" FOR SELECT TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("unit_id" IN ( SELECT "pu"."id"
   FROM "public"."property_units" "pu"
  WHERE ("pu"."property_id" IN ( SELECT "prop"."id"
           FROM "public"."properties" "prop"
          WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))))));



CREATE POLICY "Tenant Unit Link Update Access Control" ON "public"."tenant_unit_link" FOR UPDATE TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("unit_id" IN ( SELECT "pu"."id"
   FROM "public"."property_units" "pu"
  WHERE ("pu"."property_id" IN ( SELECT "prop"."id"
           FROM "public"."properties" "prop"
          WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid"))))))))) WITH CHECK (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ("unit_id" IN ( SELECT "pu"."id"
   FROM "public"."property_units" "pu"
  WHERE ("pu"."property_id" IN ( SELECT "prop"."id"
           FROM "public"."properties" "prop"
          WHERE ("prop"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))))));



CREATE POLICY "Tenant Update Access Control" ON "public"."tenants" FOR UPDATE TO "authenticated" USING (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND ((EXISTS ( SELECT 1
   FROM "public"."properties" "p"
  WHERE (("p"."user_id" = ( SELECT "auth"."uid"() AS "uid")) AND ("tenants"."current_property_id" = "p"."id")))) OR (EXISTS ( SELECT 1
   FROM ("public"."properties" "p"
     JOIN "public"."leases" "l" ON (("l"."property_id" = "p"."id")))
  WHERE (("p"."user_id" = ( SELECT "auth"."uid"() AS "uid")) AND ("l"."tenant_id" = "tenants"."id")))))))) WITH CHECK (((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND ("u"."is_admin" IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM "public"."users" "u"
  WHERE (("u"."id" = ( SELECT "auth"."uid"() AS "uid")) AND (("u"."user_type")::"text" = 'LANDLORD'::"text") AND ("u"."is_admin" IS FALSE)))) AND (("current_property_id" IS NULL) OR (EXISTS ( SELECT 1
   FROM "public"."properties" "p"
  WHERE (("p"."id" = "tenants"."current_property_id") AND ("p"."user_id" = ( SELECT "auth"."uid"() AS "uid")))))))));



CREATE POLICY "Users manage their own record" ON "public"."users" TO "authenticated" USING (("id" = ( SELECT "auth"."uid"() AS "uid"))) WITH CHECK (("id" = ( SELECT "auth"."uid"() AS "uid")));



ALTER TABLE "public"."alembic_version" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."expense_tax_details" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."expenses" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."integrations" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."invoices" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."lease_documents" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."leases" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."maintenance_requests" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."payments" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."properties" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."property_units" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."tenant_unit_link" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."tenants" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."users" ENABLE ROW LEVEL SECURITY;




ALTER PUBLICATION "supabase_realtime" OWNER TO "postgres";





GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";















































































































































































































GRANT ALL ON FUNCTION "public"."airtable_fdw_handler"() TO "postgres";
GRANT ALL ON FUNCTION "public"."airtable_fdw_handler"() TO "anon";
GRANT ALL ON FUNCTION "public"."airtable_fdw_handler"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."airtable_fdw_handler"() TO "service_role";



GRANT ALL ON FUNCTION "public"."airtable_fdw_meta"() TO "postgres";
GRANT ALL ON FUNCTION "public"."airtable_fdw_meta"() TO "anon";
GRANT ALL ON FUNCTION "public"."airtable_fdw_meta"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."airtable_fdw_meta"() TO "service_role";



GRANT ALL ON FUNCTION "public"."airtable_fdw_validator"("options" "text"[], "catalog" "oid") TO "postgres";
GRANT ALL ON FUNCTION "public"."airtable_fdw_validator"("options" "text"[], "catalog" "oid") TO "anon";
GRANT ALL ON FUNCTION "public"."airtable_fdw_validator"("options" "text"[], "catalog" "oid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."airtable_fdw_validator"("options" "text"[], "catalog" "oid") TO "service_role";



GRANT ALL ON FUNCTION "public"."auth0_fdw_handler"() TO "postgres";
GRANT ALL ON FUNCTION "public"."auth0_fdw_handler"() TO "anon";
GRANT ALL ON FUNCTION "public"."auth0_fdw_handler"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."auth0_fdw_handler"() TO "service_role";



GRANT ALL ON FUNCTION "public"."auth0_fdw_meta"() TO "postgres";
GRANT ALL ON FUNCTION "public"."auth0_fdw_meta"() TO "anon";
GRANT ALL ON FUNCTION "public"."auth0_fdw_meta"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."auth0_fdw_meta"() TO "service_role";



GRANT ALL ON FUNCTION "public"."auth0_fdw_validator"("options" "text"[], "catalog" "oid") TO "postgres";
GRANT ALL ON FUNCTION "public"."auth0_fdw_validator"("options" "text"[], "catalog" "oid") TO "anon";
GRANT ALL ON FUNCTION "public"."auth0_fdw_validator"("options" "text"[], "catalog" "oid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."auth0_fdw_validator"("options" "text"[], "catalog" "oid") TO "service_role";



GRANT ALL ON FUNCTION "public"."big_query_fdw_handler"() TO "postgres";
GRANT ALL ON FUNCTION "public"."big_query_fdw_handler"() TO "anon";
GRANT ALL ON FUNCTION "public"."big_query_fdw_handler"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."big_query_fdw_handler"() TO "service_role";



GRANT ALL ON FUNCTION "public"."big_query_fdw_meta"() TO "postgres";
GRANT ALL ON FUNCTION "public"."big_query_fdw_meta"() TO "anon";
GRANT ALL ON FUNCTION "public"."big_query_fdw_meta"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."big_query_fdw_meta"() TO "service_role";



GRANT ALL ON FUNCTION "public"."big_query_fdw_validator"("options" "text"[], "catalog" "oid") TO "postgres";
GRANT ALL ON FUNCTION "public"."big_query_fdw_validator"("options" "text"[], "catalog" "oid") TO "anon";
GRANT ALL ON FUNCTION "public"."big_query_fdw_validator"("options" "text"[], "catalog" "oid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."big_query_fdw_validator"("options" "text"[], "catalog" "oid") TO "service_role";



GRANT ALL ON FUNCTION "public"."click_house_fdw_handler"() TO "postgres";
GRANT ALL ON FUNCTION "public"."click_house_fdw_handler"() TO "anon";
GRANT ALL ON FUNCTION "public"."click_house_fdw_handler"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."click_house_fdw_handler"() TO "service_role";



GRANT ALL ON FUNCTION "public"."click_house_fdw_meta"() TO "postgres";
GRANT ALL ON FUNCTION "public"."click_house_fdw_meta"() TO "anon";
GRANT ALL ON FUNCTION "public"."click_house_fdw_meta"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."click_house_fdw_meta"() TO "service_role";



GRANT ALL ON FUNCTION "public"."click_house_fdw_validator"("options" "text"[], "catalog" "oid") TO "postgres";
GRANT ALL ON FUNCTION "public"."click_house_fdw_validator"("options" "text"[], "catalog" "oid") TO "anon";
GRANT ALL ON FUNCTION "public"."click_house_fdw_validator"("options" "text"[], "catalog" "oid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."click_house_fdw_validator"("options" "text"[], "catalog" "oid") TO "service_role";



GRANT ALL ON FUNCTION "public"."cognito_fdw_handler"() TO "postgres";
GRANT ALL ON FUNCTION "public"."cognito_fdw_handler"() TO "anon";
GRANT ALL ON FUNCTION "public"."cognito_fdw_handler"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."cognito_fdw_handler"() TO "service_role";



GRANT ALL ON FUNCTION "public"."cognito_fdw_meta"() TO "postgres";
GRANT ALL ON FUNCTION "public"."cognito_fdw_meta"() TO "anon";
GRANT ALL ON FUNCTION "public"."cognito_fdw_meta"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."cognito_fdw_meta"() TO "service_role";



GRANT ALL ON FUNCTION "public"."cognito_fdw_validator"("options" "text"[], "catalog" "oid") TO "postgres";
GRANT ALL ON FUNCTION "public"."cognito_fdw_validator"("options" "text"[], "catalog" "oid") TO "anon";
GRANT ALL ON FUNCTION "public"."cognito_fdw_validator"("options" "text"[], "catalog" "oid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."cognito_fdw_validator"("options" "text"[], "catalog" "oid") TO "service_role";



GRANT ALL ON FUNCTION "public"."firebase_fdw_handler"() TO "postgres";
GRANT ALL ON FUNCTION "public"."firebase_fdw_handler"() TO "anon";
GRANT ALL ON FUNCTION "public"."firebase_fdw_handler"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."firebase_fdw_handler"() TO "service_role";



GRANT ALL ON FUNCTION "public"."firebase_fdw_meta"() TO "postgres";
GRANT ALL ON FUNCTION "public"."firebase_fdw_meta"() TO "anon";
GRANT ALL ON FUNCTION "public"."firebase_fdw_meta"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."firebase_fdw_meta"() TO "service_role";



GRANT ALL ON FUNCTION "public"."firebase_fdw_validator"("options" "text"[], "catalog" "oid") TO "postgres";
GRANT ALL ON FUNCTION "public"."firebase_fdw_validator"("options" "text"[], "catalog" "oid") TO "anon";
GRANT ALL ON FUNCTION "public"."firebase_fdw_validator"("options" "text"[], "catalog" "oid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."firebase_fdw_validator"("options" "text"[], "catalog" "oid") TO "service_role";



GRANT ALL ON FUNCTION "public"."get_current_app_user_id"() TO "anon";
GRANT ALL ON FUNCTION "public"."get_current_app_user_id"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_current_app_user_id"() TO "service_role";



GRANT ALL ON FUNCTION "public"."hello_world_fdw_handler"() TO "postgres";
GRANT ALL ON FUNCTION "public"."hello_world_fdw_handler"() TO "anon";
GRANT ALL ON FUNCTION "public"."hello_world_fdw_handler"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."hello_world_fdw_handler"() TO "service_role";



GRANT ALL ON FUNCTION "public"."hello_world_fdw_meta"() TO "postgres";
GRANT ALL ON FUNCTION "public"."hello_world_fdw_meta"() TO "anon";
GRANT ALL ON FUNCTION "public"."hello_world_fdw_meta"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."hello_world_fdw_meta"() TO "service_role";



GRANT ALL ON FUNCTION "public"."hello_world_fdw_validator"("options" "text"[], "catalog" "oid") TO "postgres";
GRANT ALL ON FUNCTION "public"."hello_world_fdw_validator"("options" "text"[], "catalog" "oid") TO "anon";
GRANT ALL ON FUNCTION "public"."hello_world_fdw_validator"("options" "text"[], "catalog" "oid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."hello_world_fdw_validator"("options" "text"[], "catalog" "oid") TO "service_role";



GRANT ALL ON FUNCTION "public"."is_current_user_landlord"() TO "anon";
GRANT ALL ON FUNCTION "public"."is_current_user_landlord"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."is_current_user_landlord"() TO "service_role";



GRANT ALL ON FUNCTION "public"."is_expense_owner"("p_expense_id" integer, "p_user_id" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."is_expense_owner"("p_expense_id" integer, "p_user_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."is_expense_owner"("p_expense_id" integer, "p_user_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."logflare_fdw_handler"() TO "postgres";
GRANT ALL ON FUNCTION "public"."logflare_fdw_handler"() TO "anon";
GRANT ALL ON FUNCTION "public"."logflare_fdw_handler"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."logflare_fdw_handler"() TO "service_role";



GRANT ALL ON FUNCTION "public"."logflare_fdw_meta"() TO "postgres";
GRANT ALL ON FUNCTION "public"."logflare_fdw_meta"() TO "anon";
GRANT ALL ON FUNCTION "public"."logflare_fdw_meta"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."logflare_fdw_meta"() TO "service_role";



GRANT ALL ON FUNCTION "public"."logflare_fdw_validator"("options" "text"[], "catalog" "oid") TO "postgres";
GRANT ALL ON FUNCTION "public"."logflare_fdw_validator"("options" "text"[], "catalog" "oid") TO "anon";
GRANT ALL ON FUNCTION "public"."logflare_fdw_validator"("options" "text"[], "catalog" "oid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."logflare_fdw_validator"("options" "text"[], "catalog" "oid") TO "service_role";



GRANT ALL ON FUNCTION "public"."mssql_fdw_handler"() TO "postgres";
GRANT ALL ON FUNCTION "public"."mssql_fdw_handler"() TO "anon";
GRANT ALL ON FUNCTION "public"."mssql_fdw_handler"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."mssql_fdw_handler"() TO "service_role";



GRANT ALL ON FUNCTION "public"."mssql_fdw_meta"() TO "postgres";
GRANT ALL ON FUNCTION "public"."mssql_fdw_meta"() TO "anon";
GRANT ALL ON FUNCTION "public"."mssql_fdw_meta"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."mssql_fdw_meta"() TO "service_role";



GRANT ALL ON FUNCTION "public"."mssql_fdw_validator"("options" "text"[], "catalog" "oid") TO "postgres";
GRANT ALL ON FUNCTION "public"."mssql_fdw_validator"("options" "text"[], "catalog" "oid") TO "anon";
GRANT ALL ON FUNCTION "public"."mssql_fdw_validator"("options" "text"[], "catalog" "oid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."mssql_fdw_validator"("options" "text"[], "catalog" "oid") TO "service_role";



GRANT ALL ON FUNCTION "public"."redis_fdw_handler"() TO "postgres";
GRANT ALL ON FUNCTION "public"."redis_fdw_handler"() TO "anon";
GRANT ALL ON FUNCTION "public"."redis_fdw_handler"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."redis_fdw_handler"() TO "service_role";



GRANT ALL ON FUNCTION "public"."redis_fdw_meta"() TO "postgres";
GRANT ALL ON FUNCTION "public"."redis_fdw_meta"() TO "anon";
GRANT ALL ON FUNCTION "public"."redis_fdw_meta"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."redis_fdw_meta"() TO "service_role";



GRANT ALL ON FUNCTION "public"."redis_fdw_validator"("options" "text"[], "catalog" "oid") TO "postgres";
GRANT ALL ON FUNCTION "public"."redis_fdw_validator"("options" "text"[], "catalog" "oid") TO "anon";
GRANT ALL ON FUNCTION "public"."redis_fdw_validator"("options" "text"[], "catalog" "oid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."redis_fdw_validator"("options" "text"[], "catalog" "oid") TO "service_role";



GRANT ALL ON FUNCTION "public"."s3_fdw_handler"() TO "postgres";
GRANT ALL ON FUNCTION "public"."s3_fdw_handler"() TO "anon";
GRANT ALL ON FUNCTION "public"."s3_fdw_handler"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."s3_fdw_handler"() TO "service_role";



GRANT ALL ON FUNCTION "public"."s3_fdw_meta"() TO "postgres";
GRANT ALL ON FUNCTION "public"."s3_fdw_meta"() TO "anon";
GRANT ALL ON FUNCTION "public"."s3_fdw_meta"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."s3_fdw_meta"() TO "service_role";



GRANT ALL ON FUNCTION "public"."s3_fdw_validator"("options" "text"[], "catalog" "oid") TO "postgres";
GRANT ALL ON FUNCTION "public"."s3_fdw_validator"("options" "text"[], "catalog" "oid") TO "anon";
GRANT ALL ON FUNCTION "public"."s3_fdw_validator"("options" "text"[], "catalog" "oid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."s3_fdw_validator"("options" "text"[], "catalog" "oid") TO "service_role";



GRANT ALL ON FUNCTION "public"."stripe_fdw_handler"() TO "postgres";
GRANT ALL ON FUNCTION "public"."stripe_fdw_handler"() TO "anon";
GRANT ALL ON FUNCTION "public"."stripe_fdw_handler"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."stripe_fdw_handler"() TO "service_role";



GRANT ALL ON FUNCTION "public"."stripe_fdw_meta"() TO "postgres";
GRANT ALL ON FUNCTION "public"."stripe_fdw_meta"() TO "anon";
GRANT ALL ON FUNCTION "public"."stripe_fdw_meta"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."stripe_fdw_meta"() TO "service_role";



GRANT ALL ON FUNCTION "public"."stripe_fdw_validator"("options" "text"[], "catalog" "oid") TO "postgres";
GRANT ALL ON FUNCTION "public"."stripe_fdw_validator"("options" "text"[], "catalog" "oid") TO "anon";
GRANT ALL ON FUNCTION "public"."stripe_fdw_validator"("options" "text"[], "catalog" "oid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."stripe_fdw_validator"("options" "text"[], "catalog" "oid") TO "service_role";



GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "anon";
GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."update_updated_at_column"() TO "service_role";



GRANT ALL ON FUNCTION "public"."wasm_fdw_handler"() TO "postgres";
GRANT ALL ON FUNCTION "public"."wasm_fdw_handler"() TO "anon";
GRANT ALL ON FUNCTION "public"."wasm_fdw_handler"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."wasm_fdw_handler"() TO "service_role";



GRANT ALL ON FUNCTION "public"."wasm_fdw_meta"() TO "postgres";
GRANT ALL ON FUNCTION "public"."wasm_fdw_meta"() TO "anon";
GRANT ALL ON FUNCTION "public"."wasm_fdw_meta"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."wasm_fdw_meta"() TO "service_role";



GRANT ALL ON FUNCTION "public"."wasm_fdw_validator"("options" "text"[], "catalog" "oid") TO "postgres";
GRANT ALL ON FUNCTION "public"."wasm_fdw_validator"("options" "text"[], "catalog" "oid") TO "anon";
GRANT ALL ON FUNCTION "public"."wasm_fdw_validator"("options" "text"[], "catalog" "oid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."wasm_fdw_validator"("options" "text"[], "catalog" "oid") TO "service_role";
























GRANT ALL ON TABLE "public"."alembic_version" TO "anon";
GRANT ALL ON TABLE "public"."alembic_version" TO "authenticated";
GRANT ALL ON TABLE "public"."alembic_version" TO "service_role";



GRANT ALL ON TABLE "public"."expense_tax_details" TO "anon";
GRANT ALL ON TABLE "public"."expense_tax_details" TO "authenticated";
GRANT ALL ON TABLE "public"."expense_tax_details" TO "service_role";



GRANT ALL ON SEQUENCE "public"."expense_tax_details_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."expense_tax_details_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."expense_tax_details_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."expenses" TO "anon";
GRANT ALL ON TABLE "public"."expenses" TO "authenticated";
GRANT ALL ON TABLE "public"."expenses" TO "service_role";



GRANT ALL ON SEQUENCE "public"."expenses_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."expenses_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."expenses_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."integrations" TO "anon";
GRANT ALL ON TABLE "public"."integrations" TO "authenticated";
GRANT ALL ON TABLE "public"."integrations" TO "service_role";



GRANT ALL ON SEQUENCE "public"."integrations_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."integrations_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."integrations_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."invoices" TO "anon";
GRANT ALL ON TABLE "public"."invoices" TO "authenticated";
GRANT ALL ON TABLE "public"."invoices" TO "service_role";



GRANT ALL ON SEQUENCE "public"."invoices_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."invoices_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."invoices_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."lease_documents" TO "anon";
GRANT ALL ON TABLE "public"."lease_documents" TO "authenticated";
GRANT ALL ON TABLE "public"."lease_documents" TO "service_role";



GRANT ALL ON SEQUENCE "public"."lease_documents_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."lease_documents_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."lease_documents_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."leases" TO "anon";
GRANT ALL ON TABLE "public"."leases" TO "authenticated";
GRANT ALL ON TABLE "public"."leases" TO "service_role";



GRANT ALL ON SEQUENCE "public"."leases_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."leases_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."leases_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."maintenance_requests" TO "anon";
GRANT ALL ON TABLE "public"."maintenance_requests" TO "authenticated";
GRANT ALL ON TABLE "public"."maintenance_requests" TO "service_role";



GRANT ALL ON SEQUENCE "public"."maintenance_requests_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."maintenance_requests_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."maintenance_requests_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."payments" TO "anon";
GRANT ALL ON TABLE "public"."payments" TO "authenticated";
GRANT ALL ON TABLE "public"."payments" TO "service_role";



GRANT ALL ON SEQUENCE "public"."payments_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."payments_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."payments_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."properties" TO "anon";
GRANT ALL ON TABLE "public"."properties" TO "authenticated";
GRANT ALL ON TABLE "public"."properties" TO "service_role";



GRANT ALL ON SEQUENCE "public"."properties_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."properties_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."properties_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."property_units" TO "anon";
GRANT ALL ON TABLE "public"."property_units" TO "authenticated";
GRANT ALL ON TABLE "public"."property_units" TO "service_role";



GRANT ALL ON SEQUENCE "public"."property_units_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."property_units_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."property_units_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."tenant_unit_link" TO "anon";
GRANT ALL ON TABLE "public"."tenant_unit_link" TO "authenticated";
GRANT ALL ON TABLE "public"."tenant_unit_link" TO "service_role";



GRANT ALL ON TABLE "public"."tenants" TO "anon";
GRANT ALL ON TABLE "public"."tenants" TO "authenticated";
GRANT ALL ON TABLE "public"."tenants" TO "service_role";



GRANT ALL ON SEQUENCE "public"."tenants_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."tenants_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."tenants_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."user_agent_threads" TO "anon";
GRANT ALL ON TABLE "public"."user_agent_threads" TO "authenticated";
GRANT ALL ON TABLE "public"."user_agent_threads" TO "service_role";



GRANT ALL ON TABLE "public"."users" TO "anon";
GRANT ALL ON TABLE "public"."users" TO "authenticated";
GRANT ALL ON TABLE "public"."users" TO "service_role";



GRANT ALL ON SEQUENCE "public"."users_id_seq" TO "anon";
GRANT ALL ON SEQUENCE "public"."users_id_seq" TO "authenticated";
GRANT ALL ON SEQUENCE "public"."users_id_seq" TO "service_role";



GRANT ALL ON TABLE "public"."wrappers_fdw_stats" TO "postgres";
GRANT ALL ON TABLE "public"."wrappers_fdw_stats" TO "anon";
GRANT ALL ON TABLE "public"."wrappers_fdw_stats" TO "authenticated";
GRANT ALL ON TABLE "public"."wrappers_fdw_stats" TO "service_role";









ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES  TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES  TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES  TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES  TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS  TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS  TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS  TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS  TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES  TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES  TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES  TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES  TO "service_role";






























RESET ALL;
