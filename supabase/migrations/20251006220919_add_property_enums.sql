-- Add missing enum values to propertystatus enum
-- These values are defined in Backend/models/enums.py but were missing from the database

ALTER TYPE propertystatus ADD VALUE IF NOT EXISTS 'RENTED';
ALTER TYPE propertystatus ADD VALUE IF NOT EXISTS 'VACANT';
ALTER TYPE propertystatus ADD VALUE IF NOT EXISTS 'PARTIALLY_RENTED';
