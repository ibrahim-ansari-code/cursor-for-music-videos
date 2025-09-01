-- Add Google Maps fields to properties table
ALTER TABLE properties 
ADD COLUMN IF NOT EXISTS latitude DECIMAL(10, 8),
ADD COLUMN IF NOT EXISTS longitude DECIMAL(11, 8),
ADD COLUMN IF NOT EXISTS place_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS formatted_address VARCHAR(500),
ADD COLUMN IF NOT EXISTS google_maps_data JSONB;

-- Create property images table
CREATE TABLE IF NOT EXISTS property_images (
  id SERIAL PRIMARY KEY,
  property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  image_url VARCHAR(500) NOT NULL,
  image_type VARCHAR(50) DEFAULT 'photo',
  is_primary BOOLEAN DEFAULT false,
  caption VARCHAR(255),
  display_order INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_properties_location ON properties(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_properties_place_id ON properties(place_id);
CREATE INDEX IF NOT EXISTS idx_property_images_property ON property_images(property_id);
CREATE INDEX IF NOT EXISTS idx_property_images_primary ON property_images(property_id, is_primary) WHERE is_primary = true;

-- Add unique constraint to ensure only one primary image per property
CREATE UNIQUE INDEX IF NOT EXISTS idx_property_images_single_primary 
ON property_images(property_id) WHERE is_primary = true;

-- Add safety checks for lat/lng ranges
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE table_name = 'properties' AND constraint_name = 'chk_properties_latitude_range'
  ) THEN
    ALTER TABLE properties
    ADD CONSTRAINT chk_properties_latitude_range CHECK (latitude IS NULL OR (latitude >= -90 AND latitude <= 90));
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE table_name = 'properties' AND constraint_name = 'chk_properties_longitude_range'
  ) THEN
    ALTER TABLE properties
    ADD CONSTRAINT chk_properties_longitude_range CHECK (longitude IS NULL OR (longitude >= -180 AND longitude <= 180));
  END IF;
END $$;

-- Add RLS policies for property_images
ALTER TABLE property_images ENABLE ROW LEVEL SECURITY;

-- Policy for authenticated users to view property images
CREATE POLICY "Users can view property images for properties they can see"
  ON property_images FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = property_images.property_id
      AND (properties.user_id = auth.uid() OR EXISTS (
        SELECT 1 FROM users WHERE users.id = auth.uid() AND users.is_admin = true
      ))
    )
  );

-- Policy for property owners to insert images
CREATE POLICY "Property owners can insert images"
  ON property_images FOR INSERT
  WITH CHECK (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = property_images.property_id
      AND (properties.user_id = auth.uid() OR EXISTS (
        SELECT 1 FROM users WHERE users.id = auth.uid() AND users.is_admin = true
      ))
    )
  );

-- Policy for property owners to update images
CREATE POLICY "Property owners can update images"
  ON property_images FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = property_images.property_id
      AND (properties.user_id = auth.uid() OR EXISTS (
        SELECT 1 FROM users WHERE users.id = auth.uid() AND users.is_admin = true
      ))
    )
  );

-- Policy for property owners to delete images
CREATE POLICY "Property owners can delete images"
  ON property_images FOR DELETE
  USING (
    EXISTS (
      SELECT 1 FROM properties 
      WHERE properties.id = property_images.property_id
      AND (properties.user_id = auth.uid() OR EXISTS (
        SELECT 1 FROM users WHERE users.id = auth.uid() AND users.is_admin = true
      ))
    )
  );

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for property_images updated_at
CREATE TRIGGER update_property_images_updated_at BEFORE UPDATE ON property_images
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();