#!/bin/bash
# Simple script to run UI tests

echo "🧪 Starting UI Tests for Expense Tracker"
echo "========================================"

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "📦 Installing test dependencies..."
    pip install -r requirements-test.txt
fi

echo ""
echo "🏃 Running tests..."
echo ""

# Run the tests with nice output
pytest tests/test_basic_ui.py -v --tb=short

echo ""
echo "✅ Tests completed!"
echo ""
echo "What each test does:"
echo "📝 test_login_page_loads - Checks if login page works"
echo "🔐 test_user_can_login - Checks if login functionality works"
echo "🚪 test_main_page_requires_login - Checks security (login required)"
echo "🏠 test_main_page_after_login - Checks main page loads after login"
echo "⚡ test_quick_add_buttons_exist - Checks if quick add buttons are there"
echo "➕ test_can_add_expense - Checks if we can add expenses"
echo "💰 test_budget_page_loads - Checks if budget page works"
echo "❤️ test_status_endpoint - Checks if health check works"