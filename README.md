# Rebold Email Intelligence — Dashboards

4 dashboards automáticos de email marketing para Granite Nutrition, Ayoba, Brooklyn Biltong y Beg & Barker.

Se actualizan **cada lunes a las 8am** automáticamente vía GitHub Actions + Klaviyo API + Netlify.

## Setup (una sola vez)

### 1. Subir a GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/TU_USUARIO/rebold-dashboards.git
git push -u origin main
```

### 2. Agregar secrets en GitHub
Ve a tu repositorio → Settings → Secrets and variables → Actions → New repository secret

Agrega estos secrets:
```
GRANITE_API_KEY     = pk_XH3TM4_993ba3c779cea78552ef4c4dfe9caf0783
GRANITE_METRIC_ID   = T3ZNfY
AYOBA_API_KEY       = pk_PFSEH6_94c54725e3b3b02090dd00c5f4c1960033
AYOBA_METRIC_ID     = Q8VsyA
BROOKLYN_API_KEY    = pk_QPi6TF_082ea8c374c1efb6d5e0d2911c3e8341e3
BROOKLYN_METRIC_ID  = (dejar vacío, el script lo detecta automáticamente)
BEG_API_KEY         = pk_VYN5jd_b6cdf50c53deafca2a858a8a3b4c61795d
BEG_METRIC_ID       = (dejar vacío, el script lo detecta automáticamente)
NETLIFY_AUTH_TOKEN  = (tu token de Netlify)
NETLIFY_SITE_ID     = (tu site ID de Netlify)
```

### 3. Crear sitio en Netlify
1. Ve a netlify.com → Add new site → Deploy manually
2. Sube la carpeta `dashboards/` (primero corre el script localmente)
3. Copia el Site ID desde Site settings → General

### 4. Obtener token de Netlify
1. Netlify → User settings → Applications → Personal access tokens
2. Crea un token nuevo y cópialo

### 5. Primer deploy manual (para probar)
Ve a GitHub → Actions → "Rebold — Actualizar Dashboards Email" → Run workflow

## Uso

Los dashboards quedan en URLs públicas permanentes en Netlify:
- `tu-sitio.netlify.app/granite_dashboard.html`
- `tu-sitio.netlify.app/ayoba_dashboard.html`
- `tu-sitio.netlify.app/brooklyn_dashboard.html`
- `tu-sitio.netlify.app/beg_dashboard.html`

Cualquier persona puede abrirlos sin login ni Claude.

## Ejecución manual
```bash
pip install requests
python generate_dashboards.py
```

Los HTMLs quedan en la carpeta `dashboards/`.
