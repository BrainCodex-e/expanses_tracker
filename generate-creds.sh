#!/usr/bin/env bash
# Generate secure credentials for the expense tracker

echo "=== Expense Tracker Credential Generator ==="
echo ""

# Generate a secure secret key
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")

echo "Here are your secure credentials:"
echo ""
echo "Copy these lines to use:"
echo ""
echo "export USERS=\"yourname:yourpassword,partner:theirpassword\""
echo "export SECRET_KEY=\"$SECRET_KEY\""
echo ""
echo "For Render deployment, add these environment variables:"
echo ""
echo "USERS = yourname:yourpassword,partner:theirpassword"
echo "SECRET_KEY = $SECRET_KEY"
echo "SESSION_COOKIE_SECURE = 1"
echo ""
echo "Remember to replace 'yourname:yourpassword' with real credentials!"