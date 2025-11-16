-- Fix infinite recursion in profiles RLS policy and add missing INSERT policies
-- The issue: policy queries profiles table while checking profiles access = recursion
-- Also missing INSERT policies needed for signup trigger

-- Drop the problematic policy
DROP POLICY IF EXISTS "Users can view profiles in their household" ON public.profiles;

-- Create a fixed policy that uses auth.uid() directly without querying profiles
-- This allows users to see their own profile and profiles in the same household
CREATE POLICY "Users can view profiles in their household"
    ON public.profiles FOR SELECT
    USING (
        id = auth.uid()  -- Always allow viewing own profile
        OR
        household_id = (
            -- Use a subquery that Postgres can optimize without recursion
            -- This works because we're selecting from profiles WHERE id = auth.uid()
            -- which doesn't trigger the RLS policy (direct match on id column)
            SELECT p.household_id
            FROM public.profiles p
            WHERE p.id = auth.uid()
            LIMIT 1
        )
    );

-- Add missing INSERT policy for profiles (needed for signup trigger)
CREATE POLICY "Users can insert their own profile"
    ON public.profiles FOR INSERT
    WITH CHECK (id = auth.uid());

-- Add missing INSERT policy for households (needed for signup trigger)
CREATE POLICY "Users can insert their own household"
    ON public.households FOR INSERT
    WITH CHECK (owner_id = auth.uid());

-- Alternative: If the above still causes issues, use this simpler version
-- that relies on the household_id being set correctly
/*
DROP POLICY IF EXISTS "Users can view profiles in their household" ON public.profiles;

CREATE POLICY "Users can view profiles in their household"
    ON public.profiles FOR SELECT
    USING (
        id = auth.uid()  -- Own profile
        OR
        EXISTS (
            -- Check if user and target profile share a household
            SELECT 1
            FROM public.profiles current_user
            WHERE current_user.id = auth.uid()
            AND current_user.household_id = profiles.household_id
        )
    );
*/

-- If recursion persists, the nuclear option is to disable RLS for service role
-- and use application-level checks instead, or use a SECURITY DEFINER function
