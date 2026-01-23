# Test ESC/POS - Odoo 19 Fiscal & Non-Fiscal Printer Module

## 📦 Repository Contents

Questo repository contiene un **modulo Odoo 19 completo** per l'integrazione di stampanti fiscali e non-fiscali nel POS.

### 🎯 Oggetto del Modulo

Integrazione di **Odoo POS** con:
1. **Stampante Fiscale** (SF20 - Protocollo Fiscale HYDRA)
2. **Stampante Non-Fiscale** (ESC/POS per comande cucina/bar)

---

## 📂 Struttura Repository

```
test-escpos/
│
├── 📄 README.md                    ← Questo file
├── 📄 INSTALLATION.md              ← Guida installazione step-by-step
├── 📄 PROJECT_STRUCTURE.py         ← Sintesi struttura progetto
├── 📄 requirements.txt              ← Dipendenze Python
│
├── 📁 it_epos_fiscal_nonfiscal_printer/  ← MODULO PRINCIPALE
│   ├── 📄 __manifest__.py          # Manifest Odoo
│   ├── 📄 README.md                # Documentazione modulo
│   ├── 📄 SUMMARY.md               # Riepilogo features
│   ├── 📄 EXAMPLES.py              # Esempi di utilizzo
│   │
│   ├── 📁 models/
│   │   ├── pos_config.py           # Config stampanti
│   │   ├── pos_printer_status.py   # Tracking stato
│   │   └── pos_session.py          # Session extension
│   │
│   ├── 📁 services/
│   │   ├── fiscal_printer_service.py   # Adapter SF20
│   │   ├── nonfiscal_printer_service.py # Adapter ESC/POS
│   │   └── printer_factory.py          # Factory pattern
│   │
│   ├── 📁 controllers/
│   │   └── printer_controller.py   # JSON-RPC API
│   │
│   ├── 📁 views/
│   │   ├── pos_config_views.xml
│   │   └── pos_printer_status_views.xml
│   │
│   ├── 📁 static/src/
│   │   ├── 📁 js/          # Frontend services
│   │   └── 📁 css/         # Stylesheets
│   │
│   ├── 📁 security/
│   │   └── ir.model.access.csv
│   │
│   ├── tests.py            # Unit tests
│   ├── hooks.py            # Integration hooks
│   ├── config.py           # Costanti
│   └── utils.py            # Diagnostica
│
├── 📁 [Legacy]
│   ├── main.py             # Script test originale
│   └── sample_data.json    # Dati sample
│
└── 📝 LICENSE              # AGPL-3
```

---

## ✨ Features Principali

### 🖨️ Stampante Fiscale (SF20)
- ✅ Configurazione IP/porta nel backend Odoo
- ✅ Apertura/chiusura ricevute
- ✅ Registrazione articoli con tassazione
- ✅ Elaborazione pagamenti
- ✅ Rapporti Z (fine giornata)
- ✅ Monitoraggio stato real-time
- ✅ Modalità fail-safe (opzionale)

### 🍳 Stampante Non-Fiscale (ESC/POS)
- ✅ Invio comande cucina/bar
- ✅ Layout personalizzabile
- ✅ Taglio carta automatico
- ✅ Apertura cassetto
- ✅ Stato in tempo reale

### 📊 Backend Odoo
- ✅ Estensione POS configuration
- ✅ Tracking stato stampanti
- ✅ API JSON-RPC endpoints
- ✅ Logging dettagliato

### 🎨 POS Frontend
- ✅ Widget stato stampanti
- ✅ Status monitoring (30s)
- ✅ Indicatori colore
- ✅ Notifiche errori

---

## 🚀 Quick Start

### 1. Installazione
```bash
# Clonare repository
git clone <repo-url>
cd test-escpos

# Copiare modulo in addons Odoo
cp -r it_epos_fiscal_nonfiscal_printer /path/to/odoo/addons/
```

### 2. Configurazione Odoo
1. Accedere a **Impostazioni > Moduli > Aggiorna lista**
2. Cercare e installare `it_epos_fiscal_nonfiscal_printer`
3. Andare in **POS > Configurazione > Configurazione POS**
4. Aggiungere IP stampanti (es: 192.168.1.100)

### 3. Test
```bash
# Test connessione stampante
python -m it_epos_fiscal_nonfiscal_printer.utils test_sf20 192.168.1.100 9100
python -m it_epos_fiscal_nonfiscal_printer.utils test_escpos 192.168.1.101 9100
```

### 4. Verificare Installation
- Dashboard → **POS > Stato Stampanti**
- Dovrebbe mostrare stato stampanti

---

## 📖 Documentazione

| File | Descrizione |
|------|------------|
| [INSTALLATION.md](INSTALLATION.md) | Guida installazione completa |
| [it_epos_fiscal_nonfiscal_printer/README.md](it_epos_fiscal_nonfiscal_printer/README.md) | Documentazione modulo |
| [it_epos_fiscal_nonfiscal_printer/EXAMPLES.py](it_epos_fiscal_nonfiscal_printer/EXAMPLES.py) | Esempi di integrazione |
| [PROJECT_STRUCTURE.py](PROJECT_STRUCTURE.py) | Sintesi architettura |

---

## 🔌 API Endpoints

### Stampante Fiscale
```
POST /pos_printer/fiscal/status
POST /pos_printer/fiscal/print_receipt
POST /pos_printer/fiscal/z_report
```

### Stampante Non-Fiscale
```
POST /pos_printer/nonfiscal/status
POST /pos_printer/nonfiscal/print_comanda
```

Vedi [README.md](it_epos_fiscal_nonfiscal_printer/README.md) per dettagli API.

---

## 🏗️ Architettura

### Pattern Utilizzati
- **Adapter Pattern** - Isolamento protocollo stampante
- **Factory Pattern** - Creazione adapter e caching
- **Service Layer** - Business logic separata
- **State Machine** - SF20 protocol compliance

### Componenti Principali
1. **Backend Models** - Configurazione e tracking
2. **Printer Adapters** - Comunicazione stampanti
3. **JSON-RPC Controller** - API endpoints
4. **Frontend Services** - Integrazione POS UI
5. **Status Widget** - Monitoraggio real-time

---

## 🔒 Sicurezza

- Autenticazione: Basata POS session
- Autorizzazione: ACL su modelli
- Validazione: IP, porte, timeout
- Crittografia: (trasporto HTTPS se configurato)

---

## 📊 Monitoring

### Dashboard Stato
**POS > Stato Stampanti**
- Indicatori colore (OK/Error/Offline)
- Response time
- Errori consecutivi
- Last check time

### Log Applicazione
```bash
tail -f /var/log/odoo/odoo.log | grep -i printer
```

---

## 🧪 Testing

### Unit Tests
```bash
python -m pytest it_epos_fiscal_nonfiscal_printer/tests.py -v
```

### Coverage
```bash
python -m pytest --cov=it_epos_fiscal_nonfiscal_printer
```

---

## 🛠️ Utilities

### Diagnostica Stampante
```bash
# Test SF20
python -m it_epos_fiscal_nonfiscal_printer.utils test_sf20 <IP> [PORT]

# Test ESC/POS
python -m it_epos_fiscal_nonfiscal_printer.utils test_escpos <IP> [PORT]
```

---

## 📋 Requisiti

- **Odoo**: 19.0+
- **Python**: 3.8+
- **Moduli**: point_of_sale, base
- **Network**: Stampanti su stessa LAN

---

## 🔄 Workflow Tipico

```
1. Cliente ordina nel POS
           ↓
2. Totale ordine
           ↓
3. Pagamento effettuato
           ↓
4. print_receipt()
           ├─ Stampante fiscale (SF20)
           │  └─ Ricevuta fiscale
           │
           └─ Stampante non-fiscale (ESC/POS)
              └─ Comanda cucina
```

---

## ⚙️ Configurazione Predefinita

```
Stampante Fiscale:
  Port: 9100
  Timeout: 30s
  Fail-Safe: ON

Stampante Non-Fiscale:
  Port: 9100
  Timeout: 10s
  Width: 32 chars
  Auto-Cut: OFF
  Auto-Open-Drawer: OFF
```

---

## 🐛 Troubleshooting

### Stampante Non Raggiungibile
```bash
# Test connessione
ping 192.168.1.100
nc -zv 192.168.1.100 9100

# Verificare firewall
sudo ufw status
```

### Ricevuta Non Stampata
1. Verificare configurazione POS
2. Controllare stato stampa in dashboard
3. Consultare log applicazione

Vedi [INSTALLATION.md](INSTALLATION.md#troubleshooting) per troubleshooting completo.

---

## 📝 Licenza

AGPL-3 - Vedi [LICENSE](LICENSE)

---

## 👤 Autore

Alfredo Salata

---

## 🤝 Contributi

Per reportare bug o suggerire feature:
1. Aprire un issue
2. Descrivere il problema/feature
3. Allegare log se possibile

---

## 📚 Risorse Aggiuntive

- [Odoo Documentation](https://www.odoo.com/documentation/19.0/)
- [SF20 Protocollo Fiscale](https://www.hydra-italy.com/)
- [ESC/POS Standard](https://en.wikipedia.org/wiki/ESC/P)

---

**Modulo pronto per l'uso in ambienti di produzione!** 🚀
