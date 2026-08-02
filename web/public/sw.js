const SHELL_CACHE = 'mbfd-eoc-shell-v1'
const DATA_CACHE = 'mbfd-eoc-last-rendered-v1'
const SHELL_ASSETS = ['/', '/index.html', '/mbfd-logo.jpg', '/manifest.webmanifest']

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(SHELL_CACHE).then((cache) => cache.addAll(SHELL_ASSETS)))
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => ![SHELL_CACHE, DATA_CACHE].includes(key))
            .map((key) => caches.delete(key)),
        ),
      ),
  )
  self.clients.claim()
})

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return
  const url = new URL(event.request.url)
  if (url.origin !== self.location.origin) return

  if (url.pathname.startsWith('/api/v1/')) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          if (response.ok) {
            const copy = response.clone()
            void caches.open(DATA_CACHE).then((cache) => cache.put(event.request, copy))
          }
          return response
        })
        .catch(async () => {
          const cached = await caches.match(event.request)
          if (cached) {
            const headers = new Headers(cached.headers)
            headers.set('X-EOC-Cache', 'hit')
            return new Response(cached.body, {
              status: cached.status,
              statusText: cached.statusText,
              headers,
            })
          }
          return new Response(
            JSON.stringify({
              detail: 'No cached dashboard snapshot is available.',
            }),
            {
              status: 503,
              headers: {'Content-Type': 'application/json'},
            },
          )
        }),
    )
    return
  }

  event.respondWith(
    fetch(event.request).catch(async () => {
      const cached = await caches.match(event.request)
      return cached ?? caches.match('/index.html')
    }),
  )
})
