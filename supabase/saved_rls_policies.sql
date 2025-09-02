-- Saved RLS Policies for restoration after migration
-- Generated on migration fix

-- Enable RLS on tables
ALTER TABLE alembic_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE expense_tax_details ENABLE ROW LEVEL SECURITY;
ALTER TABLE expenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE integrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE lease_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE leases ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE properties ENABLE ROW LEVEL SECURITY;
ALTER TABLE property_units ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_unit_link ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Alembic Version Policy
CREATE POLICY "Allow authenticated read access to alembic version" 
ON alembic_version 
FOR SELECT 
TO authenticated 
USING (true);

-- Expense Tax Details Policies
CREATE POLICY "Expense Tax Details Delete Access Control" 
ON expense_tax_details 
FOR DELETE 
TO authenticated 
USING (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (expense_id IN ( SELECT exp.id
       FROM expenses exp
      WHERE (exp.property_id IN ( SELECT prop.id
               FROM properties prop
              WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))))
);

CREATE POLICY "Expense Tax Details Insert Access Control" 
ON expense_tax_details 
FOR INSERT 
TO authenticated 
WITH CHECK (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (expense_id IN ( SELECT exp.id
       FROM expenses exp
      WHERE (exp.property_id IN ( SELECT prop.id
               FROM properties prop
              WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))))
);

CREATE POLICY "Expense Tax Details Select Access Control" 
ON expense_tax_details 
FOR SELECT 
TO authenticated 
USING (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (expense_id IN ( SELECT exp.id
       FROM expenses exp
      WHERE (exp.property_id IN ( SELECT prop.id
               FROM properties prop
              WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))))
);

CREATE POLICY "Expense Tax Details Update Access Control" 
ON expense_tax_details 
FOR UPDATE 
TO authenticated 
USING (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (expense_id IN ( SELECT exp.id
       FROM expenses exp
      WHERE (exp.property_id IN ( SELECT prop.id
               FROM properties prop
              WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))))
)
WITH CHECK (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (expense_id IN ( SELECT exp.id
       FROM expenses exp
      WHERE (exp.property_id IN ( SELECT prop.id
               FROM properties prop
              WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))))
);

-- Expenses Policies
CREATE POLICY "Expenses Delete Access Control" 
ON expenses 
FOR DELETE 
TO authenticated 
USING (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (property_id IN ( SELECT prop.id
       FROM properties prop
      WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))
);

CREATE POLICY "Expenses Insert Access Control" 
ON expenses 
FOR INSERT 
TO authenticated 
WITH CHECK (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (property_id IN ( SELECT prop.id
       FROM properties prop
      WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))
);

CREATE POLICY "Expenses Select Access Control" 
ON expenses 
FOR SELECT 
TO authenticated 
USING (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (property_id IN ( SELECT prop.id
       FROM properties prop
      WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))
);

CREATE POLICY "Expenses Update Access Control" 
ON expenses 
FOR UPDATE 
TO authenticated 
USING (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (property_id IN ( SELECT prop.id
       FROM properties prop
      WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))
)
WITH CHECK (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (property_id IN ( SELECT prop.id
       FROM properties prop
      WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))
);

-- Integrations Policies
CREATE POLICY "Integrations Delete Access Control" 
ON integrations 
FOR DELETE 
TO authenticated 
USING (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (user_id = ( SELECT auth.uid() AS uid)))
);

CREATE POLICY "Integrations Insert Access Control" 
ON integrations 
FOR INSERT 
TO authenticated 
WITH CHECK (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (user_id = ( SELECT auth.uid() AS uid)))
);

CREATE POLICY "Integrations Select Access Control" 
ON integrations 
FOR SELECT 
TO authenticated 
USING (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (user_id = ( SELECT auth.uid() AS uid)))
);

CREATE POLICY "Integrations Update Access Control" 
ON integrations 
FOR UPDATE 
TO authenticated 
USING (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (user_id = ( SELECT auth.uid() AS uid)))
)
WITH CHECK (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (user_id = ( SELECT auth.uid() AS uid)))
);

-- Invoices Policies
CREATE POLICY "Invoices Delete Access Control" 
ON invoices 
FOR DELETE 
TO authenticated 
USING (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (property_id IN ( SELECT prop.id
       FROM properties prop
      WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))
);

CREATE POLICY "Invoices Insert Access Control" 
ON invoices 
FOR INSERT 
TO authenticated 
WITH CHECK (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (property_id IN ( SELECT prop.id
       FROM properties prop
      WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))
);

CREATE POLICY "Invoices Select Access Control" 
ON invoices 
FOR SELECT 
TO authenticated 
USING (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (property_id IN ( SELECT prop.id
       FROM properties prop
      WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))
);

CREATE POLICY "Invoices Update Access Control" 
ON invoices 
FOR UPDATE 
TO authenticated 
USING (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (property_id IN ( SELECT prop.id
       FROM properties prop
      WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))
)
WITH CHECK (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (property_id IN ( SELECT prop.id
       FROM properties prop
      WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))
);

-- Lease Documents Policies
CREATE POLICY "Lease Documents Delete Access Control" 
ON lease_documents 
FOR DELETE 
TO authenticated 
USING (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (lease_id IN ( SELECT l.id
       FROM (leases l
         JOIN properties p ON ((l.property_id = p.id)))
      WHERE (p.user_id = ( SELECT auth.uid() AS uid)))))
);

CREATE POLICY "Lease Documents Insert Access Control" 
ON lease_documents 
FOR INSERT 
TO authenticated 
WITH CHECK (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (lease_id IN ( SELECT l.id
       FROM (leases l
         JOIN properties p ON ((l.property_id = p.id)))
      WHERE (p.user_id = ( SELECT auth.uid() AS uid)))))
);

CREATE POLICY "Lease Documents Select Access Control" 
ON lease_documents 
FOR SELECT 
TO authenticated 
USING (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (lease_id IN ( SELECT l.id
       FROM (leases l
         JOIN properties p ON ((l.property_id = p.id)))
      WHERE (p.user_id = ( SELECT auth.uid() AS uid)))))
);

CREATE POLICY "Lease Documents Update Access Control" 
ON lease_documents 
FOR UPDATE 
TO authenticated 
USING (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (lease_id IN ( SELECT l.id
       FROM (leases l
         JOIN properties p ON ((l.property_id = p.id)))
      WHERE (p.user_id = ( SELECT auth.uid() AS uid)))))
)
WITH CHECK (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (lease_id IN ( SELECT l.id
       FROM (leases l
         JOIN properties p ON ((l.property_id = p.id)))
      WHERE (p.user_id = ( SELECT auth.uid() AS uid)))))
);

-- Leases Policies
CREATE POLICY "Leases Delete Access Control" 
ON leases 
FOR DELETE 
TO authenticated 
USING (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (property_id IN ( SELECT prop.id
       FROM properties prop
      WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))
);

CREATE POLICY "Leases Insert Access Control" 
ON leases 
FOR INSERT 
TO authenticated 
WITH CHECK (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (property_id IN ( SELECT prop.id
       FROM properties prop
      WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))
);

CREATE POLICY "Leases Select Access Control" 
ON leases 
FOR SELECT 
TO authenticated 
USING (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (property_id IN ( SELECT prop.id
       FROM properties prop
      WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))
);

CREATE POLICY "Leases Update Access Control" 
ON leases 
FOR UPDATE 
TO authenticated 
USING (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (property_id IN ( SELECT prop.id
       FROM properties prop
      WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))
)
WITH CHECK (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (property_id IN ( SELECT prop.id
       FROM properties prop
      WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))
);

-- Maintenance Requests Policies
CREATE POLICY "Maintenance Requests Delete Access Control" 
ON maintenance_requests 
FOR DELETE 
TO authenticated 
USING (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (property_id IN ( SELECT prop.id
       FROM properties prop
      WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))
);

CREATE POLICY "Maintenance Requests Insert Access Control" 
ON maintenance_requests 
FOR INSERT 
TO authenticated 
WITH CHECK (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (property_id IN ( SELECT prop.id
       FROM properties prop
      WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))
);

CREATE POLICY "Maintenance Requests Select Access Control" 
ON maintenance_requests 
FOR SELECT 
TO authenticated 
USING (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (property_id IN ( SELECT prop.id
       FROM properties prop
      WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))
);

CREATE POLICY "Maintenance Requests Update Access Control" 
ON maintenance_requests 
FOR UPDATE 
TO authenticated 
USING (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (property_id IN ( SELECT prop.id
       FROM properties prop
      WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))
)
WITH CHECK (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (property_id IN ( SELECT prop.id
       FROM properties prop
      WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))
);

-- Payments Policies
CREATE POLICY "Payments Delete Access Control" 
ON payments 
FOR DELETE 
TO authenticated 
USING (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (lease_id IN ( SELECT l.id
       FROM (leases l
         JOIN properties p ON ((l.property_id = p.id)))
      WHERE (p.user_id = ( SELECT auth.uid() AS uid)))))
);

CREATE POLICY "Payments Insert Access Control" 
ON payments 
FOR INSERT 
TO authenticated 
WITH CHECK (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (lease_id IN ( SELECT l.id
       FROM (leases l
         JOIN properties p ON ((l.property_id = p.id)))
      WHERE (p.user_id = ( SELECT auth.uid() AS uid)))))
);

CREATE POLICY "Payments Select Access Control" 
ON payments 
FOR SELECT 
TO authenticated 
USING (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (lease_id IN ( SELECT l.id
       FROM (leases l
         JOIN properties p ON ((l.property_id = p.id)))
      WHERE (p.user_id = ( SELECT auth.uid() AS uid)))))
);

CREATE POLICY "Payments Update Access Control" 
ON payments 
FOR UPDATE 
TO authenticated 
USING (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (lease_id IN ( SELECT l.id
       FROM (leases l
         JOIN properties p ON ((l.property_id = p.id)))
      WHERE (p.user_id = ( SELECT auth.uid() AS uid)))))
)
WITH CHECK (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (lease_id IN ( SELECT l.id
       FROM (leases l
         JOIN properties p ON ((l.property_id = p.id)))
      WHERE (p.user_id = ( SELECT auth.uid() AS uid)))))
);

-- Properties Policies
CREATE POLICY "Properties Delete Access Control" 
ON properties 
FOR DELETE 
TO authenticated 
USING (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (user_id = ( SELECT auth.uid() AS uid)))
);

CREATE POLICY "Properties Insert Access Control" 
ON properties 
FOR INSERT 
TO authenticated 
WITH CHECK (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (user_id = ( SELECT auth.uid() AS uid)))
);

CREATE POLICY "Properties Select Access Control" 
ON properties 
FOR SELECT 
TO authenticated 
USING (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (user_id = ( SELECT auth.uid() AS uid)))
);

CREATE POLICY "Properties Update Access Control" 
ON properties 
FOR UPDATE 
TO authenticated 
USING (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (user_id = ( SELECT auth.uid() AS uid)))
)
WITH CHECK (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (user_id = ( SELECT auth.uid() AS uid)))
);

-- Property Units Policies
CREATE POLICY "Property Units Delete Access Control" 
ON property_units 
FOR DELETE 
TO authenticated 
USING (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (property_id IN ( SELECT prop.id
       FROM properties prop
      WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))
);

CREATE POLICY "Property Units Insert Access Control" 
ON property_units 
FOR INSERT 
TO authenticated 
WITH CHECK (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (property_id IN ( SELECT prop.id
       FROM properties prop
      WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))
);

CREATE POLICY "Property Units Select Access Control" 
ON property_units 
FOR SELECT 
TO authenticated 
USING (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (property_id IN ( SELECT prop.id
       FROM properties prop
      WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))
);

CREATE POLICY "Property Units Update Access Control" 
ON property_units 
FOR UPDATE 
TO authenticated 
USING (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (property_id IN ( SELECT prop.id
       FROM properties prop
      WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))
)
WITH CHECK (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND (property_id IN ( SELECT prop.id
       FROM properties prop
      WHERE (prop.user_id = ( SELECT auth.uid() AS uid)))))
);

-- Tenant Unit Link Policy
CREATE POLICY "Landlord manage tenant_unit_links for own units" 
ON tenant_unit_link 
FOR ALL 
TO public 
USING (
    is_current_user_landlord() 
    AND 
    (EXISTS ( SELECT 1
       FROM (property_units pu
         JOIN properties p ON ((pu.property_id = p.id)))
      WHERE ((pu.id = tenant_unit_link.unit_id) AND (p.user_id = get_current_app_user_id()))))
)
WITH CHECK (
    is_current_user_landlord() 
    AND 
    (EXISTS ( SELECT 1
       FROM (property_units pu
         JOIN properties p ON ((pu.property_id = p.id)))
      WHERE ((pu.id = tenant_unit_link.unit_id) AND (p.user_id = get_current_app_user_id()))))
);

-- Tenants Policies
CREATE POLICY "Tenant Delete Access Control" 
ON tenants 
FOR DELETE 
TO authenticated 
USING (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND 
     ((EXISTS ( SELECT 1
       FROM properties p
      WHERE ((p.user_id = ( SELECT auth.uid() AS uid)) AND (tenants.current_property_id = p.id)))) 
      OR 
      (EXISTS ( SELECT 1
       FROM (properties p
         JOIN leases l ON ((l.property_id = p.id)))
      WHERE ((p.user_id = ( SELECT auth.uid() AS uid)) AND (l.tenant_id = tenants.id))))))
);

CREATE POLICY "Tenant Insert Access Control" 
ON tenants 
FOR INSERT 
TO authenticated 
WITH CHECK (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND 
     ((current_property_id IS NULL) 
      OR 
      (EXISTS ( SELECT 1
       FROM properties p
      WHERE ((p.id = tenants.current_property_id) AND (p.user_id = ( SELECT auth.uid() AS uid)))))))
);

CREATE POLICY "Tenant Select Access Control" 
ON tenants 
FOR SELECT 
TO authenticated 
USING (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND 
     ((EXISTS ( SELECT 1
       FROM properties p
      WHERE ((p.user_id = ( SELECT auth.uid() AS uid)) AND (tenants.current_property_id = p.id)))) 
      OR 
      (EXISTS ( SELECT 1
       FROM (properties p
         JOIN leases l ON ((l.property_id = p.id)))
      WHERE ((p.user_id = ( SELECT auth.uid() AS uid)) AND (l.tenant_id = tenants.id))))))
);

CREATE POLICY "Tenant Update Access Control" 
ON tenants 
FOR UPDATE 
TO authenticated 
USING (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND 
     ((EXISTS ( SELECT 1
       FROM properties p
      WHERE ((p.user_id = ( SELECT auth.uid() AS uid)) AND (tenants.current_property_id = p.id)))) 
      OR 
      (EXISTS ( SELECT 1
       FROM (properties p
         JOIN leases l ON ((l.property_id = p.id)))
      WHERE ((p.user_id = ( SELECT auth.uid() AS uid)) AND (l.tenant_id = tenants.id))))))
)
WITH CHECK (
    (EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND (u.is_admin IS TRUE)))) 
    OR 
    ((EXISTS ( SELECT 1
       FROM users u
      WHERE ((u.id = ( SELECT auth.uid() AS uid)) AND ((u.user_type)::text = 'LANDLORD'::text) AND (u.is_admin IS FALSE)))) 
     AND 
     ((current_property_id IS NULL) 
      OR 
      (EXISTS ( SELECT 1
       FROM properties p
      WHERE ((p.id = tenants.current_property_id) AND (p.user_id = ( SELECT auth.uid() AS uid)))))))
);

-- Users Policy
CREATE POLICY "Users manage their own record" 
ON users 
FOR ALL 
TO authenticated 
USING (id = ( SELECT auth.uid() AS uid))
WITH CHECK (id = ( SELECT auth.uid() AS uid));

-- Property Type Tables RLS Policies (Added from property_type_split migration)

-- Enable RLS on new property type tables
ALTER TABLE properties_apartment_complex ENABLE ROW LEVEL SECURITY;
ALTER TABLE properties_commercial ENABLE ROW LEVEL SECURITY;
ALTER TABLE properties_residential ENABLE ROW LEVEL SECURITY;
ALTER TABLE properties_industrial ENABLE ROW LEVEL SECURITY;
ALTER TABLE properties_mixed_use ENABLE ROW LEVEL SECURITY;
ALTER TABLE properties_land ENABLE ROW LEVEL SECURITY;
ALTER TABLE properties_special_purpose ENABLE ROW LEVEL SECURITY;
ALTER TABLE properties_other ENABLE ROW LEVEL SECURITY;

-- Apartment Complex Policies
CREATE POLICY "Users can view their own apartment complex details"
  ON properties_apartment_complex FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_apartment_complex.property_id
      AND (properties.user_id = (SELECT auth.uid()) OR EXISTS (
        SELECT 1 FROM users WHERE users.id = (SELECT auth.uid()) AND users.is_admin = true
      ))
    )
  );

CREATE POLICY "Users can insert their own apartment complex details"
  ON properties_apartment_complex FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_apartment_complex.property_id
      AND properties.user_id = (SELECT auth.uid())
    )
  );

CREATE POLICY "Users can update their own apartment complex details"
  ON properties_apartment_complex FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_apartment_complex.property_id
      AND properties.user_id = (SELECT auth.uid())
    )
  );

CREATE POLICY "Users can delete their own apartment complex details"
  ON properties_apartment_complex FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_apartment_complex.property_id
      AND properties.user_id = (SELECT auth.uid())
    )
  );

-- Commercial Properties Policies
CREATE POLICY "Users can view their own commercial details"
  ON properties_commercial FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_commercial.property_id
      AND (properties.user_id = (SELECT auth.uid()) OR EXISTS (
        SELECT 1 FROM users WHERE users.id = (SELECT auth.uid()) AND users.is_admin = true
      ))
    )
  );

CREATE POLICY "Users can insert their own commercial details"
  ON properties_commercial FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_commercial.property_id
      AND properties.user_id = (SELECT auth.uid())
    )
  );

CREATE POLICY "Users can update their own commercial details"
  ON properties_commercial FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_commercial.property_id
      AND properties.user_id = (SELECT auth.uid())
    )
  );

CREATE POLICY "Users can delete their own commercial details"
  ON properties_commercial FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_commercial.property_id
      AND properties.user_id = (SELECT auth.uid())
    )
  );

-- Residential Properties Policies
CREATE POLICY "Users can view their own residential details"
  ON properties_residential FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_residential.property_id
      AND (properties.user_id = (SELECT auth.uid()) OR EXISTS (
        SELECT 1 FROM users WHERE users.id = (SELECT auth.uid()) AND users.is_admin = true
      ))
    )
  );

CREATE POLICY "Users can insert their own residential details"
  ON properties_residential FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_residential.property_id
      AND properties.user_id = (SELECT auth.uid())
    )
  );

CREATE POLICY "Users can update their own residential details"
  ON properties_residential FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_residential.property_id
      AND properties.user_id = (SELECT auth.uid())
    )
  );

CREATE POLICY "Users can delete their own residential details"
  ON properties_residential FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_residential.property_id
      AND properties.user_id = (SELECT auth.uid())
    )
  );

-- Industrial Properties Policies
CREATE POLICY "Users can view their own industrial details"
  ON properties_industrial FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_industrial.property_id
      AND (properties.user_id = (SELECT auth.uid()) OR EXISTS (
        SELECT 1 FROM users WHERE users.id = (SELECT auth.uid()) AND users.is_admin = true
      ))
    )
  );

CREATE POLICY "Users can insert their own industrial details"
  ON properties_industrial FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_industrial.property_id
      AND properties.user_id = (SELECT auth.uid())
    )
  );

CREATE POLICY "Users can update their own industrial details"
  ON properties_industrial FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_industrial.property_id
      AND properties.user_id = (SELECT auth.uid())
    )
  );

CREATE POLICY "Users can delete their own industrial details"
  ON properties_industrial FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_industrial.property_id
      AND properties.user_id = (SELECT auth.uid())
    )
  );

-- Mixed Use Properties Policies
CREATE POLICY "Users can view their own mixed use details"
  ON properties_mixed_use FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_mixed_use.property_id
      AND (properties.user_id = (SELECT auth.uid()) OR EXISTS (
        SELECT 1 FROM users WHERE users.id = (SELECT auth.uid()) AND users.is_admin = true
      ))
    )
  );

CREATE POLICY "Users can insert their own mixed use details"
  ON properties_mixed_use FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_mixed_use.property_id
      AND properties.user_id = (SELECT auth.uid())
    )
  );

CREATE POLICY "Users can update their own mixed use details"
  ON properties_mixed_use FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_mixed_use.property_id
      AND properties.user_id = (SELECT auth.uid())
    )
  );

CREATE POLICY "Users can delete their own mixed use details"
  ON properties_mixed_use FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_mixed_use.property_id
      AND properties.user_id = (SELECT auth.uid())
    )
  );

-- Land Properties Policies
CREATE POLICY "Users can view their own land details"
  ON properties_land FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_land.property_id
      AND (properties.user_id = (SELECT auth.uid()) OR EXISTS (
        SELECT 1 FROM users WHERE users.id = (SELECT auth.uid()) AND users.is_admin = true
      ))
    )
  );

CREATE POLICY "Users can insert their own land details"
  ON properties_land FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_land.property_id
      AND properties.user_id = (SELECT auth.uid())
    )
  );

CREATE POLICY "Users can update their own land details"
  ON properties_land FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_land.property_id
      AND properties.user_id = (SELECT auth.uid())
    )
  );

CREATE POLICY "Users can delete their own land details"
  ON properties_land FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_land.property_id
      AND properties.user_id = (SELECT auth.uid())
    )
  );

-- Special Purpose Properties Policies
CREATE POLICY "Users can view their own special purpose details"
  ON properties_special_purpose FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_special_purpose.property_id
      AND (properties.user_id = (SELECT auth.uid()) OR EXISTS (
        SELECT 1 FROM users WHERE users.id = (SELECT auth.uid()) AND users.is_admin = true
      ))
    )
  );

CREATE POLICY "Users can insert their own special purpose details"
  ON properties_special_purpose FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_special_purpose.property_id
      AND properties.user_id = (SELECT auth.uid())
    )
  );

CREATE POLICY "Users can update their own special purpose details"
  ON properties_special_purpose FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_special_purpose.property_id
      AND properties.user_id = (SELECT auth.uid())
    )
  );

CREATE POLICY "Users can delete their own special purpose details"
  ON properties_special_purpose FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_special_purpose.property_id
      AND properties.user_id = (SELECT auth.uid())
    )
  );

-- Other Properties Policies
CREATE POLICY "Users can view their own other property details"
  ON properties_other FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_other.property_id
      AND (properties.user_id = (SELECT auth.uid()) OR EXISTS (
        SELECT 1 FROM users WHERE users.id = (SELECT auth.uid()) AND users.is_admin = true
      ))
    )
  );

CREATE POLICY "Users can insert their own other property details"
  ON properties_other FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_other.property_id
      AND properties.user_id = (SELECT auth.uid())
    )
  );

CREATE POLICY "Users can update their own other property details"
  ON properties_other FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_other.property_id
      AND properties.user_id = (SELECT auth.uid())
    )
  );

CREATE POLICY "Users can delete their own other property details"
  ON properties_other FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = properties_other.property_id
      AND properties.user_id = (SELECT auth.uid())
    )
  );

-- ============================================
-- VIEWS AND FUNCTIONS (Security Fixes)
-- ============================================

-- Unified properties view with security invoker
CREATE VIEW v_properties_full 
WITH (security_invoker=on) AS
SELECT 
  p.*,
  -- Include type-specific data as JSON
  CASE 
    WHEN p.property_type = 'Apartment Complex' THEN row_to_json(pac)
    WHEN p.property_type = 'Commercial' THEN row_to_json(pc)
    WHEN p.property_type = 'Residential' THEN row_to_json(pr)
    WHEN p.property_type = 'Industrial' THEN row_to_json(pi)
    WHEN p.property_type = 'Mixed-Use' THEN row_to_json(pmu)
    WHEN p.property_type = 'Land' THEN row_to_json(pl)
    WHEN p.property_type = 'Special Purpose' THEN row_to_json(psp)
    WHEN p.property_type = 'Other' THEN row_to_json(po)
    ELSE NULL
  END AS type_specific_details
FROM properties p
LEFT JOIN properties_apartment_complex pac ON p.id = pac.property_id
LEFT JOIN properties_commercial pc ON p.id = pc.property_id
LEFT JOIN properties_residential pr ON p.id = pr.property_id
LEFT JOIN properties_industrial pi ON p.id = pi.property_id
LEFT JOIN properties_mixed_use pmu ON p.id = pmu.property_id
LEFT JOIN properties_land pl ON p.id = pl.property_id
LEFT JOIN properties_special_purpose psp ON p.id = psp.property_id
LEFT JOIN properties_other po ON p.id = po.property_id;

-- Update function with secure search_path
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ language 'plpgsql'
SET search_path = ''; 