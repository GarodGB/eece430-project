import test from 'node:test'
import assert from 'node:assert/strict'
import { discountPercent, discountedTotal, salePayload } from '../src/api/cart.js'

const cart = [{ barcode: '8000001', name: 'Panadol', price: '4.00', quantity: 2 }]

test('empty or zero discount is not sent', () => {
  assert.deepEqual(salePayload(cart, 'cash', ''), { payment_method: 'cash', items: [{ barcode: '8000001', quantity: 2 }] })
  assert.equal('discount_percent' in salePayload(cart, 'cash', '0'), false)
})

test('a valid discount is sent with 2 decimals', () => {
  assert.equal(salePayload(cart, 'cash', '10').discount_percent, '10.00')
  assert.equal(salePayload(cart, 'cash', '46.15').discount_percent, '46.15')
})

test('invalid discounts are rejected before sending', () => {
  for (const value of ['-5', '101', 'abc', '10.555', '1e2']) {
    assert.throws(() => discountPercent(value), /between 0 and 100/)
  }
})

test('discounted total estimate', () => {
  assert.equal(discountedTotal(1300, 10), 1170)
  assert.equal(discountedTotal(1300, 0), 1300)
})
