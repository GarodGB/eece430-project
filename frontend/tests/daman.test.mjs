import test from 'node:test'
import assert from 'node:assert/strict'
import { salePayload } from '../src/api/cart.js'
import { beirutDate, damanDetails, damanSplit, statusLabel } from '../src/api/daman.js'

const panadol = { barcode: '8400001', name: 'Panadol', price: '25.00', quantity: 2, needs_prescription: false }

test('Daman pays 80% and the cents always add up', () => {
  assert.deepEqual(damanSplit(5000), { daman: 4000, customer: 1000 })
  assert.deepEqual(damanSplit(1235), { daman: 988, customer: 247 })
  assert.deepEqual(damanSplit(0), { daman: 0, customer: 0 })
})

test('a Daman sale needs only a digits-only Daman number', () => {
  assert.deepEqual(damanDetails(' 1234567 '), { daman_number: '1234567' })
  for (const number of ['', '12a', '-1', '1.5', undefined]) assert.throws(() => damanDetails(number), /digits only/)
})

test('the sale sends the Daman details only for a Daman payment', () => {
  const daman = { damanNumber: '42' }
  const insured = salePayload([panadol], 'insurance', 0, false, daman)
  assert.equal(insured.payment_method, 'insurance')
  assert.equal('patient_name' in insured, false)
  assert.equal(insured.daman_number, '42')
  const cash = salePayload([panadol], 'cash', 0, false, daman)
  assert.equal('daman_number' in cash, false)
})

test('labels and Lebanon dates', () => {
  assert.equal(statusLabel('sent'), 'Sent to Daman')
  assert.equal(statusLabel('paid'), 'Paid')
  assert.equal(beirutDate('2026-11-25T23:30:00Z'), '26 Nov 2026')
  assert.equal(beirutDate('nonsense'), '—')
})
