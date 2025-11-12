"""
Example: Integrating Supabase into Flask App
This shows how to modify your existing routes to use Supabase
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import date, datetime
from supabase_config import (
    add_expense_supabase,
    load_expenses_supabase,
    delete_expense_supabase,
    update_expense_supabase,
    get_expense_by_id_supabase,
    get_user_budgets_supabase,
    set_user_budget_supabase,
    get_supabase_client
)
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret")

# Supabase credentials
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", "")

# =====================================================
# AUTHENTICATION ROUTES (Supabase Auth)
# =====================================================

@app.route('/supabase/login', methods=['GET', 'POST'])
def supabase_login():
    """
    Supabase Auth login page
    Users can login with email/password or OAuth (Google, GitHub)
    """
    if request.method == 'POST':
        # For server-side auth, verify the JWT token from client
        token = request.form.get('access_token')
        
        if token:
            supabase = get_supabase_client()
            try:
                # Verify user with token
                user = supabase.auth.get_user(token)
                
                if user:
                    session['user_id'] = user.id
                    session['user_email'] = user.email
                    session['user'] = user.email.split('@')[0]  # Simple username
                    return redirect(url_for('index_supabase'))
            except Exception as e:
                print(f"Auth error: {e}")
                return render_template('supabase_login.html', 
                                     error="Authentication failed",
                                     supabase_url=SUPABASE_URL,
                                     supabase_key=SUPABASE_KEY)
    
    return render_template('supabase_login.html',
                         supabase_url=SUPABASE_URL,
                         supabase_key=SUPABASE_KEY)


@app.route('/supabase/logout')
def supabase_logout():
    """Logout and clear session"""
    session.clear()
    
    # Also sign out from Supabase client-side
    supabase = get_supabase_client()
    if supabase:
        try:
            supabase.auth.sign_out()
        except:
            pass
    
    return redirect(url_for('supabase_login'))


# =====================================================
# EXPENSE ROUTES (Supabase Backend)
# =====================================================

@app.route('/supabase/')
def index_supabase():
    """
    Main dashboard - now using Supabase
    Shows expenses with real-time updates
    """
    if 'user' not in session:
        return redirect(url_for('supabase_login'))
    
    current_user = session.get('user')
    household = session.get('household', current_user)
    
    # Get current month dates
    today = date.today()
    month_start = date(today.year, today.month, 1)
    if today.month == 12:
        month_end = date(today.year + 1, 1, 1)
    else:
        month_end = date(today.year, today.month + 1, 1)
    
    # Load expenses from Supabase
    try:
        expenses = load_expenses_supabase(
            user=household,
            month_start=month_start,
            month_end=month_end
        )
        
        # Calculate totals
        total = sum(float(e.get('amount', 0)) for e in expenses)
        user_expenses = [e for e in expenses if e.get('payer', '').lower() == current_user.lower()]
        user_total = sum(float(e.get('amount', 0)) for e in user_expenses)
        
        # Get budgets
        budgets = get_user_budgets_supabase(current_user)
        
    except Exception as e:
        print(f"Error loading data: {e}")
        expenses = []
        total = 0
        user_total = 0
        budgets = {}
    
    return render_template('index.html',
                         current_user=current_user,
                         household=household,
                         expenses=expenses,
                         user_expenses=user_expenses,
                         total=total,
                         user_total=user_total,
                         budgets=budgets,
                         today=today.isoformat(),
                         supabase_url=SUPABASE_URL,
                         supabase_key=SUPABASE_KEY,
                         # Enable realtime
                         enable_realtime=True)


@app.route('/supabase/add', methods=['POST'])
def add_expense_route_supabase():
    """Add expense using Supabase"""
    if 'user' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        tx_date = request.form.get('tx_date') or date.today().isoformat()
        category = request.form.get('category')
        amount = float(request.form.get('amount', 0))
        payer = request.form.get('payer') or session.get('user')
        notes = request.form.get('notes', '')
        split_with = request.form.get('split_with') or None
        household = session.get('household', session.get('user'))
        
        if amount <= 0:
            return jsonify({"error": "Amount must be positive"}), 400
        
        # Add to Supabase
        expense = add_expense_supabase(
            tx_date=tx_date,
            category=category,
            amount=amount,
            payer=payer,
            notes=notes,
            split_with=split_with,
            household=household
        )
        
        # Realtime subscribers will be notified automatically!
        
        return jsonify({
            "success": True,
            "expense": expense,
            "message": f"₪{amount} added successfully"
        })
        
    except Exception as e:
        print(f"Error adding expense: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/supabase/delete/<int:expense_id>', methods=['POST'])
def delete_expense_route_supabase(expense_id):
    """Delete expense using Supabase"""
    if 'user' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        success = delete_expense_supabase(expense_id)
        
        if success:
            # Realtime subscribers will be notified automatically!
            return jsonify({
                "success": True,
                "message": "Expense deleted"
            })
        else:
            return jsonify({"error": "Failed to delete"}), 500
            
    except Exception as e:
        print(f"Error deleting expense: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/supabase/update/<int:expense_id>', methods=['POST'])
def update_expense_route_supabase(expense_id):
    """Update expense using Supabase"""
    if 'user' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        tx_date = request.form.get('tx_date')
        category = request.form.get('category')
        amount = float(request.form.get('amount', 0))
        payer = request.form.get('payer')
        notes = request.form.get('notes', '')
        split_with = request.form.get('split_with') or None
        
        if amount <= 0:
            return jsonify({"error": "Amount must be positive"}), 400
        
        # Update in Supabase
        expense = update_expense_supabase(
            expense_id=expense_id,
            tx_date=tx_date,
            category=category,
            amount=amount,
            payer=payer,
            notes=notes,
            split_with=split_with
        )
        
        # Realtime subscribers will be notified automatically!
        
        return jsonify({
            "success": True,
            "expense": expense,
            "message": "Expense updated"
        })
        
    except Exception as e:
        print(f"Error updating expense: {e}")
        return jsonify({"error": str(e)}), 500


# =====================================================
# BUDGET ROUTES (Supabase Backend)
# =====================================================

@app.route('/supabase/budget/settings')
def budget_settings_supabase():
    """Budget settings page using Supabase"""
    if 'user' not in session:
        return redirect(url_for('supabase_login'))
    
    current_user = session.get('user')
    
    try:
        budgets = get_user_budgets_supabase(current_user)
    except Exception as e:
        print(f"Error loading budgets: {e}")
        budgets = {}
    
    return render_template('budget_settings.html',
                         current_user=current_user,
                         budget_limits=budgets)


@app.route('/supabase/budget/update', methods=['POST'])
def update_budget_supabase():
    """Update budget using Supabase"""
    if 'user' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    current_user = session.get('user')
    household = session.get('household', current_user)
    
    try:
        data = request.get_json()
        category = data.get('category')
        budget_limit = float(data.get('budget_limit', 0))
        
        if budget_limit < 0:
            return jsonify({"error": "Budget must be non-negative"}), 400
        
        success = set_user_budget_supabase(
            username=current_user,
            category=category,
            budget_limit=budget_limit,
            household=household
        )
        
        if success:
            return jsonify({
                "success": True,
                "message": f"Budget updated for {category}"
            })
        else:
            return jsonify({"error": "Failed to update budget"}), 500
            
    except Exception as e:
        print(f"Error updating budget: {e}")
        return jsonify({"error": str(e)}), 500


# =====================================================
# API ENDPOINTS
# =====================================================

@app.route('/api/supabase/status')
def supabase_status():
    """Check Supabase connection status"""
    try:
        supabase = get_supabase_client()
        if supabase:
            # Try a simple query
            result = supabase.table('expenses').select('id').limit(1).execute()
            return jsonify({
                "status": "connected",
                "message": "Supabase connection is healthy",
                "url": SUPABASE_URL[:30] + "..."
            })
        else:
            return jsonify({
                "status": "not_configured",
                "message": "Supabase not configured"
            }), 503
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


if __name__ == '__main__':
    # Make sure to set environment variables:
    # export SUPABASE_URL="https://your-project.supabase.co"
    # export SUPABASE_ANON_KEY="your-anon-key"
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("⚠️  WARNING: Supabase credentials not set!")
        print("Set SUPABASE_URL and SUPABASE_ANON_KEY environment variables")
    
    app.run(debug=True, host='0.0.0.0', port=8000)
