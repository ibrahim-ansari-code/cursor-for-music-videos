alter table "public"."payments" drop constraint "payments_lease_id_fkey";

alter type "public"."paymentmethod" rename to "paymentmethod__old_version_to_be_dropped";

create type "public"."paymentmethod" as enum ('Credit Card', 'Debit Card', 'Bank Transfer', 'Wire Transfer', 'Direct Deposit', 'Interac e-Transfer', 'Cash', 'Check', 'Bank Draft', 'PayPal', 'Internal Transfer', 'Other');

alter table "public"."payments" alter column payment_method type "public"."paymentmethod" using payment_method::text::"public"."paymentmethod";

drop type "public"."paymentmethod__old_version_to_be_dropped";

alter table "public"."expenses" add column "payment_method" paymentmethod not null default 'Other'::paymentmethod;

alter table "public"."payments" add column "reduction_amount" numeric(12,2);

alter table "public"."payments" add column "reduction_reason" character varying;

alter table "public"."tenant_unit_link" alter column "end_date" set data type timestamp with time zone using "end_date"::timestamp with time zone;

alter table "public"."tenant_unit_link" alter column "start_date" set data type timestamp with time zone using "start_date"::timestamp with time zone;

alter table "public"."payments" add constraint "check_reduction_amount_not_greater_than_amount" CHECK ((reduction_amount <= amount)) not valid;

alter table "public"."payments" validate constraint "check_reduction_amount_not_greater_than_amount";

alter table "public"."payments" add constraint "payments_lease_id_fkey" FOREIGN KEY (lease_id) REFERENCES leases(id) ON DELETE RESTRICT not valid;

alter table "public"."payments" validate constraint "payments_lease_id_fkey";

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




