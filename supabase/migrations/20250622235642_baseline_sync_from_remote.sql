create schema if not exists "dev";


create extension if not exists "hypopg" with schema "extensions";

create extension if not exists "index_advisor" with schema "extensions";


create extension if not exists "wrappers" with schema "public";

create type "public"."integration_type_enum" as enum ('QUICKBOOKS', 'XERO', 'SAGE', 'NETSUITE');

create type "public"."integrationstatus" as enum ('Connected', 'Disconnected', 'Error', 'Pending');

create type "public"."integrationtype" as enum ('QuickBooks');

create type "public"."leasestatus" as enum ('DRAFT', 'PENDING', 'ACTIVE', 'EXPIRED', 'TERMINATED', 'RENEWED');

create type "public"."maintenance_priority" as enum ('Low', 'Medium', 'High');

create type "public"."maintenance_status" as enum ('Pending', 'In Progress', 'Scheduled', 'Completed', 'Cancelled');

create type "public"."messagetype" as enum ('DIRECT', 'ANNOUNCEMENT', 'SYSTEM');

create type "public"."paymentmethod" as enum ('Credit Card', 'Bank Transfer', 'Cash', 'Check', 'Other');

create type "public"."paymentstatus" as enum ('Pending', 'Paid', 'Partial', 'Overdue', 'Cancelled', 'Refunded', 'Draft', 'Void', 'Uncollectible');

create type "public"."property_type_enum" as enum ('Residential', 'Commercial', 'Industrial', 'Land', 'Special Purpose', 'Mixed-Use', 'Apartment Complex', 'Other');

create type "public"."propertystatus" as enum ('ACTIVE', 'INACTIVE', 'DRAFT', 'ARCHIVED');

create type "public"."tenantstatus" as enum ('ACTIVE', 'INACTIVE', 'PENDING', 'EVICTED', 'MOVED_OUT');

create type "public"."vendorstatus" as enum ('PENDING', 'APPROVED', 'DENIED', 'INACTIVE');

create sequence "public"."expense_tax_details_id_seq";

create sequence "public"."expenses_id_seq";

create sequence "public"."integrations_id_seq";

create sequence "public"."invoices_id_seq";

create sequence "public"."lease_documents_id_seq";

create sequence "public"."leases_id_seq";

create sequence "public"."maintenance_requests_id_seq";

create sequence "public"."payments_id_seq";

create sequence "public"."properties_id_seq";

create sequence "public"."property_units_id_seq";

create sequence "public"."tenants_id_seq";

create sequence "public"."users_id_seq";

create table "public"."alembic_version" (
    "version_num" character varying(32) not null
);


alter table "public"."alembic_version" enable row level security;

create table "public"."expense_tax_details" (
    "id" integer not null default nextval('expense_tax_details_id_seq'::regclass),
    "tax_name" character varying not null,
    "tax_rate" numeric(5,2) not null,
    "tax_amount" numeric(12,2) not null,
    "expense_id" integer,
    "created_at" timestamp with time zone not null,
    "updated_at" timestamp with time zone not null
);


alter table "public"."expense_tax_details" enable row level security;

create table "public"."expenses" (
    "id" integer not null default nextval('expenses_id_seq'::regclass),
    "category" character varying not null,
    "description" character varying,
    "expense_date" timestamp with time zone not null,
    "receipt_url" character varying,
    "property_id" integer not null,
    "created_at" timestamp with time zone not null,
    "updated_at" timestamp with time zone not null,
    "subtotal_amount" numeric(12,2) not null,
    "total_tax_amount" numeric(12,2) not null default '0'::double precision,
    "quickbooks_id" character varying(64),
    "last_synced_at" timestamp with time zone
);


alter table "public"."expenses" enable row level security;

create table "public"."integrations" (
    "id" integer not null default nextval('integrations_id_seq'::regclass),
    "user_id" uuid not null,
    "integration_type" integration_type_enum not null,
    "status" integrationstatus not null default 'Disconnected'::integrationstatus,
    "apideck_consumer_id" character varying,
    "apideck_service_id" character varying,
    "connected_at" timestamp with time zone,
    "last_sync_at" timestamp with time zone,
    "connection_metadata" jsonb,
    "last_error" character varying(255),
    "error_count" integer not null default 0,
    "created_at" timestamp with time zone not null default now(),
    "updated_at" timestamp with time zone not null default now()
);


alter table "public"."integrations" enable row level security;

create table "public"."invoices" (
    "id" integer not null default nextval('invoices_id_seq'::regclass),
    "invoice_number" character varying not null,
    "amount" numeric(12,2) not null,
    "description" character varying not null,
    "issue_date" timestamp with time zone not null,
    "due_date" timestamp with time zone not null,
    "property_id" integer,
    "created_at" timestamp with time zone not null,
    "updated_at" timestamp with time zone not null,
    "status" paymentstatus not null default 'Pending'::paymentstatus,
    "tenant_id" integer,
    "quickbooks_id" character varying(64),
    "last_synced_at" timestamp with time zone
);


alter table "public"."invoices" enable row level security;

create table "public"."lease_documents" (
    "id" integer not null default nextval('lease_documents_id_seq'::regclass),
    "name" character varying not null,
    "file_path" character varying not null,
    "document_type" character varying not null,
    "upload_date" timestamp with time zone not null,
    "lease_id" integer,
    "uploaded_by_id" uuid
);


alter table "public"."lease_documents" enable row level security;

create table "public"."leases" (
    "id" integer not null default nextval('leases_id_seq'::regclass),
    "start_date" date not null,
    "end_date" date not null,
    "monthly_rent" numeric(12,2) not null,
    "security_deposit" numeric(12,2) not null,
    "status" leasestatus not null,
    "is_renewable" boolean not null,
    "auto_renew" boolean not null,
    "rent_due_day" integer not null,
    "late_fee_amount" numeric(12,2),
    "late_fee_after_days" integer,
    "special_terms" character varying,
    "property_id" integer not null,
    "unit_id" integer,
    "tenant_id" integer not null,
    "created_at" timestamp with time zone not null,
    "updated_at" timestamp with time zone not null
);


alter table "public"."leases" enable row level security;

create table "public"."maintenance_requests" (
    "id" integer not null default nextval('maintenance_requests_id_seq'::regclass),
    "issue_title" character varying(255) not null,
    "description" text,
    "property_id" integer not null,
    "unit_id" integer,
    "tenant_id" integer,
    "user_id" uuid,
    "request_date" timestamp with time zone not null default CURRENT_TIMESTAMP,
    "priority" maintenance_priority not null,
    "status" maintenance_status not null default 'Pending'::maintenance_status,
    "scheduled_date" date,
    "estimated_cost" numeric(10,2),
    "actual_cost" numeric(10,2),
    "photos" json,
    "created_at" timestamp with time zone not null default CURRENT_TIMESTAMP,
    "updated_at" timestamp with time zone not null default CURRENT_TIMESTAMP,
    "assigned_to" character varying(255)
);


alter table "public"."maintenance_requests" enable row level security;

create table "public"."payments" (
    "id" integer not null default nextval('payments_id_seq'::regclass),
    "amount" numeric(12,2) not null,
    "payment_date" timestamp with time zone not null,
    "lease_id" integer,
    "created_at" timestamp with time zone not null,
    "updated_at" timestamp with time zone not null,
    "description" character varying,
    "status" paymentstatus default 'Pending'::paymentstatus,
    "payment_method" paymentmethod not null,
    "transaction_reference" character varying,
    "receipt_url" character varying,
    "tenant_id" integer,
    "quickbooks_id" character varying(64),
    "last_synced_at" timestamp with time zone
);


alter table "public"."payments" enable row level security;

create table "public"."properties" (
    "id" integer not null default nextval('properties_id_seq'::regclass),
    "name" character varying,
    "address" character varying,
    "city" character varying,
    "province" character varying,
    "postal_code" character varying,
    "property_type" property_type_enum not null,
    "year_built" integer,
    "description" character varying,
    "status" propertystatus not null,
    "created_at" timestamp with time zone not null,
    "updated_at" timestamp with time zone not null,
    "user_id" uuid not null
);


alter table "public"."properties" enable row level security;

create table "public"."property_units" (
    "id" integer not null default nextval('property_units_id_seq'::regclass),
    "property_id" integer,
    "tenant_id" integer,
    "name" character varying not null,
    "description" character varying,
    "size" double precision,
    "monthly_rent" numeric(12,2),
    "is_rented" boolean not null,
    "bedrooms" integer,
    "bathrooms" double precision,
    "floor" integer,
    "created_at" timestamp with time zone not null,
    "updated_at" timestamp with time zone not null
);


alter table "public"."property_units" enable row level security;

create table "public"."tenant_unit_link" (
    "tenant_id" integer not null,
    "unit_id" integer not null,
    "start_date" timestamp without time zone,
    "end_date" timestamp without time zone
);


alter table "public"."tenant_unit_link" enable row level security;

create table "public"."tenants" (
    "id" integer not null default nextval('tenants_id_seq'::regclass),
    "user_id" uuid,
    "first_name" character varying(100) not null,
    "last_name" character varying(100) not null,
    "phone" character varying,
    "email" character varying,
    "status" tenantstatus not null,
    "created_at" timestamp with time zone not null,
    "updated_at" timestamp with time zone not null,
    "current_property_id" integer,
    "landlord_id" uuid not null,
    "quickbooks_id" character varying,
    "last_synced_at" timestamp with time zone,
    "profile_image_url" character varying
);


alter table "public"."tenants" enable row level security;

create table "public"."users" (
    "id" uuid not null default gen_random_uuid(),
    "email" character varying not null,
    "first_name" character varying,
    "last_name" character varying,
    "user_type" character varying,
    "phone" character varying,
    "address" character varying,
    "city" character varying,
    "province" character varying,
    "postal_code" character varying,
    "profile_image_url" character varying,
    "is_active" boolean not null,
    "is_admin" boolean not null,
    "created_at" timestamp with time zone not null,
    "updated_at" timestamp with time zone not null,
    "is_email_verified" boolean not null
);


alter table "public"."users" enable row level security;

alter sequence "public"."expense_tax_details_id_seq" owned by "public"."expense_tax_details"."id";

alter sequence "public"."expenses_id_seq" owned by "public"."expenses"."id";

alter sequence "public"."integrations_id_seq" owned by "public"."integrations"."id";

alter sequence "public"."invoices_id_seq" owned by "public"."invoices"."id";

alter sequence "public"."lease_documents_id_seq" owned by "public"."lease_documents"."id";

alter sequence "public"."leases_id_seq" owned by "public"."leases"."id";

alter sequence "public"."maintenance_requests_id_seq" owned by "public"."maintenance_requests"."id";

alter sequence "public"."payments_id_seq" owned by "public"."payments"."id";

alter sequence "public"."properties_id_seq" owned by "public"."properties"."id";

alter sequence "public"."property_units_id_seq" owned by "public"."property_units"."id";

alter sequence "public"."tenants_id_seq" owned by "public"."tenants"."id";

alter sequence "public"."users_id_seq" owned by "public"."users"."id";

CREATE UNIQUE INDEX alembic_version_pkc ON public.alembic_version USING btree (version_num);

CREATE UNIQUE INDEX expense_tax_details_pkey ON public.expense_tax_details USING btree (id);

CREATE UNIQUE INDEX expenses_pkey ON public.expenses USING btree (id);

CREATE UNIQUE INDEX expenses_quickbooks_id_key ON public.expenses USING btree (quickbooks_id);

CREATE INDEX idx_integration_type ON public.integrations USING btree (integration_type);

CREATE INDEX idx_integration_user_id ON public.integrations USING btree (user_id);

CREATE INDEX idx_integration_user_type ON public.integrations USING btree (user_id, integration_type);

CREATE UNIQUE INDEX idx_tenant_email_unique_per_landlord ON public.tenants USING btree (landlord_id, lower((email)::text)) WHERE (email IS NOT NULL);

CREATE INDEX idx_tenants_email_lower ON public.tenants USING btree (lower((email)::text)) WHERE (email IS NOT NULL);

CREATE INDEX idx_tenants_landlord_id ON public.tenants USING btree (landlord_id);

CREATE UNIQUE INDEX integrations_pkey ON public.integrations USING btree (id);

CREATE UNIQUE INDEX invoices_pkey ON public.invoices USING btree (id);

CREATE INDEX ix_expense_tax_details_expense_id ON public.expense_tax_details USING btree (expense_id);

CREATE INDEX ix_expenses_property_id ON public.expenses USING btree (property_id);

CREATE INDEX ix_invoices_last_synced_at ON public.invoices USING btree (last_synced_at);

CREATE INDEX ix_invoices_property_id ON public.invoices USING btree (property_id);

CREATE INDEX ix_invoices_tenant_id ON public.invoices USING btree (tenant_id);

CREATE INDEX ix_lease_documents_lease_id ON public.lease_documents USING btree (lease_id);

CREATE INDEX ix_lease_documents_uploaded_by_id ON public.lease_documents USING btree (uploaded_by_id);

CREATE INDEX ix_leases_property_id ON public.leases USING btree (property_id);

CREATE INDEX ix_leases_status ON public.leases USING btree (status);

CREATE INDEX ix_leases_tenant_id ON public.leases USING btree (tenant_id);

CREATE INDEX ix_leases_unit_id ON public.leases USING btree (unit_id);

CREATE INDEX ix_maintenance_requests_property_id ON public.maintenance_requests USING btree (property_id);

CREATE INDEX ix_maintenance_requests_tenant_id ON public.maintenance_requests USING btree (tenant_id);

CREATE INDEX ix_maintenance_requests_unit_id ON public.maintenance_requests USING btree (unit_id);

CREATE INDEX ix_maintenance_requests_user_id ON public.maintenance_requests USING btree (user_id);

CREATE INDEX ix_payments_lease_id ON public.payments USING btree (lease_id);

CREATE INDEX ix_payments_tenant_id ON public.payments USING btree (tenant_id);

CREATE INDEX ix_properties_user_id ON public.properties USING btree (user_id);

CREATE INDEX ix_property_units_name ON public.property_units USING btree (name);

CREATE INDEX ix_property_units_property_tenant ON public.property_units USING btree (property_id, tenant_id);

CREATE INDEX ix_tenant_unit_link_unit_id ON public.tenant_unit_link USING btree (unit_id);

CREATE INDEX ix_tenants_current_property_id ON public.tenants USING btree (current_property_id);

CREATE INDEX ix_tenants_status ON public.tenants USING btree (status);

CREATE INDEX ix_tenants_user_id ON public.tenants USING btree (user_id);

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);

CREATE UNIQUE INDEX lease_documents_pkey ON public.lease_documents USING btree (id);

CREATE UNIQUE INDEX leases_pkey ON public.leases USING btree (id);

CREATE UNIQUE INDEX maintenance_requests_pkey ON public.maintenance_requests USING btree (id);

CREATE UNIQUE INDEX payments_pkey ON public.payments USING btree (id);

CREATE UNIQUE INDEX properties_pkey ON public.properties USING btree (id);

CREATE UNIQUE INDEX property_units_pkey ON public.property_units USING btree (id);

CREATE UNIQUE INDEX tenant_unit_link_pkey ON public.tenant_unit_link USING btree (tenant_id, unit_id);

CREATE UNIQUE INDEX tenants_pkey ON public.tenants USING btree (id);

CREATE UNIQUE INDEX unique_user_integration ON public.integrations USING btree (user_id, integration_type);

CREATE UNIQUE INDEX uq_invoices_invoice_number ON public.invoices USING btree (invoice_number);

CREATE UNIQUE INDEX uq_invoices_quickbooks_id ON public.invoices USING btree (quickbooks_id);

CREATE UNIQUE INDEX uq_payments_quickbooks_id ON public.payments USING btree (quickbooks_id);

CREATE UNIQUE INDEX users_pkey ON public.users USING btree (id);

alter table "public"."alembic_version" add constraint "alembic_version_pkc" PRIMARY KEY using index "alembic_version_pkc";

alter table "public"."expense_tax_details" add constraint "expense_tax_details_pkey" PRIMARY KEY using index "expense_tax_details_pkey";

alter table "public"."expenses" add constraint "expenses_pkey" PRIMARY KEY using index "expenses_pkey";

alter table "public"."integrations" add constraint "integrations_pkey" PRIMARY KEY using index "integrations_pkey";

alter table "public"."invoices" add constraint "invoices_pkey" PRIMARY KEY using index "invoices_pkey";

alter table "public"."lease_documents" add constraint "lease_documents_pkey" PRIMARY KEY using index "lease_documents_pkey";

alter table "public"."leases" add constraint "leases_pkey" PRIMARY KEY using index "leases_pkey";

alter table "public"."maintenance_requests" add constraint "maintenance_requests_pkey" PRIMARY KEY using index "maintenance_requests_pkey";

alter table "public"."payments" add constraint "payments_pkey" PRIMARY KEY using index "payments_pkey";

alter table "public"."properties" add constraint "properties_pkey" PRIMARY KEY using index "properties_pkey";

alter table "public"."property_units" add constraint "property_units_pkey" PRIMARY KEY using index "property_units_pkey";

alter table "public"."tenant_unit_link" add constraint "tenant_unit_link_pkey" PRIMARY KEY using index "tenant_unit_link_pkey";

alter table "public"."tenants" add constraint "tenants_pkey" PRIMARY KEY using index "tenants_pkey";

alter table "public"."users" add constraint "users_pkey" PRIMARY KEY using index "users_pkey";

alter table "public"."expense_tax_details" add constraint "expense_tax_details_expense_id_fkey" FOREIGN KEY (expense_id) REFERENCES expenses(id) not valid;

alter table "public"."expense_tax_details" validate constraint "expense_tax_details_expense_id_fkey";

alter table "public"."expenses" add constraint "expenses_property_id_fkey" FOREIGN KEY (property_id) REFERENCES properties(id) not valid;

alter table "public"."expenses" validate constraint "expenses_property_id_fkey";

alter table "public"."expenses" add constraint "expenses_quickbooks_id_key" UNIQUE using index "expenses_quickbooks_id_key";

alter table "public"."integrations" add constraint "integrations_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(id) not valid;

alter table "public"."integrations" validate constraint "integrations_user_id_fkey";

alter table "public"."integrations" add constraint "unique_user_integration" UNIQUE using index "unique_user_integration";

alter table "public"."invoices" add constraint "invoices_property_id_fkey" FOREIGN KEY (property_id) REFERENCES properties(id) not valid;

alter table "public"."invoices" validate constraint "invoices_property_id_fkey";

alter table "public"."invoices" add constraint "invoices_tenant_id_fkey" FOREIGN KEY (tenant_id) REFERENCES tenants(id) not valid;

alter table "public"."invoices" validate constraint "invoices_tenant_id_fkey";

alter table "public"."invoices" add constraint "uq_invoices_invoice_number" UNIQUE using index "uq_invoices_invoice_number";

alter table "public"."invoices" add constraint "uq_invoices_quickbooks_id" UNIQUE using index "uq_invoices_quickbooks_id";

alter table "public"."lease_documents" add constraint "lease_documents_lease_id_fkey_corrected" FOREIGN KEY (lease_id) REFERENCES leases(id) ON DELETE CASCADE not valid;

alter table "public"."lease_documents" validate constraint "lease_documents_lease_id_fkey_corrected";

alter table "public"."lease_documents" add constraint "lease_documents_uploaded_by_id_fkey" FOREIGN KEY (uploaded_by_id) REFERENCES users(id) ON DELETE SET NULL not valid;

alter table "public"."lease_documents" validate constraint "lease_documents_uploaded_by_id_fkey";

alter table "public"."leases" add constraint "leases_property_id_fkey" FOREIGN KEY (property_id) REFERENCES properties(id) not valid;

alter table "public"."leases" validate constraint "leases_property_id_fkey";

alter table "public"."leases" add constraint "leases_tenant_id_fkey" FOREIGN KEY (tenant_id) REFERENCES tenants(id) not valid;

alter table "public"."leases" validate constraint "leases_tenant_id_fkey";

alter table "public"."leases" add constraint "leases_unit_id_fkey" FOREIGN KEY (unit_id) REFERENCES property_units(id) not valid;

alter table "public"."leases" validate constraint "leases_unit_id_fkey";

alter table "public"."maintenance_requests" add constraint "maintenance_requests_property_id_fkey" FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE not valid;

alter table "public"."maintenance_requests" validate constraint "maintenance_requests_property_id_fkey";

alter table "public"."maintenance_requests" add constraint "maintenance_requests_tenant_id_fkey" FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE SET NULL not valid;

alter table "public"."maintenance_requests" validate constraint "maintenance_requests_tenant_id_fkey";

alter table "public"."maintenance_requests" add constraint "maintenance_requests_unit_id_fkey" FOREIGN KEY (unit_id) REFERENCES property_units(id) ON DELETE SET NULL not valid;

alter table "public"."maintenance_requests" validate constraint "maintenance_requests_unit_id_fkey";

alter table "public"."maintenance_requests" add constraint "maintenance_requests_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL not valid;

alter table "public"."maintenance_requests" validate constraint "maintenance_requests_user_id_fkey";

alter table "public"."payments" add constraint "payments_lease_id_fkey" FOREIGN KEY (lease_id) REFERENCES leases(id) ON DELETE SET NULL not valid;

alter table "public"."payments" validate constraint "payments_lease_id_fkey";

alter table "public"."payments" add constraint "payments_tenant_id_fkey" FOREIGN KEY (tenant_id) REFERENCES tenants(id) not valid;

alter table "public"."payments" validate constraint "payments_tenant_id_fkey";

alter table "public"."payments" add constraint "uq_payments_quickbooks_id" UNIQUE using index "uq_payments_quickbooks_id";

alter table "public"."properties" add constraint "properties_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE not valid;

alter table "public"."properties" validate constraint "properties_user_id_fkey";

alter table "public"."property_units" add constraint "property_units_property_id_fkey_corrected" FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE not valid;

alter table "public"."property_units" validate constraint "property_units_property_id_fkey_corrected";

alter table "public"."property_units" add constraint "property_units_tenant_id_fkey" FOREIGN KEY (tenant_id) REFERENCES tenants(id) not valid;

alter table "public"."property_units" validate constraint "property_units_tenant_id_fkey";

alter table "public"."tenant_unit_link" add constraint "tenant_unit_link_tenant_id_fkey" FOREIGN KEY (tenant_id) REFERENCES tenants(id) not valid;

alter table "public"."tenant_unit_link" validate constraint "tenant_unit_link_tenant_id_fkey";

alter table "public"."tenant_unit_link" add constraint "tenant_unit_link_unit_id_fkey" FOREIGN KEY (unit_id) REFERENCES property_units(id) not valid;

alter table "public"."tenant_unit_link" validate constraint "tenant_unit_link_unit_id_fkey";

alter table "public"."tenants" add constraint "tenants_current_property_id_fkey_corrected" FOREIGN KEY (current_property_id) REFERENCES properties(id) ON DELETE SET NULL not valid;

alter table "public"."tenants" validate constraint "tenants_current_property_id_fkey_corrected";

alter table "public"."tenants" add constraint "tenants_landlord_id_fkey" FOREIGN KEY (landlord_id) REFERENCES users(id) not valid;

alter table "public"."tenants" validate constraint "tenants_landlord_id_fkey";

alter table "public"."tenants" add constraint "tenants_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL not valid;

alter table "public"."tenants" validate constraint "tenants_user_id_fkey";

set check_function_bodies = off;

CREATE OR REPLACE FUNCTION public.get_current_app_user_id()
 RETURNS uuid
 LANGUAGE plpgsql
 STABLE
 SET search_path TO 'public'
AS $function$
BEGIN
  RETURN auth.uid();
END;
$function$
;

CREATE OR REPLACE FUNCTION public.is_current_user_landlord()
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE
 SET search_path TO 'public'
AS $function$
BEGIN
  RETURN EXISTS (
    SELECT 1 FROM public.users
    WHERE auth_provider_id = auth.uid() AND user_type = 'LANDLORD'
  );
END;
$function$
;

CREATE OR REPLACE FUNCTION public.is_expense_owner(p_expense_id integer, p_user_id uuid)
 RETURNS boolean
 LANGUAGE sql
 STABLE SECURITY DEFINER
AS $function$
  SELECT EXISTS (
    SELECT 1
    FROM public.expenses e
    JOIN public.properties p ON e.property_id = p.id
    WHERE e.id = p_expense_id AND p.user_id = p_user_id
  );
$function$
;

CREATE OR REPLACE FUNCTION public.update_updated_at_column()
 RETURNS trigger
 LANGUAGE plpgsql
 SET search_path TO ''
AS $function$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$function$
;

grant delete on table "public"."alembic_version" to "anon";

grant insert on table "public"."alembic_version" to "anon";

grant references on table "public"."alembic_version" to "anon";

grant select on table "public"."alembic_version" to "anon";

grant trigger on table "public"."alembic_version" to "anon";

grant truncate on table "public"."alembic_version" to "anon";

grant update on table "public"."alembic_version" to "anon";

grant delete on table "public"."alembic_version" to "authenticated";

grant insert on table "public"."alembic_version" to "authenticated";

grant references on table "public"."alembic_version" to "authenticated";

grant select on table "public"."alembic_version" to "authenticated";

grant trigger on table "public"."alembic_version" to "authenticated";

grant truncate on table "public"."alembic_version" to "authenticated";

grant update on table "public"."alembic_version" to "authenticated";

grant delete on table "public"."alembic_version" to "service_role";

grant insert on table "public"."alembic_version" to "service_role";

grant references on table "public"."alembic_version" to "service_role";

grant select on table "public"."alembic_version" to "service_role";

grant trigger on table "public"."alembic_version" to "service_role";

grant truncate on table "public"."alembic_version" to "service_role";

grant update on table "public"."alembic_version" to "service_role";

grant delete on table "public"."expense_tax_details" to "anon";

grant insert on table "public"."expense_tax_details" to "anon";

grant references on table "public"."expense_tax_details" to "anon";

grant select on table "public"."expense_tax_details" to "anon";

grant trigger on table "public"."expense_tax_details" to "anon";

grant truncate on table "public"."expense_tax_details" to "anon";

grant update on table "public"."expense_tax_details" to "anon";

grant delete on table "public"."expense_tax_details" to "authenticated";

grant insert on table "public"."expense_tax_details" to "authenticated";

grant references on table "public"."expense_tax_details" to "authenticated";

grant select on table "public"."expense_tax_details" to "authenticated";

grant trigger on table "public"."expense_tax_details" to "authenticated";

grant truncate on table "public"."expense_tax_details" to "authenticated";

grant update on table "public"."expense_tax_details" to "authenticated";

grant delete on table "public"."expense_tax_details" to "service_role";

grant insert on table "public"."expense_tax_details" to "service_role";

grant references on table "public"."expense_tax_details" to "service_role";

grant select on table "public"."expense_tax_details" to "service_role";

grant trigger on table "public"."expense_tax_details" to "service_role";

grant truncate on table "public"."expense_tax_details" to "service_role";

grant update on table "public"."expense_tax_details" to "service_role";

grant delete on table "public"."expenses" to "anon";

grant insert on table "public"."expenses" to "anon";

grant references on table "public"."expenses" to "anon";

grant select on table "public"."expenses" to "anon";

grant trigger on table "public"."expenses" to "anon";

grant truncate on table "public"."expenses" to "anon";

grant update on table "public"."expenses" to "anon";

grant delete on table "public"."expenses" to "authenticated";

grant insert on table "public"."expenses" to "authenticated";

grant references on table "public"."expenses" to "authenticated";

grant select on table "public"."expenses" to "authenticated";

grant trigger on table "public"."expenses" to "authenticated";

grant truncate on table "public"."expenses" to "authenticated";

grant update on table "public"."expenses" to "authenticated";

grant delete on table "public"."expenses" to "service_role";

grant insert on table "public"."expenses" to "service_role";

grant references on table "public"."expenses" to "service_role";

grant select on table "public"."expenses" to "service_role";

grant trigger on table "public"."expenses" to "service_role";

grant truncate on table "public"."expenses" to "service_role";

grant update on table "public"."expenses" to "service_role";

grant delete on table "public"."integrations" to "anon";

grant insert on table "public"."integrations" to "anon";

grant references on table "public"."integrations" to "anon";

grant select on table "public"."integrations" to "anon";

grant trigger on table "public"."integrations" to "anon";

grant truncate on table "public"."integrations" to "anon";

grant update on table "public"."integrations" to "anon";

grant delete on table "public"."integrations" to "authenticated";

grant insert on table "public"."integrations" to "authenticated";

grant references on table "public"."integrations" to "authenticated";

grant select on table "public"."integrations" to "authenticated";

grant trigger on table "public"."integrations" to "authenticated";

grant truncate on table "public"."integrations" to "authenticated";

grant update on table "public"."integrations" to "authenticated";

grant delete on table "public"."integrations" to "service_role";

grant insert on table "public"."integrations" to "service_role";

grant references on table "public"."integrations" to "service_role";

grant select on table "public"."integrations" to "service_role";

grant trigger on table "public"."integrations" to "service_role";

grant truncate on table "public"."integrations" to "service_role";

grant update on table "public"."integrations" to "service_role";

grant delete on table "public"."invoices" to "anon";

grant insert on table "public"."invoices" to "anon";

grant references on table "public"."invoices" to "anon";

grant select on table "public"."invoices" to "anon";

grant trigger on table "public"."invoices" to "anon";

grant truncate on table "public"."invoices" to "anon";

grant update on table "public"."invoices" to "anon";

grant delete on table "public"."invoices" to "authenticated";

grant insert on table "public"."invoices" to "authenticated";

grant references on table "public"."invoices" to "authenticated";

grant select on table "public"."invoices" to "authenticated";

grant trigger on table "public"."invoices" to "authenticated";

grant truncate on table "public"."invoices" to "authenticated";

grant update on table "public"."invoices" to "authenticated";

grant delete on table "public"."invoices" to "service_role";

grant insert on table "public"."invoices" to "service_role";

grant references on table "public"."invoices" to "service_role";

grant select on table "public"."invoices" to "service_role";

grant trigger on table "public"."invoices" to "service_role";

grant truncate on table "public"."invoices" to "service_role";

grant update on table "public"."invoices" to "service_role";

grant delete on table "public"."lease_documents" to "anon";

grant insert on table "public"."lease_documents" to "anon";

grant references on table "public"."lease_documents" to "anon";

grant select on table "public"."lease_documents" to "anon";

grant trigger on table "public"."lease_documents" to "anon";

grant truncate on table "public"."lease_documents" to "anon";

grant update on table "public"."lease_documents" to "anon";

grant delete on table "public"."lease_documents" to "authenticated";

grant insert on table "public"."lease_documents" to "authenticated";

grant references on table "public"."lease_documents" to "authenticated";

grant select on table "public"."lease_documents" to "authenticated";

grant trigger on table "public"."lease_documents" to "authenticated";

grant truncate on table "public"."lease_documents" to "authenticated";

grant update on table "public"."lease_documents" to "authenticated";

grant delete on table "public"."lease_documents" to "service_role";

grant insert on table "public"."lease_documents" to "service_role";

grant references on table "public"."lease_documents" to "service_role";

grant select on table "public"."lease_documents" to "service_role";

grant trigger on table "public"."lease_documents" to "service_role";

grant truncate on table "public"."lease_documents" to "service_role";

grant update on table "public"."lease_documents" to "service_role";

grant delete on table "public"."leases" to "anon";

grant insert on table "public"."leases" to "anon";

grant references on table "public"."leases" to "anon";

grant select on table "public"."leases" to "anon";

grant trigger on table "public"."leases" to "anon";

grant truncate on table "public"."leases" to "anon";

grant update on table "public"."leases" to "anon";

grant delete on table "public"."leases" to "authenticated";

grant insert on table "public"."leases" to "authenticated";

grant references on table "public"."leases" to "authenticated";

grant select on table "public"."leases" to "authenticated";

grant trigger on table "public"."leases" to "authenticated";

grant truncate on table "public"."leases" to "authenticated";

grant update on table "public"."leases" to "authenticated";

grant delete on table "public"."leases" to "service_role";

grant insert on table "public"."leases" to "service_role";

grant references on table "public"."leases" to "service_role";

grant select on table "public"."leases" to "service_role";

grant trigger on table "public"."leases" to "service_role";

grant truncate on table "public"."leases" to "service_role";

grant update on table "public"."leases" to "service_role";

grant delete on table "public"."maintenance_requests" to "anon";

grant insert on table "public"."maintenance_requests" to "anon";

grant references on table "public"."maintenance_requests" to "anon";

grant select on table "public"."maintenance_requests" to "anon";

grant trigger on table "public"."maintenance_requests" to "anon";

grant truncate on table "public"."maintenance_requests" to "anon";

grant update on table "public"."maintenance_requests" to "anon";

grant delete on table "public"."maintenance_requests" to "authenticated";

grant insert on table "public"."maintenance_requests" to "authenticated";

grant references on table "public"."maintenance_requests" to "authenticated";

grant select on table "public"."maintenance_requests" to "authenticated";

grant trigger on table "public"."maintenance_requests" to "authenticated";

grant truncate on table "public"."maintenance_requests" to "authenticated";

grant update on table "public"."maintenance_requests" to "authenticated";

grant delete on table "public"."maintenance_requests" to "service_role";

grant insert on table "public"."maintenance_requests" to "service_role";

grant references on table "public"."maintenance_requests" to "service_role";

grant select on table "public"."maintenance_requests" to "service_role";

grant trigger on table "public"."maintenance_requests" to "service_role";

grant truncate on table "public"."maintenance_requests" to "service_role";

grant update on table "public"."maintenance_requests" to "service_role";

grant delete on table "public"."payments" to "anon";

grant insert on table "public"."payments" to "anon";

grant references on table "public"."payments" to "anon";

grant select on table "public"."payments" to "anon";

grant trigger on table "public"."payments" to "anon";

grant truncate on table "public"."payments" to "anon";

grant update on table "public"."payments" to "anon";

grant delete on table "public"."payments" to "authenticated";

grant insert on table "public"."payments" to "authenticated";

grant references on table "public"."payments" to "authenticated";

grant select on table "public"."payments" to "authenticated";

grant trigger on table "public"."payments" to "authenticated";

grant truncate on table "public"."payments" to "authenticated";

grant update on table "public"."payments" to "authenticated";

grant delete on table "public"."payments" to "service_role";

grant insert on table "public"."payments" to "service_role";

grant references on table "public"."payments" to "service_role";

grant select on table "public"."payments" to "service_role";

grant trigger on table "public"."payments" to "service_role";

grant truncate on table "public"."payments" to "service_role";

grant update on table "public"."payments" to "service_role";

grant delete on table "public"."properties" to "anon";

grant insert on table "public"."properties" to "anon";

grant references on table "public"."properties" to "anon";

grant select on table "public"."properties" to "anon";

grant trigger on table "public"."properties" to "anon";

grant truncate on table "public"."properties" to "anon";

grant update on table "public"."properties" to "anon";

grant delete on table "public"."properties" to "authenticated";

grant insert on table "public"."properties" to "authenticated";

grant references on table "public"."properties" to "authenticated";

grant select on table "public"."properties" to "authenticated";

grant trigger on table "public"."properties" to "authenticated";

grant truncate on table "public"."properties" to "authenticated";

grant update on table "public"."properties" to "authenticated";

grant delete on table "public"."properties" to "service_role";

grant insert on table "public"."properties" to "service_role";

grant references on table "public"."properties" to "service_role";

grant select on table "public"."properties" to "service_role";

grant trigger on table "public"."properties" to "service_role";

grant truncate on table "public"."properties" to "service_role";

grant update on table "public"."properties" to "service_role";

grant delete on table "public"."property_units" to "anon";

grant insert on table "public"."property_units" to "anon";

grant references on table "public"."property_units" to "anon";

grant select on table "public"."property_units" to "anon";

grant trigger on table "public"."property_units" to "anon";

grant truncate on table "public"."property_units" to "anon";

grant update on table "public"."property_units" to "anon";

grant delete on table "public"."property_units" to "authenticated";

grant insert on table "public"."property_units" to "authenticated";

grant references on table "public"."property_units" to "authenticated";

grant select on table "public"."property_units" to "authenticated";

grant trigger on table "public"."property_units" to "authenticated";

grant truncate on table "public"."property_units" to "authenticated";

grant update on table "public"."property_units" to "authenticated";

grant delete on table "public"."property_units" to "service_role";

grant insert on table "public"."property_units" to "service_role";

grant references on table "public"."property_units" to "service_role";

grant select on table "public"."property_units" to "service_role";

grant trigger on table "public"."property_units" to "service_role";

grant truncate on table "public"."property_units" to "service_role";

grant update on table "public"."property_units" to "service_role";

grant delete on table "public"."tenant_unit_link" to "anon";

grant insert on table "public"."tenant_unit_link" to "anon";

grant references on table "public"."tenant_unit_link" to "anon";

grant select on table "public"."tenant_unit_link" to "anon";

grant trigger on table "public"."tenant_unit_link" to "anon";

grant truncate on table "public"."tenant_unit_link" to "anon";

grant update on table "public"."tenant_unit_link" to "anon";

grant delete on table "public"."tenant_unit_link" to "authenticated";

grant insert on table "public"."tenant_unit_link" to "authenticated";

grant references on table "public"."tenant_unit_link" to "authenticated";

grant select on table "public"."tenant_unit_link" to "authenticated";

grant trigger on table "public"."tenant_unit_link" to "authenticated";

grant truncate on table "public"."tenant_unit_link" to "authenticated";

grant update on table "public"."tenant_unit_link" to "authenticated";

grant delete on table "public"."tenant_unit_link" to "service_role";

grant insert on table "public"."tenant_unit_link" to "service_role";

grant references on table "public"."tenant_unit_link" to "service_role";

grant select on table "public"."tenant_unit_link" to "service_role";

grant trigger on table "public"."tenant_unit_link" to "service_role";

grant truncate on table "public"."tenant_unit_link" to "service_role";

grant update on table "public"."tenant_unit_link" to "service_role";

grant delete on table "public"."tenants" to "anon";

grant insert on table "public"."tenants" to "anon";

grant references on table "public"."tenants" to "anon";

grant select on table "public"."tenants" to "anon";

grant trigger on table "public"."tenants" to "anon";

grant truncate on table "public"."tenants" to "anon";

grant update on table "public"."tenants" to "anon";

grant delete on table "public"."tenants" to "authenticated";

grant insert on table "public"."tenants" to "authenticated";

grant references on table "public"."tenants" to "authenticated";

grant select on table "public"."tenants" to "authenticated";

grant trigger on table "public"."tenants" to "authenticated";

grant truncate on table "public"."tenants" to "authenticated";

grant update on table "public"."tenants" to "authenticated";

grant delete on table "public"."tenants" to "service_role";

grant insert on table "public"."tenants" to "service_role";

grant references on table "public"."tenants" to "service_role";

grant select on table "public"."tenants" to "service_role";

grant trigger on table "public"."tenants" to "service_role";

grant truncate on table "public"."tenants" to "service_role";

grant update on table "public"."tenants" to "service_role";

grant delete on table "public"."users" to "anon";

grant insert on table "public"."users" to "anon";

grant references on table "public"."users" to "anon";

grant select on table "public"."users" to "anon";

grant trigger on table "public"."users" to "anon";

grant truncate on table "public"."users" to "anon";

grant update on table "public"."users" to "anon";

grant delete on table "public"."users" to "authenticated";

grant insert on table "public"."users" to "authenticated";

grant references on table "public"."users" to "authenticated";

grant select on table "public"."users" to "authenticated";

grant trigger on table "public"."users" to "authenticated";

grant truncate on table "public"."users" to "authenticated";

grant update on table "public"."users" to "authenticated";

grant delete on table "public"."users" to "service_role";

grant insert on table "public"."users" to "service_role";

grant references on table "public"."users" to "service_role";

grant select on table "public"."users" to "service_role";

grant trigger on table "public"."users" to "service_role";

grant truncate on table "public"."users" to "service_role";

grant update on table "public"."users" to "service_role";

grant delete on table "public"."wrappers_fdw_stats" to "anon";

grant insert on table "public"."wrappers_fdw_stats" to "anon";

grant references on table "public"."wrappers_fdw_stats" to "anon";

grant select on table "public"."wrappers_fdw_stats" to "anon";

grant trigger on table "public"."wrappers_fdw_stats" to "anon";

grant truncate on table "public"."wrappers_fdw_stats" to "anon";

grant update on table "public"."wrappers_fdw_stats" to "anon";

grant delete on table "public"."wrappers_fdw_stats" to "authenticated";

grant insert on table "public"."wrappers_fdw_stats" to "authenticated";

grant references on table "public"."wrappers_fdw_stats" to "authenticated";

grant select on table "public"."wrappers_fdw_stats" to "authenticated";

grant trigger on table "public"."wrappers_fdw_stats" to "authenticated";

grant truncate on table "public"."wrappers_fdw_stats" to "authenticated";

grant update on table "public"."wrappers_fdw_stats" to "authenticated";

grant delete on table "public"."wrappers_fdw_stats" to "postgres";

grant insert on table "public"."wrappers_fdw_stats" to "postgres";

grant references on table "public"."wrappers_fdw_stats" to "postgres";

grant select on table "public"."wrappers_fdw_stats" to "postgres";

grant trigger on table "public"."wrappers_fdw_stats" to "postgres";

grant truncate on table "public"."wrappers_fdw_stats" to "postgres";

grant update on table "public"."wrappers_fdw_stats" to "postgres";

grant delete on table "public"."wrappers_fdw_stats" to "service_role";

grant insert on table "public"."wrappers_fdw_stats" to "service_role";

grant references on table "public"."wrappers_fdw_stats" to "service_role";

grant select on table "public"."wrappers_fdw_stats" to "service_role";

grant trigger on table "public"."wrappers_fdw_stats" to "service_role";

grant truncate on table "public"."wrappers_fdw_stats" to "service_role";

grant update on table "public"."wrappers_fdw_stats" to "service_role";

create policy "Allow authenticated read access to alembic version"
on "public"."alembic_version"
as permissive
for select
to authenticated
using (true);


create policy "Expense Tax Details Delete Access Control"
on "public"."expense_tax_details"
as permissive
for delete
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (expense_id IN ( SELECT exp.id
   FROM expenses exp
  WHERE (exp.property_id IN ( SELECT prop.id
           FROM properties prop
          WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))))));


create policy "Expense Tax Details Insert Access Control"
on "public"."expense_tax_details"
as permissive
for insert
to authenticated
with check (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (expense_id IN ( SELECT exp.id
   FROM expenses exp
  WHERE (exp.property_id IN ( SELECT prop.id
           FROM properties prop
          WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))))));


create policy "Expense Tax Details Select Access Control"
on "public"."expense_tax_details"
as permissive
for select
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (expense_id IN ( SELECT exp.id
   FROM expenses exp
  WHERE (exp.property_id IN ( SELECT prop.id
           FROM properties prop
          WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))))));


create policy "Expense Tax Details Update Access Control"
on "public"."expense_tax_details"
as permissive
for update
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (expense_id IN ( SELECT exp.id
   FROM expenses exp
  WHERE (exp.property_id IN ( SELECT prop.id
           FROM properties prop
          WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))))))
with check (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (expense_id IN ( SELECT exp.id
   FROM expenses exp
  WHERE (exp.property_id IN ( SELECT prop.id
           FROM properties prop
          WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))))));


create policy "Expenses Delete Access Control"
on "public"."expenses"
as permissive
for delete
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (property_id IN ( SELECT prop.id
   FROM properties prop
  WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))));


create policy "Expenses Insert Access Control"
on "public"."expenses"
as permissive
for insert
to authenticated
with check (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (property_id IN ( SELECT prop.id
   FROM properties prop
  WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))));


create policy "Expenses Select Access Control"
on "public"."expenses"
as permissive
for select
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (property_id IN ( SELECT prop.id
   FROM properties prop
  WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))));


create policy "Expenses Update Access Control"
on "public"."expenses"
as permissive
for update
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (property_id IN ( SELECT prop.id
   FROM properties prop
  WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))))
with check (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (property_id IN ( SELECT prop.id
   FROM properties prop
  WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))));


create policy "Integrations Delete Access Control"
on "public"."integrations"
as permissive
for delete
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR (user_id = ( SELECT auth.uid() AS uid))));


create policy "Integrations Insert Access Control"
on "public"."integrations"
as permissive
for insert
to authenticated
with check (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR (user_id = ( SELECT auth.uid() AS uid))));


create policy "Integrations Select Access Control"
on "public"."integrations"
as permissive
for select
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR (user_id = ( SELECT auth.uid() AS uid))));


create policy "Integrations Update Access Control"
on "public"."integrations"
as permissive
for update
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR (user_id = ( SELECT auth.uid() AS uid))))
with check (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR (user_id = ( SELECT auth.uid() AS uid))));


create policy "Invoices Delete Access Control"
on "public"."invoices"
as permissive
for delete
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (property_id IN ( SELECT prop.id
   FROM properties prop
  WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))));


create policy "Invoices Insert Access Control"
on "public"."invoices"
as permissive
for insert
to authenticated
with check (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (property_id IN ( SELECT prop.id
   FROM properties prop
  WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))));


create policy "Invoices Select Access Control"
on "public"."invoices"
as permissive
for select
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (property_id IN ( SELECT prop.id
   FROM properties prop
  WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))));


create policy "Invoices Update Access Control"
on "public"."invoices"
as permissive
for update
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (property_id IN ( SELECT prop.id
   FROM properties prop
  WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))))
with check (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (property_id IN ( SELECT prop.id
   FROM properties prop
  WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))));


create policy "Lease Documents Delete Access Control"
on "public"."lease_documents"
as permissive
for delete
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (lease_id IN ( SELECT l.id
   FROM leases l
  WHERE (l.property_id IN ( SELECT prop.id
           FROM properties prop
          WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))))));


create policy "Lease Documents Insert Access Control"
on "public"."lease_documents"
as permissive
for insert
to authenticated
with check (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (lease_id IN ( SELECT l.id
   FROM leases l
  WHERE (l.property_id IN ( SELECT prop.id
           FROM properties prop
          WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))))));


create policy "Lease Documents Select Access Control"
on "public"."lease_documents"
as permissive
for select
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (lease_id IN ( SELECT l.id
   FROM leases l
  WHERE (l.property_id IN ( SELECT prop.id
           FROM properties prop
          WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))))));


create policy "Lease Documents Update Access Control"
on "public"."lease_documents"
as permissive
for update
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (lease_id IN ( SELECT l.id
   FROM leases l
  WHERE (l.property_id IN ( SELECT prop.id
           FROM properties prop
          WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))))))
with check (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (lease_id IN ( SELECT l.id
   FROM leases l
  WHERE (l.property_id IN ( SELECT prop.id
           FROM properties prop
          WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))))));


create policy "Leases Delete Access Control"
on "public"."leases"
as permissive
for delete
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (property_id IN ( SELECT prop.id
   FROM properties prop
  WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))));


create policy "Leases Insert Access Control"
on "public"."leases"
as permissive
for insert
to authenticated
with check (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (property_id IN ( SELECT prop.id
   FROM properties prop
  WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))));


create policy "Leases Select Access Control"
on "public"."leases"
as permissive
for select
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (property_id IN ( SELECT prop.id
   FROM properties prop
  WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))));


create policy "Leases Update Access Control"
on "public"."leases"
as permissive
for update
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (property_id IN ( SELECT prop.id
   FROM properties prop
  WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))))
with check (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (property_id IN ( SELECT prop.id
   FROM properties prop
  WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))));


create policy "Maintenance Requests Delete Access Control"
on "public"."maintenance_requests"
as permissive
for delete
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (property_id IN ( SELECT prop.id
   FROM properties prop
  WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))));


create policy "Maintenance Requests Insert Access Control"
on "public"."maintenance_requests"
as permissive
for insert
to authenticated
with check (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (property_id IN ( SELECT prop.id
   FROM properties prop
  WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))));


create policy "Maintenance Requests Select Access Control"
on "public"."maintenance_requests"
as permissive
for select
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (property_id IN ( SELECT prop.id
   FROM properties prop
  WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))));


create policy "Maintenance Requests Update Access Control"
on "public"."maintenance_requests"
as permissive
for update
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (property_id IN ( SELECT prop.id
   FROM properties prop
  WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))))
with check (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (property_id IN ( SELECT prop.id
   FROM properties prop
  WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))));


create policy "Payments Delete Access Control"
on "public"."payments"
as permissive
for delete
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (lease_id IN ( SELECT l.id
   FROM leases l
  WHERE (l.property_id IN ( SELECT prop.id
           FROM properties prop
          WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))))));


create policy "Payments Insert Access Control"
on "public"."payments"
as permissive
for insert
to authenticated
with check (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (lease_id IN ( SELECT l.id
   FROM leases l
  WHERE (l.property_id IN ( SELECT prop.id
           FROM properties prop
          WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))))));


create policy "Payments Select Access Control"
on "public"."payments"
as permissive
for select
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (lease_id IN ( SELECT l.id
   FROM leases l
  WHERE (l.property_id IN ( SELECT prop.id
           FROM properties prop
          WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))))));


create policy "Payments Update Access Control"
on "public"."payments"
as permissive
for update
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (lease_id IN ( SELECT l.id
   FROM leases l
  WHERE (l.property_id IN ( SELECT prop.id
           FROM properties prop
          WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))))))
with check (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (lease_id IN ( SELECT l.id
   FROM leases l
  WHERE (l.property_id IN ( SELECT prop.id
           FROM properties prop
          WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))))));


create policy "Properties Delete Access Control"
on "public"."properties"
as permissive
for delete
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (user_id = ( SELECT auth.uid() AS uid)))));


create policy "Properties Insert Access Control"
on "public"."properties"
as permissive
for insert
to authenticated
with check (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (user_id = ( SELECT auth.uid() AS uid)))));


create policy "Properties Select Access Control"
on "public"."properties"
as permissive
for select
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (user_id = ( SELECT auth.uid() AS uid)))));


create policy "Properties Update Access Control"
on "public"."properties"
as permissive
for update
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (user_id = ( SELECT auth.uid() AS uid)))))
with check (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (user_id = ( SELECT auth.uid() AS uid)))));


create policy "Property Units Delete Access Control"
on "public"."property_units"
as permissive
for delete
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (property_id IN ( SELECT prop.id
   FROM properties prop
  WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))));


create policy "Property Units Insert Access Control"
on "public"."property_units"
as permissive
for insert
to authenticated
with check (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (property_id IN ( SELECT prop.id
   FROM properties prop
  WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))));


create policy "Property Units Select Access Control"
on "public"."property_units"
as permissive
for select
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (property_id IN ( SELECT prop.id
   FROM properties prop
  WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))));


create policy "Property Units Update Access Control"
on "public"."property_units"
as permissive
for update
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (property_id IN ( SELECT prop.id
   FROM properties prop
  WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))))
with check (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (property_id IN ( SELECT prop.id
   FROM properties prop
  WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))));


create policy "Tenant Unit Link Delete Access Control"
on "public"."tenant_unit_link"
as permissive
for delete
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (unit_id IN ( SELECT pu.id
   FROM property_units pu
  WHERE (pu.property_id IN ( SELECT prop.id
           FROM properties prop
          WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))))));


create policy "Tenant Unit Link Insert Access Control"
on "public"."tenant_unit_link"
as permissive
for insert
to authenticated
with check (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (unit_id IN ( SELECT pu.id
   FROM property_units pu
  WHERE (pu.property_id IN ( SELECT prop.id
           FROM properties prop
          WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))))));


create policy "Tenant Unit Link Select Access Control"
on "public"."tenant_unit_link"
as permissive
for select
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (unit_id IN ( SELECT pu.id
   FROM property_units pu
  WHERE (pu.property_id IN ( SELECT prop.id
           FROM properties prop
          WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))))));


create policy "Tenant Unit Link Update Access Control"
on "public"."tenant_unit_link"
as permissive
for update
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (unit_id IN ( SELECT pu.id
   FROM property_units pu
  WHERE (pu.property_id IN ( SELECT prop.id
           FROM properties prop
          WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))))))
with check (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND (unit_id IN ( SELECT pu.id
   FROM property_units pu
  WHERE (pu.property_id IN ( SELECT prop.id
           FROM properties prop
          WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))))));


create policy "Tenant Delete Access Control"
on "public"."tenants"
as permissive
for delete
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND ((EXISTS ( SELECT 1
   FROM properties p
  WHERE ((p.user_id = ( SELECT auth.uid() AS uid)) AND (tenants.current_property_id = p.id)))) OR (EXISTS ( SELECT 1
   FROM (properties p
     JOIN leases l ON ((l.property_id = p.id)))
  WHERE ((p.user_id = ( SELECT auth.uid() AS uid)) AND (l.tenant_id = tenants.id))))))));


create policy "Tenant Insert Access Control"
on "public"."tenants"
as permissive
for insert
to authenticated
with check (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND ((current_property_id IS NULL) OR (EXISTS ( SELECT 1
   FROM properties p
  WHERE ((p.id = tenants.current_property_id) AND (p.user_id = ( SELECT auth.uid() AS uid)))))))));


create policy "Tenant Select Access Control"
on "public"."tenants"
as permissive
for select
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND ((EXISTS ( SELECT 1
   FROM properties p
  WHERE ((p.user_id = ( SELECT auth.uid() AS uid)) AND (tenants.current_property_id = p.id)))) OR (EXISTS ( SELECT 1
   FROM (properties p
     JOIN leases l ON ((l.property_id = p.id)))
  WHERE ((p.user_id = ( SELECT auth.uid() AS uid)) AND (l.tenant_id = tenants.id))))))));


create policy "Tenant Update Access Control"
on "public"."tenants"
as permissive
for update
to authenticated
using (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND ((EXISTS ( SELECT 1
   FROM properties p
  WHERE ((p.user_id = ( SELECT auth.uid() AS uid)) AND (tenants.current_property_id = p.id)))) OR (EXISTS ( SELECT 1
   FROM (properties p
     JOIN leases l ON ((l.property_id = p.id)))
  WHERE ((p.user_id = ( SELECT auth.uid() AS uid)) AND (l.tenant_id = tenants.id))))))))
with check (((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) OR ((EXISTS ( SELECT 1
   FROM users u
  WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) AND ((current_property_id IS NULL) OR (EXISTS ( SELECT 1
   FROM properties p
  WHERE ((p.id = tenants.current_property_id) AND (p.user_id = ( SELECT auth.uid() AS uid)))))))));


create policy "Users manage their own record"
on "public"."users"
as permissive
for all
to authenticated
using ((id = ( SELECT auth.uid() AS uid)))
with check ((id = ( SELECT auth.uid() AS uid)));


CREATE TRIGGER update_maintenance_requests_updated_at BEFORE UPDATE ON public.maintenance_requests FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


create schema if not exists "vector";

create extension if not exists "vector" with schema "vector" version '0.8.0';



