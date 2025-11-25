"""
AI-powered financial insights and tips
Uses OpenAI API to analyze spending patterns and provide personalized advice
"""
import os
from datetime import date, timedelta
from typing import Dict, List, Optional
import pandas as pd

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️  OpenAI not available - pip install openai")


def get_ai_client():
    """Get OpenAI client if API key is configured"""
    if not OPENAI_AVAILABLE:
        return None
    
    api_key = os.environ.get('OPENAI_API_KEY')
    if not api_key:
        print("⚠️  OPENAI_API_KEY not set")
        return None
    
    try:
        # Initialize OpenAI client - let it use default HTTP client
        client = OpenAI(
            api_key=api_key,
            timeout=30.0,  # Set reasonable timeout
            max_retries=2  # Retry failed requests
        )
        return client
    except Exception as e:
        print(f"⚠️  OpenAI client initialization error: {e}")
        return None


def generate_spending_insights(month_df: pd.DataFrame, budgets: Dict, previous_month_df: Optional[pd.DataFrame] = None) -> Dict:
    """
    Generate AI-powered insights about spending patterns
    
    Args:
        month_df: DataFrame with current month expenses
        budgets: Dict of budget limits by user/category
        previous_month_df: Optional DataFrame with previous month for comparison
    
    Returns:
        Dict with insights, tips, and warnings
    """
    client = get_ai_client()
    if not client or month_df.empty:
        return {
            'enabled': False,
            'tips': [],
            'warnings': [],
            'summary': 'AI insights not available. Set OPENAI_API_KEY to enable.'
        }
    
    try:
        # Prepare spending summary
        total_spent = month_df['amount'].sum()
        category_spending = month_df.groupby('category')['amount'].sum().to_dict()
        top_categories = sorted(category_spending.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Calculate budget usage
        budget_status = []
        for user, user_budgets in budgets.items():
            user_expenses = month_df[month_df['payer'] == user]
            for category, budget_limit in user_budgets.items():
                spent = user_expenses[user_expenses['category'] == category]['amount'].sum()
                percentage = (spent / budget_limit * 100) if budget_limit > 0 else 0
                if percentage > 0:
                    budget_status.append(f"{user} - {category}: ₪{spent:.0f}/₪{budget_limit:.0f} ({percentage:.0f}%)")
        
        # Month-over-month comparison
        comparison_text = ""
        if previous_month_df is not None and not previous_month_df.empty:
            prev_total = previous_month_df['amount'].sum()
            change = ((total_spent - prev_total) / prev_total * 100) if prev_total > 0 else 0
            comparison_text = f"\nCompared to last month: {'↑' if change > 0 else '↓'} {abs(change):.1f}% ({'+' if change > 0 else ''}{total_spent - prev_total:.0f})"
        
        # Build prompt
        prompt = f"""Analyze this monthly spending data and provide 3-4 actionable financial tips in Hebrew:

Total Spent: ₪{total_spent:.2f}
{comparison_text}

Top Spending Categories:
{chr(10).join([f'- {cat}: ₪{amount:.2f}' for cat, amount in top_categories])}

Budget Status:
{chr(10).join([f'- {status}' for status in budget_status[:5]])}

Provide:
1. 2-3 specific insights about spending patterns
2. 2-3 actionable tips to save money (be specific, not generic)
3. 1-2 warnings about budget overruns or concerning trends

Format as JSON:
{{
  "insights": ["insight1", "insight2"],
  "tips": ["tip1", "tip2"],
  "warnings": ["warning1"] or []
}}

Keep each point concise (1-2 sentences). Focus on specific numbers and categories from the data."""

        # Call OpenAI
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a financial advisor providing personalized advice in Hebrew. Be specific, actionable, and reference actual spending amounts."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=800,
            response_format={"type": "json_object"}
        )
        
        import json
        result = json.loads(response.choices[0].message.content)
        
        return {
            'enabled': True,
            'insights': result.get('insights', []),
            'tips': result.get('tips', []),
            'warnings': result.get('warnings', []),
            'summary': f"AI analysis based on ₪{total_spent:.0f} across {len(month_df)} transactions"
        }
        
    except Exception as e:
        print(f"❌ AI insights error: {e}")
        return {
            'enabled': False,
            'tips': [],
            'warnings': [],
            'summary': f'AI insights temporarily unavailable: {str(e)}'
        }


def generate_budget_recommendations(user_expenses: pd.DataFrame, current_budgets: Dict, months_history: int = 3) -> List[Dict]:
    """
    Generate AI-powered budget adjustment recommendations
    
    Args:
        user_expenses: DataFrame with user's expense history
        current_budgets: Current budget limits by category
        months_history: Number of months to analyze
    
    Returns:
        List of recommended budget adjustments
    """
    client = get_ai_client()
    if not client or user_expenses.empty:
        return []
    
    try:
        # Calculate average spending per category over last N months
        user_expenses['tx_date'] = pd.to_datetime(user_expenses['tx_date'])
        cutoff_date = date.today() - timedelta(days=months_history * 30)
        recent_expenses = user_expenses[user_expenses['tx_date'] >= pd.to_datetime(cutoff_date)]
        
        avg_spending = recent_expenses.groupby('category')['amount'].mean().to_dict()
        
        recommendations = []
        for category, avg_spent in avg_spending.items():
            current_budget = current_budgets.get(category, 0)
            if current_budget == 0:
                continue
            
            variance = ((avg_spent - current_budget) / current_budget * 100)
            
            # Only recommend if variance is significant (>15%)
            if abs(variance) > 15:
                action = "increase" if variance > 0 else "decrease"
                recommended = avg_spent * 1.1  # Add 10% buffer
                
                recommendations.append({
                    'category': category,
                    'current': current_budget,
                    'average_spending': avg_spent,
                    'recommended': recommended,
                    'action': action,
                    'variance': variance
                })
        
        return sorted(recommendations, key=lambda x: abs(x['variance']), reverse=True)[:5]
        
    except Exception as e:
        print(f"❌ Budget recommendations error: {e}")
        return []
