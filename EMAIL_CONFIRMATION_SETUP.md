# Email Confirmation Setup Guide

## Problem
When users click email confirmation links from Supabase, they were being redirected to the website but not properly authenticated. The Flask app had no route to handle the authentication callback.

## Solution

### 1. Authentication Callback Route
Created `/auth/callback` endpoint that:
- Renders a callback page that processes Supabase authentication tokens
- Handles URL fragments sent by Supabase (tokens in #hash)
- Establishes Flask session after successful verification

### 2. Session Handler Endpoint
Created `/auth/session` POST endpoint that:
- Receives session data from the client-side callback
- Sets up Flask session with user credentials
- Returns success/error response

### 3. Client-Side Processing
Created `templates/auth_callback.html` that:
- Uses Supabase JS client to read session from URL
- Fetches user profile from database
- Sends session data to Flask backend
- Redirects to home page on success
- Shows error and redirects to login on failure

## Configuration Required

### Supabase Dashboard Settings

1. **Go to Supabase Dashboard**
   - Navigate to: Your Project → Authentication → URL Configuration

2. **Set Site URL**
   ```
   https://expanses-tracker.onrender.com
   ```

3. **Add Redirect URLs**
   Add these to the allowed redirect URLs list:
   ```
   https://expanses-tracker.onrender.com/auth/callback
   https://expanses-tracker.onrender.com/**
   http://localhost:8000/auth/callback  (for local development)
   http://localhost:8000/**  (for local development)
   ```

### Environment Variables

Add to Render environment variables:
```bash
APP_URL=https://expanses-tracker.onrender.com
```

This is used by `auth_helpers.py` to set the email redirect destination:
```python
"email_redirect_to": f"{os.environ.get('APP_URL', 'http://localhost:8000')}/auth/callback"
```

## Testing the Flow

### Complete Email Confirmation Flow:
1. User signs up at `/signup`
2. Supabase sends confirmation email
3. User clicks confirmation link in email
4. Supabase redirects to: `https://expanses-tracker.onrender.com/auth/callback#access_token=...`
5. Callback page loads and processes tokens
6. Session data sent to `/auth/session`
7. Flask session established
8. User redirected to home page (`/`)
9. User is now logged in

### What to Test:
```bash
# 1. Sign up with new account
# 2. Check email for confirmation link
# 3. Click confirmation link
# 4. Should see "Completing Authentication..." page briefly
# 5. Should redirect to home page with flash message
# 6. Should be able to access protected routes
# 7. Check that session persists across page loads
```

## Files Changed

### New Files:
- `templates/auth_callback.html` - Client-side callback handler

### Modified Files:
- `app.py` - Added `/auth/callback` and `/auth/session` routes
- `auth_helpers.py` - Added `email_redirect_to` option in signup

## Technical Details

### Why URL Fragments?
Supabase sends authentication tokens in URL fragments (`#access_token=...`) for security:
- Fragments never sent to server in HTTP requests
- Must be processed client-side with JavaScript
- Prevents tokens from appearing in server logs

### Flow Diagram:
```
Supabase Email → User Clicks Link → /auth/callback
                                          ↓
                              auth_callback.html loads
                                          ↓
                              Supabase JS reads #tokens
                                          ↓
                              Fetch user profile
                                          ↓
                              POST to /auth/session
                                          ↓
                              Flask sets session cookies
                                          ↓
                              Redirect to /
```

## Troubleshooting

### Issue: "No authentication session found"
- **Cause**: Tokens not in URL or expired
- **Fix**: Request new confirmation email

### Issue: "Could not load user profile"
- **Cause**: RLS policy blocking profile access
- **Fix**: Verify RLS policies allow authenticated users to read own profile

### Issue: "Failed to establish session"
- **Cause**: CSRF token missing or session configuration issue
- **Fix**: Check Flask session configuration and CSRF exemption for `/auth/session`

### Issue: Still redirecting to localhost
- **Cause**: Supabase Site URL not updated
- **Fix**: Update Site URL in Supabase Dashboard (see Configuration section above)

## Local Development

For local testing, use:
```bash
export APP_URL=http://localhost:8000
```

And add to Supabase redirect URLs:
```
http://localhost:8000/auth/callback
http://localhost:8000/**
```

## Security Notes

1. ✅ Tokens transmitted via URL fragments (not query params)
2. ✅ Session validation on backend
3. ✅ CSRF protection maintained
4. ✅ Redirect URLs whitelisted in Supabase
5. ✅ User profile verified before session creation
