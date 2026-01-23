# -*- coding: utf-8 -*-
"""
Example: Simple POS Receipt Integration

This example demonstrates how to integrate fiscal printer printing
directly into POS order processing.
"""

# EXAMPLE 1: Print receipt after payment
# Add this to POS order_paid signal handler

def on_order_paid(order):
    """
    Called when order is fully paid
    Sends receipt to fiscal printer
    """
    from odoo import http
    from odoo.http import request
    
    # Get POS config
    pos_config = request.env['pos.config'].browse(order.session_id.config_id.id)
    
    if not pos_config.fiscal_printer_enabled:
        return
    
    # Build receipt data
    receipt_data = {
        'items': [],
        'payments': [],
    }
    
    # Add items
    for line in order.lines:
        receipt_data['items'].append({
            'description': line.product_id.name[:40],
            'quantity': line.qty,
            'unit_price': line.price_unit,
            'tax_percent': line.tax_id.amount if line.tax_id else 0,
        })
    
    # Add payments
    for payment in order.payment_ids:
        payment_type = 'cash'
        if payment.payment_method_id.name.lower() in ['carta', 'card', 'credit']:
            payment_type = 'card'
        
        receipt_data['payments'].append({
            'type': payment_type,
            'amount': payment.amount,
        })
    
    # Print fiscal receipt via API
    print_fiscal_receipt(
        pos_config_id=pos_config.id,
        receipt_data=receipt_data
    )


# EXAMPLE 2: Print comanda to kitchen printer

def on_order_line_added(order, line):
    """
    Called when order line is added
    Sends comanda to kitchen printer
    """
    from odoo import http
    from odoo.http import request
    
    pos_config = request.env['pos.config'].browse(order.session_id.config_id.id)
    
    if not pos_config.nonfiscal_printer_enabled:
        return
    
    # Build comanda for this item
    comanda_data = {
        'order_number': order.name,
        'table': getattr(order, 'table_id', None) and order.table_id.name or 'No Table',
        'timestamp': str(datetime.now().time()),
        'items': [
            {
                'description': line.product_id.name,
                'quantity': line.qty,
                'notes': line.note or '',
            }
        ],
        'header': 'COMANDA CUCINA',
        'footer': 'Grazie',
    }
    
    # Print comanda
    print_comanda(
        pos_config_id=pos_config.id,
        order_data=comanda_data,
        auto_cut=pos_config.comanda_auto_cut,
    )


# EXAMPLE 3: Execute Z report at end of session

def on_session_close(session):
    """
    Called when POS session closes
    Executes Z report on fiscal printer
    """
    from odoo import http
    from odoo.http import request
    
    pos_config = session.config_id
    
    if not pos_config.fiscal_printer_enabled:
        return
    
    try:
        # Check if fiscal receipt count > 0
        if session.fiscal_receipts_count > 0:
            # Execute Z report
            response = execute_z_report(pos_config_id=pos_config.id)
            
            if response['success']:
                session.fiscal_z_report_printed = True
                session.fiscal_z_report_timestamp = datetime.now()
                print(f"✓ Z Report eseguito con successo")
            else:
                print(f"✗ Errore Z Report: {response['message']}")
    except Exception as e:
        print(f"✗ Errore during session close: {str(e)}")


# EXAMPLE 4: Frontend - Handling printer status in POS

# In POS JavaScript code
def setup_printer_monitoring():
    """
    Setup printer status monitoring in POS UI
    """
    javascript_code = """
    // In POS module init
    
    const pos = this.env.pos;
    const fiscalService = this.env.services.fiscal_printer_service;
    const comandaService = this.env.services.comanda_printer_service;
    
    // Monitor fiscal printer
    setInterval(async () => {
        const status = await fiscalService.getStatus();
        updateUI('fiscal-status', status);
        
        if (status.status === 'error') {
            showWarning('Fiscal printer error: ' + status.message);
        }
    }, 30000);  // Check every 30 seconds
    
    // Before closing order
    async function processOrderPayment(order) {
        // Print to fiscal printer
        const receiptData = fiscalService.buildReceiptData(order);
        const fiscal_result = await fiscalService.printReceipt(receiptData);
        
        if (!fiscal_result.success && !fiscal_result.fail_safe_triggered) {
            // Fail-strict mode - block order
            showError('Cannot print fiscal receipt');
            return false;
        }
        
        // Print comanda
        const comandaData = comandaService.buildComandaData(order);
        const comanda_result = await comandaService.printComanda(comandaData);
        
        if (!comanda_result.success) {
            showWarning('Comanda print failed: ' + comanda_result.message);
            // Don't block - comanda failure is not critical
        }
        
        return true;  // Allow order completion
    }
    """
    return javascript_code
