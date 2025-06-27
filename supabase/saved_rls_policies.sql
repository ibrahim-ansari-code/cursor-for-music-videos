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