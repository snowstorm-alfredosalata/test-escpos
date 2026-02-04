# Point of Sale — Printing: end-to-end report 📄

This document describes how printing currently works in Odoo's `point_of_sale` app (receipt printing, kitchen/order printing, and device interactions). It covers:

- how order and order-line data are prepared and sent to the client,
- which client templates/components render receipts,
- where and how printing is initiated,
- how print jobs reach printers (IoT Box / Hardware Proxy / Epson direct), and
- the main code locations to inspect.

---

## Quick summary (one-liner) ✅
- PoS prepares order data on the server (via the pos.load.mixin read helpers), the frontend renders receipt HTML (OWL templates) using client-side `pos.order` and `pos.order.line` model objects, and the resulting DOM is converted to an image and sent to a device using either the IoT hardware proxy (`/hw_proxy/*`) or directly to network printers (e.g. Epson `ePOS`).

---

## 1) Where order + line data come from (server → client)

- Server-side models use the `pos.load.mixin` helpers to explicitly expose data to the client. The mixin calls:
  - `pos.config` triggers loading of many related models; see `point_of_sale/models/pos_config.py`.
  - `pos.order` _and_ `pos.order.line` are loaded via `pos.order._load_pos_data_read()` which calls `env['pos.order.line']._load_pos_data_read(this_order.lines, config)`.

- Key server files to inspect:
  - `point_of_sale/models/pos_order.py` (pos.order read logic and `pos.order` _load helpers)
  - `point_of_sale/models/pos_order.py` (pos.order.line `_load_pos_data_fields`) — the fields exposed for each order line are:

    - 'qty', 'attribute_value_ids', 'custom_attribute_value_ids', 'price_unit',
    - 'uuid', 'price_subtotal', 'price_subtotal_incl', 'order_id', 'note', 'price_type',
    - 'product_id', 'discount', 'tax_ids', 'pack_lot_ids', 'customer_note',
    - 'refunded_qty', 'price_extra', 'full_product_name', 'refunded_orderline_id',
    - 'combo_parent_id', 'combo_line_ids', 'combo_item_id', 'refund_orderline_ids',
    - 'extra_tax_data', 'write_date'

  - `point_of_sale/models/pos_printer.py` (printer records, `_load_pos_data_fields` returns `['id','name','proxy_ip','product_categories_ids','printer_type','epson_printer_ip']`)

- The client receives these entities and constructs client-side models found in `point_of_sale/static/src/app/models/` (`pos_order.js`, `pos_order_line.js`). These client models compute derived properties used by receipt templates (e.g., formatted quantities, computed totals, currency display values, `full_product_name` conversions, tax labels, etc.).

---

## 2) How receipts are rendered in the client (HTML path)

- Frontend templates and components:
  - `OrderReceipt` (OWL component) — `point_of_sale/static/src/app/screens/receipt_screen/receipt/order_receipt.js` uses `point_of_sale.OrderReceipt` template.
  - `Orderline` component renders each order line (`Orderline` component in `components/orderline/orderline.js`).
  - For order change / kitchen prints, `OrderChangeReceipt` template is used (`point_of_sale/static/src/app/store/order_change_receipt_template.xml`).

- Rendering flow:
  1. PoS store prepares an object describing the order (see `getOrderData()` and `generateOrderChange()` in `point_of_sale/static/src/app/services/pos_store.js`). For preparation printing, it builds `orderData` + `changes` arrays.
  2. The service calls `renderToElement("point_of_sale.OrderChangeReceipt", { data })` or uses `OrderReceipt` component for regular receipts.
  3. The produced DOM (HTML / element) is passed to the printer service, which converts it to a canvas/image using `htmlToCanvas` (`BasePrinter.printReceipt` uses `htmlToCanvas(receipt)`).

- Note: The rendering step uses client models and templates so the printed content is exactly what a user sees in the receipt/presenter UI.

---

## 3) Where/when printing is initiated (user & automatic triggers)

- User-initiated:
  - The user clicks the Print button on `ReceiptScreen` (UI) and the store executes `pos.printReceipt({ order })` (`point_of_sale/static/src/app/services/pos_store.js::printReceipt`).

- Automatic / preparation (kitchen) printing:
  - When orders change and there are preparation printers configured, `sendOrderInPreparation()` is called (e.g., when an order is created/updated or synced). It calls `printChanges()` which groups modifications and calls `printOrderChanges()` → rendering → `printer.printReceipt()`.

- Receipt printing calls through the printer service which chooses the active device:
  - `pos_printer_service` / `printer_service` orchestrate printing. The default device is provided by the `HardwareProxy` (`hardware_proxy.printer`). See `point_of_sale/static/src/app/services/pos_printer_service.js` and `hardware_proxy_service.js`.

---

## 4) How the print job reaches the printer (protocols / endpoints)

- Generic flow (most common):
  - Frontend converts DOM to an image (BasePrinter.processCanvas) and calls `sendPrintingJob(image)`.
  - The `HWPrinter` implementation sends an RPC to the local proxy:
    - `rpc(
        `${this.url}/hw_proxy/default_printer_action`,
        { data }
      )` — where `data` is { action: 'print_receipt', receipt: image }
  - The local proxy / IoT Box receives the call at `/hw_proxy/default_printer_action` and performs the final hardware interaction (this proxy implementation lives outside core PoS in the IoT Box / proxy server code).

- Epson direct (networked ePOS):
  - Client can talk directly to an Epson receipt printer using the `EpsonPrinter` class (sends a `POST` to `/cgi-bin/epos/service.cgi?devid=local_printer`) using the printer's IP and the ePOS XML format (see `point_of_sale/static/src/app/utils/printer/epson_printer.js`).

- Device-side or server-side alternative: Odoo can also be extended with server controllers (e.g., `hw_proxy.py` server-side helpers) to accept print actions server-side and forward them to drivers (this repository plans to add server adapters so server-driven printing is possible). The canonical client proxy endpoint remains `/hw_proxy/*`.

---

## 5) Special notes about order-lines & the reporting engine

- The terminal "reporting engine" for PoS receipts is essentially the OWL templates (`OrderReceipt`, `OrderChangeReceipt`) fed with client models (`pos.order`, `pos.order.line`). The server side prepares domain objects and serializes minimal fields; the client enriches them with computed fields.

- The server decides which columns to send (via `_load_pos_data_fields`) to limit payload. Client-side `pos.order.line` computes additional values such as quantity strings, display price, totals, tax labels, product attribute strings, and `full_product_name`.

- For kitchen printing, the store computes `orderChange` objects using differences between `last_order_preparation_change` and current order state, then groups lines by product/category where necessary and renders the `OrderChangeReceipt` template. That means kitchen printers receive only the deltas (new/cancelled/note updates) prepared by JavaScript.

---

## 6) Key files & entry points (quick map) 🔎

- Server models & data load
  - `point_of_sale/models/pos_printer.py` (printer record + `_load_pos_data_fields`)
  - `point_of_sale/models/pos_config.py` (config + `printer_ids`, printing-related flags)
  - `point_of_sale/models/pos_order.py` (how orders & order lines are read/sent to client; field lists)

- Client models & rendering
  - `point_of_sale/static/src/app/models/pos_order.js`
  - `point_of_sale/static/src/app/models/pos_order_line.js`
  - `point_of_sale/static/src/app/screens/receipt_screen/receipt/order_receipt.js` (OrderReceipt)
  - `point_of_sale/static/src/app/screens/receipt_screen/receipt/order_receipt.xml` template
  - `point_of_sale/static/src/app/store/order_change_receipt_template.xml` (kitchen/order change template)

- Printer orchestration & transport
  - `point_of_sale/static/src/app/services/pos_store.js` (print flow for orders and order-changes)
  - `point_of_sale/static/src/app/services/pos_printer_service.js` (printer service)
  - `point_of_sale/static/src/app/services/hardware_proxy_service.js` (connects to hardware proxy)
  - `point_of_sale/static/src/app/utils/printer/base_printer.js` (image conversion queue)
  - `point_of_sale/static/src/app/utils/printer/hw_printer.js` (RPC to `/hw_proxy/*` endpoints)
  - `point_of_sale/static/src/app/utils/printer/epson_printer.js` (direct Epson network printing using ePOS)

- Proxy endpoints (used by client):
  - `/hw_proxy/default_printer_action` (client → proxy RPC) — proxy must provide handlers (outside core PoS); `HWPrinter` calls it with `{ action: 'print_receipt', receipt: <base64 image> }`.

---

## 7) Where to look / what to change if you want server-driven printing

- Add lightweight controllers (e.g., `pos_it_fiscal_nonfiscal_printer/controllers/hw_proxy.py`) that replicate `default_printer_action` semantics and delegate to a driver registry.
- Reuse established abstractions: prefer delegating to `epson_epos` or IoT modules (do not invent a new RPC vocabulary unless strictly necessary).
- Keep hardware logic isolated (drivers/adapters) and make them dependency-injectable for unit tests.

---

If you want, I can turn this into a short `docs/PRINTING_FLOW.md` file inside `pos_it_fiscal_nonfiscal_printer/` as well (with notes on how our extension should integrate). Do you want that copied to the `pos_it_fiscal_nonfiscal_printer` folder too? ✨