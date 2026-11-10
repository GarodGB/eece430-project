import test from 'node:test'
import assert from 'node:assert/strict'
import { createApi } from '../src/api/client.js'
const reply = (body, status = 200) => new Response(JSON.stringify(body), { status })

test('concurrent expired searches share one refresh and retain new token', async t => {
  let refreshes = 0
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    if (url === '/api/token/refresh/') {
      refreshes++
      assert.deepEqual(JSON.parse(options.body), { refresh: 'refresh' })
      return reply({ access: 'new' })
    }
    return options.headers.Authorization === 'Bearer old' ? reply({}, 401) : reply([])
  })
  const api = createApi('old', () => assert.fail('unexpected logout'), 'refresh')
  await Promise.all([api.medicines('a'), api.stock(), api.finder('b')])
  await api.stock()
  assert.equal(refreshes, 1)
})

test('invalid refresh expires session once', async t => {
  let expired = 0
  t.mock.method(globalThis, 'fetch', async () => reply({}, 401))
  const api = createApi('old', () => expired++, 'refresh')
  await assert.rejects(api.stock(), /session expired/)
  await assert.rejects(api.stock(), /session expired/)
  assert.equal(expired, 1)
})

test('temporary refresh failure preserves login and allows a later attempt', async t => {
  let fail = true
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    if (url === '/api/token/refresh/') {
      if (fail) throw new TypeError('offline')
      return reply({ access: 'new' })
    }
    return options.headers.Authorization === 'Bearer old' ? reply({}, 401) : reply([])
  })
  const api = createApi('old', () => assert.fail('unexpected logout'), 'refresh')
  await assert.rejects(api.stock(), /Check your connection/)
  fail = false
  assert.deepEqual(await api.stock(), [])
})

test('401 after renewal stops after one retry', async t => {
  let calls = 0
  let expired = 0
  t.mock.method(globalThis, 'fetch', async url => {
    calls++
    return url === '/api/token/refresh/' ? reply({ access: 'new' }) : reply({}, 401)
  })
  await assert.rejects(createApi('old', () => expired++, 'refresh').stock(), /session expired/)
  assert.equal(calls, 3)
  assert.equal(expired, 1)
})

test('checkout refreshes first and never replays failed sale', async t => {
  for (const status of [401, 500]) {
    const calls = []
    const mock = t.mock.method(globalThis, 'fetch', async (url, options) => {
      calls.push(url)
      if (url === '/api/token/refresh/') return reply({ access: 'new' })
      assert.equal(options.headers.Authorization, 'Bearer new')
      return reply({ detail: 'Rejected' }, status)
    })
    await assert.rejects(createApi('old', () => {}, 'refresh').sale({}))
    assert.deepEqual(calls, ['/api/token/refresh/', '/api/sales/'])
    mock.mock.restore()
  }
})

test('failed preflight sends no sale and marks it safe to try manually again', async t => {
  t.mock.method(globalThis, 'fetch', async url => {
    assert.equal(url, '/api/token/refresh/')
    return reply({}, 503)
  })
  await assert.rejects(createApi('old', () => assert.fail('unexpected logout'), 'refresh').sale({}), error => error.notSent === true)
})

test('rotated refresh tokens are used on the next renewal', async t => {
  let count = 0
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    if (url === '/api/token/refresh/') {
      assert.equal(JSON.parse(options.body).refresh, count++ ? 'rotated' : 'initial')
      return reply({ access: 'new', refresh: 'rotated' })
    }
    return reply({ id: 1 })
  })
  const api = createApi('old', () => {}, 'initial')
  await api.sale({})
  await api.sale({})
})
