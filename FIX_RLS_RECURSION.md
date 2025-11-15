# Fix Supabase Profiles RLS Infinite Recursion

## Problem
Error: `'infinite recursion detected in policy for relation "profiles"', 'code': '42P17'`

The RLS policy for profiles creates infinite recursion because it queries the `profiles` table while checking access to the `profiles` table.

## Root Cause
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

## Solution Options

### Option 1: Use EXISTS with explicit table reference (RECOMMENDED)

Run this in Supabase SQL Editor:

```sql
-- Drop the problematic policy
DROP POLICY IF EXISTS "Users can view profiles in their household" ON public.profiles;

-- Create fixed policy using EXISTS
CREATE POLICY "Users can view profiles in their household"
    ON public.profiles FOR SELECT
    USING (
        id = auth.uid()  -- Always allow viewing own profile
        OR 
        EXISTS (
            SELECT 1 
            FROM public.profiles AS current_user
            WHERE current_user.id = auth.uid()
            AND current_user.household_id = profiles.household_id
        )
    );
```

### Option 2: Simpler approach - only check own profile directly

```sql
DROP POLICY IF EXISTS "Users can view profiles in their household" ON public.profiles;

CREATE POLICY "Users can view profiles in their household"
    ON public.profiles FOR SELECT
    USING (
        id = auth.uid()  -- Own profile always visible
        OR
        household_id = (
            SELECT household_id 
            FROM public.profiles 
            WHERE id = auth.uid()
            LIMIT 1
        )
    );
```

### Option 3: Bypass RLS for specific queries (APPLICATION LEVEL)

If the recursion persists, modify Python code to use service role key for household queries:

```python
# In household_management.py or auth_helpers.py
from supabase import create_client, Client

# Use service_role key (bypasses RLS) for admin operations
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
admin_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Use admin client for household member queries
def get_household_members(household_id: str):
    response = admin_client.table('profiles').select(
        'id, username, is_household_owner'
    ).eq('household_id', household_id).execute()
    return response.data
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
Run this query to verify:
```sql
-- Should return your profile without error
SELECT * FROM profiles WHERE id = auth.uid();

-- Should return household members without recursion
SELECT * FROM profiles WHERE household_id = (
    SELECT household_id FROM profiles WHERE id = auth.uid()
);
```

### Step 4: Update Schema File
Update `supabase_household_schema.sql` lines 94-103 with the fixed policy so future deployments don't recreate the bug.

## Why This Fixes It

**Option 1 (EXISTS)**: 
- Uses `EXISTS` with an aliased table (`current_user`)
- Postgres optimizes EXISTS differently than IN
- The alias helps Postgres understand these are separate query contexts

**Option 2 (LIMIT 1)**:
- The `LIMIT 1` hint tells Postgres this is a simple lookup
- Combined with `id = auth.uid()` (indexed), it's a direct fetch
- Avoids triggering the policy recursively

## Prevention

Always avoid querying the same table that the policy protects. Use:
- `auth.uid()` for user identity
- `auth.jwt()` for metadata
- Separate lookup tables
- SECURITY DEFINER functions

## Related Files
- `/home/user/projects/expanses_tracker/supabase_household_schema.sql` (line 94-103)
- `/home/user/projects/expanses_tracker/migrations/fix_profiles_rls_recursion.sql`
