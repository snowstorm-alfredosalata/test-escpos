# Driver registry for pos_it_fiscal_nonfiscal_printer
from .base import BaseDriver
from .escpos_tcp import EscposTCPDriver
from .epson_adapter import EpsonAdapter
from .sf20_tcp import SF20Driver

DRIVERS = {
    'escpos_tcp': EscposTCPDriver,
    'epson_epos': EpsonAdapter,
    'sf20_tcp': SF20Driver,
}


def get_driver(printer, env, **kwargs):
    """Return an instantiated driver for the given `pos.printer` record.

    Raises ValueError when no driver is available for this printer type.
    """
    driver_type = getattr(printer, 'printer_type', None) or 'iot'
    cls = DRIVERS.get(driver_type)
    if not cls:
        raise ValueError(f"No driver for type {driver_type}")
    return cls(printer=printer, env=env, **kwargs)
