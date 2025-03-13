const CACHE_NAME = 'fitfuel-v1';
const STATIC_CACHE = 'static-v1';
const DYNAMIC_CACHE = 'dynamic-v1';

const STATIC_ASSETS = [
  '/',
  '/static/css/tailwind.css',
  '/static/js/app.js',
  '/static/manifest.json',
  '/offline',
  '/static/icons/icon-192x192.png'
];

// Install Service Worker
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => {
        console.log('Caching static assets');
        return cache.addAll(STATIC_ASSETS);
      })
  );
  self.skipWaiting();
});

// Activate Service Worker
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(key => key !== STATIC_CACHE && key !== DYNAMIC_CACHE)
          .map(key => caches.delete(key))
      );
    })
  );
});

// Fetch Event Strategy
self.addEventListener('fetch', event => {
  // API calls
  if (event.request.url.includes('/api/')) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          return caches.open(DYNAMIC_CACHE)
            .then(cache => {
              cache.put(event.request.url, response.clone());
              return response;
            });
        })
        .catch(() => {
          return caches.match(event.request);
        })
    );
    return;
  }

  // Static assets
  if (event.request.url.match(/\.(css|js|png|jpg|jpeg|gif|svg)$/)) {
    event.respondWith(
      caches.match(event.request)
        .then(response => {
          return response || fetch(event.request)
            .then(fetchResponse => {
              return caches.open(DYNAMIC_CACHE)
                .then(cache => {
                  cache.put(event.request.url, fetchResponse.clone());
                  return fetchResponse;
                });
            });
        })
    );
    return;
  }

  // HTML pages
  event.respondWith(
    fetch(event.request)
      .then(response => {
        return caches.open(DYNAMIC_CACHE)
          .then(cache => {
            cache.put(event.request.url, response.clone());
            return response;
          });
      })
      .catch(() => {
        return caches.match(event.request)
          .then(response => {
            if (response) {
              return response;
            }
            if (event.request.headers.get('accept').includes('text/html')) {
              return caches.match('/offline');
            }
          });
      })
  );
});

// Background Sync for offline data
self.addEventListener('sync', event => {
  if (event.tag === 'sync-workout-logs') {
    event.waitUntil(syncWorkoutLogs());
  }
});

// Push Notifications
self.addEventListener('push', event => {
  const options = {
    body: event.data.text(),
    icon: '/static/icons/icon-192x192.png',
    badge: '/static/icons/badge-72x72.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'explore',
        title: 'View Details'
      }
    ]
  };

  event.waitUntil(
    self.registration.showNotification('FitFuel Update', options)
  );
});

// Helper function to sync workout logs
async function syncWorkoutLogs() {
  try {
    const logsToSync = await getLogsToSync();
    await Promise.all(logsToSync.map(log => 
      fetch('/api/workout-logs', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(log)
      })
    ));
    await clearSyncedLogs();
  } catch (error) {
    console.error('Error syncing workout logs:', error);
  }
} 