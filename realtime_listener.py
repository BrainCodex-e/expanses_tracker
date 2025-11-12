"""
Realtime Dashboard Update Listener
Uses Supabase Realtime to automatically update the dashboard when expenses change
"""

# Add this to your index.html or create a separate JavaScript file

REALTIME_DASHBOARD_JS = """
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
<script>
// Initialize Supabase client for realtime
const SUPABASE_URL = '{{ supabase_url }}';
const SUPABASE_ANON_KEY = '{{ supabase_key }}';
const { createClient } = supabase;
const realtimeClient = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// Get current user's household
const currentHousehold = '{{ household }}';

console.log('🔥 Initializing realtime updates for household:', currentHousehold);

// Subscribe to expenses changes
const expensesChannel = realtimeClient
  .channel('expenses_changes')
  .on(
    'postgres_changes',
    {
      event: '*', // Listen to all events (INSERT, UPDATE, DELETE)
      schema: 'public',
      table: 'expenses',
      filter: `household=eq.${currentHousehold}`
    },
    (payload) => {
      console.log('💰 Expense change detected:', payload);
      
      // Handle different event types
      switch(payload.eventType) {
        case 'INSERT':
          handleNewExpense(payload.new);
          break;
        case 'UPDATE':
          handleUpdatedExpense(payload.new, payload.old);
          break;
        case 'DELETE':
          handleDeletedExpense(payload.old);
          break;
      }
      
      // Refresh the entire dashboard after a short delay
      setTimeout(() => {
        console.log('🔄 Refreshing dashboard...');
        location.reload();
      }, 500);
    }
  )
  .subscribe((status) => {
    if (status === 'SUBSCRIBED') {
      console.log('✅ Successfully subscribed to realtime updates');
    } else if (status === 'CHANNEL_ERROR') {
      console.error('❌ Error subscribing to realtime channel');
    }
  });

// Handle new expense
function handleNewExpense(expense) {
  console.log('➕ New expense added:', expense);
  
  // Show toast notification
  showToast(`New expense: ₪${expense.amount} - ${expense.category}`, 'success');
  
  // Optional: Add animation to highlight new expense
  setTimeout(() => {
    const newCard = document.querySelector(`[data-expense-id="${expense.id}"]`);
    if (newCard) {
      newCard.classList.add('highlight-new');
      setTimeout(() => newCard.classList.remove('highlight-new'), 2000);
    }
  }, 600);
}

// Handle updated expense
function handleUpdatedExpense(newExpense, oldExpense) {
  console.log('✏️ Expense updated:', { old: oldExpense, new: newExpense });
  showToast(`Expense updated: ₪${newExpense.amount}`, 'info');
}

// Handle deleted expense
function handleDeletedExpense(expense) {
  console.log('🗑️ Expense deleted:', expense);
  showToast(`Expense deleted: ₪${expense.amount}`, 'warning');
}

// Toast notification helper
function showToast(message, type = 'info') {
  // Check if toast container exists, if not create it
  let toastContainer = document.getElementById('toast-container');
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.id = 'toast-container';
    toastContainer.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      z-index: 9999;
    `;
    document.body.appendChild(toastContainer);
  }
  
  // Create toast element
  const toast = document.createElement('div');
  toast.className = `alert alert-${type} alert-dismissible fade show`;
  toast.style.cssText = `
    min-width: 300px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    animation: slideIn 0.3s ease-out;
  `;
  toast.innerHTML = `
    ${message}
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
  `;
  
  toastContainer.appendChild(toast);
  
  // Auto-remove after 3 seconds
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 150);
  }, 3000);
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
  @keyframes slideIn {
    from {
      transform: translateX(100%);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }
  
  .highlight-new {
    animation: highlightPulse 2s ease-in-out;
    background-color: rgba(40, 167, 69, 0.1) !important;
  }
  
  @keyframes highlightPulse {
    0%, 100% { background-color: transparent; }
    50% { background-color: rgba(40, 167, 69, 0.2); }
  }
`;
document.head.appendChild(style);

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
  expensesChannel.unsubscribe();
});

// Connection status monitoring
realtimeClient.channel('system').on('system', {}, (payload) => {
  if (payload.status === 'ok') {
    console.log('🟢 Realtime connection healthy');
  }
});

// Reconnect logic if connection drops
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;

function monitorConnection() {
  setInterval(async () => {
    const { data: { session }, error } = await realtimeClient.auth.getSession();
    
    if (error || !session) {
      console.warn('⚠️ Realtime connection lost, attempting to reconnect...');
      
      if (reconnectAttempts < maxReconnectAttempts) {
        reconnectAttempts++;
        expensesChannel.subscribe();
      } else {
        console.error('❌ Max reconnection attempts reached');
        showToast('Connection lost. Please refresh the page.', 'danger');
      }
    } else {
      reconnectAttempts = 0;
    }
  }, 30000); // Check every 30 seconds
}

monitorConnection();
</script>
"""

# Export for use in templates
def get_realtime_script(supabase_url, supabase_key, household):
    """Generate realtime script with proper values"""
    return REALTIME_DASHBOARD_JS.replace('{{ supabase_url }}', supabase_url)\
                                .replace('{{ supabase_key }}', supabase_key)\
                                .replace('{{ household }}', household)
