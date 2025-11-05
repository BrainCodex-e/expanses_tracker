const CACHE_NAME = 'expenses-v2';
const STATIC_ASSETS = [
  '/static/style.css',
  '/static/manifest.json'
];

// Install event - cache static assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(STATIC_ASSETS);
    }).then(() => {
      self.skipWaiting(); // Activate immediately
    })
  );
});

// Fetch event - cache-first strategy for static assets, network-first for dynamic content
self.addEventListener('fetch', event => {
  const req = event.request;
  const url = new URL(req.url);
  
  // Skip non-GET requests
  if (req.method !== 'GET') {
    return;
  }
  
  // Cache-first strategy for static assets
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(req).then(cached => {
        return cached || fetch(req).then(response => {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then(cache => {
            cache.put(req, responseClone);
          });
          return response;
        });
      }).catch(() => {
        // Return a fallback if both cache and network fail
        return new Response('Offline', { status: 503 });
      })
    );
  } else {
    // Network-first strategy for dynamic content
    event.respondWith(
      fetch(req).catch(() => {
        return caches.match(req);
      })
    );
  }
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(key => key !== CACHE_NAME)
           .map(key => caches.delete(key))
      );
    }).then(() => {
      return self.clients.claim(); // Take control immediately
    })
  );
});

// Background sync for offline form submissions (if supported)
self.addEventListener('sync', event => {
  if (event.tag === 'budget-sync') {
    event.waitUntil(
      // Handle offline budget updates when connection is restored
      syncBudgetUpdates()
    );
  }
});

async function syncBudgetUpdates() {
  // Implementation for offline sync would go here
  // For now, just log that sync was attempted
  console.log('Background sync attempted');
}
