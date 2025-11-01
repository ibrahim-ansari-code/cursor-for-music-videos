-- Fix RLS performance issues for specific tables with warnings
-- Replace auth.uid() with (SELECT auth.uid()) to prevent per-row re-evaluation

-- =============================================
-- INVOICE_TAX_DETAILS TABLE
-- =============================================
DROP POLICY IF EXISTS "Users can view own invoice tax details" ON public.invoice_tax_details;
DROP POLICY IF EXISTS "Users can insert own invoice tax details" ON public.invoice_tax_details;
DROP POLICY IF EXISTS "Users can update own invoice tax details" ON public.invoice_tax_details;
DROP POLICY IF EXISTS "Users can delete own invoice tax details" ON public.invoice_tax_details;

CREATE POLICY "Users can view own invoice tax details" 
ON public.invoice_tax_details 
FOR SELECT 
TO public 
USING (
  (EXISTS (SELECT 1 FROM invoices i JOIN properties p ON i.property_id = p.id WHERE i.id = invoice_tax_details.invoice_id AND p.user_id = (SELECT auth.uid()))) 
  OR 
  (EXISTS (SELECT 1 FROM invoices i JOIN tenants t ON i.tenant_id = t.id WHERE i.id = invoice_tax_details.invoice_id AND t.landlord_id = (SELECT auth.uid())))
);

CREATE POLICY "Users can insert own invoice tax details" 
ON public.invoice_tax_details 
FOR INSERT 
TO public 
WITH CHECK (
  (EXISTS (SELECT 1 FROM invoices i JOIN properties p ON i.property_id = p.id WHERE i.id = invoice_tax_details.invoice_id AND p.user_id = (SELECT auth.uid()))) 
  OR 
  (EXISTS (SELECT 1 FROM invoices i JOIN tenants t ON i.tenant_id = t.id WHERE i.id = invoice_tax_details.invoice_id AND t.landlord_id = (SELECT auth.uid())))
);

CREATE POLICY "Users can update own invoice tax details" 
ON public.invoice_tax_details 
FOR UPDATE 
TO public 
USING (
  (EXISTS (SELECT 1 FROM invoices i JOIN properties p ON i.property_id = p.id WHERE i.id = invoice_tax_details.invoice_id AND p.user_id = (SELECT auth.uid()))) 
  OR 
  (EXISTS (SELECT 1 FROM invoices i JOIN tenants t ON i.tenant_id = t.id WHERE i.id = invoice_tax_details.invoice_id AND t.landlord_id = (SELECT auth.uid())))
);

CREATE POLICY "Users can delete own invoice tax details" 
ON public.invoice_tax_details 
FOR DELETE 
TO public 
USING (
  (EXISTS (SELECT 1 FROM invoices i JOIN properties p ON i.property_id = p.id WHERE i.id = invoice_tax_details.invoice_id AND p.user_id = (SELECT auth.uid()))) 
  OR 
  (EXISTS (SELECT 1 FROM invoices i JOIN tenants t ON i.tenant_id = t.id WHERE i.id = invoice_tax_details.invoice_id AND t.landlord_id = (SELECT auth.uid())))
);

-- =============================================
-- NOTIFICATIONS TABLE
-- =============================================
DROP POLICY IF EXISTS "Users can view own notifications" ON public.notifications;
DROP POLICY IF EXISTS "Users can update own notifications" ON public.notifications;
DROP POLICY IF EXISTS "Users can delete own notifications" ON public.notifications;

CREATE POLICY "Users can view own notifications" 
ON public.notifications 
FOR SELECT 
TO public 
USING ((SELECT auth.uid()) = user_id);

CREATE POLICY "Users can update own notifications" 
ON public.notifications 
FOR UPDATE 
TO public 
USING ((SELECT auth.uid()) = user_id);

CREATE POLICY "Users can delete own notifications" 
ON public.notifications 
FOR DELETE 
TO public 
USING ((SELECT auth.uid()) = user_id);

-- =============================================
-- NOTIFICATION_PREFERENCES TABLE
-- =============================================
DROP POLICY IF EXISTS "Users can view own preferences" ON public.notification_preferences;
DROP POLICY IF EXISTS "Users can insert own preferences" ON public.notification_preferences;
DROP POLICY IF EXISTS "Users can update own preferences" ON public.notification_preferences;

CREATE POLICY "Users can view own preferences" 
ON public.notification_preferences 
FOR SELECT 
TO public 
USING ((SELECT auth.uid()) = user_id);

CREATE POLICY "Users can insert own preferences" 
ON public.notification_preferences 
FOR INSERT 
TO public 
WITH CHECK ((SELECT auth.uid()) = user_id);

CREATE POLICY "Users can update own preferences" 
ON public.notification_preferences 
FOR UPDATE 
TO public 
USING ((SELECT auth.uid()) = user_id);

-- =============================================
-- NOTIFICATION_DELIVERY_LOG TABLE
-- =============================================
DROP POLICY IF EXISTS "Users can view own delivery logs" ON public.notification_delivery_log;

CREATE POLICY "Users can view own delivery logs" 
ON public.notification_delivery_log 
FOR SELECT 
TO public 
USING ((SELECT auth.uid()) = user_id);

-- =============================================
-- TENANT_DOCUMENTS TABLE
-- =============================================
DROP POLICY IF EXISTS "Users can view tenant documents they manage" ON public.tenant_documents;
DROP POLICY IF EXISTS "Users can upload documents for tenants they manage" ON public.tenant_documents;
DROP POLICY IF EXISTS "Users can update documents for tenants they manage" ON public.tenant_documents;
DROP POLICY IF EXISTS "Users can delete documents for tenants they manage" ON public.tenant_documents;

CREATE POLICY "Users can view tenant documents they manage" 
ON public.tenant_documents 
FOR SELECT 
TO public 
USING (EXISTS (SELECT 1 FROM tenants WHERE tenants.id = tenant_documents.tenant_id AND tenants.landlord_id = (SELECT auth.uid())));

CREATE POLICY "Users can upload documents for tenants they manage" 
ON public.tenant_documents 
FOR INSERT 
TO public 
WITH CHECK (EXISTS (SELECT 1 FROM tenants WHERE tenants.id = tenant_documents.tenant_id AND tenants.landlord_id = (SELECT auth.uid())));

CREATE POLICY "Users can update documents for tenants they manage" 
ON public.tenant_documents 
FOR UPDATE 
TO public 
USING (EXISTS (SELECT 1 FROM tenants WHERE tenants.id = tenant_documents.tenant_id AND tenants.landlord_id = (SELECT auth.uid())));

CREATE POLICY "Users can delete documents for tenants they manage" 
ON public.tenant_documents 
FOR DELETE 
TO public 
USING (EXISTS (SELECT 1 FROM tenants WHERE tenants.id = tenant_documents.tenant_id AND tenants.landlord_id = (SELECT auth.uid())));
