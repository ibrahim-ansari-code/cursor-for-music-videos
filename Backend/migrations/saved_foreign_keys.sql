-- Saved Foreign Key Constraints for restoration after migration
-- Generated on migration fix

-- Foreign keys referencing users.id
ALTER TABLE integrations ADD CONSTRAINT integrations_user_id_fkey FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE NO ACTION;
ALTER TABLE lease_documents ADD CONSTRAINT lease_documents_uploaded_by_id_fkey FOREIGN KEY (uploaded_by_id) REFERENCES users (id) ON DELETE SET NULL;
ALTER TABLE maintenance_requests ADD CONSTRAINT maintenance_requests_user_id_fkey FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL;
ALTER TABLE properties ADD CONSTRAINT properties_user_id_fkey FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE;
ALTER TABLE tenants ADD CONSTRAINT tenants_landlord_id_fkey FOREIGN KEY (landlord_id) REFERENCES users (id) ON DELETE SET NULL;
ALTER TABLE tenants ADD CONSTRAINT tenants_user_id_fkey FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL;

-- Foreign keys referencing tenants.id 
ALTER TABLE invoices ADD CONSTRAINT invoices_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE NO ACTION;
ALTER TABLE payments ADD CONSTRAINT payments_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES tenants (id) ON DELETE NO ACTION;

-- Other foreign keys on tenants table
ALTER TABLE tenants ADD CONSTRAINT tenants_current_property_id_fkey_corrected FOREIGN KEY (current_property_id) REFERENCES properties (id) ON DELETE SET NULL; 