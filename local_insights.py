"""
Local financial insights generator - No API required!
Provides spending analysis and tips based on rule-based logic
"""
from typing import Dict, List, Optional
import pandas as pd
from datetime import date


def generate_local_insights(month_df: pd.DataFrame, budgets: Dict, previous_month_df: Optional[pd.DataFrame] = None) -> Dict:
    """
    Generate insights using local rule-based analysis (free, no API needed)
    
    Args:
        month_df: DataFrame with current month expenses
        budgets: Dict of budget limits by user/category
        previous_month_df: Optional DataFrame with previous month for comparison
    
    Returns:
        Dict with insights, tips, and warnings in Hebrew
    """
    if month_df.empty:
        return {
            'enabled': True,
            'insights': [],
            'tips': ['התחל לעקוב אחר ההוצאות שלך כדי לקבל המלצות מותאמות אישית'],
            'warnings': [],
            'summary': 'אין נתונים לניתוח'
        }
    
    insights = []
    tips = []
    warnings = []
    
    # Calculate basic statistics
    total_spent = month_df['amount'].sum()
    transaction_count = len(month_df)
    avg_transaction = total_spent / transaction_count if transaction_count > 0 else 0
    
    # Analyze by category
    category_spending = month_df.groupby('category')['amount'].agg(['sum', 'count']).reset_index()
    category_spending.columns = ['category', 'total', 'count']
    category_spending = category_spending.sort_values('total', ascending=False)
    
    top_category = category_spending.iloc[0] if len(category_spending) > 0 else None
    
    # Month-over-month comparison
    if previous_month_df is not None and not previous_month_df.empty:
        prev_total = previous_month_df['amount'].sum()
        change_amount = total_spent - prev_total
        change_percent = (change_amount / prev_total * 100) if prev_total > 0 else 0
        
        if abs(change_percent) > 5:
            direction = "עלו" if change_percent > 0 else "ירדו"
            insights.append(
                f"ההוצאות החודשיות שלך {direction} ב-{abs(change_percent):.0f}% (₪{abs(change_amount):.0f}) לעומת החודש הקודם"
            )
            
            # Category comparison
            prev_category = previous_month_df.groupby('category')['amount'].sum()
            curr_category = month_df.groupby('category')['amount'].sum()
            
            for cat in curr_category.index:
                if cat in prev_category.index:
                    cat_change = ((curr_category[cat] - prev_category[cat]) / prev_category[cat] * 100)
                    if abs(cat_change) > 30:
                        direction = "עלו" if cat_change > 0 else "ירדו"
                        insights.append(f"הוצאות על {cat} {direction} משמעותית ב-{abs(cat_change):.0f}%")
    
    # Top spending category
    if top_category is not None:
        percentage = (top_category['total'] / total_spent * 100) if total_spent > 0 else 0
        insights.append(
            f"הקטגוריה עם ההוצאות הגבוהות ביותר היא {top_category['category']} "
            f"(₪{top_category['total']:.0f}, {percentage:.0f}% מסך ההוצאות)"
        )
    
    # Average transaction insight
    if avg_transaction > 0:
        insights.append(f"ממוצע הוצאה לעסקה: ₪{avg_transaction:.0f} ({transaction_count} עסקאות)")
    
    # Budget analysis and warnings
    budget_warnings = []
    budget_ok = []
    
    for user, user_budgets in budgets.items():
        user_expenses = month_df[month_df['payer'] == user]
        for category, budget_limit in user_budgets.items():
            spent = user_expenses[user_expenses['category'] == category]['amount'].sum()
            percentage = (spent / budget_limit * 100) if budget_limit > 0 else 0
            
            if percentage >= 100:
                over = spent - budget_limit
                warnings.append(f"⚠️ חריגה מתקציב: {category} - ₪{over:.0f} מעל התקציב!")
                budget_warnings.append(category)
            elif percentage >= 80:
                remaining = budget_limit - spent
                warnings.append(f"⚡ קרוב לגבול: {category} - נותרו רק ₪{remaining:.0f} ({100-percentage:.0f}%)")
            elif percentage > 0:
                budget_ok.append(category)
    
    # Generate smart tips based on spending patterns
    
    # Tip 1: High frequency categories
    high_freq_categories = category_spending[category_spending['count'] >= 5]
    if len(high_freq_categories) > 0:
        cat = high_freq_categories.iloc[0]
        tips.append(
            f"יש לך {cat['count']} עסקאות ב{cat['category']} - "
            f"שקול לתכנן מראש או לקנות בכמויות גדולות לחיסכון"
        )
    
    # Tip 2: Large single transactions
    large_transactions = month_df[month_df['amount'] > (avg_transaction * 3)]
    if len(large_transactions) > 0:
        tips.append(
            f"זוהו {len(large_transactions)} עסקאות גדולות - "
            f"בדוק אם אפשר לפרוס תשלומים או לחפש חלופות זולות יותר"
        )
    
    # Tip 3: Budget management
    if len(budget_warnings) > 0:
        tips.append(
            f"נמצאו חריגות תקציב ב-{len(budget_warnings)} קטגוריות - "
            f"שקול להעלות תקציב או להפחית הוצאות בחודש הבא"
        )
    elif len(budget_ok) > 0:
        tips.append("כל הכבוד! אתה מצליח לשמור על התקציבים בקטגוריות רבות 💪")
    
    # Tip 4: Weekend spending
    month_df['day_of_week'] = pd.to_datetime(month_df['tx_date']).dt.dayofweek
    weekend_spending = month_df[month_df['day_of_week'].isin([4, 5, 6])]['amount'].sum()
    weekend_pct = (weekend_spending / total_spent * 100) if total_spent > 0 else 0
    
    if weekend_pct > 40:
        tips.append(
            f"סופי השבוע מהווים {weekend_pct:.0f}% מההוצאות - "
            f"שקול תכנון פעילויות חסכוניות יותר"
        )
    
    # Tip 5: Category-specific tips
    food_categories = ['אוכל', 'מסעדות', 'קפה', 'אוכל בחוץ']
    food_spending = month_df[month_df['category'].isin(food_categories)]['amount'].sum()
    food_pct = (food_spending / total_spent * 100) if total_spent > 0 else 0
    
    if food_pct > 30:
        tips.append(
            f"הוצאות על אוכל מהוות {food_pct:.0f}% - "
            f"בישול בבית 2-3 פעמים בשבוע יכול לחסוך מאות שקלים"
        )
    
    # Default tips if none generated
    if len(tips) == 0:
        tips.append("המשך לעקוב אחר ההוצאות באופן קבוע כדי לזהות דפוסים")
        tips.append("הגדר תקציבים לכל קטגוריה כדי לשלוט טוב יותר בהוצאות")
    
    # Summary
    summary = f"ניתוח מקומי של ₪{total_spent:.0f} ב-{transaction_count} עסקאות"
    
    return {
        'enabled': True,
        'insights': insights[:4],  # Limit to 4 insights
        'tips': tips[:3],  # Limit to 3 tips
        'warnings': warnings[:3],  # Limit to 3 warnings
        'summary': summary
    }


def analyze_spending_trends(user_df: pd.DataFrame, months: int = 3) -> Dict:
    """
    Analyze spending trends over multiple months
    
    Args:
        user_df: DataFrame with user's full expense history
        months: Number of months to analyze
    
    Returns:
        Dict with trend analysis
    """
    if user_df.empty:
        return {
            'trend': 'stable',
            'average_monthly': 0,
            'highest_month': None,
            'lowest_month': None
        }
    
    user_df['tx_date'] = pd.to_datetime(user_df['tx_date'])
    user_df['year_month'] = user_df['tx_date'].dt.to_period('M')
    
    monthly_totals = user_df.groupby('year_month')['amount'].sum().sort_index(ascending=False)
    
    if len(monthly_totals) < 2:
        return {
            'trend': 'insufficient_data',
            'average_monthly': monthly_totals.iloc[0] if len(monthly_totals) > 0 else 0,
            'highest_month': None,
            'lowest_month': None
        }
    
    recent_months = monthly_totals.head(min(months, len(monthly_totals)))
    
    # Calculate trend
    first_half_avg = recent_months.iloc[:len(recent_months)//2].mean()
    second_half_avg = recent_months.iloc[len(recent_months)//2:].mean()
    
    if first_half_avg > second_half_avg * 1.1:
        trend = 'decreasing'
    elif first_half_avg < second_half_avg * 0.9:
        trend = 'increasing'
    else:
        trend = 'stable'
    
    return {
        'trend': trend,
        'average_monthly': recent_months.mean(),
        'highest_month': {
            'period': str(recent_months.idxmax()),
            'amount': recent_months.max()
        },
        'lowest_month': {
            'period': str(recent_months.idxmin()),
            'amount': recent_months.min()
        }
    }
