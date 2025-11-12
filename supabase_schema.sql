-- =====================================================
-- Supabase Database Schema Migration
-- Expense Tracker Application
-- =====================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- EXPENSES TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS expenses (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tx_date DATE NOT NULL,
    category TEXT NOT NULL,
    amount DECIMAL(10,2) NOT NULL CHECK (amount > 0),
    payer TEXT NOT NULL,
    notes TEXT,
    split_with TEXT,
    household TEXT DEFAULT 'default',
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_expenses_tx_date ON expenses(tx_date DESC);
CREATE INDEX IF NOT EXISTS idx_expenses_payer ON expenses(payer);
CREATE INDEX IF NOT EXISTS idx_expenses_household ON expenses(household);
CREATE INDEX IF NOT EXISTS idx_expenses_user_id ON expenses(user_id);
CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category);

-- Add updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_expenses_updated_at BEFORE UPDATE ON expenses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- USER BUDGETS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS user_budgets (
    id BIGSERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    category TEXT NOT NULL,
    budget_limit DECIMAL(10,2) NOT NULL CHECK (budget_limit >= 0),
    household TEXT DEFAULT 'default',
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(username, category, household)
);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_budgets_username ON user_budgets(username);
CREATE INDEX IF NOT EXISTS idx_budgets_household ON user_budgets(household);
CREATE INDEX IF NOT EXISTS idx_budgets_user_id ON user_budgets(user_id);

-- Add updated_at trigger
CREATE TRIGGER update_user_budgets_updated_at BEFORE UPDATE ON user_budgets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- HOUSEHOLDS TABLE (Optional - for multi-user households)
-- =====================================================
CREATE TABLE IF NOT EXISTS households (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    display_name TEXT,
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_households_name ON households(name);

-- =====================================================
-- HOUSEHOLD MEMBERS TABLE
-- =====================================================
CREATE TABLE IF NOT EXISTS household_members (
    id BIGSERIAL PRIMARY KEY,
    household_id BIGINT REFERENCES households(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    username TEXT NOT NULL,
    role TEXT DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member')),
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(household_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_household_members_user ON household_members(user_id);
CREATE INDEX IF NOT EXISTS idx_household_members_household ON household_members(household_id);

-- =====================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- =====================================================

-- Enable RLS on all tables
ALTER TABLE expenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_budgets ENABLE ROW LEVEL SECURITY;
ALTER TABLE households ENABLE ROW LEVEL SECURITY;
ALTER TABLE household_members ENABLE ROW LEVEL SECURITY;

-- Expenses Policies
-- Users can view expenses from their household
CREATE POLICY "Users can view household expenses"
    ON expenses FOR SELECT
    USING (
        household IN (
            SELECT h.name 
            FROM households h
            JOIN household_members hm ON h.id = hm.household_id
            WHERE hm.user_id = auth.uid()
        )
        OR user_id = auth.uid()
    );

-- Users can insert their own expenses
CREATE POLICY "Users can insert own expenses"
    ON expenses FOR INSERT
    WITH CHECK (user_id = auth.uid());

-- Users can update their own expenses
CREATE POLICY "Users can update own expenses"
    ON expenses FOR UPDATE
    USING (user_id = auth.uid());

-- Users can delete their own expenses
CREATE POLICY "Users can delete own expenses"
    ON expenses FOR DELETE
    USING (user_id = auth.uid());

-- Budget Policies
-- Users can view budgets for their household
CREATE POLICY "Users can view household budgets"
    ON user_budgets FOR SELECT
    USING (
        household IN (
            SELECT h.name 
            FROM households h
            JOIN household_members hm ON h.id = hm.household_id
            WHERE hm.user_id = auth.uid()
        )
        OR user_id = auth.uid()
    );

-- Users can manage their own budgets
CREATE POLICY "Users can manage own budgets"
    ON user_budgets FOR ALL
    USING (user_id = auth.uid());

-- Household Policies
-- Anyone authenticated can view households they belong to
CREATE POLICY "Users can view their households"
    ON households FOR SELECT
    USING (
        id IN (
            SELECT household_id 
            FROM household_members 
            WHERE user_id = auth.uid()
        )
    );

-- Only owners can update households
CREATE POLICY "Owners can update households"
    ON households FOR UPDATE
    USING (
        id IN (
            SELECT household_id 
            FROM household_members 
            WHERE user_id = auth.uid() AND role = 'owner'
        )
    );

-- Household Members Policies
-- Users can view members of their households
CREATE POLICY "Users can view household members"
    ON household_members FOR SELECT
    USING (
        household_id IN (
            SELECT household_id 
            FROM household_members 
            WHERE user_id = auth.uid()
        )
    );

-- =====================================================
-- FUNCTIONS
-- =====================================================

-- Function to get user's household
CREATE OR REPLACE FUNCTION get_user_household(p_user_id UUID)
RETURNS TEXT AS $$
    SELECT h.name
    FROM households h
    JOIN household_members hm ON h.id = hm.household_id
    WHERE hm.user_id = p_user_id
    LIMIT 1;
$$ LANGUAGE SQL STABLE;

-- Function to calculate monthly spending
CREATE OR REPLACE FUNCTION calculate_monthly_spending(
    p_user_id UUID,
    p_month_start DATE,
    p_month_end DATE
)
RETURNS TABLE(category TEXT, total_amount DECIMAL) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        e.category,
        SUM(e.amount)::DECIMAL as total_amount
    FROM expenses e
    WHERE e.user_id = p_user_id
        AND e.tx_date >= p_month_start
        AND e.tx_date < p_month_end
    GROUP BY e.category
    ORDER BY total_amount DESC;
END;
$$ LANGUAGE plpgsql STABLE;

-- Function to check budget status
CREATE OR REPLACE FUNCTION check_budget_status(
    p_username TEXT,
    p_category TEXT,
    p_month_start DATE,
    p_month_end DATE
)
RETURNS JSON AS $$
DECLARE
    v_budget DECIMAL;
    v_spent DECIMAL;
    v_remaining DECIMAL;
    v_percentage DECIMAL;
BEGIN
    -- Get budget limit
    SELECT budget_limit INTO v_budget
    FROM user_budgets
    WHERE username = p_username AND category = p_category
    LIMIT 1;
    
    -- Get total spent
    SELECT COALESCE(SUM(amount), 0) INTO v_spent
    FROM expenses
    WHERE payer = p_username 
        AND category = p_category
        AND tx_date >= p_month_start
        AND tx_date < p_month_end;
    
    -- Calculate remaining and percentage
    v_remaining := COALESCE(v_budget, 0) - v_spent;
    v_percentage := CASE 
        WHEN COALESCE(v_budget, 0) > 0 THEN (v_spent / v_budget * 100)
        ELSE 0 
    END;
    
    RETURN json_build_object(
        'budget', v_budget,
        'spent', v_spent,
        'remaining', v_remaining,
        'percentage', v_percentage,
        'status', CASE
            WHEN v_percentage > 100 THEN 'over'
            WHEN v_percentage > 80 THEN 'warning'
            ELSE 'ok'
        END
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- =====================================================
-- REALTIME PUBLICATION
-- =====================================================

-- Enable realtime for expenses table
ALTER PUBLICATION supabase_realtime ADD TABLE expenses;
ALTER PUBLICATION supabase_realtime ADD TABLE user_budgets;

-- =====================================================
-- SAMPLE DATA (Optional - for testing)
-- =====================================================

-- Insert sample households
-- INSERT INTO households (name, display_name) VALUES 
--     ('erez_lia', 'Erez & Lia'),
--     ('parents', 'Parents');

-- =====================================================
-- CLEANUP OLD SCHEMA (if migrating from old structure)
-- =====================================================

-- If you're migrating from the old structure, uncomment these:
-- ALTER TABLE expenses DROP COLUMN IF EXISTS ts;
-- ALTER TABLE expenses ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW();

-- =====================================================
-- GRANT PERMISSIONS
-- =====================================================

-- Grant usage on sequences
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon;

-- =====================================================
-- MIGRATION COMPLETE
-- =====================================================
-- Run this script in your Supabase SQL Editor
-- Then enable Realtime in Table Editor for expenses and user_budgets tables
