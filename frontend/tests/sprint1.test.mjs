import test from 'node:test'
import assert from 'node:assert/strict'
import { createApi, apiPath } from '../src/api/client.js'
import { addMedicine, cartTotal, money, salePayload } from '../src/api/cart.js'

const medicine = { id: 1, name: 'Test medicine', barcode: '00123', price: '0.10' }
const reply = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

test('barcode scans merge quantities, preserving leading zeros and exact decimal totals', () => {
  let cart = addMedicine([], medicine)
  cart = addMedicine(cart, medicine)
  cart = addMedicine(cart, { ...medicine, barcode: '456', price: '0.20' })
  assert.equal(cart.length, 2)
  assert.equal(cart[0].quantity, 2)
  assert.equal(money(cartTotal(cart)), '0.40')
  assert.deepEqual(salePayload(cart, 'card'), { payment_method: 'card', items: [{ barcode: '00123', quantity: 2 }, { barcode: '456', quantity: 1 }] })
})

test('quantity edits and removals produce the correct checkout payload', () => {
  let cart = addMedicine(addMedicine([], medicine), { ...medicine, barcode: '456' })
  cart = cart.map(item => ({ ...item, quantity: '3' })).filter(item => item.barcode === '00123')
  assert.deepEqual(salePayload(cart, 'cash').items, [{ barcode: '00123', quantity: 3 }])
})

test('empty carts, invalid quantities, missing barcodes, and invalid prices are rejected', () => {
  assert.throws(() => salePayload([], 'cash'), /at least one/)
  for (const quantity of ['', 0, -1, 1.5, 'abc', 2147483648]) assert.throws(() => salePayload([{ ...medicine, quantity }], 'cash'), /whole-number/)
  assert.throws(() => salePayload([{ ...medicine, quantity: 1 }], 'insurance'), /cash or card/)
  assert.throws(() => addMedicine([], { ...medicine, barcode: '' }), /barcode/)
  assert.throws(() => addMedicine([], { ...medicine, price: null }), /price/)
})

test('stock pagination follows proxy-safe absolute next links and includes every batch', async t => {
  const calls = []
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    calls.push(url)
    assert.equal(options.headers.Authorization, 'Bearer mock-token')
    return reply(calls.length === 1 ? { results: [{ id: 1, quantity: 4, expiry_date: '2027-01-01' }], next: 'http://localhost:8000/api/stock/?page=2' } : { results: [{ id: 2, quantity: 5, expiry_date: '2027-02-01' }], next: null })
  })
  const rows = await createApi('mock-token', () => {}).stock()
  assert.deepEqual(calls, ['/api/stock/', '/api/stock/?page=2'])
  assert.equal(rows.length, 2)
  assert.equal(rows[1].expiry_date, '2027-02-01')
})

test('unpaginated empty stock is supported', async t => {
  t.mock.method(globalThis, 'fetch', async () => reply([]))
  assert.deepEqual(await createApi('mock-token', () => {}).stock(), [])
})

test('search and Finder use their actual distinct query parameters', async t => {
  const calls = []
  t.mock.method(globalThis, 'fetch', async url => { calls.push(url); return reply([]) })
  const api = createApi('mock-token', () => {})
  await api.medicines('A & B')
  await api.finder('00123')
  assert.deepEqual(calls, ['/api/medicines/?search=A%20%26%20B', '/api/finder/?q=00123'])
})

test('mock checkout sends only the contracted payload and stock can be refreshed afterward', async t => {
  const calls = []
  const payload = salePayload(addMedicine([], medicine), 'cash')
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    calls.push(url)
    if (url === '/api/sales/') {
      assert.equal(options.method, 'POST')
      assert.deepEqual(JSON.parse(options.body), payload)
      return reply({ id: 42, total: '0.10', items: [] }, 201)
    }
    assert.equal(url, '/api/stock/')
    return reply([{ id: 1, quantity: 3 }])
  })
  const api = createApi('mock-token', () => {})
  const sale = await api.sale(payload)
  const stock = await api.stock()
  assert.equal(sale.id, 42)
  assert.equal(stock[0].quantity, 3)
  assert.deepEqual(calls, ['/api/sales/', '/api/stock/'])
})

test('insufficient stock is surfaced and a failed sale is never retried automatically', async t => {
  let count = 0
  t.mock.method(globalThis, 'fetch', async () => { count++; return reply(['Not enough Test medicine (0 left).'], 400) })
  await assert.rejects(createApi('mock-token', () => {}).sale({}), /Not enough Test medicine/)
  assert.equal(count, 1)
})

test('401 expires a session once, while permission errors do not log the user out', async t => {
  let expired = 0
  const api = createApi('mock-token', () => expired++)
  const fetchMock = t.mock.method(globalThis, 'fetch', async () => reply({ detail: 'Forbidden' }, 403))
  await assert.rejects(api.stock(), /Forbidden/)
  assert.equal(expired, 0)
  fetchMock.mock.mockImplementation(async () => reply({ detail: 'Expired token' }, 401))
  await assert.rejects(api.stock(), /session expired/)
  await assert.rejects(api.stock(), /session expired/)
  assert.equal(expired, 1)
})

test('network and unreadable responses are identified as uncertain outcomes', async t => {
  const fetchMock = t.mock.method(globalThis, 'fetch', async () => { throw new TypeError('network') })
  await assert.rejects(createApi('mock-token', () => {}).sale({}), error => error.status === 0)
  fetchMock.mock.mockImplementation(async () => new Response('not JSON', { status: 200 }))
  await assert.rejects(createApi('mock-token', () => {}).sale({}), /unreadable/)
})

test('pagination cannot leak bearer tokens to other origins or loop indefinitely', async t => {
  assert.throws(() => apiPath('https://example.com/api/stock/'), /unsupported/)
  assert.throws(() => apiPath('/admin/'), /unsupported/)
  t.mock.method(globalThis, 'fetch', async () => reply({ results: [], next: '/api/stock/' }))
  await assert.rejects(createApi('mock-token', () => {}).stock(), /repeated/)
})

test('cancelled requests preserve AbortError for unmounted searches', async t => {
  t.mock.method(globalThis, 'fetch', async () => { throw new DOMException('Aborted', 'AbortError') })
  await assert.rejects(createApi('mock-token', () => {}).medicines('x'), { name: 'AbortError' })
})
