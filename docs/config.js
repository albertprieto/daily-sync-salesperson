// Config del dashboard. Actualizado automáticamente por la tarea diaria de Cowork.
window.DAILY_SYNC_CONFIG = {
  // GitHub repo donde están los datos cifrados y se commitean las decisiones
  repo: "albertprieto/daily-sync-salesperson",

  // Branch donde commitear decisiones (default: main)
  branch: "main",

  // Path relativo dentro del repo donde se publican las propuestas cifradas
  dataPath: "data",

  // Path donde se commitean las decisiones (que recoge la tarea de polling de Cowork)
  decisionsPath: "decisions",

  // PAT cifrado con la passphrase del día — actualizado cada madrugada por Cowork.
  // Formato: {v:1, iv:base64, salt:base64, ct:base64}
  // Si es null, el dashboard pedirá el PAT manualmente.
  encryptedPat: null,

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
