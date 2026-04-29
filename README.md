# Daily Sync Salesperson — Industrial Shields

Auditoría diaria de asignación de Salesperson en Odoo (sale.order, crm.lead, res.partner)
con dashboard web y aprobación humana antes de aplicar cambios.

## Arquitectura

```
                    ┌─────────────────────┐
                    │  GitHub Actions     │
   04:00 cron ───►  │  nightly-fetch.yml  │
                    │                     │
                    │  1. Odoo XMLRPC     │  (ODOO_API_KEY)
                    │  2. daily_sync      │
                    │  3. AES-GCM encrypt │  (key=PBKDF2(GMAIL_APP_PASS))
                    │  4. git commit      │
                    │  5. Gmail SMTP      │  (GMAIL_APP_PASS)
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  GitHub Pages       │
   Albert opens ──► │  docs/index.html    │
                    │                     │
                    │  WebCrypto decrypt  4��  (App Pass en sessionStorage)
                    │  Render proposals   │
                    │  Checkboxes SI/NO   │
                    │  [Aplicar] button   │
                    └──────────┬──────────┘
                               │ git push (PAT en localStorage cifrado)
                               ▼
                    ┌─────────────────────┐
                    │  GitHub Actions     │
   on push ───────► │  apply-decisions.yml│
                    │                     │
                    │  1. Decrypt         │
                    │  2. Validate        │
                    │  3. odoo_write      │  (ODOO_API_KEY)
                    │  4. Commit results  │
                    │  5. Email confirm   │  (GMAIL_APP_PASS)
                    └─────────────────────┘
```

## Seguridad

- Repo público — pero TODOS los datos cifrados con AES-GCM (key derivada del App Password de Gmail vía PBKDF2).
- Sin passwords reales en el repo: `ODOO_PASSWORD` es una API Key de Odoo, `GMAIL_APP_PASS` es un Gmail App Password — ambos revocables sin tocar la cuenta principal.
- GitHub PAT del usuario para hacer commits desde el browser, almacenado cifrado en localStorage.
- Sin escrituras a Odoo sin commit explícito firmado por el dashboard.

## Estructura

```
daily-sync-salesperson/
├── .github/workflows/
│   ├── nightly-fetch.yml         # cron diario
│   └── apply-decisions.yml       # trigger por push
├── scripts/
│   ├── fetch_and_analyze.py      # Odoo XMLRPC + lógica daily_sync
│   ├── crypto.py                 # AES-GCM helpers (Python)
│   ├── notify.py                 # Gmail SMTP
│   └── apply.py                  # aplica decisions a Odoo
├── docs/                         # GitHub Pages root
│   ├── index.html
│   ├── app.js                    # decrypt + UI + commit
│   └── styles.css
├── docs/data/                    # propuestas cifradas YYYY-MM-DD.json.enc
├── decisions/                    # aprobaciones cifradas (commiteadas por web)
├── results/                      # logs de aplicaciones
├── requirements.txt
├── README.md
└── SETUP.md                      # paso a paso para Albert
```

## Uso día a día

1. **04:00** llega email a `apm@industrialshields.com` con asunto `[Daily Sync] N propuestas DD/MM` y link al dashboard.
2. Albert abre el link, mete su Gmail App Password (cached durante la sesión).
3. Revisa propuestas, marca SI en las que apruebe, click "Aplicar seleccionadas".
4. ~30s después llega email de confirmación con cambios aplicados.

## Ver también

- `SETUP.md` — instrucciones para configurar el repo desde cero
- Pattern hermano: `albertprieto/comisiones-comerciales` (mismo stack)
