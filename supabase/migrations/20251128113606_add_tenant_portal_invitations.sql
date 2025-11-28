-- =============================================================================
-- Migration: Add Tenant Portal Invitations
-- Description: Creates the tenant_portal_invitations table for managing
--              landlord-to-tenant portal invitations with secure tokens
-- =============================================================================

-- Create the tenant_portal_invitations table
CREATE TABLE IF NOT EXISTS tenant_portal_invitations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- Links to tenant and inviting landlord
  tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  invited_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  
  -- Invitation details
  invitation_token TEXT NOT NULL,
  email TEXT NOT NULL,
  
  -- Status tracking
  -- pending: invitation sent, awaiting acceptance
  -- accepted: tenant created account and linked
  -- expired: invitation passed expiry date without acceptance
  -- revoked: landlord cancelled the invitation
  status TEXT NOT NULL DEFAULT 'pending' 
    CHECK (status IN ('pending', 'accepted', 'expired', 'revoked')),
  
  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '7 days'),
  accepted_at TIMESTAMPTZ,
  revoked_at TIMESTAMPTZ
);

-- Add comments for documentation
COMMENT ON TABLE tenant_portal_invitations IS 'Tracks invitations sent by landlords to tenants for portal access. Links tenant records to user accounts upon acceptance.';
COMMENT ON COLUMN tenant_portal_invitations.tenant_id IS 'The tenant record being invited to the portal';
COMMENT ON COLUMN tenant_portal_invitations.invited_by IS 'The landlord user who sent the invitation';
COMMENT ON COLUMN tenant_portal_invitations.invitation_token IS 'Secure token used in the invitation URL (hashed for storage)';
COMMENT ON COLUMN tenant_portal_invitations.email IS 'Email address the invitation was sent to';
COMMENT ON COLUMN tenant_portal_invitations.status IS 'Current status: pending, accepted, expired, or revoked';
COMMENT ON COLUMN tenant_portal_invitations.expires_at IS 'Invitation expiration timestamp (default 7 days from creation)';
COMMENT ON COLUMN tenant_portal_invitations.accepted_at IS 'Timestamp when tenant accepted and created their account';
COMMENT ON COLUMN tenant_portal_invitations.revoked_at IS 'Timestamp when landlord revoked the invitation';

-- =============================================================================
-- Indexes for Performance
-- =============================================================================

-- Fast token lookup (primary use case for acceptance flow)
CREATE UNIQUE INDEX idx_tenant_portal_invitations_token 
  ON tenant_portal_invitations(invitation_token);

-- Fast tenant lookup (for checking invitation status on tenant profile)
CREATE INDEX idx_tenant_portal_invitations_tenant_id 
  ON tenant_portal_invitations(tenant_id);

-- Fast lookup by inviting landlord (for invitation management)
CREATE INDEX idx_tenant_portal_invitations_invited_by 
  ON tenant_portal_invitations(invited_by);

-- Partial index for pending invitations (most common query)
CREATE INDEX idx_tenant_portal_invitations_pending 
  ON tenant_portal_invitations(status, expires_at) 
  WHERE status = 'pending';

-- Enforce only one pending invitation per tenant at a time
CREATE UNIQUE INDEX idx_tenant_portal_invitations_one_pending_per_tenant 
  ON tenant_portal_invitations(tenant_id) 
  WHERE status = 'pending';

-- =============================================================================
-- Row Level Security (RLS) - OPTIMIZED
-- =============================================================================
-- Note: Using (SELECT auth.uid()) instead of auth.uid() to prevent per-row
-- re-evaluation. This is the Supabase-recommended performance optimization.
-- See: Supabase Performance Advisor - Auth RLS Initialization Plan warnings

ALTER TABLE tenant_portal_invitations ENABLE ROW LEVEL SECURITY;

-- Policy: Landlords can view invitations they sent
CREATE POLICY "Landlords can view their own invitations"
  ON tenant_portal_invitations
  FOR SELECT
  USING (invited_by = (SELECT auth.uid()));

-- Policy: Landlords can create invitations for their tenants
CREATE POLICY "Landlords can create invitations for their tenants"
  ON tenant_portal_invitations
  FOR INSERT
  WITH CHECK (
    invited_by = (SELECT auth.uid())
    AND EXISTS (
      SELECT 1 FROM tenants t 
      WHERE t.id = tenant_id 
      AND t.landlord_id = (SELECT auth.uid())
    )
  );

-- Policy: Landlords can update (revoke) invitations they sent
CREATE POLICY "Landlords can update their invitations"
  ON tenant_portal_invitations
  FOR UPDATE
  USING (invited_by = (SELECT auth.uid()))
  WITH CHECK (invited_by = (SELECT auth.uid()));

-- Policy: Landlords can delete invitations they sent
CREATE POLICY "Landlords can delete their invitations"
  ON tenant_portal_invitations
  FOR DELETE
  USING (invited_by = (SELECT auth.uid()));

-- Policy: Service role bypass for backend operations
-- (The backend uses service role key for invitation acceptance)
-- This is handled automatically by Supabase for service_role

-- =============================================================================
-- Trigger for updated_at
-- =============================================================================

-- Create trigger function if it doesn't exist
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql
SET search_path = public;

-- Add trigger to update updated_at on changes
DROP TRIGGER IF EXISTS tenant_portal_invitations_updated_at ON tenant_portal_invitations;
CREATE TRIGGER tenant_portal_invitations_updated_at
  BEFORE UPDATE ON tenant_portal_invitations
  FOR EACH ROW
  EXECUTE FUNCTION public.update_updated_at_column();

-- =============================================================================
-- Function to check invitation validity
-- =============================================================================

CREATE OR REPLACE FUNCTION public.is_invitation_valid(p_token TEXT)
RETURNS TABLE (
  is_valid BOOLEAN,
  tenant_id INTEGER,
  email TEXT,
  expires_at TIMESTAMPTZ,
  status TEXT
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    (i.status = 'pending' AND i.expires_at > NOW()) AS is_valid,
    i.tenant_id,
    i.email,
    i.expires_at,
    i.status
  FROM tenant_portal_invitations i
  WHERE i.invitation_token = p_token;
END;
$$ LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public;

COMMENT ON FUNCTION public.is_invitation_valid IS 'Validates an invitation token and returns its status. Used by the tenant portal acceptance flow.';

