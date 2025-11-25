# AI Insights Setup Guide

## Overview
AI-powered financial insights provide personalized spending analysis and money-saving tips using OpenAI's GPT-4 API.

## Features
- 🤖 **Automated spending analysis** - AI reviews your monthly expenses
- 💡 **Personalized insights** - Identifies spending patterns and trends
- 💰 **Money-saving tips** - Actionable recommendations based on your data
- ⚠️ **Budget warnings** - Alerts about overspending and concerning trends
- 📊 **Month-over-month comparison** - Tracks changes in spending habits
- 🇮🇱 **Hebrew language support** - Tips and insights in Hebrew

## Setup Instructions

### 1. Get OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Sign up or log in
3. Click "Create new secret key"
4. Copy the key (starts with `sk-proj-...`)

### 2. Add to Render Environment Variables
1. Go to your Render dashboard
2. Select your `expanses-tracker` service
3. Go to **Environment** tab
4. Click **Add Environment Variable**
5. Add:
   - **Key:** `OPENAI_API_KEY`
   - **Value:** `sk-proj-your-key-here`
6. Click **Save Changes**

### 3. Deploy
The app will automatically redeploy with AI insights enabled.

## Usage

### Viewing AI Insights
1. Go to **Monthly Summary** page (`/monthly/summary`)
2. Select a month from the dropdown
3. Scroll down to see the **AI Financial Insights** section

### What You'll See:
- **Key Observations:** Pattern analysis (e.g., "הוצאות על אוכל בחוץ עלו ב-30%")
- **Money-Saving Tips:** Specific recommendations (e.g., "שקול להכין אוכל בבית 2-3 פעמים בשבוע")
- **Warnings:** Budget alerts (e.g., "חריגה מתקציב בקטגוריית ספורט")

## Cost Information

### OpenAI API Pricing
- Model used: **GPT-4o-mini** (cost-effective)
- Average cost per insight: ~$0.01-0.02
- Monthly cost estimate: $0.30-1.00 (if checking daily)

### Free Tier
- OpenAI offers $5 free credit for new accounts
- Good for ~250-500 AI insight requests

## Configuration

### Environment Variables
```bash
# Required for AI insights
OPENAI_API_KEY=sk-proj-...

# Optional: Model selection (default: gpt-4o-mini)
OPENAI_MODEL=gpt-4o-mini
```

### Disabling AI Insights
If you don't want AI insights:
- Don't set `OPENAI_API_KEY` environment variable
- The app will work normally without AI features
- You'll see: "AI insights not available"

## Technical Details

### Files Added
- `ai_insights.py` - Core AI insight generation logic
- Updated `app.py` - Integration with monthly summary
- Updated `monthly_summary.html` - Display AI insights
- Updated `requirements.txt` - Added `openai==1.54.0`

### How It Works
1. Collects monthly spending data
2. Calculates category totals and budget usage
3. Compares with previous month
4. Sends structured data to OpenAI API
5. Receives personalized insights in Hebrew
6. Displays in user-friendly format

### Privacy & Security
- ✅ Only aggregated spending data sent to OpenAI (no personal info)
- ✅ API key stored as environment variable (not in code)
- ✅ No data stored by OpenAI (per their API policy)
- ✅ Insights generated on-demand (not cached)

## Troubleshooting

### "AI insights not available"
**Cause:** OPENAI_API_KEY not set or invalid
**Fix:** 
1. Check environment variable is set in Render
2. Verify API key is correct (starts with `sk-proj-`)
3. Check OpenAI account has available credits

### "AI insights temporarily unavailable"
**Cause:** API error or rate limit
**Fix:**
1. Check OpenAI API status: https://status.openai.com
2. Verify you have available credits
3. Wait a minute and refresh the page
4. Check Render logs for detailed error

### Insights in wrong language
**Cause:** System prompt might need adjustment
**Fix:** Edit `ai_insights.py`, line with "Hebrew" and ensure it says:
```python
"You are a financial advisor providing personalized advice in Hebrew."
```

## Advanced: Customization

### Adjust AI Temperature
In `ai_insights.py`, change `temperature` parameter:
```python
temperature=0.7  # Lower = more focused, Higher = more creative
```

### Change Model
To use GPT-4 (more expensive but better):
```python
model="gpt-4"  # or "gpt-4-turbo"
```

### Add More Context
Modify the prompt in `generate_spending_insights()` to include:
- Household members
- Income information
- Savings goals
- Financial constraints

## Future Enhancements
- 📈 Trend predictions for next month
- 🎯 Goal-based recommendations
- 📧 Email alerts for budget warnings
- 🤝 Household-wide insights
- 📊 Visual spending charts with AI annotations

## Support
If AI insights aren't working:
1. Check Render logs for error messages
2. Verify OpenAI API key is active
3. Test API key with curl:
   ```bash
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY"
   ```
