# Setup paso a paso — Daily Sync Salesperson

Mismo patrón que `albertprieto/comisiones-comerciales`, adaptado para esta tarea.

## 1. Crear el repo en GitHub

1. Ve a https://github.com/new
2. Owner: `albertprieto` · Name: `daily-sync-salesperson`
3. **Public** (los datos están cifrados — no hay riesgo)
4. Add README: **NO** (ya está local)
5. Create repository

## 2. Push inicial

Desde tu Mac, en `/Users/pc02/Downloads/daily-sync-salesperson/`:

```bash
cd "/Users/pc02/Downloads/daily-sync-salesperson"
git init -b main
git add .
git commit -m "initial commit: daily sync salesperson scaffold"
git remote add origin https://github.com/albertprieto/daily-sync-salesperson.git
git push -u origin main
```

(Si tienes 2FA, usa un PAT como password — el mismo que usarás en el dashboard.)

## 3. Habilitar GitHub Pages

1. Repo → Settings → Pages
2. Source: **Deploy from a branch**
3. Branch: `main` · Folder: `/docs`
4. Save
5. URL aparecerá en ~30s: `https://albertprieto.github.io/daily-sync-salesperson/`

## 4. Generar las credenciales

### 4a. Odoo API Key (no es tu password)
1. https://bootandwork-bootodoo2.odoo.com/odoo/my-account?tab=security
2. **API Keys** → **New API Key**
3. Description: `daily-sync-salesperson workflow`
4. Click Generate → copia la clave (se muestra **una sola vez**)

### 4b. Gmail App Password
- Si ya tienes una de comisiones, **NO la reutilices** — genera una nueva exclusiva:
1. https://myaccount.google.com/apppasswords (necesita 2FA en Google)
2. App name: `daily-sync-salesperson`
3. Click Create → copia los 16 caracteres **sin espacios**

### 4c. GitHub PAT (Personal Access Token) para el dashboard
1. https://github.com/settings/tokens?type=beta (Fine-grained tokens)
2. Token name: `daily-sync-dashboard`
3. Repository access: **Only select repositories** → `daily-sync-salesperson`
4. Permissions:
   - **Contents**: Read and write
   - **Metadata**: Read (auto)
5. Generate → copia el token (`github_pat_…`)

## 5. Añadir secrets al repo

Repo → Settings → Secrets and variables → Actions → **New repository secret** (uno por uno):

| Name              | Valor |
|-------------------|-------|
| `ODOO_URL`        | `https://bootandwork-bootodoo2.odoo.com` |
| `ODOO_DB`         | (mismo que en comisiones-comerciales) |
| `ODOO_USER`       | `apm@industrialshields.com` |
| `ODOO_PASSWORD`   | la API Key del paso 4a |
| `GMAIL_USER`      | `apm@industrialshields.com` |
| `GMAIL_APP_PASS`  | los 16 chars del paso 4b |
| `NOTIFY_TO`       | `apm@industrialshields.com` |
| `DASHBOARD_URL`   | `https://albertprieto.github.io/daily-sync-salesperson/` |

> El `GitHub PAT` (paso 4c) NO va aquí — lo metes desde el dashboard la primera vez.

## 6. Editar `docs/config.js`

Si tu usuario GitHub no es `albertprieto`, edita la línea `repo:` antes del primer push.

## 7. Primera ejecución (dry run manual)

Repo → Actions → **Nightly fetch & analyze** → **Run workflow** → main → Run

Espera ~3 min. Si todo va bien:
- Hay un commit nuevo en `docs/data/YYYY-MM-DD.json.enc`
- Te llega email a tu Gmail con el link al dashboard

## 8. Probar el dashboard

1. Abre la URL del dashboard (la del email o la de Pages)
2. Mete tu **Gmail App Password** (paso 4b) → desbloquea
3. Marca 1 propuesta de prueba (alguna HIGH segura)
4. Click "Aplicar seleccionadas" → mete tu **GitHub PAT** (paso 4c) → Confirmar
5. Espera ~2 min — recibirás email de confirmación
6. Verifica en Odoo que el cambio se aplicó

## 9. Activar el cron diario

Ya está activo en `nightly-fetch.yml` (`cron: '0 2 * * *'` UTC = 04:00 hora España).
Solo tienes que confirmar que el workflow está habilitado:
- Repo → Actions → Verifica que no aparece "Workflows aren't being run on this repository"

---

## Cómo revocar credenciales

| Si se filtra…    | Ve a… |
|-------------------|-------|
| Odoo API Key      | Odoo → Profile → Account Security → Borrar la key |
| Gmail App Pass    | https://myaccount.google.com/apppasswords → Revoke |
| GitHub PAT        | https://github.com/settings/tokens → Revoke |

Cada credencial es independiente — revocar una NO afecta a las demás ni a tu cuenta principal.

## Troubleshooting

**"Authentication failed" en el workflow**
→ Revisa `ODOO_USER` y `ODOO_PASSWORD`. La API Key se copia una sola vez; si no la guardaste, genera otra.

**"App Password incorrecta" en el dashboard**
→ La App Pass del paso 4b debe ser **igual** a la de `GMAIL_APP_PASS` del paso 5. Si las has generado por separado, no van a coincidir las claves de cifrado.

**"GitHub API 403" al aplicar**
→ El PAT del paso 4c expiró o le falta scope `Contents: write`. Genera otro.

**"No data" en el dashboard**
→ El workflow nightly aún no ha corrido. Lánzalo manualmente (paso 7).
