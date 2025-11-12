"""
Supabase Configuration and Client Setup
"""
import os
from supabase import create_client, Client
from datetime import datetime, date
from typing import Optional, Dict, List

# Supabase credentials from environment variables
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None


def get_supabase_client() -> Optional[Client]:
    """Get or create Supabase client"""
    global supabase
    if not supabase and SUPABASE_URL and SUPABASE_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return supabase


def add_expense_supabase(tx_date: str, category: str, amount: float, payer: str, 
                         notes: str = "", split_with: Optional[str] = None, 
                         household: str = "default") -> Dict:
    """
    Add expense using Supabase
    
    Args:
        tx_date: Transaction date in YYYY-MM-DD format
        category: Expense category
        amount: Amount in currency
        payer: Username who paid
        notes: Optional notes
        split_with: Optional username to split with
        household: Household identifier
    
    Returns:
        Dict with the created expense record
    """
    client = get_supabase_client()
    if not client:
        raise Exception("Supabase client not initialized. Set SUPABASE_URL and SUPABASE_ANON_KEY environment variables.")
    
    expense_data = {
        "ts": datetime.utcnow().isoformat(),
        "tx_date": tx_date,
        "category": category,
        "amount": float(amount),
        "payer": payer,
        "notes": notes,
        "split_with": split_with,
        "household": household
    }
    
    print(f"DEBUG: Adding expense to Supabase - {expense_data}")
    
    try:
        response = client.table("expenses").insert(expense_data).execute()
        print(f"DEBUG: Expense added successfully to Supabase")
        return response.data[0] if response.data else {}
    except Exception as e:
        print(f"ERROR: Failed to add expense to Supabase: {e}")
        raise


def load_expenses_supabase(user: Optional[str] = None, 
                          month_start: Optional[date] = None,
                          month_end: Optional[date] = None) -> List[Dict]:
    """
    Load expenses from Supabase with optional filtering
    
    Args:
        user: Username to filter by household
        month_start: Start date for filtering
        month_end: End date for filtering
    
    Returns:
        List of expense records
    """
    client = get_supabase_client()
    if not client:
        raise Exception("Supabase client not initialized")
    
    query = client.table("expenses").select("*")
    
    # Filter by household if user is specified
    if user:
        # You'll need to implement get_user_household logic
        # For now, using a simple approach
        query = query.eq("household", user)
    
    # Filter by date range
    if month_start:
        query = query.gte("tx_date", month_start.isoformat())
    if month_end:
        query = query.lt("tx_date", month_end.isoformat())
    
    # Order by date descending
    query = query.order("tx_date", desc=True).order("id", desc=True)
    
    try:
        response = query.execute()
        print(f"DEBUG: Loaded {len(response.data)} expenses from Supabase")
        return response.data
    except Exception as e:
        print(f"ERROR: Failed to load expenses from Supabase: {e}")
        return []


def delete_expense_supabase(expense_id: int) -> bool:
    """Delete an expense by ID"""
    client = get_supabase_client()
    if not client:
        raise Exception("Supabase client not initialized")
    
    try:
        response = client.table("expenses").delete().eq("id", expense_id).execute()
        print(f"DEBUG: Deleted expense {expense_id} from Supabase")
        return True
    except Exception as e:
        print(f"ERROR: Failed to delete expense from Supabase: {e}")
        return False


def update_expense_supabase(expense_id: int, tx_date: str, category: str, 
                           amount: float, payer: str, notes: str = "",
                           split_with: Optional[str] = None) -> Dict:
    """Update an existing expense"""
    client = get_supabase_client()
    if not client:
        raise Exception("Supabase client not initialized")
    
    update_data = {
        "tx_date": tx_date,
        "category": category,
        "amount": float(amount),
        "payer": payer,
        "notes": notes,
        "split_with": split_with
    }
    
    try:
        response = client.table("expenses").update(update_data).eq("id", expense_id).execute()
        print(f"DEBUG: Updated expense {expense_id} in Supabase")
        return response.data[0] if response.data else {}
    except Exception as e:
        print(f"ERROR: Failed to update expense in Supabase: {e}")
        raise


def get_expense_by_id_supabase(expense_id: int) -> Optional[Dict]:
    """Get a single expense by ID"""
    client = get_supabase_client()
    if not client:
        raise Exception("Supabase client not initialized")
    
    try:
        response = client.table("expenses").select("*").eq("id", expense_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"ERROR: Failed to get expense from Supabase: {e}")
        return None


# Budget operations
def get_user_budgets_supabase(username: str) -> Dict[str, float]:
    """Get all budget limits for a user"""
    client = get_supabase_client()
    if not client:
        return {}
    
    try:
        response = client.table("user_budgets").select("category, budget_limit").eq("username", username).execute()
        budgets = {}
        for row in response.data:
            budgets[row["category"]] = float(row["budget_limit"])
        return budgets
    except Exception as e:
        print(f"ERROR: Failed to get user budgets from Supabase: {e}")
        return {}


def set_user_budget_supabase(username: str, category: str, budget_limit: float, household: str = "default") -> bool:
    """Set or update a budget limit"""
    client = get_supabase_client()
    if not client:
        return False
    
    budget_data = {
        "username": username,
        "category": category,
        "budget_limit": float(budget_limit),
        "household": household,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    try:
        # Try to upsert (insert or update)
        response = client.table("user_budgets").upsert(budget_data).execute()
        print(f"DEBUG: Set budget for {username}/{category} = {budget_limit}")
        return True
    except Exception as e:
        print(f"ERROR: Failed to set budget in Supabase: {e}")
        return False


def delete_user_budget_supabase(username: str, category: str, household: str = "default") -> bool:
    """Delete a budget limit"""
    client = get_supabase_client()
    if not client:
        return False
    
    try:
        response = client.table("user_budgets").delete()\
            .eq("username", username)\
            .eq("category", category)\
            .eq("household", household)\
            .execute()
        print(f"DEBUG: Deleted budget for {username}/{category}")
        return True
    except Exception as e:
        print(f"ERROR: Failed to delete budget from Supabase: {e}")
        return False


# Realtime subscription helper
def subscribe_to_expenses(callback, household: Optional[str] = None):
    """
    Subscribe to realtime updates for expenses table
    
    Args:
        callback: Function to call when data changes
        household: Optional household filter
    """
    client = get_supabase_client()
    if not client:
        print("WARNING: Cannot subscribe to realtime - Supabase client not initialized")
        return None
    
    try:
        # Subscribe to INSERT, UPDATE, DELETE events
        channel = client.channel("expenses_changes")
        
        if household:
            # Filter by household if specified
            channel = channel.on_postgres_changes(
                event="*",
                schema="public",
                table="expenses",
                filter=f"household=eq.{household}",
                callback=callback
            )
        else:
            channel = channel.on_postgres_changes(
                event="*",
                schema="public",
                table="expenses",
                callback=callback
            )
        
        channel.subscribe()
        print(f"DEBUG: Subscribed to realtime updates for expenses")
        return channel
    except Exception as e:
        print(f"ERROR: Failed to subscribe to realtime updates: {e}")
        return None
