"""change_user_related_ids_to_native_uuid

Revision ID: 4483ad5df02d
Revises: a630e93e0aa3
Create Date: 2025-06-03 19:11:29.532429

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql  # For UUID type

# revision identifiers, used by Alembic.
revision: str = '4483ad5df02d'
down_revision: Union[str, None] = 'a630e93e0aa3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
transactional = False  # <<< This migration should not run in a single transaction

# RLS Policies for 'users' table
USERS_POLICY_NAME = "Users manage their own record"
USERS_TABLE_NAME = "users"
USERS_POLICY_DEF_UUID = f'CREATE POLICY "{USERS_POLICY_NAME}" ON public.{USERS_TABLE_NAME} FOR ALL USING (auth.uid() = id) WITH CHECK (auth.uid() = id)'
USERS_POLICY_DEF_VARCHAR = f'CREATE POLICY "{USERS_POLICY_NAME}" ON public.{USERS_TABLE_NAME} FOR ALL USING ((auth.uid())::text = (id)::text) WITH CHECK ((auth.uid())::text = (id)::text)'

# RLS Policies for 'properties' table
PROPERTIES_TABLE_NAME = "properties"
PROPERTIES_POLICIES_DEF_UUID = [
    ("Landlord can delete own properties", "DELETE",
     "(user_id = get_current_app_user_id() AND is_current_user_landlord())", None),
    ("Landlord can insert own properties", "INSERT", None,
     "(user_id = get_current_app_user_id() AND is_current_user_landlord())"),
    ("Landlord can read own properties", "SELECT",
     "(user_id = get_current_app_user_id() AND is_current_user_landlord())", None),
    ("Landlord can update own properties", "UPDATE",
     "(user_id = get_current_app_user_id() AND is_current_user_landlord())", "(user_id = get_current_app_user_id())"),
]
PROPERTIES_POLICIES_ORIGINAL_DEF = [
    ("Landlord can delete own properties", "DELETE",
     "(((user_id)::text = (get_current_app_user_id())::text) AND is_current_user_landlord())", None),
    ("Landlord can insert own properties", "INSERT", None,
     "(((user_id)::text = (get_current_app_user_id())::text) AND is_current_user_landlord())"),
    ("Landlord can read own properties", "SELECT",
     "(((user_id)::text = (get_current_app_user_id())::text) AND is_current_user_landlord())", None),
    ("Landlord can update own properties", "UPDATE", "(((user_id)::text = (get_current_app_user_id())::text) AND is_current_user_landlord())",
     "((user_id)::text = (get_current_app_user_id())::text)"),
]

# RLS Policies for 'expenses' table
EXPENSES_TABLE_NAME = "expenses"
EXPENSES_POLICIES_DEF_UUID = [
    ("Landlord insert expenses for own properties", "INSERT", None,
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE (p.id = expenses.property_id AND p.user_id = get_current_app_user_id()))))"),
    ("Landlord select expenses for own properties", "SELECT",
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE (p.id = expenses.property_id AND p.user_id = get_current_app_user_id()))))", None),
    ("Landlord update expenses for own properties", "UPDATE", "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE (p.id = expenses.property_id AND p.user_id = get_current_app_user_id()))))",
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE (p.id = expenses.property_id AND p.user_id = get_current_app_user_id()))))"),
    ("Landlord delete expenses for own properties", "DELETE",
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE (p.id = expenses.property_id AND p.user_id = get_current_app_user_id()))))", None),
]
EXPENSES_POLICIES_ORIGINAL_DEF = [
    ("Landlord insert expenses for own properties", "INSERT", None,
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE ((p.id = expenses.property_id) AND ((p.user_id)::text = (get_current_app_user_id())::text))))) "),
    ("Landlord select expenses for own properties", "SELECT",
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE ((p.id = expenses.property_id) AND ((p.user_id)::text = (get_current_app_user_id())::text))))) ", None),
    ("Landlord update expenses for own properties", "UPDATE", "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE ((p.id = expenses.property_id) AND ((p.user_id)::text = (get_current_app_user_id())::text))))) ",
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE ((p.id = expenses.property_id) AND ((p.user_id)::text = (get_current_app_user_id())::text))))) "),
    ("Landlord delete expenses for own properties", "DELETE",
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE ((p.id = expenses.property_id) AND ((p.user_id)::text = (get_current_app_user_id())::text))))) ", None),
]

# RLS Policies for 'leases' table
LEASES_TABLE_NAME = "leases"
LEASES_POLICIES_DEF_UUID = [
    ("Landlord delete leases for own properties", "DELETE",
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE (p.id = leases.property_id AND p.user_id = get_current_app_user_id()))))", None),
    ("Landlord insert leases for own properties", "INSERT", None, "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE (p.id = leases.property_id AND p.user_id = get_current_app_user_id())))) AND ((leases.unit_id IS NULL) OR (EXISTS ( SELECT 1 FROM property_units pu WHERE (pu.id = leases.unit_id AND pu.property_id = leases.property_id))))"),
    ("Landlord select leases for own properties", "SELECT",
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE (p.id = leases.property_id AND p.user_id = get_current_app_user_id()))))", None),
    ("Landlord update leases for own properties", "UPDATE", "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE (p.id = leases.property_id AND p.user_id = get_current_app_user_id()))))",
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE (p.id = leases.property_id AND p.user_id = get_current_app_user_id())))) AND ((leases.unit_id IS NULL) OR (EXISTS ( SELECT 1 FROM property_units pu WHERE (pu.id = leases.unit_id AND pu.property_id = leases.property_id))))"),
]
LEASES_POLICIES_ORIGINAL_DEF = [
    ("Landlord delete leases for own properties", "DELETE",
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE ((p.id = leases.property_id) AND ((p.user_id)::text = (get_current_app_user_id())::text))))) ", None),
    ("Landlord insert leases for own properties", "INSERT", None, "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE ((p.id = leases.property_id) AND ((p.user_id)::text = (get_current_app_user_id())::text))))) AND ((leases.unit_id IS NULL) OR (EXISTS ( SELECT 1 FROM property_units pu WHERE ((pu.id = leases.unit_id) AND (pu.property_id = leases.property_id))))) "),
    ("Landlord select leases for own properties", "SELECT",
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE ((p.id = leases.property_id) AND ((p.user_id)::text = (get_current_app_user_id())::text))))) ", None),
    ("Landlord update leases for own properties", "UPDATE", "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE ((p.id = leases.property_id) AND ((p.user_id)::text = (get_current_app_user_id())::text))))) ",
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE ((p.id = leases.property_id) AND ((p.user_id)::text = (get_current_app_user_id())::text))))) AND ((leases.unit_id IS NULL) OR (EXISTS ( SELECT 1 FROM property_units pu WHERE ((pu.id = leases.unit_id) AND (pu.property_id = leases.property_id))))) "),
]

# RLS Policies for 'payments' table
PAYMENTS_TABLE_NAME = "payments"
PAYMENTS_POLICIES_DEF_UUID = [
    ("Landlord delete payments for own leases", "DELETE",
     "(is_current_user_landlord() AND (EXISTS (SELECT 1 FROM leases l JOIN properties p ON l.property_id = p.id WHERE l.id = payments.lease_id AND p.user_id = get_current_app_user_id())))", None),
    ("Landlord insert payments for own leases", "INSERT", None,
     "(is_current_user_landlord() AND (EXISTS (SELECT 1 FROM leases l JOIN properties p ON l.property_id = p.id WHERE l.id = payments.lease_id AND p.user_id = get_current_app_user_id())))"),
    ("Landlord select payments for own leases", "SELECT",
     "(is_current_user_landlord() AND (EXISTS (SELECT 1 FROM leases l JOIN properties p ON l.property_id = p.id WHERE l.id = payments.lease_id AND p.user_id = get_current_app_user_id())))", None),
    ("Landlord update payments for own leases", "UPDATE", "(is_current_user_landlord() AND (EXISTS (SELECT 1 FROM leases l JOIN properties p ON l.property_id = p.id WHERE l.id = payments.lease_id AND p.user_id = get_current_app_user_id())))",
     "(is_current_user_landlord() AND (EXISTS (SELECT 1 FROM leases l JOIN properties p ON l.property_id = p.id WHERE l.id = payments.lease_id AND p.user_id = get_current_app_user_id())))"),
]
PAYMENTS_POLICIES_ORIGINAL_DEF = [
    ("Landlord delete payments for own leases", "DELETE",
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM (leases l JOIN properties p ON ((l.property_id = p.id))) WHERE ((l.id = payments.lease_id) AND ((p.user_id)::text = (get_current_app_user_id())::text))))) ", None),
    ("Landlord insert payments for own leases", "INSERT", None,
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM (leases l JOIN properties p ON ((l.property_id = p.id))) WHERE ((l.id = payments.lease_id) AND ((p.user_id)::text = (get_current_app_user_id())::text))))) "),
    ("Landlord select payments for own leases", "SELECT",
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM (leases l JOIN properties p ON ((l.property_id = p.id))) WHERE ((l.id = payments.lease_id) AND ((p.user_id)::text = (get_current_app_user_id())::text))))) ", None),
    ("Landlord update payments for own leases", "UPDATE", "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM (leases l JOIN properties p ON ((l.property_id = p.id))) WHERE ((l.id = payments.lease_id) AND ((p.user_id)::text = (get_current_app_user_id())::text))))) ",
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM (leases l JOIN properties p ON ((l.property_id = p.id))) WHERE ((l.id = payments.lease_id) AND ((p.user_id)::text = (get_current_app_user_id())::text))))) "),
]

# RLS Policies for 'invoices' table
INVOICES_TABLE_NAME = "invoices"
INVOICES_POLICIES_DEF_UUID = [
    ("Landlord delete invoices for own properties", "DELETE",
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE (p.id = invoices.property_id AND p.user_id = get_current_app_user_id()))))", None),
    ("Landlord insert invoices for own properties", "INSERT", None,
     "(is_current_user_landlord() AND ((invoices.property_id IS NOT NULL) AND (EXISTS ( SELECT 1 FROM properties p WHERE (p.id = invoices.property_id AND p.user_id = get_current_app_user_id()))))) "),
    ("Landlord select invoices for own properties", "SELECT",
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE (p.id = invoices.property_id AND p.user_id = get_current_app_user_id()))))", None),
    ("Landlord update invoices for own properties", "UPDATE", "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE (p.id = invoices.property_id AND p.user_id = get_current_app_user_id()))))",
     "(is_current_user_landlord() AND ((invoices.property_id IS NOT NULL) AND (EXISTS ( SELECT 1 FROM properties p WHERE (p.id = invoices.property_id AND p.user_id = get_current_app_user_id()))))) "),
]
INVOICES_POLICIES_ORIGINAL_DEF = [
    ("Landlord delete invoices for own properties", "DELETE",
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE ((p.id = invoices.property_id) AND ((p.user_id)::text = (get_current_app_user_id())::text))))) ", None),
    ("Landlord insert invoices for own properties", "INSERT", None,
     "(is_current_user_landlord() AND ((invoices.property_id IS NOT NULL) AND (EXISTS ( SELECT 1 FROM properties p WHERE ((p.id = invoices.property_id) AND ((p.user_id)::text = (get_current_app_user_id())::text)))))) "),
    ("Landlord select invoices for own properties", "SELECT",
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE ((p.id = invoices.property_id) AND ((p.user_id)::text = (get_current_app_user_id())::text))))) ", None),
    ("Landlord update invoices for own properties", "UPDATE", "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE ((p.id = invoices.property_id) AND ((p.user_id)::text = (get_current_app_user_id())::text))))) ",
     "(is_current_user_landlord() AND ((invoices.property_id IS NOT NULL) AND (EXISTS ( SELECT 1 FROM properties p WHERE ((p.id = invoices.property_id) AND ((p.user_id)::text = (get_current_app_user_id())::text)))))) "),
]

# RLS Policies for 'tenants' table
TENANTS_TABLE_NAME = "tenants"
TENANTS_POLICIES_DEF_UUID = [
    ("Landlord delete own tenants", "DELETE", "(is_current_user_landlord() AND ((EXISTS ( SELECT 1 FROM properties p WHERE (p.id = tenants.current_property_id AND p.user_id = get_current_app_user_id()))) OR (EXISTS ( SELECT 1 FROM tenant_unit_link tul JOIN property_units pu ON tul.unit_id = pu.id JOIN properties p ON pu.property_id = p.id WHERE (tul.tenant_id = tenants.id AND p.user_id = get_current_app_user_id())))))", None),
    ("Landlord insert own tenants", "INSERT", None,
     "(is_current_user_landlord() AND ((current_property_id IS NULL) OR (EXISTS ( SELECT 1 FROM properties p WHERE (p.id = tenants.current_property_id AND p.user_id = get_current_app_user_id())))))"),
    ("Landlord select own tenants", "SELECT", "(is_current_user_landlord() AND ((EXISTS ( SELECT 1 FROM properties p WHERE (p.id = tenants.current_property_id AND p.user_id = get_current_app_user_id()))) OR (EXISTS ( SELECT 1 FROM tenant_unit_link tul JOIN property_units pu ON tul.unit_id = pu.id JOIN properties p ON pu.property_id = p.id WHERE (tul.tenant_id = tenants.id AND p.user_id = get_current_app_user_id())))))", None),
    ("Landlord update own tenants", "UPDATE", "(is_current_user_landlord() AND ((EXISTS ( SELECT 1 FROM properties p WHERE (p.id = tenants.current_property_id AND p.user_id = get_current_app_user_id()))) OR (EXISTS ( SELECT 1 FROM tenant_unit_link tul JOIN property_units pu ON tul.unit_id = pu.id JOIN properties p ON pu.property_id = p.id WHERE (tul.tenant_id = tenants.id AND p.user_id = get_current_app_user_id())))))",
     "(is_current_user_landlord() AND ((current_property_id IS NULL) OR (EXISTS ( SELECT 1 FROM properties p WHERE (p.id = tenants.current_property_id AND p.user_id = get_current_app_user_id())))))"),
]
TENANTS_POLICIES_ORIGINAL_DEF = [
    ("Landlord delete own tenants", "DELETE", "(is_current_user_landlord() AND ((EXISTS ( SELECT 1 FROM properties p WHERE ((p.id = tenants.current_property_id) AND ((p.user_id)::text = (get_current_app_user_id())::text)))) OR (EXISTS ( SELECT 1 FROM ((tenant_unit_link tul JOIN property_units pu ON ((tul.unit_id = pu.id))) JOIN properties p ON ((pu.property_id = p.id))) WHERE ((tul.tenant_id = tenants.id) AND ((p.user_id)::text = (get_current_app_user_id())::text))))))", None),
    ("Landlord insert own tenants", "INSERT", None,
     "(is_current_user_landlord() AND ((current_property_id IS NULL) OR (EXISTS ( SELECT 1 FROM properties p WHERE ((p.id = tenants.current_property_id) AND ((p.user_id)::text = (get_current_app_user_id())::text)))))) "),
    ("Landlord select own tenants", "SELECT", "(is_current_user_landlord() AND ((EXISTS ( SELECT 1 FROM properties p WHERE ((p.id = tenants.current_property_id) AND ((p.user_id)::text = (get_current_app_user_id())::text)))) OR (EXISTS ( SELECT 1 FROM ((tenant_unit_link tul JOIN property_units pu ON ((tul.unit_id = pu.id))) JOIN properties p ON ((pu.property_id = p.id))) WHERE ((tul.tenant_id = tenants.id) AND ((p.user_id)::text = (get_current_app_user_id())::text))))))", None),
    ("Landlord update own tenants", "UPDATE", "(is_current_user_landlord() AND ((EXISTS ( SELECT 1 FROM properties p WHERE ((p.id = tenants.current_property_id) AND ((p.user_id)::text = (get_current_app_user_id())::text)))) OR (EXISTS ( SELECT 1 FROM ((tenant_unit_link tul JOIN property_units pu ON ((tul.unit_id = pu.id))) JOIN properties p ON ((pu.property_id = p.id))) WHERE ((tul.tenant_id = tenants.id) AND ((p.user_id)::text = (get_current_app_user_id())::text))))))",
     "(is_current_user_landlord() AND ((current_property_id IS NULL) OR (EXISTS ( SELECT 1 FROM properties p WHERE ((p.id = tenants.current_property_id) AND ((p.user_id)::text = (get_current_app_user_id())::text)))))) "),
]

# RLS Policies for 'lease_documents' table
LEASE_DOCUMENTS_TABLE_NAME = "lease_documents"
LEASE_DOCUMENTS_POLICIES_DEF_UUID = [
    ("Landlord select documents for own leases", "SELECT",
     "(is_current_user_landlord() AND (EXISTS (SELECT 1 FROM leases l JOIN properties p ON l.property_id = p.id WHERE l.id = lease_documents.lease_id AND p.user_id = get_current_app_user_id())))", None),
    ("Landlord insert documents for own leases", "INSERT", None,
     "(is_current_user_landlord() AND (lease_documents.uploaded_by_id = get_current_app_user_id()) AND (EXISTS (SELECT 1 FROM leases l JOIN properties p ON l.property_id = p.id WHERE l.id = lease_documents.lease_id AND p.user_id = get_current_app_user_id())))"),
    ("Landlord update documents for own leases", "UPDATE", "(is_current_user_landlord() AND (EXISTS (SELECT 1 FROM leases l JOIN properties p ON l.property_id = p.id WHERE l.id = lease_documents.lease_id AND p.user_id = get_current_app_user_id())))",
     "(is_current_user_landlord() AND (lease_documents.uploaded_by_id = get_current_app_user_id()) AND (EXISTS (SELECT 1 FROM leases l JOIN properties p ON l.property_id = p.id WHERE l.id = lease_documents.lease_id AND p.user_id = get_current_app_user_id())))"),
    ("Landlord delete documents for own leases", "DELETE",
     "(is_current_user_landlord() AND (EXISTS (SELECT 1 FROM leases l JOIN properties p ON l.property_id = p.id WHERE l.id = lease_documents.lease_id AND p.user_id = get_current_app_user_id())))", None),
]
LEASE_DOCUMENTS_POLICIES_ORIGINAL_DEF = [
    ("Landlord select documents for own leases", "SELECT",
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM (leases l JOIN properties p ON ((l.property_id = p.id))) WHERE ((l.id = lease_documents.lease_id) AND ((p.user_id)::text = (get_current_app_user_id())::text))))) ", None),
    ("Landlord insert documents for own leases", "INSERT", None, "(is_current_user_landlord() AND ((lease_documents.uploaded_by_id)::text = (get_current_app_user_id())::text) AND (EXISTS ( SELECT 1 FROM (leases l JOIN properties p ON ((l.property_id = p.id))) WHERE ((l.id = lease_documents.lease_id) AND ((p.user_id)::text = (get_current_app_user_id())::text))))) "),
    ("Landlord update documents for own leases", "UPDATE", "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM (leases l JOIN properties p ON ((l.property_id = p.id))) WHERE ((l.id = lease_documents.lease_id) AND ((p.user_id)::text = (get_current_app_user_id())::text))))) ",
     "(is_current_user_landlord() AND ((lease_documents.uploaded_by_id)::text = (get_current_app_user_id())::text) AND (EXISTS ( SELECT 1 FROM (leases l JOIN properties p ON ((l.property_id = p.id))) WHERE ((l.id = lease_documents.lease_id) AND ((p.user_id)::text = (get_current_app_user_id())::text))))) "),
    ("Landlord delete documents for own leases", "DELETE",
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM (leases l JOIN properties p ON ((l.property_id = p.id))) WHERE ((l.id = lease_documents.lease_id) AND ((p.user_id)::text = (get_current_app_user_id())::text))))) ", None),
]

# RLS Policies for 'tenant_unit_link' table
TENANT_UNIT_LINK_TABLE_NAME = "tenant_unit_link"
TENANT_UNIT_LINK_POLICIES_DEF_UUID = [
    ("Landlord manage tenant_unit_links for own units", "*", "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM property_units pu JOIN properties p ON pu.property_id = p.id WHERE (pu.id = tenant_unit_link.unit_id AND p.user_id = get_current_app_user_id()))))",
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM property_units pu JOIN properties p ON pu.property_id = p.id WHERE (pu.id = tenant_unit_link.unit_id AND p.user_id = get_current_app_user_id()))))"),
]
TENANT_UNIT_LINK_POLICIES_ORIGINAL_DEF = [
    ("Landlord manage tenant_unit_links for own units", "*", "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM (property_units pu JOIN properties p ON ((pu.property_id = p.id))) WHERE ((pu.id = tenant_unit_link.unit_id) AND ((p.user_id)::text = (get_current_app_user_id())::text))))) ",
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM (property_units pu JOIN properties p ON ((pu.property_id = p.id))) WHERE ((pu.id = tenant_unit_link.unit_id) AND ((p.user_id)::text = (get_current_app_user_id())::text))))) "),
]

# RLS Policies for 'property_units' table
PROPERTY_UNITS_TABLE_NAME = "property_units"
PROPERTY_UNITS_POLICIES_DEF_UUID = [
    ("Landlord select units in own properties", "SELECT",
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE (p.id = property_units.property_id AND p.user_id = get_current_app_user_id()))))", None),
    ("Landlord insert units into own properties", "INSERT", None,
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE (p.id = property_units.property_id AND p.user_id = get_current_app_user_id()))))"),
    ("Landlord update units in own properties", "UPDATE", "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE (p.id = property_units.property_id AND p.user_id = get_current_app_user_id()))))",
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE (p.id = property_units.property_id AND p.user_id = get_current_app_user_id()))))"),
    ("Landlord delete units in own properties", "DELETE",
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE (p.id = property_units.property_id AND p.user_id = get_current_app_user_id()))))", None),
]
PROPERTY_UNITS_POLICIES_ORIGINAL_DEF = [
    ("Landlord select units in own properties", "SELECT",
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE ((p.id = property_units.property_id) AND ((p.user_id)::text = (get_current_app_user_id())::text))))) ", None),
    ("Landlord insert units into own properties", "INSERT", None,
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE ((p.id = property_units.property_id) AND ((p.user_id)::text = (get_current_app_user_id())::text))))) "),
    ("Landlord update units in own properties", "UPDATE", "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE ((p.id = property_units.property_id) AND ((p.user_id)::text = (get_current_app_user_id())::text))))) ",
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE ((p.id = property_units.property_id) AND ((p.user_id)::text = (get_current_app_user_id())::text))))) "),
    ("Landlord delete units in own properties", "DELETE",
     "(is_current_user_landlord() AND (EXISTS ( SELECT 1 FROM properties p WHERE ((p.id = property_units.property_id) AND ((p.user_id)::text = (get_current_app_user_id())::text))))) ", None),
]

# Constraint names identified from Supabase schema introspection
# It's crucial these names are correct for your specific database.
FK_CONSTRAINTS_TO_DROP_AND_RECREATE = [
    ("properties_user_id_fkey", "properties",
     "users", ["user_id"], ["id"], "CASCADE"),
    ("tenants_user_id_fkey", "tenants",
     "users", ["user_id"], ["id"], "SET NULL"),
    ("payments_tenant_id_fkey", "payments",
     "users", ["tenant_id"], ["id"], "SET NULL"),
    ("invoices_tenant_id_fkey", "invoices",
     "users", ["tenant_id"], ["id"], "SET NULL"),
    ("lease_documents_uploaded_by_id_fkey", "lease_documents",
     "users", ["uploaded_by_id"], ["id"], "SET NULL"),
]

COLUMNS_TO_CONVERT_TO_UUID = [
    # This is changed before users.id, so its FK needs to be dropped first.
    ("properties", "user_id"),
    ("users", "id"),
    ("tenants", "user_id"),
    ("payments", "tenant_id"),
    ("invoices", "tenant_id"),
    ("lease_documents", "uploaded_by_id"),
]

# Assuming default Supabase sequence name
USERS_ID_SEQUENCE_NAME = "users_id_seq"


def upgrade() -> None:
    """
    Upgrades the database schema by converting user-related ID columns from string to native UUID types and recreating associated RLS policies.
    
    This migration drops and recreates foreign key constraints and alters relevant columns in multiple tables to use UUID types instead of varchar. It also recreates all affected Row-Level Security (RLS) policies with updated UUID-aware expressions. Manual dropping of existing RLS policies is required before running this upgrade.
    """
    # IMPORTANT: Manually drop policies via Supabase SQL editor BEFORE running this upgrade:
    # DROP POLICY IF EXISTS "Users manage their own record" ON public.users;
    # Policies on properties:
    # DROP POLICY IF EXISTS "Landlord can delete own properties" ON public.properties;
    # DROP POLICY IF EXISTS "Landlord can insert own properties" ON public.properties;
    # DROP POLICY IF EXISTS "Landlord can read own properties" ON public.properties;
    # DROP POLICY IF EXISTS "Landlord can update own properties" ON public.properties;
    # Policies on expenses:
    # DROP POLICY IF EXISTS "Landlord insert expenses for own properties" ON public.expenses;
    # DROP POLICY IF EXISTS "Landlord select expenses for own properties" ON public.expenses;
    # DROP POLICY IF EXISTS "Landlord update expenses for own properties" ON public.expenses;
    # DROP POLICY IF EXISTS "Landlord delete expenses for own properties" ON public.expenses;
    # Policies on leases:
    # DROP POLICY IF EXISTS "Landlord delete leases for own properties" ON public.leases;
    # DROP POLICY IF EXISTS "Landlord insert leases for own properties" ON public.leases;
    # DROP POLICY IF EXISTS "Landlord select leases for own properties" ON public.leases;
    # DROP POLICY IF EXISTS "Landlord update leases for own properties" ON public.leases;
    # Policies on payments:
    # DROP POLICY IF EXISTS "Landlord delete payments for own leases" ON public.payments;
    # DROP POLICY IF EXISTS "Landlord insert payments for own leases" ON public.payments;
    # DROP POLICY IF EXISTS "Landlord select payments for own leases" ON public.payments;
    # DROP POLICY IF EXISTS "Landlord update payments for own leases" ON public.payments;
    # Policies on invoices:
    # DROP POLICY IF EXISTS "Landlord delete invoices for own properties" ON public.invoices;
    # DROP POLICY IF EXISTS "Landlord insert invoices for own properties" ON public.invoices;
    # DROP POLICY IF EXISTS "Landlord select invoices for own properties" ON public.invoices;
    # DROP POLICY IF EXISTS "Landlord update invoices for own properties" ON public.invoices;
    # Policies on tenants:
    # DROP POLICY IF EXISTS "Landlord delete own tenants" ON public.tenants;
    # DROP POLICY IF EXISTS "Landlord insert own tenants" ON public.tenants;
    # DROP POLICY IF EXISTS "Landlord select own tenants" ON public.tenants;
    # DROP POLICY IF EXISTS "Landlord update own tenants" ON public.tenants;
    # Policies on lease_documents:
    # DROP POLICY IF EXISTS "Landlord select documents for own leases" ON public.lease_documents;
    # DROP POLICY IF EXISTS "Landlord insert documents for own leases" ON public.lease_documents;
    # DROP POLICY IF EXISTS "Landlord update documents for own leases" ON public.lease_documents;
    # DROP POLICY IF EXISTS "Landlord delete documents for own leases" ON public.lease_documents;
    # Policies on tenant_unit_link:
    # DROP POLICY IF EXISTS "Landlord manage tenant_unit_links for own units" ON public.tenant_unit_link;
    # Policies on property_units:
    # DROP POLICY IF EXISTS "Landlord select units in own properties" ON public.property_units;
    # DROP POLICY IF EXISTS "Landlord insert units into own properties" ON public.property_units;
    # DROP POLICY IF EXISTS "Landlord update units in own properties" ON public.property_units;
    # DROP POLICY IF EXISTS "Landlord delete units in own properties" ON public.property_units;

    for fk_name, table_name, _, _, _, _ in FK_CONSTRAINTS_TO_DROP_AND_RECREATE:
        op.drop_constraint(fk_name, table_name, type_='foreignkey')

    op.alter_column('users', 'id', server_default=None)
    op.alter_column('users', 'id', type_=postgresql.UUID(
        as_uuid=True), postgresql_using='id::uuid')
    op.alter_column('users', 'id', server_default=sa.text('gen_random_uuid()'))

    for table_name, column_name in COLUMNS_TO_CONVERT_TO_UUID:
        op.alter_column(table_name, column_name, type_=postgresql.UUID(
            as_uuid=True), postgresql_using=f'{column_name}::uuid')

    for fk_name, table_name, referent_table, local_cols, remote_cols, ondelete_action in FK_CONSTRAINTS_TO_DROP_AND_RECREATE:
        op.create_foreign_key(fk_name, table_name, referent_table,
                              local_cols, remote_cols, ondelete=ondelete_action)

    op.execute(USERS_POLICY_DEF_UUID)
    for policy_name, command_type_char, using_expr, check_expr in PROPERTIES_POLICIES_DEF_UUID:
        cmd_map = {"r": "SELECT", "a": "INSERT",
                   "w": "UPDATE", "d": "DELETE", "*": "ALL"}
        sql = f'CREATE POLICY "{policy_name}" ON public.{PROPERTIES_TABLE_NAME} FOR {cmd_map.get(command_type_char, "ALL")}'
        if using_expr:
            sql += f' USING ({using_expr})'
        if check_expr:
            sql += f' WITH CHECK ({check_expr})'
        op.execute(sql)
    for policy_name, command_type_char, using_expr, check_expr in EXPENSES_POLICIES_DEF_UUID:
        cmd_map = {"r": "SELECT", "a": "INSERT",
                   "w": "UPDATE", "d": "DELETE", "*": "ALL"}
        sql = f'CREATE POLICY "{policy_name}" ON public.{EXPENSES_TABLE_NAME} FOR {cmd_map.get(command_type_char, "ALL")}'
        if using_expr:
            sql += f' USING ({using_expr})'
        if check_expr:
            sql += f' WITH CHECK ({check_expr})'
        op.execute(sql)
    for policy_name, command_type_char, using_expr, check_expr in LEASES_POLICIES_DEF_UUID:
        cmd_map = {"r": "SELECT", "a": "INSERT",
                   "w": "UPDATE", "d": "DELETE", "*": "ALL"}
        sql = f'CREATE POLICY "{policy_name}" ON public.{LEASES_TABLE_NAME} FOR {cmd_map.get(command_type_char, "ALL")}'
        if using_expr:
            sql += f' USING ({using_expr})'
        if check_expr:
            sql += f' WITH CHECK ({check_expr})'
        op.execute(sql)
    for policy_name, command_type_char, using_expr, check_expr in PAYMENTS_POLICIES_DEF_UUID:
        cmd_map = {"r": "SELECT", "a": "INSERT",
                   "w": "UPDATE", "d": "DELETE", "*": "ALL"}
        sql = f'CREATE POLICY "{policy_name}" ON public.{PAYMENTS_TABLE_NAME} FOR {cmd_map.get(command_type_char, "ALL")}'
        if using_expr:
            sql += f' USING ({using_expr})'
        if check_expr:
            sql += f' WITH CHECK ({check_expr})'
        op.execute(sql)
    for policy_name, command_type_char, using_expr, check_expr in INVOICES_POLICIES_DEF_UUID:
        cmd_map = {"r": "SELECT", "a": "INSERT",
                   "w": "UPDATE", "d": "DELETE", "*": "ALL"}
        sql = f'CREATE POLICY "{policy_name}" ON public.{INVOICES_TABLE_NAME} FOR {cmd_map.get(command_type_char, "ALL")}'
        if using_expr:
            sql += f' USING ({using_expr})'
        if check_expr:
            sql += f' WITH CHECK ({check_expr})'
        op.execute(sql)
    for policy_name, command_type_char, using_expr, check_expr in TENANTS_POLICIES_DEF_UUID:
        cmd_map = {"r": "SELECT", "a": "INSERT",
                   "w": "UPDATE", "d": "DELETE", "*": "ALL"}
        sql = f'CREATE POLICY "{policy_name}" ON public.{TENANTS_TABLE_NAME} FOR {cmd_map.get(command_type_char, "ALL")}'
        if using_expr:
            sql += f' USING ({using_expr})'
        if check_expr:
            sql += f' WITH CHECK ({check_expr})'
        op.execute(sql)
    for policy_name, command_type_char, using_expr, check_expr in LEASE_DOCUMENTS_POLICIES_DEF_UUID:
        cmd_map = {"r": "SELECT", "a": "INSERT",
                   "w": "UPDATE", "d": "DELETE", "*": "ALL"}
        sql = f'CREATE POLICY "{policy_name}" ON public.{LEASE_DOCUMENTS_TABLE_NAME} FOR {cmd_map.get(command_type_char, "ALL")}'
        if using_expr:
            sql += f' USING ({using_expr})'
        if check_expr:
            sql += f' WITH CHECK ({check_expr})'
        op.execute(sql)
    for policy_name, command_type_char, using_expr, check_expr in TENANT_UNIT_LINK_POLICIES_DEF_UUID:
        cmd_map = {"r": "SELECT", "a": "INSERT",
                   "w": "UPDATE", "d": "DELETE", "*": "ALL"}
        sql = f'CREATE POLICY "{policy_name}" ON public.{TENANT_UNIT_LINK_TABLE_NAME} FOR {cmd_map.get(command_type_char, "ALL")}'
        if using_expr:
            sql += f' USING ({using_expr})'
        if check_expr:
            sql += f' WITH CHECK ({check_expr})'
        op.execute(sql)
    for policy_name, command_type_char, using_expr, check_expr in PROPERTY_UNITS_POLICIES_DEF_UUID:
        cmd_map = {"r": "SELECT", "a": "INSERT",
                   "w": "UPDATE", "d": "DELETE", "*": "ALL"}
        sql = f'CREATE POLICY "{policy_name}" ON public.{PROPERTY_UNITS_TABLE_NAME} FOR {cmd_map.get(command_type_char, "ALL")}'
        if using_expr:
            sql += f' USING ({using_expr})'
        if check_expr:
            sql += f' WITH CHECK ({check_expr})'
        op.execute(sql)


def downgrade() -> None:
    """
    Reverts user-related ID columns and associated RLS policies from UUID types back to varchar.
    
    This function downgrades the database schema by converting all previously migrated user-related UUID columns to their original varchar(36) types, restoring the default sequence for the `users.id` column, and recreating all affected foreign key constraints and Row-Level Security (RLS) policies using varchar-based definitions. Assumes all relevant RLS policies have been manually dropped prior to execution.
    """
    # IMPORTANT: Manually drop policies via Supabase SQL editor BEFORE running this downgrade

    for fk_name, table_name, _, _, _, _ in FK_CONSTRAINTS_TO_DROP_AND_RECREATE:
        op.drop_constraint(fk_name, table_name, type_='foreignkey')

    op.alter_column('users', 'id', server_default=None)
    op.alter_column('users', 'id', type_=sa.String(
        length=36), postgresql_using='id::varchar')
    op.alter_column('users', 'id', server_default=sa.text(
        f"nextval('{USERS_ID_SEQUENCE_NAME}'::regclass)"))

    for table_name, column_name in COLUMNS_TO_CONVERT_TO_UUID:
        op.alter_column(table_name, column_name, type_=sa.String(
            length=36), postgresql_using=f'{column_name}::varchar')

    for fk_name, table_name, referent_table, local_cols, remote_cols, ondelete_action in FK_CONSTRAINTS_TO_DROP_AND_RECREATE:
        op.create_foreign_key(fk_name, table_name, referent_table,
                              local_cols, remote_cols, ondelete=ondelete_action)

    op.execute(USERS_POLICY_DEF_VARCHAR)
    for policy_name, command_type_char, using_expr, check_expr in PROPERTIES_POLICIES_ORIGINAL_DEF:
        cmd_map = {"r": "SELECT", "a": "INSERT",
                   "w": "UPDATE", "d": "DELETE", "*": "ALL"}
        sql = f'CREATE POLICY "{policy_name}" ON public.{PROPERTIES_TABLE_NAME} FOR {cmd_map.get(command_type_char, "ALL")}'
        if using_expr:
            sql += f' USING ({using_expr})'
        if check_expr:
            sql += f' WITH CHECK ({check_expr})'
        op.execute(sql)
    for policy_name, command_type_char, using_expr, check_expr in EXPENSES_POLICIES_ORIGINAL_DEF:
        cmd_map = {"r": "SELECT", "a": "INSERT",
                   "w": "UPDATE", "d": "DELETE", "*": "ALL"}
        sql = f'CREATE POLICY "{policy_name}" ON public.{EXPENSES_TABLE_NAME} FOR {cmd_map.get(command_type_char, "ALL")}'
        if using_expr:
            sql += f' USING ({using_expr})'
        if check_expr:
            sql += f' WITH CHECK ({check_expr})'
        op.execute(sql)
    for policy_name, command_type_char, using_expr, check_expr in LEASES_POLICIES_ORIGINAL_DEF:
        cmd_map = {"r": "SELECT", "a": "INSERT",
                   "w": "UPDATE", "d": "DELETE", "*": "ALL"}
        sql = f'CREATE POLICY "{policy_name}" ON public.{LEASES_TABLE_NAME} FOR {cmd_map.get(command_type_char, "ALL")}'
        if using_expr:
            sql += f' USING ({using_expr})'
        if check_expr:
            sql += f' WITH CHECK ({check_expr})'
        op.execute(sql)
    for policy_name, command_type_char, using_expr, check_expr in PAYMENTS_POLICIES_ORIGINAL_DEF:
        cmd_map = {"r": "SELECT", "a": "INSERT",
                   "w": "UPDATE", "d": "DELETE", "*": "ALL"}
        sql = f'CREATE POLICY "{policy_name}" ON public.{PAYMENTS_TABLE_NAME} FOR {cmd_map.get(command_type_char, "ALL")}'
        if using_expr:
            sql += f' USING ({using_expr})'
        if check_expr:
            sql += f' WITH CHECK ({check_expr})'
        op.execute(sql)
    for policy_name, command_type_char, using_expr, check_expr in INVOICES_POLICIES_ORIGINAL_DEF:
        cmd_map = {"r": "SELECT", "a": "INSERT",
                   "w": "UPDATE", "d": "DELETE", "*": "ALL"}
        sql = f'CREATE POLICY "{policy_name}" ON public.{INVOICES_TABLE_NAME} FOR {cmd_map.get(command_type_char, "ALL")}'
        if using_expr:
            sql += f' USING ({using_expr})'
        if check_expr:
            sql += f' WITH CHECK ({check_expr})'
        op.execute(sql)
    for policy_name, command_type_char, using_expr, check_expr in TENANTS_POLICIES_ORIGINAL_DEF:
        cmd_map = {"r": "SELECT", "a": "INSERT",
                   "w": "UPDATE", "d": "DELETE", "*": "ALL"}
        sql = f'CREATE POLICY "{policy_name}" ON public.{TENANTS_TABLE_NAME} FOR {cmd_map.get(command_type_char, "ALL")}'
        if using_expr:
            sql += f' USING ({using_expr})'
        if check_expr:
            sql += f' WITH CHECK ({check_expr})'
        op.execute(sql)
    for policy_name, command_type_char, using_expr, check_expr in LEASE_DOCUMENTS_POLICIES_ORIGINAL_DEF:
        cmd_map = {"r": "SELECT", "a": "INSERT",
                   "w": "UPDATE", "d": "DELETE", "*": "ALL"}
        sql = f'CREATE POLICY "{policy_name}" ON public.{LEASE_DOCUMENTS_TABLE_NAME} FOR {cmd_map.get(command_type_char, "ALL")}'
        if using_expr:
            sql += f' USING ({using_expr})'
        if check_expr:
            sql += f' WITH CHECK ({check_expr})'
        op.execute(sql)
    for policy_name, command_type_char, using_expr, check_expr in TENANT_UNIT_LINK_POLICIES_ORIGINAL_DEF:
        cmd_map = {"r": "SELECT", "a": "INSERT",
                   "w": "UPDATE", "d": "DELETE", "*": "ALL"}
        sql = f'CREATE POLICY "{policy_name}" ON public.{TENANT_UNIT_LINK_TABLE_NAME} FOR {cmd_map.get(command_type_char, "ALL")}'
        if using_expr:
            sql += f' USING ({using_expr})'
        if check_expr:
            sql += f' WITH CHECK ({check_expr})'
        op.execute(sql)
    for policy_name, command_type_char, using_expr, check_expr in PROPERTY_UNITS_POLICIES_ORIGINAL_DEF:
        cmd_map = {"r": "SELECT", "a": "INSERT",
                   "w": "UPDATE", "d": "DELETE", "*": "ALL"}
        sql = f'CREATE POLICY "{policy_name}" ON public.{PROPERTY_UNITS_TABLE_NAME} FOR {cmd_map.get(command_type_char, "ALL")}'
        if using_expr:
            sql += f' USING ({using_expr})'
        if check_expr:
            sql += f' WITH CHECK ({check_expr})'
        op.execute(sql)
