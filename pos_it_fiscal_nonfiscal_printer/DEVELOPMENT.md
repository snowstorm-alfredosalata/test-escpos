# pos_it_fiscal_nonfiscal_printer — DEVELOPMENT

## Goal 🎯
Provide a minimal, testable extension to Odoo's PoS that supports both non-fiscal (ESC/POS) and fiscal (SF20-like) printers while reusing Odoo's existing printer/IoT patterns (IoT Box, `epson_epos`, `hw_proxy`). The objective is to add the least possible new semantics and to fit cleanly into the existing printing flow documented in `PRINTING_FLOW.md`.

---

## Guiding principles ✅
- Reuse over reinvent: prefer adapting Odoo's IoT, `epson_epos`, and `hw_proxy` connection and proxy patterns rather than reimplementing connection management or ePOS framing.
- Minimal surface area: add only DB fields, controller endpoints, or client hooks that cannot be achieved by delegating to existing modules.
- Drivers are adapters: implement thin, well-tested adapter classes that either call existing modules/drivers (preferred) or provide small fallback implementations.
- Testability and DI: every driver should accept injected factories (`escpos_factory`, `socket_factory`, `iot_proxy`) so tests can replace network/hardware with mocks.

---

## Finalized high-level architecture 🔧

### Models (server)
- Extend `point_of_sale.models.pos_printer` minimally to support our driver options. Suggested additions (non-breaking defaults):
  - `printer_type` (selection): extend choices with `escpos_tcp`, `sf20_tcp`, `epson_epos`, `iot_box` (keep existing `epson_epos`/`iot` semantics intact).
  - `use_iot_device` (boolean): whether to prefer IoT device delegation.
  - `iot_device_id` (many2one to `iot.device`): optional device reference.
  - `host` (char), `port` (integer), `timeout` (integer, seconds): optional direct connection fallbacks for TCP drivers.
  - Credentials (optional): `username`/`password` if any drivers need them (keep optional and encrypted where appropriate).
- Ensure these fields are returned to PoS clients by updating `_load_pos_data_fields` and `_load_pos_data_domain` so clients and server controllers have the data they need.
- Migration note: existing `epson_printer_ip` remains supported; prefer mapping existing records to `epson_epos` type on upgrade.

### Drivers (adapter pattern)
- Location: `pos_it_fiscal_nonfiscal_printer/drivers/`
- Files & responsibilities:
  - `base.py`: small interface (abstract BaseDriver) + exceptions + factory helper + `create_driver(printer_record, factories)`.
  - `epson_adapter.py`: lightweight adapter that delegates to `epson_epos` logic or the IoT proxy, e.g., call existing ePOS helper code or forward to `iot.device` RPC.
  - `escpos_tcp.py`: adapter for ESC/POS over TCP — support two modes:
    - Direct: use injected `escpos_factory` to create `Network(ip, port)` and call `text`, `cut`, `close`.
    - Proxy: forward a `print_order` action to an IoT proxy endpoint (if `use_iot_device` is set) so the IoT box performs the TCP-level work.
  - `sf20_tcp.py`: fiscal adapter implementing minimal lifecycle methods: `open_receipt`, `sell_item`, `apply_payment`, `close_receipt`, and `status`.
- Driver API contract (concise):
  - Non-fiscal: driver.print_order(order_data, timeout=None) -> {status: 'ok'|'error', message: str, details: dict}
  - Fiscal: methods as above; each returns a structured dict and may raise DriverError for known failure modes.
- Every driver must be covered by unit tests that mock sockets or `escpos.printer.Network`.

### Controllers & RPC semantics
- Primary goal: reuse PoS/IoT proxy semantics instead of inventing new ones.
- Implement a small controller in this module to expose a server-side printing endpoint that mirrors `/hw_proxy/*` names but acts on server-accessible printers. Suggested route(s):
  - POST `/hw_proxy/printer_action` — input: { printer_id, action, payload?, timeout? }
  - Or reuse `/hw_proxy/default_printer_action` semantics if integration with existing proxy code is preferable.
- Controller responsibilities:
  1. Validate access (user belongs to PoS groups or request originates from a trusted service). Confirm `printer.company_id` matches caller's company unless processed by IoT integration.
  2. Resolve the `pos.printer` record and instantiate the correct driver adapter (or forward to IoT device if requested).
  3. Execute the action with a configurable timeout and return a structured result: { status: 'ok'|'error', message?: str, details?: dict, canRetry?: bool, warningCode?: str }.
  4. Keep work short and synchronous: printing should return quickly; if a particular printer type requires long-running work, queue it or return an informative error and a retry suggestion.
- Security and access control: restrict controller access (`@http.route` access rules) and validate ownership/company.

### Client (JS) integration
- Minimal changes: prefer server-side orchestration; keep PoS client flows untouched.
- Existing client flow to reuse:
  - `hardware_proxy_service` (takes care of proxy discovery & keepalive).
  - `pos_printer_service` / `printer_service` (orchestrates calls, popups, retries).
  - `BasePrinter` / `HWPrinter` (convert DOM to image and call proxy endpoints).
- If a server-side print endpoint is added, only small client hooks (optional) are needed to call it directly instead of forwarding to the local IoT Box.

---

## Reporting & PRINTING_FLOW.md
- `PRINTING_FLOW.md` (copied into the module) documents the canonical end-to-end printing path and the exact fields and templates used for receipts and order-change/kitchen prints. Use it as the authoritative reference to decide which data the drivers receive (`orderData`, `changes`, `line items`).

---

## Testing strategy ✅
- Unit tests (fast):
  - Drivers: mock `escpos.printer.Network`, socket operations, or IoT proxies; assert bytes sent (text, cut, close) and that methods return structured results.
  - Fiscal driver: mock TCP sockets, assert message framing and checksums for `sf20_tcp` lifecycle methods.
  - Adapter behavior: test delegation to `epson_epos` functions or IoT RPC calls using mocks.
  - Controller: call endpoints with mocked drivers to assert routing, errors, and timeouts.
- Integration tests (optional heavier):
  - Use `nc -l -p 10000` to simulate a raw TCP sink and verify bytes received by `escpos_tcp` or `sf20_tcp` adapters.
  - Use a lightweight HTTP test double to simulate the IoT Box `/hw_proxy/*` endpoints.
- Client tests:
  - Unit tests for `pos_printer_service` and `hardware_proxy_service` interactions.
  - Tours / e2e tests that simulate printing (show retry popups for failure cases) if desired.

---

## Security & production considerations ⚖️
- Always sanitize and validate payloads before sending them to hardware devices.
- Restrict controller access by group and company.
- Use timeouts and clear error messages; `canRetry` flags should be returned to the client to drive retry logic.
- Fiscal drivers may require certification; shipping a protocol implementation should include clear warnings and tests, and not be considered legally-certified code.

---

## Prioritized implementation checklist (concrete) 📋
1. Audit: inspect `epson_epos`, `hw_proxy`, and IoT modules to identify functions/APIs we can call instead of implementing ourselves (low effort, high value). (Priority: HIGH)
2. Drivers scaffolding: add `drivers/base.py`, `drivers/epson_adapter.py` and tests for delegation (low risk). (Priority: HIGH)
3. Implement `drivers/escpos_tcp.py` with DI and unit tests mocking `escpos.printer.Network`. (Priority: HIGH)
4. Add `drivers/sf20_tcp.py` stub with tests for message framing (Priority: MEDIUM)
5. Extend `models/pos_printer.py` with minimal fields (`printer_type`, `use_iot_device`, `iot_device_id`, host/port/timeout) and include them in `_load_pos_data_fields`. Provide a migration note for `epson_printer_ip`. (Priority: MEDIUM)
6. Implement `controllers/hw_proxy.py` exposing `/hw_proxy/printer_action` (or an additive route) and write controller tests for delegation and error handling. (Priority: MEDIUM)
7. Add end-to-end integration tests and small JS service adjustments if client-side needs to call the server endpoint directly. (Priority: LOW)

---

## Example controller contract (reference)
- Incoming JSON: { printer_id: int, action: "print_order"|"open_receipt"|..., payload: dict|string, timeout: seconds }
- Response: { status: 'ok'|'error', message?: str, details?: dict, canRetry?: bool }

---

If you like, I can start right away with the audit (task 1) and then implement the `epson_adapter` and its tests (task 2). Which task shall I begin? 🔧