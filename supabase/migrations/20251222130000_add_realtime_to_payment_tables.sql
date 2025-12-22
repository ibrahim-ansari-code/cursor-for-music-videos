-- Add payment tables to Supabase Realtime publication
-- This enables real-time subscriptions for instant balance/transaction updates

-- Check if tables are already in publication before adding
DO $$
BEGIN
  -- Add rent_payment_transactions if not already in publication
  IF NOT EXISTS (
    SELECT 1 FROM pg_publication_tables
    WHERE pubname = 'supabase_realtime'
    AND tablename = 'rent_payment_transactions'
  ) THEN
    ALTER PUBLICATION supabase_realtime ADD TABLE rent_payment_transactions;
  END IF;

  -- Add payments if not already in publication
  IF NOT EXISTS (
    SELECT 1 FROM pg_publication_tables
    WHERE pubname = 'supabase_realtime'
    AND tablename = 'payments'
  ) THEN
    ALTER PUBLICATION supabase_realtime ADD TABLE payments;
  END IF;
END $$;

-- Note: Row Level Security (RLS) policies ensure tenants only receive
-- updates for their own transactions via Supabase's built-in filtering
