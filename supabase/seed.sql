-- ===================================================================
-- COMPREHENSIVE SEED DATA FOR BRIKLI-V2 LOCAL DEVELOPMENT
-- ===================================================================
-- This file provides extensive test data for all major entities
-- Run with: supabase db reset (applies to local database only)

-- ===================================================================
-- SCHEMA SETUP FROM PRODUCTION
-- ===================================================================
-- Create schemas
CREATE SCHEMA IF NOT EXISTS "dev";
ALTER SCHEMA "dev" OWNER TO "postgres";

CREATE SCHEMA IF NOT EXISTS "vector";
ALTER SCHEMA "vector" OWNER TO "postgres";

-- Create enum types
-- Note: Postgres doesn't support IF NOT EXISTS for CREATE TYPE so we need to do this differently
DO $$ 
BEGIN
    -- Create enum types if they don't exist
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'integration_type_enum') THEN
        CREATE TYPE "public"."integration_type_enum" AS ENUM (
            'QUICKBOOKS',
            'XERO',
            'SAGE',
            'NETSUITE'
        );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'integrationstatus') THEN
        CREATE TYPE "public"."integrationstatus" AS ENUM (
            'Connected',
            'Disconnected',
            'Error',
            'Pending'
        );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'integrationtype') THEN
        CREATE TYPE "public"."integrationtype" AS ENUM (
            'QuickBooks'
        );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'leasestatus') THEN
        CREATE TYPE "public"."leasestatus" AS ENUM (
            'DRAFT',
            'PENDING',
            'ACTIVE',
            'EXPIRED',
            'TERMINATED',
            'RENEWED'
        );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'maintenance_priority') THEN
        CREATE TYPE "public"."maintenance_priority" AS ENUM (
            'Low',
            'Medium',
            'High'
        );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'maintenance_status') THEN
        CREATE TYPE "public"."maintenance_status" AS ENUM (
            'Pending',
            'In Progress',
            'Scheduled',
            'Completed',
            'Cancelled'
        );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'messagetype') THEN
        CREATE TYPE "public"."messagetype" AS ENUM (
            'DIRECT',
            'ANNOUNCEMENT',
            'SYSTEM'
        );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'paymentmethod') THEN
        CREATE TYPE "public"."paymentmethod" AS ENUM (
            'Credit Card',
            'Bank Transfer',
            'Cash',
            'Check',
            'Other'
        );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'paymentstatus') THEN
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
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'property_type_enum') THEN
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
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'propertystatus') THEN
        CREATE TYPE "public"."propertystatus" AS ENUM (
            'ACTIVE',
            'INACTIVE',
            'DRAFT',
            'ARCHIVED'
        );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tenantstatus') THEN
        CREATE TYPE "public"."tenantstatus" AS ENUM (
            'ACTIVE',
            'INACTIVE',
            'PENDING',
            'EVICTED',
            'MOVED_OUT'
        );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tenanttype') THEN
        CREATE TYPE "public"."tenanttype" AS ENUM (
            'INDIVIDUAL',
            'COMPANY'
        );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'vendorstatus') THEN
        CREATE TYPE "public"."vendorstatus" AS ENUM (
            'PENDING',
            'APPROVED',
            'DENIED',
            'INACTIVE'
        );
    END IF;
END $$;

-- Create necessary functions
CREATE OR REPLACE FUNCTION "public"."get_current_app_user_id"() RETURNS "uuid"
    LANGUAGE "plpgsql" STABLE
    SET "search_path" TO 'public'
    AS $$
BEGIN
  RETURN auth.uid();
END;
$$;

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

CREATE OR REPLACE FUNCTION "public"."update_updated_at_column"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    SET "search_path" TO ''
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

-- ===================================================================
-- CREATE AUTH USER (Test User for Login)
-- ===================================================================
-- Create test user in auth.users table for login
INSERT INTO auth.users (
    instance_id,
    id,
    aud,
    role,
    email,
    encrypted_password,
    email_confirmed_at,
    invited_at,
    confirmation_token,
    confirmation_sent_at,
    recovery_token,
    recovery_sent_at,
    email_change_token_new,
    email_change,
    email_change_sent_at,
    last_sign_in_at,
    raw_app_meta_data,
    raw_user_meta_data,
    is_super_admin,
    created_at,
    updated_at,
    phone,
    phone_confirmed_at,
    phone_change,
    phone_change_token,
    phone_change_sent_at,
    email_change_token_current,
    email_change_confirm_status,
    banned_until,
    reauthentication_token,
    reauthentication_sent_at,
    is_sso_user,
    deleted_at
) VALUES (
    '00000000-0000-0000-0000-000000000000',
    '1894ba74-571a-4270-9072-9bea9486e0b1',
    'authenticated',
    'authenticated',
    'test.user@brikli.dev',
    crypt('TestUser@123', gen_salt('bf')), -- Password: TestUser@123
    NOW(),
    NOW(),
    '',
    NOW(),
    '',
    NULL,
    '',
    '',
    NULL,
    NOW(),
    '{"provider": "email", "providers": ["email"]}',
    '{"first_name": "Test", "last_name": "User"}',
    FALSE,
    NOW(),
    NOW(),
    NULL,
    NULL,
    '',
    '',
    NULL,
    '',
    0,
    NULL,
    '',
    NULL,
    FALSE,
    NULL
) ON CONFLICT (id) DO UPDATE SET
    email = EXCLUDED.email,
    encrypted_password = EXCLUDED.encrypted_password,
    updated_at = NOW();

-- Create tenant test user in auth.users table for tenant portal login
INSERT INTO auth.users (
    instance_id,
    id,
    aud,
    role,
    email,
    encrypted_password,
    email_confirmed_at,
    invited_at,
    confirmation_token,
    confirmation_sent_at,
    recovery_token,
    recovery_sent_at,
    email_change_token_new,
    email_change,
    email_change_sent_at,
    last_sign_in_at,
    raw_app_meta_data,
    raw_user_meta_data,
    is_super_admin,
    created_at,
    updated_at,
    phone,
    phone_confirmed_at,
    phone_change,
    phone_change_token,
    phone_change_sent_at,
    email_change_token_current,
    email_change_confirm_status,
    banned_until,
    reauthentication_token,
    reauthentication_sent_at,
    is_sso_user,
    deleted_at
) VALUES (
    '00000000-0000-0000-0000-000000000000',
    '11111111-2222-3333-4444-555555555555',
    'authenticated',
    'authenticated',
    'alice.tenant@example.com',
    crypt('TenantTest@123', gen_salt('bf')), -- Password: TenantTest@123
    NOW(),
    NOW(),
    '',
    NOW(),
    '',
    NULL,
    '',
    '',
    NULL,
    NOW(),
    '{"provider": "email", "providers": ["email"]}',
    '{"first_name": "Alice", "last_name": "Brown"}',
    FALSE,
    NOW(),
    NOW(),
    NULL,
    NULL,
    '',
    '',
    NULL,
    '',
    0,
    NULL,
    '',
    NULL,
    FALSE,
    NULL
) ON CONFLICT (id) DO UPDATE SET
    email = EXCLUDED.email,
    encrypted_password = EXCLUDED.encrypted_password,
    updated_at = NOW();

-- Clear existing data (in dependency order)
TRUNCATE TABLE 
  expense_tax_details,
  expenses,
  lease_documents,
  payments,
  invoices,
  maintenance_requests,
  leases,
  tenant_unit_link,
  property_units,
  tenants,
  properties,
  integrations,
  users
CASCADE;

-- ===================================================================
-- USERS (Focused on Test User + Supporting Users)
-- ===================================================================
INSERT INTO users (id, email, first_name, last_name, user_type, phone, address, city, province, postal_code, is_active, is_admin, is_email_verified, created_at, updated_at) VALUES
-- Main test user (from auth) - All data will be under this user
('1894ba74-571a-4270-9072-9bea9486e0b1', 'test.user@brikli.dev', 'Test', 'User', 'LANDLORD', '(555) 123-4567', '123 Main St', 'Toronto', 'ON', 'M5V 1A1', true, false, true, now(), now()),

-- Additional support users (for tenant accounts and staff)
('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'admin@brikli.dev', 'Admin', 'User', 'ADMIN', '(555) 999-0000', '999 Admin Blvd', 'Toronto', 'ON', 'M5H 1G1', true, true, true, now(), now()),
('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'maintenance@brikli.dev', 'Bob', 'Maintenance', 'STAFF', '(555) 777-8888', '777 Service Dr', 'Toronto', 'ON', 'M6M 2H2', true, false, true, now(), now()),

-- Tenant users (with accounts)
('11111111-2222-3333-4444-555555555555', 'alice.tenant@example.com', 'Alice', 'Brown', 'TENANT', '(555) 111-2222', NULL, NULL, NULL, NULL, true, false, true, now(), now()),
('22222222-3333-4444-5555-666666666666', 'david.renter@example.com', 'David', 'Davis', 'TENANT', '(555) 333-4444', NULL, NULL, NULL, NULL, true, false, true, now(), now()),
('33333333-4444-5555-6666-777777777777', 'emma.tenant@example.com', 'Emma', 'Wilson', 'TENANT', '(555) 555-6666', NULL, NULL, NULL, NULL, true, false, true, now(), now());

-- ===================================================================
-- PROPERTIES (All owned by Test User)
-- ===================================================================
INSERT INTO properties (id, name, address, city, province, postal_code, property_type, year_built, description, status, user_id, created_at, updated_at) VALUES
-- All properties owned by test user for comprehensive testing
(1, 'Maple Apartments', '123 Maple Street', 'Toronto', 'ON', 'M5V 1A1', 'Apartment Complex', 2010, 'Modern 24-unit apartment building with amenities', 'ACTIVE', '1894ba74-571a-4270-9072-9bea9486e0b1', now(), now()),
(2, 'Downtown Condos', '456 King Street W', 'Toronto', 'ON', 'M5V 2B2', 'Residential', 2018, 'Luxury downtown condominiums', 'ACTIVE', '1894ba74-571a-4270-9072-9bea9486e0b1', now(), now()),
(3, 'Student Housing Complex', '789 University Ave', 'Toronto', 'ON', 'M5T 3C3', 'Residential', 2015, 'Student-friendly housing near campus', 'ACTIVE', '1894ba74-571a-4270-9072-9bea9486e0b1', now(), now()),
(4, 'Oakville Family Homes', '111 Oak Street', 'Oakville', 'ON', 'L6K 4D4', 'Residential', 2005, 'Family-friendly townhomes', 'ACTIVE', '1894ba74-571a-4270-9072-9bea9486e0b1', now(), now()),
(5, 'Business Plaza', '222 Commerce Dr', 'Mississauga', 'ON', 'L5M 5E5', 'Commercial', 1995, 'Multi-tenant commercial plaza', 'ACTIVE', '1894ba74-571a-4270-9072-9bea9486e0b1', now(), now()),
(6, 'Riverside Apartments', '333 River Road', 'Hamilton', 'ON', 'L8S 6F6', 'Apartment Complex', 2012, 'Scenic riverside apartment complex', 'ACTIVE', '1894ba74-571a-4270-9072-9bea9486e0b1', now(), now()),
(7, 'Industrial Warehouse', '444 Factory Lane', 'Burlington', 'ON', 'L7P 7G7', 'Industrial', 1988, 'Large warehouse facility', 'INACTIVE', '1894ba74-571a-4270-9072-9bea9486e0b1', now(), now()),
(8, 'Suburban Duplex', '555 Suburban Ave', 'Brampton', 'ON', 'L6X 8H8', 'Residential', 2000, 'Well-maintained duplex units', 'ACTIVE', '1894ba74-571a-4270-9072-9bea9486e0b1', now(), now());

-- ===================================================================
-- PROPERTY UNITS (For Test User Properties)
-- ===================================================================
INSERT INTO property_units (id, property_id, tenant_id, name, description, size, monthly_rent, is_rented, bedrooms, bathrooms, floor, created_at, updated_at) VALUES
-- Maple Apartments units
(1, 1, NULL, 'Unit 101', 'Ground floor 1-bedroom with patio', 650.0, 1800.00, false, 1, 1.0, 1, now(), now()),
(2, 1, NULL, 'Unit 102', 'Ground floor 2-bedroom corner unit', 950.0, 2400.00, false, 2, 1.5, 1, now(), now()),
(3, 1, NULL, 'Unit 201', 'Second floor 1-bedroom with balcony', 650.0, 1900.00, true, 1, 1.0, 2, now(), now()),
(4, 1, NULL, 'Unit 202', 'Second floor 2-bedroom premium unit', 950.0, 2600.00, true, 2, 2.0, 2, now(), now()),
(5, 1, NULL, 'Unit 301', 'Third floor 1-bedroom city view', 650.0, 2000.00, false, 1, 1.0, 3, now(), now()),

-- Downtown Condos units
(6, 2, NULL, 'Penthouse A', 'Luxury penthouse with terrace', 1500.0, 4500.00, true, 3, 2.5, 20, now(), now()),
(7, 2, NULL, 'Unit 1502', 'High-floor 2-bedroom with view', 1100.0, 3200.00, false, 2, 2.0, 15, now(), now()),

-- Student Housing units
(8, 3, NULL, 'Room A1', 'Single bedroom in shared unit', 200.0, 800.00, true, 1, 1.0, 1, now(), now()),
(9, 3, NULL, 'Room A2', 'Single bedroom in shared unit', 200.0, 800.00, true, 1, 1.0, 1, now(), now()),
(10, 3, NULL, 'Studio B1', 'Private studio apartment', 400.0, 1200.00, false, 0, 1.0, 2, now(), now()),

-- Oakville Family Homes
(11, 4, NULL, 'Townhome 1', '3-bedroom family townhome', 1200.0, 2800.00, true, 3, 2.5, NULL, now(), now()),
(12, 4, NULL, 'Townhome 2', '4-bedroom family townhome', 1400.0, 3200.00, false, 4, 3.0, NULL, now(), now()),

-- Business Plaza
(13, 5, NULL, 'Suite 100', 'Ground floor retail space', 800.0, 3500.00, true, NULL, 1.0, 1, now(), now()),
(14, 5, NULL, 'Suite 200', 'Second floor office space', 600.0, 2500.00, false, NULL, 1.0, 2, now(), now()),

-- Riverside Apartments
(15, 6, NULL, 'Apt 1A', 'Riverside view 1-bedroom', 700.0, 1700.00, true, 1, 1.0, 1, now(), now()),
(16, 6, NULL, 'Apt 2B', 'Riverside view 2-bedroom', 900.0, 2200.00, false, 2, 1.5, 2, now(), now()),

-- Suburban Duplex
(17, 8, NULL, 'Unit A', 'Main floor duplex unit', 1000.0, 2000.00, true, 2, 1.5, 1, now(), now()),
(18, 8, NULL, 'Unit B', 'Upper floor duplex unit', 1000.0, 1900.00, false, 2, 1.5, 2, now(), now());

-- ===================================================================
-- TENANTS (All managed by Test User)
-- ===================================================================
INSERT INTO tenants (id, user_id, first_name, last_name, phone, email, status, current_property_id, landlord_id, profile_image_url, tenant_type, created_at, updated_at) VALUES
(1, '11111111-2222-3333-4444-555555555555', 'Alice', 'Brown', '(555) 111-2222', 'alice.tenant@example.com', 'ACTIVE', 1, '1894ba74-571a-4270-9072-9bea9486e0b1', NULL, 'INDIVIDUAL', now(), now()),
(2, '22222222-3333-4444-5555-666666666666', 'David', 'Davis', '(555) 333-4444', 'david.renter@example.com', 'ACTIVE', 2, '1894ba74-571a-4270-9072-9bea9486e0b1', NULL, 'INDIVIDUAL', now(), now()),
(3, '33333333-4444-5555-6666-777777777777', 'Emma', 'Wilson', '(555) 555-6666', 'emma.tenant@example.com', 'ACTIVE', 3, '1894ba74-571a-4270-9072-9bea9486e0b1', NULL, 'INDIVIDUAL', now(), now()),
(4, NULL, 'Robert', 'Miller', '(555) 777-8888', 'robert.miller@example.com', 'ACTIVE', 4, '1894ba74-571a-4270-9072-9bea9486e0b1', NULL, 'INDIVIDUAL', now(), now()),
(5, NULL, 'Lisa', 'Garcia', '(555) 999-0000', 'lisa.garcia@example.com', 'PENDING', NULL, '1894ba74-571a-4270-9072-9bea9486e0b1', NULL, 'INDIVIDUAL', now(), now()),
(6, NULL, 'James', 'Anderson', '(555) 123-9876', 'james.anderson@example.com', 'ACTIVE', 6, '1894ba74-571a-4270-9072-9bea9486e0b1', NULL, 'INDIVIDUAL', now(), now()),
(7, NULL, 'Maria', 'Rodriguez', '(555) 456-7890', 'maria.rodriguez@example.com', 'MOVED_OUT', NULL, '1894ba74-571a-4270-9072-9bea9486e0b1', NULL, 'INDIVIDUAL', now(), now()),
(8, NULL, 'Kevin', 'Thomas', '(555) 234-5678', 'kevin.thomas@example.com', 'ACTIVE', 8, '1894ba74-571a-4270-9072-9bea9486e0b1', NULL, 'INDIVIDUAL', now(), now());

-- ===================================================================
-- LEASES
-- ===================================================================
INSERT INTO leases (id, start_date, end_date, monthly_rent, security_deposit, status, is_renewable, auto_renew, rent_due_day, late_fee_amount, late_fee_after_days, special_terms, property_id, unit_id, tenant_id, created_at, updated_at) VALUES
-- Active leases
(1, NOW() - INTERVAL '6 months', NOW() + INTERVAL '5 months', 1900.00, 3800.00, 'ACTIVE', true, false, 1, 75.00, 5, 'Pet-friendly unit', 1, 3, 1, now(), now()),
(2, NOW() - INTERVAL '4 months', NOW() + INTERVAL '7 months', 4500.00, 9000.00, 'ACTIVE', true, false, 1, 150.00, 3, 'Luxury amenities included', 2, 6, 2, now(), now()),
(3, NOW() - INTERVAL '1 month', NOW() + INTERVAL '10 months', 800.00, 400.00, 'ACTIVE', false, false, 1, 25.00, 7, 'Student housing - semester lease', 3, 8, 3, now(), now()),
(4, NOW() - INTERVAL '5 months', NOW() + INTERVAL '6 months', 2800.00, 5600.00, 'ACTIVE', true, true, 1, 100.00, 5, 'Family-friendly community', 4, 11, 4, now(), now()),
(5, NOW() - INTERVAL '2 months', NOW() + INTERVAL '9 months', 1700.00, 3400.00, 'ACTIVE', true, false, 1, 85.00, 5, 'Riverside view premium', 6, 15, 6, now(), now()),
(6, NOW() - INTERVAL '3 months', NOW() + INTERVAL '8 months', 2000.00, 4000.00, 'ACTIVE', true, false, 1, 80.00, 5, 'Main floor duplex', 8, 17, 8, now(), now()),

-- Historical leases
(7, NOW() - INTERVAL '18 months', NOW() - INTERVAL '6 months', 1800.00, 3600.00, 'EXPIRED', false, false, 1, 75.00, 5, 'Previous year lease', 1, 3, 1, NOW() - INTERVAL '18 months', NOW() - INTERVAL '6 months'),
(8, NOW() - INTERVAL '13 months', NOW() - INTERVAL '1 month', 1600.00, 3200.00, 'TERMINATED', false, false, 1, 70.00, 5, 'Early termination - job relocation', 6, 15, 7, NOW() - INTERVAL '13 months', NOW() - INTERVAL '4 months');

-- ===================================================================
-- PAYMENTS
-- ===================================================================
INSERT INTO payments (id, amount, payment_date, lease_id, tenant_id, payment_method, transaction_reference, status, receipt_url, created_at, updated_at) VALUES
-- Paid (last month)
(1, 1900.00, date_trunc('month', current_date) - interval '1 month', 1, 1, 'Bank Transfer', 'TXN-001-LASTMONTH', 'Paid', NULL, date_trunc('month', current_date) - interval '1 month', date_trunc('month', current_date) - interval '1 month'),
(2, 4500.00, date_trunc('month', current_date) - interval '1 month', 2, 2, 'Credit Card', 'CC-002-LASTMONTH', 'Paid', NULL, date_trunc('month', current_date) - interval '1 month', date_trunc('month', current_date) - interval '1 month'),
(3, 800.00, date_trunc('month', current_date) - interval '1 month', 3, 3, 'Credit Card', 'CC-003-LASTMONTH', 'Paid', NULL, date_trunc('month', current_date) - interval '1 month', date_trunc('month', current_date) - interval '1 month'),
(4, 2800.00, date_trunc('month', current_date) - interval '1 month', 4, 4, 'Check', 'CHK-004-LASTMONTH', 'Paid', NULL, date_trunc('month', current_date) - interval '1 month', date_trunc('month', current_date) - interval '1 month'),
(5, 1700.00, date_trunc('month', current_date) - interval '1 month' + interval '14 days', 5, 6, 'Bank Transfer', 'TXN-005-LASTMONTH', 'Paid', NULL, date_trunc('month', current_date) - interval '1 month' + interval '14 days', date_trunc('month', current_date) - interval '1 month' + interval '14 days'),

-- Paid (2 months ago)
(6, 1900.00, date_trunc('month', current_date) - interval '2 months', 1, 1, 'Bank Transfer', 'TXN-001-2MONTHSAGO', 'Paid', NULL, date_trunc('month', current_date) - interval '2 months', date_trunc('month', current_date) - interval '2 months'),
(7, 4500.00, date_trunc('month', current_date) - interval '2 months', 2, 2, 'Credit Card', 'CC-002-2MONTHSAGO', 'Paid', NULL, date_trunc('month', current_date) - interval '2 months', date_trunc('month', current_date) - interval '2 months'),

-- Current Month: Overdue and Partial payments to trigger UI bug
(8, 2000.00, date_trunc('month', current_date) + interval '1 day', 6, 8, 'Credit Card', 'CC-006-THISMONTH', 'Partial', NULL, date_trunc('month', current_date) + interval '1 day', date_trunc('month', current_date) + interval '1 day'),
(9, 1700.00, date_trunc('month', current_date) + interval '1 day', 5, 6, 'Bank Transfer', NULL, 'Overdue', NULL, date_trunc('month', current_date), date_trunc('month', current_date)),
(10, 1900.00, date_trunc('month', current_date) + interval '1 day', 1, 1, 'Bank Transfer', NULL, 'Overdue', NULL, date_trunc('month', current_date), date_trunc('month', current_date)),
(11, 4500.00, date_trunc('month', current_date) + interval '1 day', 2, 2, 'Credit Card', NULL, 'Overdue', NULL, date_trunc('month', current_date), date_trunc('month', current_date)),
(12, 800.00, date_trunc('month', current_date) + interval '1 day', 3, 3, 'Credit Card', NULL, 'Overdue', NULL, date_trunc('month', current_date), date_trunc('month', current_date)),
(13, 2800.00, date_trunc('month', current_date) + interval '1 day', 4, 4, 'Check', NULL, 'Overdue', NULL, date_trunc('month', current_date), date_trunc('month', current_date));

-- ===================================================================
-- INVOICES
-- ===================================================================
INSERT INTO invoices (id, invoice_number, amount, description, issue_date, due_date, property_id, tenant_id, status, created_at, updated_at) VALUES
-- Paid Invoices (Last Month)
(1, 'INV-LM-001', 1900.00, 'Last Month Rent - Unit 201', date_trunc('month', current_date) - interval '1 month', date_trunc('month', current_date) - interval '1 month', 1, 1, 'Paid', now(), now()),
(2, 'INV-LM-002', 4500.00, 'Last Month Rent - Penthouse A', date_trunc('month', current_date) - interval '1 month', date_trunc('month', current_date) - interval '1 month', 2, 2, 'Paid', now(), now()),
(3, 'INV-LM-003', 800.00, 'Last Month Rent - Room A1', date_trunc('month', current_date) - interval '1 month', date_trunc('month', current_date) - interval '1 month', 3, 3, 'Paid', now(), now()),

-- Current Month: Overdue and Pending invoices to trigger UI bug
(4, 'INV-CM-004', 1700.00, 'Current Month Rent - Apt 1A', date_trunc('month', current_date), date_trunc('month', current_date) + interval '14 days', 6, 6, 'Overdue', now(), now()),
(5, 'INV-CM-005', 2000.00, 'Current Month Rent - Unit A', date_trunc('month', current_date), date_trunc('month', current_date) + interval '14 days', 8, 8, 'Partial', now(), now()),
(6, 'INV-CM-006', 150.00, 'Parking Spot Rental - Current Month', date_trunc('month', current_date), date_trunc('month', current_date) + interval '14 days', 2, 2, 'Pending', now(), now()),
(7, 'INV-CM-007', 250.00, 'Late Fee - Last Month Rent', date_trunc('month', current_date) - interval '10 days', date_trunc('month', current_date) + interval '5 days', 6, 6, 'Pending', now(), now()),
(8, 'INV-CM-008', 1900.00, 'Current Month Rent - Unit 201', date_trunc('month', current_date), date_trunc('month', current_date) + interval '14 days', 1, 1, 'Overdue', now(), now()),
(9, 'INV-CM-009', 4500.00, 'Current Month Rent - Penthouse A', date_trunc('month', current_date), date_trunc('month', current_date) + interval '14 days', 2, 2, 'Overdue', now(), now()),
(10, 'INV-CM-010', 800.00, 'Current Month Rent - Room A1', date_trunc('month', current_date), date_trunc('month', current_date) + interval '14 days', 3, 3, 'Overdue', now(), now()),
(11, 'INV-CM-011', 2800.00, 'Current Month Rent - Townhome 1', date_trunc('month', current_date), date_trunc('month', current_date) + interval '14 days', 4, 4, 'Overdue', now(), now());

-- ===================================================================
-- EXPENSES
-- ===================================================================
INSERT INTO expenses (id, category, description, expense_date, receipt_url, property_id, subtotal_amount, total_tax_amount, created_at, updated_at) VALUES
(1, 'Maintenance', 'HVAC system repair - Unit 201', now() - interval '15 days', NULL, 1, 850.00, 110.50, now(), now()),
(2, 'Utilities', 'Electricity bill - Last Month', now() - interval '1 month', NULL, 1, 420.00, 54.60, now(), now()),
(3, 'Landscaping', 'Monthly lawn care service', now() - interval '2 days', NULL, 4, 300.00, 39.00, now(), now()),
(4, 'Repairs', 'Plumbing repair - Bathroom leak', now() - interval '10 days', NULL, 6, 275.00, 35.75, now(), now()),
(5, 'Insurance', 'Property insurance - Q4 payment', now() - interval '1 day', NULL, 2, 1200.00, 156.00, now(), now()),
(6, 'Property Management', 'Monthly management fee', now(), NULL, 1, 500.00, 65.00, now(), now()),
(7, 'Advertising', 'Vacancy listing - Unit 102', now() - interval '20 days', NULL, 1, 180.00, 23.40, now(), now()),
(8, 'Supplies', 'Cleaning supplies and materials', now() - interval '5 days', NULL, 3, 125.00, 16.25, now(), now()),
(9, 'Professional Services', 'Legal consultation - lease review', now() - interval '12 days', NULL, 1, 350.00, 45.50, now(), now()),
(10, 'Utilities', 'Water and sewer - Last Month', now() - interval '1 month', NULL, 8, 180.00, 23.40, now(), now());

-- ===================================================================
-- EXPENSE TAX DETAILS
-- ===================================================================
INSERT INTO expense_tax_details (id, tax_name, tax_rate, tax_amount, expense_id, created_at, updated_at) VALUES
(1, 'HST', 13.00, 110.50, 1, now(), now()),
(2, 'HST', 13.00, 54.60, 2, now(), now()),
(3, 'HST', 13.00, 39.00, 3, now(), now()),
(4, 'HST', 13.00, 35.75, 4, now(), now()),
(5, 'HST', 13.00, 156.00, 5, now(), now()),
(6, 'HST', 13.00, 65.00, 6, now(), now()),
(7, 'HST', 13.00, 23.40, 7, now(), now()),
(8, 'HST', 13.00, 16.25, 8, now(), now()),
(9, 'HST', 13.00, 45.50, 9, now(), now()),
(10, 'HST', 13.00, 23.40, 10, now(), now());

-- ===================================================================
-- MAINTENANCE REQUESTS (All for Test User's Properties)
-- ===================================================================
INSERT INTO maintenance_requests (id, issue_title, description, property_id, unit_id, tenant_id, user_id, request_date, priority, status, scheduled_date, estimated_cost, actual_cost, assigned_to, created_at, updated_at) VALUES
(1, 'Heating not working', 'Unit heating system not responding, very cold in apartment', 1, 3, 1, '11111111-2222-3333-4444-555555555555', now() - interval '3 days', 'High', 'Completed', now() - interval '2 days', 300.00, 275.00, 'HVAC Solutions Inc.', now(), now()),
(2, 'Leaky faucet in kitchen', 'Kitchen sink faucet dripping constantly', 2, 6, 2, '22222222-3333-4444-5555-666666666666', now() - interval '5 days', 'Medium', 'In Progress', now() + interval '2 days', 150.00, NULL, 'City Plumbing Services', now(), now()),
(3, 'Broken window lock', 'Bedroom window lock mechanism is broken', 3, 8, 3, '33333333-4444-5555-6666-777777777777', now() - interval '8 days', 'Low', 'Scheduled', now() + interval '7 days', 80.00, NULL, 'Window Repair Co.', now(), now()),
(4, 'Garbage disposal not working', 'Kitchen garbage disposal making loud noise and not grinding', 4, 11, 4, NULL, now() - interval '1 day', 'Medium', 'Pending', NULL, NULL, NULL, NULL, now(), now()),
(5, 'Parking lot lighting', 'Several parking lot lights are out, safety concern', 1, NULL, NULL, '1894ba74-571a-4270-9072-9bea9486e0b1', now() - interval '14 days', 'High', 'Completed', now() - interval '12 days', 400.00, 380.00, 'Bright Light Electric', now(), now()),
(6, 'Elevator making noise', 'Building elevator making unusual sounds between floors', 2, NULL, NULL, '1894ba74-571a-4270-9072-9bea9486e0b1', now(), 'High', 'Scheduled', now() + interval '3 days', 800.00, NULL, 'Otis Elevator Service', now(), now()),
(7, 'Washing machine leak', 'Laundry room washing machine leaking water', 6, NULL, NULL, '1894ba74-571a-4270-9072-9bea9486e0b1', now() - interval '16 days', 'Medium', 'Completed', now() - interval '14 days', 250.00, 225.00, 'Appliance Repair Plus', now(), now());

-- ===================================================================
-- INTEGRATIONS (Test User's Integrations)
-- ===================================================================
INSERT INTO integrations (id, user_id, integration_type, status, connected_at, last_sync_at, connection_metadata, created_at, updated_at) VALUES
(1, '1894ba74-571a-4270-9072-9bea9486e0b1', 'QUICKBOOKS', 'Connected', now() - interval '1 month', now(), '{"company_name": "Test Property Management", "company_id": "QB-123456", "realm_id": "1234567890"}', now(), now());



-- ===================================================================
-- TENANT UNIT LINKS (Historical occupancy tracking)
-- ===================================================================
INSERT INTO tenant_unit_link (tenant_id, unit_id, start_date, end_date) VALUES
-- Current assignments
(1, 3, '2024-01-01', NULL),  -- Alice in Unit 201
(2, 6, '2024-03-01', NULL),  -- David in Penthouse A
(3, 8, '2024-09-01', NULL),  -- Emma in Room A1
(4, 11, '2024-02-01', NULL), -- Robert in Townhome 1
(6, 15, '2024-06-01', NULL), -- James in Apt 1A
(8, 17, '2024-04-01', NULL), -- Kevin in Unit A

-- Historical assignments
(1, 2, '2023-01-01', '2023-12-31'), -- Alice's previous lease in Unit 102
(7, 15, '2023-06-01', '2024-03-15'); -- Maria's terminated lease

-- ===================================================================
-- RESET SEQUENCES
-- ===================================================================
SELECT setval('expenses_id_seq', COALESCE((SELECT MAX(id) FROM expenses), 1));
SELECT setval('expense_tax_details_id_seq', COALESCE((SELECT MAX(id) FROM expense_tax_details), 1));
SELECT setval('invoices_id_seq', COALESCE((SELECT MAX(id) FROM invoices), 1));
SELECT setval('leases_id_seq', COALESCE((SELECT MAX(id) FROM leases), 1));
SELECT setval('lease_documents_id_seq', COALESCE((SELECT MAX(id) FROM lease_documents), 1));
SELECT setval('maintenance_requests_id_seq', COALESCE((SELECT MAX(id) FROM maintenance_requests), 1));
SELECT setval('payments_id_seq', COALESCE((SELECT MAX(id) FROM payments), 1));
SELECT setval('properties_id_seq', COALESCE((SELECT MAX(id) FROM properties), 1));
SELECT setval('property_units_id_seq', COALESCE((SELECT MAX(id) FROM property_units), 1));
SELECT setval('tenants_id_seq', COALESCE((SELECT MAX(id) FROM tenants), 1));
SELECT setval('integrations_id_seq', COALESCE((SELECT MAX(id) FROM integrations), 1));

-- ===================================================================
-- VERIFICATION QUERIES
-- ===================================================================
-- Uncomment these to verify data after seeding:
-- SELECT 'Users' as table_name, count(*) as record_count FROM users
-- UNION ALL SELECT 'Properties', count(*) FROM properties  
-- UNION ALL SELECT 'Property Units', count(*) FROM property_units
-- UNION ALL SELECT 'Tenants', count(*) FROM tenants
-- UNION ALL SELECT 'Leases', count(*) FROM leases
-- UNION ALL SELECT 'Payments', count(*) FROM payments
-- UNION ALL SELECT 'Invoices', count(*) FROM invoices
-- UNION ALL SELECT 'Expenses', count(*) FROM expenses
-- UNION ALL SELECT 'Maintenance Requests', count(*) FROM maintenance_requests
-- UNION ALL SELECT 'Integrations', count(*) FROM integrations; 