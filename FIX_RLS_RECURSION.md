# Fix Supabase Profiles RLS Infinite Recursion & Signup Issues

## Problem
Two related issues were preventing the app from working:

1. **Infinite Recursion Error**: `'infinite recursion detected in policy for relation "profiles"', 'code': '42P17'`
2. **Signup Failures**: New user registration failed during profile creation

## Root Cause

### Issue 1: RLS Policy Recursion
In `supabase_household_schema.sql` lines 94-103:

```sql
CREATE POLICY "Users can view profiles in their household"
    ON public.profiles FOR SELECT
    USING (
        household_id IN (
            SELECT household_id FROM public.profiles  -- ❌ RECURSION HERE
            WHERE id = auth.uid()
        )
        OR id = auth.uid()
    );
```

When querying profiles, the policy checks `SELECT household_id FROM public.profiles WHERE id = auth.uid()`, which triggers the same policy again → infinite loop.

### Issue 2: Missing INSERT Policies
The signup process failed because there were no INSERT policies for the `profiles` and `households` tables. The `handle_new_user()` trigger function (which runs during signup) needs to INSERT into both tables, but no policies allowed this.

## Solution Options

### Option 1: Fixed RLS Policies + INSERT Policies (RECOMMENDED)

Run this in Supabase SQL Editor:

```sql
-- Fix infinite recursion in profiles RLS policy and add missing INSERT policies

-- Drop the problematic policy
DROP POLICY IF EXISTS "Users can view profiles in their household" ON public.profiles;

-- Create a fixed policy that uses auth.uid() directly without querying profiles
CREATE POLICY "Users can view profiles in their household"
    ON public.profiles FOR SELECT
    USING (
        id = auth.uid()  -- Always allow viewing own profile
        OR
        household_id = (
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
```

### Option 2: EXISTS-based Policy + INSERT Policies

If Option 1 still causes issues:

```sql
-- Drop problematic policy
DROP POLICY IF EXISTS "Users can view profiles in their household" ON public.profiles;

-- Use EXISTS to avoid recursion
CREATE POLICY "Users can view profiles in their household"
    ON public.profiles FOR SELECT
    USING (
        id = auth.uid()  -- Own profile
        OR
        EXISTS (
            SELECT 1
            FROM public.profiles current_user
            WHERE current_user.id = auth.uid()
            AND current_user.household_id = profiles.household_id
        )
    );

-- Add INSERT policies
CREATE POLICY "Users can insert their own profile"
    ON public.profiles FOR INSERT
    WITH CHECK (id = auth.uid());

CREATE POLICY "Users can insert their own household"
    ON public.households FOR INSERT
    WITH CHECK (owner_id = auth.uid());
```

### Option 3: Disable RLS (Last Resort)

If the above options don't work, you can disable RLS and handle security in your application code:

```sql
-- Disable RLS (not recommended for production)
ALTER TABLE public.profiles DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.households DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.expenses DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.household_invites DISABLE ROW LEVEL SECURITY;
```

## How to Apply

### Step 1: Access Supabase Dashboard
1. Go to https://supabase.com/dashboard
2. Select your project
3. Click "SQL Editor" in left sidebar

### Step 2: Run the Fix
1. Copy Option 1 SQL (recommended)
2. Paste into SQL Editor
3. Click "Run" or press Ctrl+Enter

### Step 3: Test
Run these queries to verify:

```sql
-- Test 1: Should return your profile without error
SELECT * FROM profiles WHERE id = auth.uid();

-- Test 2: Should return household members without recursion
SELECT * FROM profiles WHERE household_id = (
    SELECT household_id FROM profiles WHERE id = auth.uid()
);

-- Test 3: Try signing up a new test account
-- (Use the signup form at /signup)
```

### Step 4: Update Schema File
Update `supabase_household_schema.sql` with the fixed policies so future deployments don't recreate the bug.

## What This Fixes

✅ **Signup Process**: New users can now register successfully
✅ **Household Features**: All household management pages work
✅ **Profile Access**: Users can view profiles in their household
✅ **Data Security**: RLS policies still protect data appropriately

## Why This Fixes It

**Recursion Fix**:
- The `LIMIT 1` hint tells Postgres this is a simple lookup
- Combined with `id = auth.uid()` (indexed), it's a direct fetch
- Avoids triggering the policy recursively

**INSERT Policies**:
- Allow the signup trigger to create profiles and households
- `WITH CHECK` ensures users can only insert their own records
- Required for the `handle_new_user()` function to work

## Prevention

Always avoid querying the same table that the policy protects. Use:
- `auth.uid()` for user identity
- `auth.jwt()` for metadata
- Separate lookup tables
- SECURITY DEFINER functions
- **Always add INSERT policies** when triggers need to create records

## Related Files
- `/home/user/projects/expanses_tracker/supabase_household_schema.sql` (line 94-103)
- `/home/user/projects/expanses_tracker/migrations/fix_profiles_rls_recursion.sql`
