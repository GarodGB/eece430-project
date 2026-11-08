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

export function salePayload(cart, paymentMethod) {
  if (!cart.length) throw new Error('Add at least one medicine to the cart.')
  if (!['cash', 'card'].includes(paymentMethod)) throw new Error('Choose cash or card.')
  return {
    payment_method: paymentMethod,
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

export const money = cents => (cents / 100).toFixed(2)
