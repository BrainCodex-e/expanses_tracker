# Simple UI Tests for Expense Tracker
# These tests check if our web pages work correctly

import pytest
from app import app


# This is a "fixture" - it sets up a test version of our app
@pytest.fixture
def client():
    """Create a test version of our Flask app"""
    app.config['TESTING'] = True  # Tell Flask we're testing
    app.config['WTF_CSRF_ENABLED'] = False  # Disable security for easier testing
    
    with app.test_client() as client:
        yield client


# Test 1: Check if login page loads
def test_login_page_loads(client):
    """Test: Can we visit the login page?"""
    response = client.get('/login')
    
    # Check if page loaded successfully (status code 200 = OK)
    assert response.status_code == 200
    
    # Check if the word "login" appears on the page
    assert b'login' in response.data.lower()
    print("✅ Login page loads correctly!")


# Test 2: Check if we can log in
def test_user_can_login(client):
    """Test: Can a user log in with correct password?"""
    response = client.post('/login', data={
        'username': 'erez',
        'password': 'password'
    }, follow_redirects=True)
    
    # Should redirect to main page after successful login
    assert response.status_code == 200
    print("✅ User can log in successfully!")


# Test 3: Check if main page requires login
def test_main_page_requires_login(client):
    """Test: Does the main page redirect to login if not logged in?"""
    response = client.get('/')
    
    # Should redirect (status code 302) to login page
    assert response.status_code == 302
    print("✅ Main page properly requires login!")


# Test 4: Check if we can access main page after login
def test_main_page_after_login(client):
    """Test: Can we see the main page after logging in?"""
    # First, log in
    client.post('/login', data={
        'username': 'erez',
        'password': 'password'
    })
    
    # Then try to access main page
    response = client.get('/')
    assert response.status_code == 200
    
    # Check if we can see expense-related content
    assert b'Expenses' in response.data
    print("✅ Main page shows after login!")


# Test 5: Check if quick add buttons exist
def test_quick_add_buttons_exist(client):
    """Test: Are the quick add buttons visible on the page?"""
    # Log in first
    client.post('/login', data={
        'username': 'erez',
        'password': 'password'
    })
    
    # Get the main page
    response = client.get('/')
    
    # Check if quick add buttons are there
    assert b'Coffee' in response.data
    assert b'Lunch' in response.data
    assert b'Gas' in response.data
    print("✅ Quick add buttons are visible!")


# Test 6: Check if we can add an expense
def test_can_add_expense(client):
    """Test: Can we add a new expense?"""
    # Log in first
    client.post('/login', data={
        'username': 'erez',
        'password': 'password'
    })
    
    # Try to add an expense
    response = client.post('/add', data={
        'tx_date': '2025-11-06',
        'category': 'Food: Groceries',
        'amount': '50.00',
        'payer': 'erez',
        'notes': 'Test grocery shopping'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    print("✅ Can add expenses successfully!")


# Test 7: Check if budget page loads
def test_budget_page_loads(client):
    """Test: Can we access the budget settings page?"""
    # Log in first
    client.post('/login', data={
        'username': 'erez',
        'password': 'password'
    })
    
    # Try to access budget page
    response = client.get('/budget/settings')
    assert response.status_code == 200
    print("✅ Budget page loads correctly!")


# Test 8: Check if status endpoint works (for health checks)
def test_status_endpoint(client):
    """Test: Does our health check endpoint work?"""
    response = client.get('/status')
    assert response.status_code == 200
    print("✅ Health check endpoint works!")


if __name__ == "__main__":
    # If you run this file directly, it will run all tests
    pytest.main([__file__, "-v"])  # -v means "verbose" (show details)