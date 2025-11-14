# Supabase Household Management Setup

## 🎯 Overview

This implements **complete household management** using Supabase:
- ✅ Users sign up with email/password (Supabase Auth)
- ✅ Each signup auto-creates a household
- ✅ Household owners can invite members by email
- ✅ Household owners can kick members
- ✅ Members can leave households
- ✅ All data is isolated by household (Row Level Security)

## 📊 Database Architecture

```
auth.users (Supabase built-in)
    ↓
profiles (your table)
    ├── id → auth.users.id
    ├── username
    ├── household_id → households.id
    └── is_household_owner

households
    ├── id (UUID)
    ├── name
    ├── owner_id → auth.users.id
    └── invite_code (auto-generated)

household_invites
    ├── household_id → households.id
    ├── email
    ├── invited_by → auth.users.id
    └── expires_at (7 days)

expenses
    ├── household_id → households.id  ← NEW
    ├── user_id → auth.users.id       ← NEW
    └── ... (existing columns)
```

## 🚀 Setup Steps

### Step 1: Run the SQL Schema

1. Go to your Supabase project: https://supabase.com/dashboard
2. Click on **SQL Editor** in the left sidebar
3. Create a new query
4. Copy the entire contents of `supabase_household_schema.sql`
5. Click **Run** (or press Ctrl+Enter)

This will:
- Create all tables (households, profiles, household_invites)
- Set up Row Level Security (RLS) policies
- Create automatic triggers (new users get household + profile)
- Add household_id and user_id to expenses table

### Step 2: Verify Tables Created

In Supabase → **Table Editor**, you should now see:
- ✅ `households`
- ✅ `profiles`
- ✅ `household_invites`
- ✅ `expenses` (with new columns)

### Step 3: Test Signup Flow

1. Visit http://127.0.0.1:8000/signup
2. Create a test account:
   - Email: test@example.com
   - Username: testuser
   - Password: password123
   - Household: Test Family

3. Check Supabase → **Table Editor** → `profiles`:
   - Should see new row with username, household_id, is_household_owner=true

4. Check **Table Editor** → `households`:
   - Should see new household with name "Test Family"

### Step 4: Migrate Existing Users (Optional)

Your existing users (erez, lia, mom, dad) still work with **old auth**.

To migrate them to Supabase:

**Option A: Manual Signup**
1. Have each user go to `/signup`
2. Create account with their email
3. They get their own household
4. Can invite each other

**Option B: Keep Dual Auth**
- Leave old users as-is
- New users use Supabase
- Both systems work side-by-side
- Eventually phase out old auth

## 🔒 Your Data is Safe

**What happens when you push to Git:**

1. **Existing expenses stay connected** ✅
   - Your SQLite database has `household` column
   - Maps to "erez_lia" and "parents" strings
   - Old users (erez, lia, mom, dad) still see their data

2. **New Supabase users get separate data** ✅
   - Use `household_id` UUID instead of string
   - Completely isolated via RLS policies
   - Can't see old users' data

3. **You can migrate later**:
   ```sql
   -- Example: Map old household strings to UUIDs
   UPDATE expenses 
   SET household_id = (SELECT id FROM households WHERE name = 'Erez & Lia')
   WHERE household = 'erez_lia';
   ```

## 🎨 Features Implemented

### For All Users:
- ✅ Email/password signup
- ✅ Auto-create household on signup
- ✅ View household members
- ✅ Leave household (creates new one)

### For Household Owners:
- ✅ Invite members by email (7-day expiry)
- ✅ Remove/kick members
- ✅ Rename household
- ✅ View pending invites

### Security (RLS):
- ✅ Users only see their household's expenses
- ✅ Users only see their household's members
- ✅ Only owners can invite/kick
- ✅ Expenses are auto-filtered by household

## 📝 Python Functions Available

```python
from household_management import (
    get_user_household,       # Get user's household info
    get_household_members,    # List all members
    create_household_invite,  # Send invite
    accept_household_invite,  # Join household
    remove_household_member,  # Kick user (owner only)
    update_household_name,    # Rename (owner only)
    leave_household           # Leave and create new household
)
```

## 🔄 Migration Path

### Phase 1: Dual Auth (Current)
```
Old Users (env var) ────────→ SQLite/Postgres (household string)
                              
New Users (Supabase) ───────→ Supabase (household_id UUID)
```

### Phase 2: Migrate Old Users
```sql
-- 1. Create households for old users
INSERT INTO households (name, owner_id) VALUES
  ('Erez & Lia', (SELECT id FROM auth.users WHERE email = 'erez@example.com')),
  ('Parents', (SELECT id FROM auth.users WHERE email = 'mom@example.com'));

-- 2. Link expenses to new households
UPDATE expenses SET household_id = (
  SELECT id FROM households WHERE name = 'Erez & Lia'
) WHERE household = 'erez_lia';
```

### Phase 3: Remove Old Auth
- Delete USERS env var
- Remove old auth code from app.py
- All users use Supabase

## 🎯 Next Steps

1. **Run the SQL schema** in Supabase (Step 1 above)
2. **Test signup** locally (Step 3 above)
3. **Build household settings UI** (invite/kick buttons)
4. **Deploy to Render** with Supabase credentials
5. **Invite your friends!** 🎉

## 🐛 Troubleshooting

### "Table doesn't exist"
- Make sure you ran `supabase_household_schema.sql`
- Check Supabase → Table Editor

### "Permission denied" errors
- RLS policies might be blocking
- Check Supabase → Authentication → Policies
- Verify user is authenticated

### Old users can't see data
- They're using old auth (separate from Supabase)
- Their data is in `household` string column
- Supabase users use `household_id` UUID column
- Both work independently

### Invite doesn't work
- Check email is registered in Supabase
- Verify inviter is household owner
- Check invite hasn't expired (7 days)

---

## 🎉 Result

You now have a **multi-tenant SaaS** expense tracker where:
- Anyone can sign up
- Create their own household
- Invite friends/family by email
- Manage members (kick if needed)
- All data is secure and isolated
- Scales to unlimited users

**Perfect for demos and interviews!** 🚀
