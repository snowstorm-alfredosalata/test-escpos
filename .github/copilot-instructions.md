This repositori aims to create an Odoo 19.0 compatible expansion module for the point_of_sale that allows to configure multiple printers for the same point of sale:
- Non-fiscal/Order printer, receiving only order information (products, table, quantities, notes etc.)
- Fiscal printer, receiving relevant information for italian e-invoicing (products, tables, quantities, notes, tax information etc.)

For the Non-fiscal printer, we need to support a escpos driver, using the escpos.printer library.
For the fiscal printer, we need to support a driver Protocollo Fiscale SF20 TCP.

In any case, we need to scaffold with proper abstractions for more drivers down the line

Under point_of_sale, the standard odoo module has been added for context and reference. The final module should be placed in pos_it_fiscal_nonfiscal_printer.

We want to reuse existing odoo infrastructure AS MUCH AS POSSIBLE, including existing models and views for printers, configurations, etc.
To do this we need a proper in depth analisis of the existing point_of_sale module, and how it manages printers and printing tasks.