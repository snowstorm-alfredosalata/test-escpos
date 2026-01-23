# Guida di Installazione e Deployment

## Requisiti

- **Odoo 19.0** (punto di vendita)
- **Python 3.8+**
- **Rete**: Stampanti raggiungibili dalla stessa LAN del server Odoo

## Installazione Modulo

### 1. Copia dei File

```bash
# Copiare il modulo nella cartella addons
cp -r it_epos_fiscal_nonfiscal_printer /path/to/odoo/addons/

# Verificare i permessi
chmod -R 755 /path/to/odoo/addons/it_epos_fiscal_nonfiscal_printer
```

### 2. Aggiornare Odoo

```bash
# Accedere a Odoo come amministratore
# Andare in: Impostazioni > Moduli > Aggiorna lista

# Cercare: it_epos_fiscal_nonfiscal_printer
# Cliccare "Installa"
```

### 3. Verifica Installazione

Dopo l'installazione, il modulo dovrebbe aggiungere:
- Campo "Configurazione Stampanti" in **Punto di Vendita > Configurazione > Configurazione POS**
- Menu **Punto di Vendita > Stato Stampanti**

## Configurazione Stampanti

### Stampante Fiscale SF20

1. Accedere a **Punto di Vendita > Configurazione > Configurazione POS**
2. Selezionare la configurazione POS
3. Nella tab "Configurazione Stampanti":
   - ✓ Abilitare "Abilita Stampante Fiscale"
   - Inserire **Indirizzo IP** stampante (es: `192.168.1.100`)
   - Inserire **Porta** (default: `9100`)
   - Impostare **Timeout** in secondi (default: `30`)
   - Selezionare **Modalità Fail-Safe** (consigliato per ambienti produttivi)
4. Salvare

### Stampante Non-Fiscale (ESC/POS)

1. Nella stessa tab:
   - ✓ Abilitare "Abilita Stampante Non-Fiscale"
   - Inserire **Indirizzo IP** stampante (es: `192.168.1.101`)
   - Inserire **Porta** (default: `9100`)
   - Impostare **Timeout** (default: `10` secondi)
   - Impostare **Larghezza Stampante** (default: `32` caratteri)
   - Opzionali:
     - ✓ "Taglio Automatico" - taglia carta dopo ogni comanda
     - ✓ "Apertura Cassetto" - apre il cassetto dopo comanda
2. Salvare

## Test di Connessione

### Via Bash

```bash
# Test SF20
ping 192.168.1.100
nc -zv 192.168.1.100 9100

# Test ESC/POS
ping 192.168.1.101
nc -zv 192.168.1.101 9100
```

### Via Odoo

1. Accedere a **Punto di Vendita > Stato Stampanti**
2. Dovrebbe mostrare lo stato di tutte le stampanti
3. Cliccare il bottone "Aggiorna Stato" per un controllo manuale

## Integrazione POS

### Opzione 1: Integrazione Automatica (Consigliata)

Modificare il file `static/src/xml/pos_screens.xml` per aggiungere i bottoni di stampa:

```xml
<t t-extend="OrderWidget">
    <t t-jquery=".button-section" t-operation="append">
        <button class="button print-fiscal">Stampa Fiscale</button>
        <button class="button print-comanda">Stampa Comanda</button>
    </t>
</t>
```

### Opzione 2: Integrazione Manuale (JavaScript)

Nel vostro file POS personalizzato:

```javascript
// In models.Order
var Order = require('point_of_sale.models').Order;

Order.prototype.print_fiscal = async function() {
    const fiscalService = this.env.services.fiscal_printer_service;
    const receiptData = fiscalService.buildReceiptData(this);
    const result = await fiscalService.printReceipt(receiptData);
    
    if (result.success) {
        this.fiscal_receipt_number = result.receipt_number;
        this.trigger('change');
    }
};

Order.prototype.print_comanda = async function() {
    const comandaService = this.env.services.comanda_printer_service;
    const comandaData = comandaService.buildComandaData(this);
    await comandaService.printComanda(comandaData);
};
```

## Monitoring e Diagnostica

### Dashboard Stato

1. Accedere a **Punto di Vendita > Stato Stampanti**
2. Visualizzare stato in tempo reale di tutte le stampanti

### Log Applicazione

```bash
# Consultare i log di Odoo
tail -f /var/log/odoo/odoo.log | grep -i printer

# Oppure in Odoo: Impostazioni > Log del registro
```

### Test Manuale Stampante

```bash
# Via python (nel server Odoo)
python
>>> from odoo import http
>>> from odoo.http import request
>>> from it_epos_fiscal_nonfiscal_printer.services.printer_factory import PrinterFactory
>>> 
>>> # Test SF20
>>> printer = PrinterFactory.create_fiscal_printer(
...     pos_config_id=1,
...     ip='192.168.1.100',
...     port=9100
... )
>>> success, msg = printer.connect()
>>> print(f"Connection: {success} - {msg}")
>>> 
>>> status = printer.get_status()
>>> print(f"Status: {status}")
```

## Troubleshooting

### Stampante Non Raggiungibile

1. **Verificare rete:**
   ```bash
   ping 192.168.1.100
   ```

2. **Verificare firewall:**
   - Controllare che la porta 9100 sia aperta sul firewall
   - Verificare il firewall della stampante

3. **Verificare configurazione stampante:**
   - Stampante accesa
   - Indirizzo IP corretto
   - Porta configurata correttamente

### Ricevuta Non Stampata

1. **Verificare configurazione:**
   - POS Config ha "Abilita Stampante Fiscale" selezionato?
   - IP e porta corretti?

2. **Verificare stato stampante:**
   - Accedere a **Stato Stampanti** e controllare
   - Se in stato "Z_REPORT_REQUIRED", eseguire Z report

3. **Consultare log:**
   ```bash
   grep "fiscal" /var/log/odoo/odoo.log
   ```

### Comanda Non Stampata su Stampante Non-Fiscale

1. **Verificare configurazione:**
   - POS Config ha "Abilita Stampante Non-Fiscale" selezionato?

2. **Verificare connessione:**
   - Test ping manuale
   - Controllare porta

3. **Aumentare timeout:**
   - Se stampante lenta, aumentare timeout in configurazione

## Performance e Ottimizzazioni

### Caching Adapter

Gli adapter printer sono cached in memoria. Per resettare:

```python
from it_epos_fiscal_nonfiscal_printer.services.printer_factory import PrinterFactory
PrinterFactory.disconnect_all()
```

### Configurazione Timeout

- **Stampante Fiscale**: 30 secondi (consigliato)
  - Operazioni più lente
  - Comunicazione critica
  
- **Stampante Non-Fiscale**: 10 secondi (consigliato)
  - Operazioni veloci
  - Non critica

### Monitoraggio Periodico

Status check default: 30 secondi. Per modificare:

```javascript
// In printer_status_widget.js
const checkInterval = 30000; // millisecondi
```

## Backup e Ripristino

### Backup Configurazione

```sql
-- Backup POS Config con stampanti
SELECT * FROM pos_config 
WHERE fiscal_printer_enabled = True OR nonfiscal_printer_enabled = True;
```

### Ripristino

Reimportare il dump SQL nel database Odoo.

## Produzione - Checklist

- [ ] Stampanti fiscali collaudate con documenti reali
- [ ] Modalità fail-safe abilitata in produzione
- [ ] IP e porte corrette
- [ ] Test Z report eseguito
- [ ] Log monitoring abilitato
- [ ] Backup regolare del database
- [ ] Documentazione conservata
- [ ] Personale formato su procedura

## Supporto e Contatti

Per problemi:
1. Consultare README.md completo
2. Controllare log applicazione
3. Contactare l'amministratore di sistema
4. Report issue su repository GitHub

## Aggiornamenti Futuri

Controllare regolarmente per aggiornamenti del modulo:

```bash
git pull origin main
```

Dopo aggiornamento, reinstallare il modulo in Odoo.
