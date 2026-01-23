# it_epos_fiscal_nonfiscal_printer

Modulo Odoo 19 per l'integrazione di stampanti fiscali e non-fiscali nel POS.

## Descrizione

Questo modulo integra il **Odoo Point of Sale (POS)** con:

1. **Stampante Fiscale (SF20)** - Protocollo Fiscale HYDRA per ricevute fiscali
2. **Stampante Non-Fiscale (ESC/POS)** - Per comande cucina/bar

Consente la gestione completa del ciclo di vita dei documenti fiscali e delle comande, con monitoraggio dello stato in tempo reale.

## Caratteristiche

### Stampante Fiscale (SF20)
- Configurazione IP e porta nel backend Odoo
- Apertura/chiusura ricevute fiscali
- Registrazione articoli con tassazione
- Elaborazione pagamenti
- Esecuzione rapporti Z (fine giornata)
- Monitoraggio stato in tempo reale
- Gestione errori con modalità "fail-safe"

### Stampante Non-Fiscale (ESC/POS)
- Invio comande cucina/bar
- Layout personalizzabile
- Taglio carta automatico (opzionale)
- Apertura cassetto automatica (opzionale)
- Stato di connessione in tempo reale

### UI POS
- Widget di stato per entrambe le stampanti
- Visualizzazione in tempo reale stato connessione
- Indicatori colore (OK/Errore/Offline)
- Notifiche di errore chiare

## Installazione

1. Copiare il modulo in `/addons/`
2. Aggiornare la lista dei moduli in Odoo
3. Installare il modulo `it_epos_fiscal_nonfiscal_printer`

## Configurazione

### Backend (Odoo)

1. Accedere a **Punto di Vendita > Configurazione > Configurazione POS**
2. Selezionare la configurazione da modificare
3. Nella tab "Configurazione Stampanti":

#### Stampante Fiscale (SF20)
- **Abilita Stampante Fiscale**: Attivare il flag
- **Indirizzo IP**: IP della stampante (es: 192.168.1.100)
- **Porta**: Porta TCP (default: 9100)
- **Timeout (secondi)**: Timeout comunicazione (default: 30)
- **Modalità Fail-Safe**: Se attivato, errori fiscali non bloccano la vendita

#### Stampante Non-Fiscale (ESC/POS)
- **Abilita Stampante Non-Fiscale**: Attivare il flag
- **Indirizzo IP**: IP della stampante (es: 192.168.1.101)
- **Porta**: Porta TCP (default: 9100)
- **Timeout (secondi)**: Timeout comunicazione (default: 10)
- **Larghezza Stampante (caratteri)**: Larghezza output (default: 32)
- **Taglio Automatico**: Tagliare carta dopo ogni comanda
- **Apertura Cassetto**: Aprire cassetto dopo comanda

## Architettura

### Moduli

```
it_epos_fiscal_nonfiscal_printer/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── pos_config.py           # Estensione configurazione POS
│   ├── pos_printer_status.py   # Tracking stato stampanti
│   └── pos_session.py          # Estensione sessione POS
├── services/
│   ├── fiscal_printer_service.py   # Adapter SF20
│   ├── nonfiscal_printer_service.py# Adapter ESC/POS
│   └── printer_factory.py          # Factory pattern
├── controllers/
│   └── printer_controller.py   # API JSON-RPC
├── views/
│   ├── pos_config_views.xml    # View configurazione
│   └── pos_printer_status_views.xml
├── static/src/
│   ├── js/
│   │   ├── fiscal_printer_service.js
│   │   ├── comanda_printer_service.js
│   │   └── printer_status_widget.js
│   └── css/
│       └── printer_status.css
└── security/
    └── ir.model.access.csv
```

### Pattern Architetturale

**Adapter Pattern**: Ogni stampante (SF20, ESC/POS) ha un adapter dedicato che astrae il protocollo specifico.

**Factory Pattern**: `PrinterFactory` gestisce la creazione e il caching degli adapter.

**Service Layer**: Controller backend espone API JSON-RPC per il frontend POS.

**Separation of Concerns**:
- Backend: logica di comunicazione, stato, persistenza
- Frontend: UI, interazione utente, notifiche

## API JSON-RPC

### Stampante Fiscale

#### GET Status
```
POST /pos_printer/fiscal/status
{
    "pos_config_id": 1
}
```

Response:
```json
{
    "status": "ok|busy|error|offline|warning",
    "state": "receipt_open|receipt_closed|z_required",
    "ready": true,
    "response_time_ms": 150
}
```

#### Print Receipt
```
POST /pos_printer/fiscal/print_receipt
{
    "pos_config_id": 1,
    "receipt_data": {
        "items": [
            {
                "description": "Item 1",
                "quantity": 2,
                "unit_price": 10.00,
                "tax_percent": 22
            }
        ],
        "payments": [
            {
                "type": "cash",
                "amount": 20.00
            }
        ]
    }
}
```

#### Z Report
```
POST /pos_printer/fiscal/z_report
{
    "pos_config_id": 1
}
```

### Stampante Non-Fiscale

#### GET Status
```
POST /pos_printer/nonfiscal/status
{
    "pos_config_id": 1
}
```

#### Print Comanda
```
POST /pos_printer/nonfiscal/print_comanda
{
    "pos_config_id": 1,
    "order_data": {
        "order_number": "ORD-001",
        "table": "TABLE-5",
        "timestamp": "14:30:25",
        "items": [
            {
                "description": "Margherita",
                "quantity": 2,
                "notes": "Senza cipolla"
            }
        ]
    },
    "auto_cut": false,
    "open_drawer": false
}
```

## Utilizzo nel POS

### Stampa Ricevuta Fiscale

```javascript
// Nel codice POS
const receiptData = fiscalService.buildReceiptData(order);
const result = await fiscalService.printReceipt(receiptData);

if (result.success) {
    console.log('Ricevuta stampata:', result.receipt_number);
} else if (result.fail_safe_triggered) {
    console.warn('Errore stampante, modalità fail-safe attiva');
}
```

### Stampa Comanda

```javascript
// Nel codice POS
const comandaData = comandaService.buildComandaData(order, {
    table_name: 'Tavolo 5',
    header: 'COMANDA CUCINA'
});

const result = await comandaService.printComanda(comandaData, {
    auto_cut: true,
    open_drawer: false
});
```

## Monitoraggio Stato

Le stampanti sono monitorate in tempo reale. Lo stato è disponibile in:

1. **Dashboard**: Menu **Punto di Vendita > Stato Stampanti**
2. **POS Frontend**: Widget di stato nella barra superiore
3. **API**: Endpoint `/pos_printer/*/status`

### Interpretation dello Stato

| Stato | Colore | Significato |
|-------|--------|------------|
| **OK** | 🟢 Verde | Stampante pronta |
| **Busy** | 🟡 Giallo | Stampante in elaborazione |
| **Error** | 🔴 Rosso | Errore comunicazione |
| **Offline** | ⚫ Grigio | Stampante non raggiungibile |
| **Warning** | 🟠 Arancione | Azione richiesta (Z report?) |

## Gestione Errori

### Modalità Fail-Safe (Stampante Fiscale)

Quando attivata, gli errori di stampa fiscale non bloccano il POS:

```
Receipt Sale
    ↓
Try: Print Fiscal Receipt
    ├─ Success → Receipt #12345 ✓
    └─ Error (Fail-Safe Mode) → Proceed with sale + Warning ⚠️
```

### Modalità Strict (Default)

Gli errori bloccano la vendita fino a risoluzione.

## Logging & Debug

Tutti i log sono registrati in Odoo. Consultare **Impostazioni > Log del registro** per errori e comunicazioni.

Livello log per il modulo: `DEBUG` in Odoo con `--logfile=...`

## Limitazioni e Considerazioni

1. **SF20 Protocol**: L'implementazione è semplificata. Consultare la documentazione SF20 per dettagli completi del protocollo.
2. **ESC/POS**: Compatibile con stampanti standard ESC/POS over TCP/IP.
3. **Network**: Stampanti e POS devono essere sulla stessa LAN.
4. **Timeout**: Configurare timeout appropriato per stampante e rete.

## Supporto SF20 (Dettagli Tecnici)

### Stato Macchina SF20

La stampante SF20 segue una state machine rigida:

```
[INIT] → [RECEIPT_OPEN] → [ITEMS] → [PAYMENT] → [RECEIPT_CLOSED]
  ↓                                                        ↑
  └────────────────── [Z_REQUIRED] ←──────────────────────┘
```

Quando necessario un Z report, la stampante entra nello stato `Z_REQUIRED` e rifiuta altre operazioni.

### Comandi SF20

- `ESC @` (0x1B 0x40): Initialize
- `ESC n` (0x1B 0x6E): Request Status
- `ESC G` (0x1B 0x47): Open Receipt
- `ESC C` (0x1B 0x43): Close Receipt
- `ESC J` (0x1B 0x4A): Register Item
- `ESC P` (0x1B 0x50): Process Payment
- `ESC Z` (0x1B 0x5A): Z Report

## Troubleshooting

### Stampante non raggiungibile
- Verificare indirizzo IP e porta
- Pingare la stampante: `ping 192.168.1.100`
- Controllare firewall

### Errore di comunicazione
- Aumentare timeout in configurazione
- Verificare cavi di rete
- Controllare stato stampante (display)

### Ricevuta non stampata
- Verificare saldo carta fiscale
- Controllare stato Z report
- Consultare manuale SF20

## Sviluppi Futuri

- [ ] Supporto per altre stampanti fiscali (RT, SWEDA, etc.)
- [ ] Integrazione con servizi cloud per backup fiscale
- [ ] Generazione automatica rapporti
- [ ] Multi-printer per punto vendita
- [ ] Logging dettagliato per audit
- [ ] Dashboard statistiche

## Licenza

AGPL-3

## Autore

Alfredo Salata
