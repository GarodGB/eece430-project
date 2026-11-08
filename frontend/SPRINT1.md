# Sprint 1 frontend integration

The existing layout, sidebar, colors, login styling, cards, and contact dialog are retained. AI and prediction remain explicitly labelled previews; reports and insurance remain deferred.

## API contracts used

- `POST /api/login/` and `GET /api/me/`: existing JWT login. Role and pharmacy come exclusively from `/api/me/`. Tokens remain in memory. Logout clears the session; any authenticated 401 returns to login with an expiry message. No automatic sale retry or token refresh.
- `GET /api/stock/`: batch ID, medicine name, quantity, reorder level, expiry date, low-stock and expiry flags. Current settings do not enable pagination; the frontend supports both arrays and DRF `results`/`next` pagination for stock, medicine search, and Finder.
- `GET /api/medicines/?search=...`: name, generic name, or barcode search. An exact barcode match adds to the cart, preserving leading zeros. A keyboard-wedge scanner can enter its barcode and Enter in the search field; camera scanning is not implemented.
- `POST /api/sales/`: `{ "payment_method": "cash", "items": [{ "barcode": "00123", "quantity": 2 }] }`. The frontend offers cash/card, validates positive integer quantities, merges repeated scans, and calculates display totals in cents. The server remains authoritative for price and unexpired stock. On success the cart clears and stock reloads. Card is only a recorded payment method, not payment processing.
- `GET /api/finder/?q=...`: returns `{ pharmacy: { id, name, address, phone, latitude, longitude }, medicine, available }`. Results and contact details use these fields only. Directions use valid supplied coordinates. No invented distances, opening hours, quantities, or update timestamps.

## Backend/product follow-up

1. Specify and enforce the role-permission matrix. Current endpoints use global `IsAuthenticated`; there are no role-specific permissions. The frontend does not invent role gates. Checkout requires pharmacy membership because the sale endpoint explicitly requires it.
2. Stock for superusers includes all pharmacies, but the serializer omits pharmacy identity. The frontend cannot label those batches by pharmacy. Clarify the intended admin inventory view.
3. Finder has no radius/location filtering, distance ordering, opening hours, quantities, or update timestamps. Its `medicine` field is a name rather than a stable ID, which can be ambiguous for duplicate names.
4. Network sharing cannot be read or updated via the available API. The former local-only toggle is disabled and status is shown as unknown.
5. Sales have no idempotency key or sale lookup/list route. After a network/server failure the UI locks checkout and asks the user to verify the outcome before retrying or clearing the cart. Backend idempotency and reconciliation are needed for reliable recovery. The sale transaction also does not lock stock rows, so concurrent checkouts may race; backend ownership is unchanged.
6. `needs_prescription` is displayed, but there is no prescription validation workflow in the sale contract. Currency is not supplied; the existing dollar display is retained. Confirm currency and prescription requirements with the team.
7. Logout clears this browser's in-memory session; no server logout/revocation route exists. Reloading requires login again.

## Checks

- `npm run build`
- `npm run lint`
- `node --test tests/sprint1.test.mjs` (all requests mocked; never calls the local database)

Manual acceptance: log in, check real role/pharmacy, browse Inventory, search by name, enter/scan an exact barcode, edit/remove quantities, and check Finder contacts. Only perform a real checkout when you intend to record a sale. Sale validation/failure tests use mocks.
