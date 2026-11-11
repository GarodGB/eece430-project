export function priceCents(price) {
  const match = /^(\d+)(?:\.(\d{1,2}))?$/.exec(String(price))
  if (!match) throw new Error('Medicine price is unavailable or invalid.')
  const cents = Number(match[1]) * 100 + Number((match[2] || '').padEnd(2, '0'))
  if (!Number.isSafeInteger(cents)) throw new Error('Medicine price is too large.')
  return cents
}

export function addMedicine(cart, medicine) {
  if (!medicine.barcode) throw new Error('This medicine has no barcode and cannot be sold.')
  priceCents(medicine.price)
  const existing = cart.find(item => item.barcode === medicine.barcode)
  return existing
    ? cart.map(item => item.barcode === medicine.barcode ? { ...item, quantity: Number(item.quantity) + 1 } : item)
    : [...cart, { ...medicine, quantity: 1 }]
}

// Discount on the whole receipt, in percent: '' or 0 to 100, at most 2 decimals.
export function discountPercent(value) {
  const text = String(value ?? '').trim()
  if (text === '') return 0
  if (!/^\d{1,3}(\.\d{1,2})?$/.test(text) || Number(text) > 100) {
    throw new Error('Enter a discount between 0 and 100%.')
  }
  return Number(text)
}

export function salePayload(cart, paymentMethod, discount = 0) {
  if (!cart.length) throw new Error('Add at least one medicine to the cart.')
  if (!['cash', 'card'].includes(paymentMethod)) throw new Error('Choose cash or card.')
  const percent = discountPercent(discount)
  return {
    payment_method: paymentMethod,
    ...(percent > 0 && { discount_percent: percent.toFixed(2) }),
    items: cart.map(item => {
      const quantity = Number(item.quantity)
      if (!Number.isSafeInteger(quantity) || quantity < 1 || quantity > 2147483647) {
        throw new Error(`Enter a positive whole-number quantity for ${item.name}.`)
      }
      return { barcode: item.barcode, quantity }
    }),
  }
}

export function cartTotal(cart) {
  return cart.reduce((sum, item) => sum + priceCents(item.price) * Number(item.quantity), 0)
}

// Estimate shown on screen; the server calculates the real total at checkout.
export function discountedTotal(cents, percent) {
  return Math.round(cents * (100 - percent) / 100)
}

export const money = cents => (cents / 100).toFixed(2)
