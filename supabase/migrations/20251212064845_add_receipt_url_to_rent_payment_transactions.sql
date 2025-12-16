-- Add receipt_url column to rent_payment_transactions table
ALTER TABLE rent_payment_transactions 
ADD COLUMN IF NOT EXISTS receipt_url TEXT NULL;

