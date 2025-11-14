"""
Supabase Household Management
Handles households, member invites, and kicking users
"""
from typing import Optional, Dict, List
from supabase_config import get_supabase_client
from datetime import datetime, timedelta

def get_user_household(user_id: str) -> Optional[Dict]:
    """Get the household for a user"""
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        # Get user's profile with household info
        response = client.table('profiles').select(
            'household_id, username, is_household_owner, households(*)'
        ).eq('id', user_id).single().execute()
        
        if response.data:
            profile = response.data
            household = profile.get('households')
            
            if household:
                return {
                    'id': household['id'],
                    'name': household['name'],
                    'owner_id': household['owner_id'],
                    'invite_code': household['invite_code'],
                    'is_owner': profile['is_household_owner']
                }
    except Exception as e:
        print(f"❌ Error getting household: {e}")
    
    return None


def get_household_members(household_id: str) -> List[Dict]:
    """Get all members of a household"""
    client = get_supabase_client()
    if not client:
        return []
    
    try:
        response = client.table('profiles').select(
            'id, username, is_household_owner, created_at'
        ).eq('household_id', household_id).execute()
        
        return response.data if response.data else []
    except Exception as e:
        print(f"❌ Error getting members: {e}")
        return []


def create_household_invite(household_id: str, email: str, invited_by: str) -> Optional[str]:
    """
    Create an invitation to join a household
    
    Args:
        household_id: The household to invite to
        email: Email to invite
        invited_by: User ID of inviter
    
    Returns:
        Invite ID if successful
    """
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        # Check if user is household owner
        profile = client.table('profiles').select('is_household_owner').eq(
            'id', invited_by
        ).eq('household_id', household_id).single().execute()
        
        if not profile.data or not profile.data.get('is_household_owner'):
            print("❌ Only household owners can invite members")
            return None
        
        # Create invite
        invite_data = {
            'household_id': household_id,
            'email': email,
            'invited_by': invited_by,
            'expires_at': (datetime.now() + timedelta(days=7)).isoformat()
        }
        
        response = client.table('household_invites').insert(invite_data).execute()
        
        if response.data:
            print(f"✅ Invite created for {email}")
            return response.data[0]['id']
    except Exception as e:
        print(f"❌ Error creating invite: {e}")
    
    return None


def get_pending_invites(household_id: str) -> List[Dict]:
    """Get all pending invites for a household"""
    client = get_supabase_client()
    if not client:
        return []
    
    try:
        response = client.table('household_invites').select(
            'id, email, created_at, expires_at'
        ).eq('household_id', household_id).eq('accepted', False).gt(
            'expires_at', datetime.now().isoformat()
        ).execute()
        
        return response.data if response.data else []
    except Exception as e:
        print(f"❌ Error getting invites: {e}")
        return []


def accept_household_invite(user_id: str, invite_id: str) -> bool:
    """
    Accept a household invitation
    
    Args:
        user_id: The user accepting the invite
        invite_id: The invite ID
    
    Returns:
        True if successful
    """
    client = get_supabase_client()
    if not client:
        return False
    
    try:
        # Get the invite
        invite = client.table('household_invites').select(
            'household_id, email, expires_at, accepted'
        ).eq('id', invite_id).single().execute()
        
        if not invite.data:
            print("❌ Invite not found")
            return False
        
        if invite.data['accepted']:
            print("❌ Invite already used")
            return False
        
        # Check expiry
        if datetime.fromisoformat(invite.data['expires_at'].replace('Z', '+00:00')) < datetime.now():
            print("❌ Invite expired")
            return False
        
        # Get user's email to verify
        user = client.auth.get_user()
        if not user or user.user.email != invite.data['email']:
            print("❌ Invite email doesn't match user")
            return False
        
        # Update user's household
        client.table('profiles').update({
            'household_id': invite.data['household_id'],
            'is_household_owner': False
        }).eq('id', user_id).execute()
        
        # Mark invite as accepted
        client.table('household_invites').update({
            'accepted': True
        }).eq('id', invite_id).execute()
        
        print(f"✅ User {user_id} joined household")
        return True
        
    except Exception as e:
        print(f"❌ Error accepting invite: {e}")
        return False


def remove_household_member(household_id: str, user_id_to_remove: str, removed_by: str) -> bool:
    """
    Remove a member from a household (kick)
    
    Args:
        household_id: The household
        user_id_to_remove: User to remove
        removed_by: User doing the removal (must be owner)
    
    Returns:
        True if successful
    """
    client = get_supabase_client()
    if not client:
        return False
    
    try:
        # Verify remover is household owner
        remover = client.table('profiles').select('is_household_owner').eq(
            'id', removed_by
        ).eq('household_id', household_id).single().execute()
        
        if not remover.data or not remover.data.get('is_household_owner'):
            print("❌ Only household owners can remove members")
            return False
        
        # Can't remove yourself
        if user_id_to_remove == removed_by:
            print("❌ Can't remove yourself")
            return False
        
        # Create a new household for the removed user
        removed_user = client.table('profiles').select('username').eq(
            'id', user_id_to_remove
        ).single().execute()
        
        if removed_user.data:
            username = removed_user.data['username']
            
            # Create new household
            new_household = client.table('households').insert({
                'name': f"{username}'s Household",
                'owner_id': user_id_to_remove
            }).execute()
            
            if new_household.data:
                new_household_id = new_household.data[0]['id']
                
                # Move user to new household
                client.table('profiles').update({
                    'household_id': new_household_id,
                    'is_household_owner': True
                }).eq('id', user_id_to_remove).execute()
                
                print(f"✅ User {user_id_to_remove} removed and given new household")
                return True
        
    except Exception as e:
        print(f"❌ Error removing member: {e}")
    
    return False


def update_household_name(household_id: str, new_name: str, user_id: str) -> bool:
    """Update household name (owner only)"""
    client = get_supabase_client()
    if not client:
        return False
    
    try:
        # Verify user is owner
        profile = client.table('profiles').select('is_household_owner').eq(
            'id', user_id
        ).eq('household_id', household_id).single().execute()
        
        if not profile.data or not profile.data.get('is_household_owner'):
            print("❌ Only household owners can rename")
            return False
        
        # Update name
        client.table('households').update({
            'name': new_name
        }).eq('id', household_id).execute()
        
        print(f"✅ Household renamed to: {new_name}")
        return True
        
    except Exception as e:
        print(f"❌ Error updating name: {e}")
        return False


def leave_household(user_id: str) -> bool:
    """
    Leave current household and create a new one
    (Can't leave if you're the owner and have other members)
    """
    client = get_supabase_client()
    if not client:
        return False
    
    try:
        # Get user's profile
        profile = client.table('profiles').select(
            'household_id, username, is_household_owner'
        ).eq('id', user_id).single().execute()
        
        if not profile.data:
            return False
        
        household_id = profile.data['household_id']
        is_owner = profile.data['is_household_owner']
        username = profile.data['username']
        
        # If owner, check if there are other members
        if is_owner:
            members = get_household_members(household_id)
            if len(members) > 1:
                print("❌ Transfer ownership before leaving")
                return False
        
        # Create new household
        new_household = client.table('households').insert({
            'name': f"{username}'s Household",
            'owner_id': user_id
        }).execute()
        
        if new_household.data:
            new_household_id = new_household.data[0]['id']
            
            # Move user to new household
            client.table('profiles').update({
                'household_id': new_household_id,
                'is_household_owner': True
            }).eq('id', user_id).execute()
            
            print(f"✅ User left household and created new one")
            return True
            
    except Exception as e:
        print(f"❌ Error leaving household: {e}")
    
    return False
