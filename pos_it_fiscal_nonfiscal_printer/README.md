# pos_it_fiscal_nonfiscal_printer

A small Odoo module to add multi-printer support for PoS setups: non-fiscal (ESC/POS) and fiscal (Protocollo Fiscale SF20) printers. It keeps most of Odoo's `point_of_sale` infrastructure, adding drivers and server-side handlers so printers can be configured per PoS and invoked from the PoS client or a hardware proxy.

## Features ✅
- Add multiple printers per PoS config (kitchen/order and fiscal).
- Support for ESC/POS (networked `escpos.printer.Network`) for non-fiscal receipts/orders.
- Support for SF20-like fiscal printers over TCP for fiscal commands.
- Isolated, testable driver interfaces so hardware interactions are mockable.
- Server controller endpoints compatible with PoS proxy semantics.

## Quick start ⚡
1. Install the module in your Odoo addons path and enable it in Apps.
2. In the PoS configuration, add printers and set `printer_type` (`escpos_tcp` or `sf20_tcp`) with host/port and any needed flags.
3. Start an Odoo server (see `example/main.py` to exercise drivers without Odoo).

Example to test a network sink locally (for integration/manual tests):

- Start a TCP sink: `nc -l -p 10000` and point an `escpos_tcp` or `sf20_tcp` printer at `localhost:10000`.
- Run `python3 example/main.py` and inspect bytes arriving on the sink.

## Where to look 🔎
- Examples: `example/main.py`
- Driver implementations: `pos_it_fiscal_nonfiscal_printer/drivers/` (driver interface + per-protocol drivers)
- Models: `pos_it_fiscal_nonfiscal_printer/models/` (extensions to `pos.printer`/`pos.config`)
- Controllers: server RPC bodies to accept print requests and delegate to drivers
- Tests: add unit tests that mock network interactions and controller integration tests

## Constraints & notes ⚠️
- Hardware logic is intentionally isolated in `drivers/` to make unit testing easy and safe.
- Fiscal protocol implementations may require compliance review for production use; this module provides the plumbing and test harness, not certified fiscal firmware.

## Contributing 🙌
- Add drivers by following the driver interface in `drivers/` and add unit tests mocking sockets or `escpos` classes.
- Add controller tests to assert requests are correctly delegated and errors are handled gracefully.

---

For development details and design rationale see `DEVELOPMENT.md`.