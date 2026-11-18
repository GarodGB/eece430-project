import test from 'node:test'
import assert from 'node:assert/strict'
import { formatMargin, formatMoney, isLoss, profitBarWidth, shortDate, weekLabel } from '../src/api/reports.js'

test('dates are shown short and never shifted by time zone', () => {
  assert.equal(shortDate('2026-11-16'), 'Nov 16')
  assert.equal(shortDate('2026-01-01'), 'Jan 1')
  assert.equal(weekLabel({ week_start: '2026-12-28', week_end: '2027-01-03' }), 'Dec 28 – Jan 3')
})

test('money keeps the server value and shows losses with a minus', () => {
  assert.equal(formatMoney('13.00'), '$13.00')
  assert.equal(formatMoney('0.00'), '$0.00')
  assert.equal(formatMoney('-2.00'), '-$2.00')
  assert.equal(formatMoney(null), '—')
  assert.equal(formatMoney('abc'), '—')
})

test('margin is empty when nothing was sold', () => {
  assert.equal(formatMargin('46.15'), '46.15%')
  assert.equal(formatMargin(null), '—')
})

test('loss detection', () => {
  assert.equal(isLoss('-2.00'), true)
  assert.equal(isLoss('6.00'), false)
  assert.equal(isLoss(null), false)
})

test('profit bars compare with the best week', () => {
  const weeks = [{ profit: '10.00' }, { profit: '5.00' }, { profit: '-2.50' }, { profit: '0.00' }]
  assert.deepEqual(weeks.map(w => profitBarWidth(w.profit, weeks)), [100, 50, 25, 0])
  assert.equal(profitBarWidth('0.00', [{ profit: '0.00' }]), 0)
})
