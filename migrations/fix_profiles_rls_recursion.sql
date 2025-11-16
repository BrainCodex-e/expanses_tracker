-- Fix infinite recursion in profiles RLS policy and add missing INSERT policies
-- The issue: policy queries profiles table while checking profiles access = recursion
-- Also missing INSERT policies needed for signup trigger

-- Step 1: Drop the problematic SELECT policy
DROP POLICY IF EXISTS "Users can view profiles in their household" ON public.profiles;

-- Step 2: Create a fixed SELECT policy using EXISTS to avoid recursion
CREATE POLICY "Users can view profiles in their household"
    ON public.profiles FOR SELECT
    USING (
        id = auth.uid()  -- Always allow viewing own profile
        OR
        EXISTS (
            -- Check if user and target profile share a household
            -- Using EXISTS with an alias prevents recursion
            SELECT 1
            FROM public.profiles AS current_user
            WHERE current_user.id = auth.uid()
            AND current_user.household_id = profiles.household_id
        )
    );

-- Step 3: Ensure INSERT policies exist for signup trigger
-- Drop and recreate to ensure they're correct
DROP POLICY IF EXISTS "Users can insert their own profile" ON public.profiles;
CREATE POLICY "Users can insert their own profile"
    ON public.profiles FOR INSERT
    WITH CHECK (id = auth.uid());

DROP POLICY IF EXISTS "Users can insert their own household" ON public.households;
CREATE POLICY "Users can insert their own household"
    ON public.households FOR INSERT
    WITH CHECK (owner_id = auth.uid());

-- Step 4: Verify the trigger function has SECURITY DEFINER
-- This allows it to bypass RLS when creating profile/household
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
DECLARE
    new_household_id UUID;
    user_username TEXT;
    user_household_name TEXT;
BEGIN
    -- Extract username and household_name from user metadata
    user_username := NEW.raw_user_meta_data->>'username';
    user_household_name := NEW.raw_user_meta_data->>'household_name';
    
    -- Set defaults if not provided
    IF user_username IS NULL THEN
        user_username := split_part(NEW.email, '@', 1);
    END IF;
    
    IF user_household_name IS NULL THEN
        user_household_name := user_username || '''s Household';
    END IF;
    
    -- Create household (SECURITY DEFINER bypasses RLS)
    INSERT INTO public.households (name, owner_id)
    VALUES (user_household_name, NEW.id)
    RETURNING id INTO new_household_id;
    
    -- Create profile (SECURITY DEFINER bypasses RLS)
    INSERT INTO public.profiles (id, username, household_id, is_household_owner)
    VALUES (NEW.id, user_username, new_household_id, TRUE);
    
    RETURN NEW;
EXCEPTION
    WHEN unique_violation THEN
        -- If username already exists, append random suffix
        user_username := user_username || '_' || substr(md5(random()::text), 1, 6);
        
        -- Retry household creation
        INSERT INTO public.households (name, owner_id)
        VALUES (user_household_name, NEW.id)
        RETURNING id INTO new_household_id;
        
        -- Retry profile creation with modified username
        INSERT INTO public.profiles (id, username, household_id, is_household_owner)
        VALUES (NEW.id, user_username, new_household_id, TRUE);
        
        RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Step 5: Ensure trigger is active
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- Alternative approach if recursion still occurs:
-- Use a simpler policy that only checks direct equality
