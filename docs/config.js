// Config del dashboard. Edita estos valores DESPUÉS de crear el repo en GitHub.
window.DAILY_SYNC_CONFIG = {
  // GitHub repo donde están los datos cifrados y se commitean las decisiones
  // Formato: "owner/repo"
  repo: "albertprieto/daily-sync-salesperson",

  // Branch donde commitear decisiones (default: main)
  branch: "main",

  // Path relativo dentro del repo donde se publican las propuestas cifradas
  // (cargadas desde data/index.json)
  dataPath: "data",

  // Path donde se commitean las decisiones (que disparan el workflow apply)
  decisionsPath: "decisions",

  // Mapa de salesperson IDs → nombres legibles (para mostrar en UI sin fetch extra)
  // Mantener sincronizado con Odoo. IDs vienen de res.users.
  salespersons: {
    6:    "Albert Prieto",
    9:    "Josep Massó",
    881:  "Eloi Davila Lopez",
    3854: "Gerard Montero Martínez",
    845:  "Jordi Hernandez",
    738:  "Ramon Boncompte",
    4528: "Garima Arora",
    4307: "(histórico)",
    4308: "(histórico)",
    4309: "(histórico)",
    16:   "Industrial Shields - Website",
    2:    "Administrator",
    1:    "OdooBot",
    10:   "Joan F. Aubets",
  },
};
