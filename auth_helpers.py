"""
Supabase Authentication Integration
Uses Supabase Auth for email/password authentication
"""
import os
from typing import Optional, Dict
from supabase import create_client, Client
from supabase_config import get_supabase_client

def signup_user(email: str, password: str, username: str, household_name: Optional[str] = None) -> Dict:
    """
    Sign up a new user with Supabase Auth
    
    Args:
        email: User's email
        password: User's password (min 6 characters)
        username: Display username
        household_name: Optional household name
    
    Returns:
        Dict with user info and session
    """
    client = get_supabase_client()
    if not client:
        raise Exception("Supabase not configured. Set SUPABASE_URL and SUPABASE_ANON_KEY")
    
    try:
        # Note: Username uniqueness is enforced by database constraint
        # Pre-signup check removed because RLS blocks anonymous queries
        # Duplicate usernames will be caught by the trigger/constraint
        
        # Sign up with Supabase Auth
        response = client.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "username": username,
                    "household_name": household_name or f"{username}'s Household"
                }
            }
        })
        
        if response.user:
            print(f"✅ User created: {email} (username: {username})")
            return {
                "success": True,
                "user": response.user,
                "session": response.session,
                "message": "Account created successfully! Check your email to verify your account."
            }
        else:
            return {
                "success": False,
                "error": "Failed to create account"
            }
    
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Signup error: {error_msg}")
        
        # Parse common Supabase errors
        if "already registered" in error_msg.lower() or "already exists" in error_msg.lower():
            return {"success": False, "error": "Email already registered"}
        elif "duplicate key" in error_msg.lower() or "unique constraint" in error_msg.lower():
            if "username" in error_msg.lower():
                return {"success": False, "error": "Username already taken. Please choose a different username."}
            else:
                return {"success": False, "error": "Account with this information already exists"}
        elif "password" in error_msg.lower():
            return {"success": False, "error": "Password must be at least 6 characters"}
        else:
            return {"success": False, "error": f"Failed to create account: {error_msg}"}


def login_user(email: str, password: str) -> Dict:
    """
    Log in a user with email and password
    
    Args:
        email: User's email
        password: User's password
    
    Returns:
        Dict with user info and session
    """
    client = get_supabase_client()
    if not client:
        raise Exception("Supabase not configured")
    
    try:
        response = client.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if response.user and response.session:
            user_metadata = response.user.user_metadata or {}
            username = user_metadata.get('username', email.split('@')[0])
            
            print(f"✅ User logged in: {email} (username: {username})")
            return {
                "success": True,
                "user": response.user,
                "session": response.session,
                "username": username,
                "email": email,
                "user_id": response.user.id
            }
        else:
            return {
                "success": False,
                "error": "Invalid credentials"
            }
    
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Login error: {error_msg}")
        
        if "invalid" in error_msg.lower() or "credentials" in error_msg.lower():
            return {"success": False, "error": "Invalid email or password"}
        else:
            return {"success": False, "error": "Login failed"}


def logout_user() -> bool:
    """Log out the current user"""
    client = get_supabase_client()
    if not client:
        return False
    
    try:
        client.auth.sign_out()
        print("✅ User logged out")
        return True
    except Exception as e:
        print(f"❌ Logout error: {e}")
        return False


def get_current_user() -> Optional[Dict]:
    """
    Get the currently authenticated user
    
    Returns:
        Dict with user info or None
    """
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        user = client.auth.get_user()
        if user:
            user_metadata = user.user.user_metadata or {}
            return {
                "user_id": user.user.id,
                "email": user.user.email,
                "username": user_metadata.get('username', user.user.email.split('@')[0]),
                "household_name": user_metadata.get('household_name', 'My Household'),
                "email_confirmed": user.user.email_confirmed_at is not None
            }
    except:
        return None
    
    return None


def reset_password_email(email: str) -> Dict:
    """
    Send password reset email
    
    Args:
        email: User's email
    
    Returns:
        Dict with success status
    """
    client = get_supabase_client()
    if not client:
        raise Exception("Supabase not configured")
    
    try:
        client.auth.reset_password_email(email)
        return {
            "success": True,
            "message": "Password reset email sent! Check your inbox."
        }
    except Exception as e:
        print(f"❌ Password reset error: {e}")
        return {
            "success": False,
            "error": "Failed to send reset email"
        }


def update_user_metadata(username: Optional[str] = None, household_name: Optional[str] = None) -> bool:
    """
    Update user metadata (username, household_name)
    
    Args:
        username: New username
        household_name: New household name
    
    Returns:
        True if successful
    """
    client = get_supabase_client()
    if not client:
        return False
    
    try:
        data = {}
        if username:
            data["username"] = username
        if household_name:
            data["household_name"] = household_name
        
        if data:
            client.auth.update_user({"data": data})
            print(f"✅ User metadata updated: {data}")
            return True
    except Exception as e:
        print(f"❌ Metadata update error: {e}")
        return False
    
    return False


def verify_session(access_token: str) -> Optional[Dict]:
    """
    Verify a session token and get user info
    
    Args:
        access_token: JWT access token
    
    Returns:
        User dict if valid, None otherwise
    """
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        # Set the session and get user
        client.auth.set_session(access_token, access_token)  # Supabase needs both tokens
        user = client.auth.get_user()
        
        if user:
            return get_current_user()
    except:
        pass
    
    return None


def check_supabase_auth_enabled() -> bool:
    """Check if Supabase Auth is properly configured"""
    client = get_supabase_client()
    if not client:
        print("⚠️  Supabase Auth NOT enabled - missing SUPABASE_URL or SUPABASE_ANON_KEY")
        return False
    
    print("✅ Supabase Auth enabled")
    return True
