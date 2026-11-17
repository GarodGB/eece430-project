import test from 'node:test'
import assert from 'node:assert/strict'
import { prescriptionItems, salePayload } from '../src/api/cart.js'

const panadol = { barcode: '8100002', name: 'Panadol', price: '4.00', quantity: 1, needs_prescription: false }
const augmentin = { barcode: '8100001', name: 'Augmentin', price: '12.00', quantity: 1, needs_prescription: true }

test('finds the medicines that need a prescription', () => {
  assert.deepEqual(prescriptionItems([panadol, augmentin]).map(item => item.name), ['Augmentin'])
})

test('a normal cart needs no confirmation and sends no flag', () => {
  assert.equal('prescription_confirmed' in salePayload([panadol], 'cash'), false)
})

test('a prescription cart is blocked until confirmed', () => {
  assert.throws(() => salePayload([panadol, augmentin], 'cash'), /prescription for: Augmentin/)
})

test('a confirmed prescription cart sends the flag', () => {
  assert.equal(salePayload([augmentin], 'cash', 0, true).prescription_confirmed, true)
})
