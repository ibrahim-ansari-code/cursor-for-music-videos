-- Add trigger to clear user subscription cache on DELETE
-- This migration was applied via MCP during development

-- Function to clear user subscription cache on DELETE
CREATE OR REPLACE FUNCTION billing.clear_user_subscription_cache()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE public.users
    SET
        subscription_status = 'none',
        subscription_tier = 'free',
        current_period_end = NULL,
        trial_ends_at = NULL,
        updated_at = NOW()
    WHERE id = OLD.user_id;
    
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

-- Drop old trigger and create new ones with proper names
DROP TRIGGER IF EXISTS trigger_update_user_subscription_cache ON billing.user_subscriptions;
DROP TRIGGER IF EXISTS trigger_update_user_subscription_cache_upsert ON billing.user_subscriptions;
DROP TRIGGER IF EXISTS trigger_update_user_subscription_cache_delete ON billing.user_subscriptions;

-- Trigger for INSERT or UPDATE
CREATE TRIGGER trigger_update_user_subscription_cache_upsert
    AFTER INSERT OR UPDATE ON billing.user_subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION billing.update_user_subscription_cache();

-- Trigger for DELETE
CREATE TRIGGER trigger_update_user_subscription_cache_delete
    AFTER DELETE ON billing.user_subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION billing.clear_user_subscription_cache();

