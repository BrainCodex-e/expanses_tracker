-- Supabase Schema for Household Management
-- Run this in your Supabase SQL Editor

-- 1. Create households table
CREATE TABLE IF NOT EXISTS public.households (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    owner_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    invite_code TEXT UNIQUE DEFAULT substring(md5(random()::text) from 1 for 8),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Create user profiles table (extends auth.users)
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    username TEXT UNIQUE NOT NULL,
    household_id UUID REFERENCES public.households(id) ON DELETE SET NULL,
    is_household_owner BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Create household invites table
CREATE TABLE IF NOT EXISTS public.household_invites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    household_id UUID REFERENCES public.households(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    invited_by UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    accepted BOOLEAN DEFAULT FALSE,
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '7 days'),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Create expenses table (if not exists)
CREATE TABLE IF NOT EXISTS public.expenses (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    tx_date DATE NOT NULL,
    category TEXT NOT NULL,
    amount NUMERIC(10,2) NOT NULL,
    payer TEXT NOT NULL,
    notes TEXT,
    split_with TEXT,
    household TEXT DEFAULT 'default',
    household_id UUID REFERENCES public.households(id),
    user_id UUID REFERENCES auth.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Create user_budgets table (if not exists)
CREATE TABLE IF NOT EXISTS public.user_budgets (
    id BIGSERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    category TEXT NOT NULL,
    budget_limit NUMERIC(10,2) NOT NULL,
    household TEXT DEFAULT 'default',
    household_id UUID REFERENCES public.households(id),
    user_id UUID REFERENCES auth.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(username, category, household)
);

-- 6. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_profiles_household ON public.profiles(household_id);
CREATE INDEX IF NOT EXISTS idx_profiles_username ON public.profiles(username);
CREATE INDEX IF NOT EXISTS idx_expenses_household ON public.expenses(household_id);
CREATE INDEX IF NOT EXISTS idx_expenses_user ON public.expenses(user_id);
CREATE INDEX IF NOT EXISTS idx_invites_household ON public.household_invites(household_id);
CREATE INDEX IF NOT EXISTS idx_invites_email ON public.household_invites(email);

-- 7. Enable Row Level Security (RLS)
ALTER TABLE public.households ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.household_invites ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.expenses ENABLE ROW LEVEL SECURITY;

-- 8. RLS Policies for households
CREATE POLICY "Users can view their own household"
    ON public.households FOR SELECT
    USING (
        id IN (
            SELECT household_id FROM public.profiles 
            WHERE id = auth.uid()
        )
    );

CREATE POLICY "Users can update their own household if owner"
    ON public.households FOR UPDATE
    USING (owner_id = auth.uid());

-- 9. RLS Policies for profiles
CREATE POLICY "Users can view profiles in their household"
    ON public.profiles FOR SELECT
    USING (
        household_id IN (
            SELECT household_id FROM public.profiles 
            WHERE id = auth.uid()
        )
        OR id = auth.uid()
    );

CREATE POLICY "Users can update their own profile"
    ON public.profiles FOR UPDATE
    USING (id = auth.uid());

-- 10. RLS Policies for expenses
CREATE POLICY "Users can view expenses in their household"
    ON public.expenses FOR SELECT
    USING (
        household_id IN (
            SELECT household_id FROM public.profiles 
            WHERE id = auth.uid()
        )
    );

CREATE POLICY "Users can insert expenses in their household"
    ON public.expenses FOR INSERT
    WITH CHECK (
        household_id IN (
            SELECT household_id FROM public.profiles 
            WHERE id = auth.uid()
        )
    );

CREATE POLICY "Users can update expenses in their household"
    ON public.expenses FOR UPDATE
    USING (
        household_id IN (
            SELECT household_id FROM public.profiles 
            WHERE id = auth.uid()
        )
    );

CREATE POLICY "Users can delete expenses in their household"
    ON public.expenses FOR DELETE
    USING (
        household_id IN (
            SELECT household_id FROM public.profiles 
            WHERE id = auth.uid()
        )
    );

-- 11. RLS Policies for household_invites
CREATE POLICY "Household owners can view invites"
    ON public.household_invites FOR SELECT
    USING (
        household_id IN (
            SELECT household_id FROM public.profiles 
            WHERE id = auth.uid() AND is_household_owner = TRUE
        )
    );

CREATE POLICY "Household owners can create invites"
    ON public.household_invites FOR INSERT
    WITH CHECK (
        household_id IN (
            SELECT household_id FROM public.profiles 
            WHERE id = auth.uid() AND is_household_owner = TRUE
        )
    );

-- 12. Function to automatically create profile and household on signup
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
    
    -- Create household
    INSERT INTO public.households (name, owner_id)
    VALUES (user_household_name, NEW.id)
    RETURNING id INTO new_household_id;
    
    -- Create profile
    INSERT INTO public.profiles (id, username, household_id, is_household_owner)
    VALUES (NEW.id, user_username, new_household_id, TRUE);
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 13. Trigger to create profile and household on signup
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- 14. Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 15. Triggers for updated_at
CREATE TRIGGER set_households_updated_at
    BEFORE UPDATE ON public.households
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_updated_at();

CREATE TRIGGER set_profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_updated_at();

-- Done! Now when users sign up:
-- 1. Supabase Auth creates the user
-- 2. Trigger automatically creates household + profile
-- 3. User is set as household owner
-- 4. Invite code is generated automatically
