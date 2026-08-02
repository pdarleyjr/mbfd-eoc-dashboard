import {readFileSync} from 'node:fs'
import {resolve} from 'node:path'
import {runInNewContext} from 'node:vm'
import {expect, it, vi} from 'vitest'

it('service worker labels an API cache fallback for the frontend', async () => {
  const source = readFileSync(resolve(process.cwd(), 'public/sw.js'), 'utf8')
  const listeners = new Map()
  const cached = new Response(JSON.stringify({metadata: {stale: false}}), {
    status: 200,
    headers: {'Content-Type': 'application/json'},
  })
  const fetchListenerEvent = {
    request: new Request('https://eoc.example/api/v1/dashboard/summary'),
    respondWith: vi.fn(),
  }

  runInNewContext(source, {
    self: {
      addEventListener: (name, listener) => listeners.set(name, listener),
      location: {origin: 'https://eoc.example'},
    },
    caches: {
      match: vi.fn().mockResolvedValue(cached),
    },
    fetch: vi.fn().mockRejectedValue(new TypeError('offline')),
    Headers,
    Response,
    URL,
  })

  listeners.get('fetch')(fetchListenerEvent)
  expect(fetchListenerEvent.respondWith).toHaveBeenCalledOnce()
  const response = await fetchListenerEvent.respondWith.mock.calls[0][0]

  expect(response.status).toBe(200)
  expect(response.headers.get('X-EOC-Cache')).toBe('hit')
  await expect(response.json()).resolves.toEqual({metadata: {stale: false}})
})
