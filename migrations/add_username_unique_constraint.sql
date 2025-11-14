-- Add unique constraint to profiles.username
-- This ensures each username is unique across all users
-- Run this in Supabase SQL Editor (PostgreSQL syntax)

ALTER TABLE profiles 
ADD CONSTRAINT profiles_username_unique UNIQUE (username);

-- Create index for faster username lookups (PostgreSQL syntax)
-- Note: If you get an error that the index exists, you can ignore it
CREATE INDEX idx_profiles_username ON profiles(username);
