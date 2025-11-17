-- Connect existing test account to Supabase auth user
-- This script links an existing profile to a Supabase auth user by email

-- INSTRUCTIONS:
-- 1. First, find your auth user ID by running:
--    SELECT id, email, created_at FROM auth.users WHERE email = 'your-email@example.com';
--
-- 2. Then update the profile with that user ID:
--    UPDATE public.profiles 
--    SET id = 'USER_ID_FROM_STEP_1'
--    WHERE username = 'your_username';
--
-- 3. Verify the link:
--    SELECT p.id, p.username, p.email, u.email as auth_email 
--    FROM public.profiles p
--    JOIN auth.users u ON p.id = u.id
--    WHERE p.username = 'your_username';

-- Example: Connect user 'erez' to email 'erezengel2805@gmail.com'

-- Step 1: Find the auth user
SELECT id, email, email_confirmed_at, created_at 
FROM auth.users 
WHERE email = 'erezengel2805@gmail.com';

-- Step 2: Update the profile (replace 'COPY_USER_ID_HERE' with the id from step 1)
-- UPDATE public.profiles 
-- SET id = 'COPY_USER_ID_HERE'
-- WHERE username = 'erez';

-- Step 3: Verify the connection
-- SELECT p.id, p.username, p.email, u.email as auth_email, u.email_confirmed_at
-- FROM public.profiles p
-- JOIN auth.users u ON p.id = u.id
-- WHERE p.username = 'erez';

-- NOTE: If you get an error about the ID already existing, it means there's already
-- a profile for that auth user. In that case, you can either:
-- A) Delete the duplicate profile and keep the one you want
-- B) Update the existing profile's username to match what you want
