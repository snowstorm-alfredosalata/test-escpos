# Goal
This repository implements an Odoo 19.0 expansion module (pos_it_fiscal_nonfiscal_printer) to support multiple printers per PoS config:

- Non-fiscal / Order printers (kitchen/comanda) using ESC/POS (via the Python escpos.printer.Network API)
- Fiscal printers (Protocollo Fiscale SF20 over TCP) for e‑invoicing / fiscal commands

We must preserve and reuse as much of the existing Point of Sale (point_of_sale) infrastructure as possible and provide clear, testable abstractions so future drivers can be added easily.

---

## Big-picture architecture & where to look first 🔎
- Server (models / controllers): extend `point_of_sale.models.pos_printer` (see `point_of_sale/models/pos_printer.py`) to add driver types and driver-specific configuration (ip/port, credentials, flags). Expose what the POS client needs through the `pos.load.mixin` methods (`_load_pos_data_fields/_domain`).
- Driver layer: create a `drivers/` package in `pos_it_fiscal_nonfiscal_printer` that defines a small, testable Python interface (e.g. `open_receipt`, `sell_item`, `payment`, `close_receipt` for fiscal printers; `print_order` for non-fiscal). The `example/main.py` file demonstrates the intended shape of these interfaces.
- Proxy / RPC integration: the existing PoS hardware proxy flow uses `/hw_proxy/*` RPC endpoints and `HWPrinter` client code (`point_of_sale/static/src/app/utils/printer/hw_printer.js`). Implement server-side handlers (controllers) or extend the existing IoT/Proxy so the PoS client can ask the server/proxy to perform ESC/POS and SF20 actions.
- Client (JS): add client-side logic only when necessary. Follow the existing pattern: `BasePrinter` → `HWPrinter` → specific printer classes (`epson_printer.js`) and `pos_printer_service.js` to plug into the PoS services registry.

Key files to read first (in order):
1. `point_of_sale/models/pos_printer.py` (how printers are modelled & what data is sent to the client)
2. `point_of_sale/models/pos_config.py` (how `printer_ids` and printing-related flags live on configs)
3. `point_of_sale/static/src/app/utils/printer/base_printer.js`, `hw_printer.js`, `epson_printer.js` (client-side patterns)
4. `point_of_sale/static/src/app/services/pos_printer_service.js` and `hardware_proxy_service.js` (how printing is orchestrated)
5. `example/main.py` (simple Python examples for ESC/POS and a stub fiscal implementation)

---

## Concrete agent instructions (what an AI should do first) 🤖
- Read the files listed above to internalize current responsibilities (model ↔ client data flow, proxy RPC, and error handling patterns).
- Add a minimal driver interface in `pos_it_fiscal_nonfiscal_printer/drivers/` with unit tests that mock network interactions.
- Extend `pos.printer` (via inheritance) to add new `printer_type` values (e.g. `escpos_tcp`, `sf20_tcp`) and driver-specific fields (ip, port, timeout, optional credentials). Use `_load_pos_data_fields` to ensure client receives them when starting a PoS session.
- Implement server controller endpoints to accept print requests from the PoS client or proxy (ideally reuse `/hw_proxy/default_printer_action` semantics). Write unit tests that call these controllers and assert driver behavior using mocks/stubs.
- Add at least: Python unit tests for driver logic, Python integration tests for controllers, and JS unit tests (or tours) for client-side interactions.
- Keep hardware interaction code isolated in `drivers/` and always design with dependency injection so it can be mocked (see `example/main.py` for simple stubs).

---

## Developer workflows & quick commands ⚙️
- Start an Odoo dev server with this repository included in `addons_path`:
  - Example: python3 odoo-bin -d pos_dev --addons-path=/path/to/odoo/addons,/workspaces/test-escpos --dev=assets
- Run server-side tests (module unit tests):
  - python3 odoo-bin -d test_db --test-enable -i pos_it_fiscal_nonfiscal_printer --stop-after-init
- Run the example ESC/POS script locally to validate driver logic (no Odoo required):
  - python3 example/main.py (edit `data.json` to point to a test printer or to a `nc` listener)
- Simulate a fiscal TCP device using netcat for integration tests:
  - On a terminal: nc -l -p 10000  (listen as a simple TCP sink to verify bytes)
- Debug JS client side: open PoS in the browser with `?debug=assets`, use the console logs (`pretty_console_log`) and check the `HardwareProxy` state (`localStorage.hw_proxy_url`).

---

## Project-specific patterns & conventions 🧭
- Prefer reusing existing PoS hooks and services rather than creating ad-hoc endpoints: extend `pos_printer` and `pos_config`, use the `pos.load.mixin` to send static data to clients.
- Client-side printers follow a service model: subclass `BasePrinter`, add a JS file under `static/src/app/utils/printer/`, and register any orchestration through the `printer` service (`pos_printer_service.js`).
- Isolate hardware logic in `drivers/` (Python) and provide a small interface so tests can inject fake drivers.
- Tests: follow the existing style in `point_of_sale/tests/` (unittest + mocks for Python tests). For JS, follow existing `static/tests/` and tours.

---

## Test ideas (concrete) ✅
- Unit: Mock `escpos.printer.Network` to assert that `print_order()` formats the correct bytes and calls `.text()/.cut()`/`.close()`.
- Unit: Mock a TCP socket for SF20 to ensure `open_receipt`/`sell_item`/`payment`/`close_receipt` send correctly formatted messages (check framing and checksums where applicable).
- Integration: Call controller endpoint that receives a PoS print request and assert it delegates to the correct driver and returns success/failure codes.
- Client: Add a tour that simulates a print action and asserts that the `RetryPrintPopup`/errors are shown for known failure cases.

---

If anything above is unclear or you want more concrete patches (e.g., a starter `drivers/` package, a proof-of-concept controller, or unit tests), tell me which first step to implement and I'll create the first branch with changes. Thanks — ready to iterate on wording or missing parts! 🔧