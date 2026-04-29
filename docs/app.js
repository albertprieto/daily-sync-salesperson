// Dashboard logic: load encrypted proposals, decrypt with daily passphrase,
// render UI, commit decisions via GitHub API using embedded PAT.
//
// Crypto: must match scripts/crypto.py (PBKDF2-HMAC-SHA256, AES-GCM, salt fijo).
// Passphrase: 32-char random string generated daily by Cowork, sent via email.

const CFG = window.DAILY_SYNC_CONFIG;
const SALT_STR = "daily-sync-salesperson-v1";
const ITERATIONS = 100_000;

const $ = (id) => document.getElementById(id);
const enc = new TextEncoder();
const dec = new TextDecoder();

// --- State ---
let APP_PASS = null;       // passphrase del email (para descifrar datos + PAT)
let GH_PAT = null;         // PAT descifrado del blob (para commits)
let CURRENT_DATA = null;   // descifrado: {sale_order, crm_lead, res_partner, summary, ...}
let CURRENT_DATE = null;
let DATES_INDEX = {};      // del data/index.json

// =========================
// Crypto helpers
// =========================
async function deriveKey(passphrase, saltBytes) {
  const baseKey = await crypto.subtle.importKey(
    "raw", enc.encode(passphrase), "PBKDF2", false, ["deriveKey"]
  );
  return crypto.subtle.deriveKey(
    { name: "PBKDF2", salt: saltBytes, iterations: ITERATIONS, hash: "SHA-256" },
    baseKey,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"]
  );
}

function b64ToBytes(b64) {
  const bin = atob(b64);
  const arr = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
  return arr;
}
function bytesToB64(bytes) {
  let s = "";
  for (let i = 0; i < bytes.byteLength; i++) s += String.fromCharCode(bytes[i]);
  return btoa(s);
}

async function decryptBlob(blob, passphrase) {
  const salt = b64ToBytes(blob.salt);
  const iv   = b64ToBytes(blob.iv);
  const ct   = b64ToBytes(blob.ct);
  const key  = await deriveKey(passphrase, salt);
  const pt   = await crypto.subtle.decrypt({ name: "AES-GCM", iv }, key, ct);
  return JSON.parse(dec.decode(pt));
}

async function encryptBlob(obj, passphrase) {
  const data = enc.encode(JSON.stringify(obj));
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const saltBytes = enc.encode(SALT_STR);
  const key = await deriveKey(passphrase, saltBytes);
  const ct = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, data);
  return {
    v: 1,
    iv: bytesToB64(iv),
    salt: bytesToB64(saltBytes),
    ct: bytesToB64(new Uint8Array(ct)),
  };
}

// =========================
// Login / unlock
// =========================
async function unlock(passphrase, remember) {
  // Cargar índice
  const r = await fetch(`${CFG.dataPath}/index.json?t=${Date.now()}`);
  if (!r.ok) throw new Error(`No se pudo cargar ${CFG.dataPath}/index.json (${r.status})`);
  DATES_INDEX = await r.json();
  const dates = Object.keys(DATES_INDEX).sort().reverse();
  if (dates.length === 0) throw new Error("No hay datos en data/. ¿Ya corrió la tarea diaria?");

  // Leer fecha querystring si existe
  const params = new URLSearchParams(location.search);
  const requested = params.get("d");
  CURRENT_DATE = (requested && DATES_INDEX[requested]) ? requested : dates[0];

  // Descargar y descifrar
  const blob = await (await fetch(
    `${CFG.dataPath}/${CURRENT_DATE}.json.enc?t=${Date.now()}`
  )).json();
  CURRENT_DATA = await decryptBlob(blob, passphrase);

  // Si llegamos aquí, la passphrase es correcta
  APP_PASS = passphrase;
  if (remember) sessionStorage.setItem("dsync_pp", passphrase);

  // Extraer PAT embebido (si existe en el blob de datos)
  GH_PAT = null;
  if (CURRENT_DATA._pat) {
    GH_PAT = CURRENT_DATA._pat;
    delete CURRENT_DATA._pat; // no exponer en UI
  }

  // Si no hay PAT en datos, intentar descifrar desde config.js
  if (!GH_PAT && CFG.encryptedPat) {
    try {
      const patObj = await decryptBlob(CFG.encryptedPat, passphrase);
      GH_PAT = patObj.pat || null;
    } catch (e) {
      console.warn("[dsync] No se pudo descifrar PAT de config.js:", e.message);
    }
  }

  // Mostrar/ocultar sección de PAT en modal según disponibilidad
  const patSection = $("applyAuth");
  if (patSection) patSection.style.display = GH_PAT ? "none" : "block";

  // Poblar selector de fechas
  const sel = $("dateSelect");
  sel.innerHTML = "";
  dates.forEach((d) => {
    const o = document.createElement("option");
    o.value = d;
    o.textContent = `${d} (${DATES_INDEX[d].totals.sale_order +
                            DATES_INDEX[d].totals.crm_lead +
                            DATES_INDEX[d].totals.res_partner} propuestas)`;
    if (d === CURRENT_DATE) o.selected = true;
    sel.appendChild(o);
  });

  // Mostrar UI
  $("loginOverlay").style.display = "none";
  $("app").hidden = false;
  $("lockBtn").hidden = false;
  render();
}

// =========================
// Render
// =========================
function userName(uid) {
  if (uid == null || uid === false || uid === "") return "(vacío)";
  return CFG.salespersons[uid] || `uid#${uid}`;
}

function renderItem(model, it) {
  const div = document.createElement("label");
  div.className = `item ${it.confidence}`;
  div.dataset.model = model;
  div.dataset.id = it.id;
  div.dataset.newUid = it.new_user_id;
  div.dataset.currentUid = it.current_user_id || "";
  div.innerHTML = `
    <input type="checkbox" ${it.confidence === "high" ? "" : ""}>
    <div class="meta">
      <span class="title">${escapeHtml(it.name || `#${it.id}`)}</span>
      <span class="detail">
        <b>${escapeHtml(userName(it.current_user_id))}</b>
        <span class="arrow">→</span>
        <b>${escapeHtml(userName(it.new_user_id))}</b>
        · ${escapeHtml(it.reason)}
      </span>
    </div>
    <span class="badge">${it.confidence.toUpperCase()}</span>
  `;
  div.querySelector("input").addEventListener("change", updateApplyBar);
  return div;
}

function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

function render() {
  const d = CURRENT_DATA;
  const s = d.summary || {total_in:{}, total_out:{}};
  const t = s.total_out || {};

  $("summary").innerHTML = `
    <div class="stat"><div class="num">${t.sale_order||0}</div><div class="lbl">Sale orders</div></div>
    <div class="stat"><div class="num">${t.crm_lead||0}</div><div class="lbl">CRM leads</div></div>
    <div class="stat"><div class="num">${t.res_partner||0}</div><div class="lbl">Partners</div></div>
    <div class="stat"><div class="num">${t.skipped||0}</div><div class="lbl">Skipped</div></div>
  `;

  const sortFn = (a,b) => {
    const order = {high:0, medium:1, low:2};
    return (order[a.confidence]||9) - (order[b.confidence]||9) || (a.id - b.id);
  };

  const renderList = (containerId, countId, items) => {
    const c = $(containerId);
    c.innerHTML = "";
    items.sort(sortFn).forEach((it) => c.appendChild(renderItem(detectModel(containerId), it)));
    $(countId).textContent = items.length;
  };

  renderList("soList",     "soCount",     d.sale_order || []);
  renderList("leadList",   "leadCount",   d.crm_lead || []);
  renderList("partnerList","partnerCount",d.res_partner || []);

  updateApplyBar();
}

function detectModel(containerId) {
  return { soList: "sale.order", leadList: "crm.lead", partnerList: "res.partner" }[containerId];
}

function updateApplyBar() {
  const checks = document.querySelectorAll(".item input[type=checkbox]:checked");
  $("selectedCount").textContent = `${checks.length} seleccionada${checks.length === 1 ? "" : "s"}`;
  $("applyBtn").disabled = checks.length === 0;
}

// =========================
// Apply (commit decisions)
// =========================
function collectSelected() {
  const items = [];
  document.querySelectorAll(".item input[type=checkbox]:checked").forEach((cb) => {
    const div = cb.closest(".item");
    items.push({
      model: div.dataset.model,
      id: parseInt(div.dataset.id),
      new_user_id: parseInt(div.dataset.newUid),
      current_user_id: div.dataset.currentUid ? parseInt(div.dataset.currentUid) : null,
    });
  });
  return items;
}

async function commitDecisions(pat, decisions) {
  const filename = `${CURRENT_DATE}-${Date.now()}.json.enc`;
  const path = `${CFG.decisionsPath}/${filename}`;
  const blob = await encryptBlob(decisions, APP_PASS);
  const content = btoa(JSON.stringify(blob, null, 2));

  const url = `https://api.github.com/repos/${CFG.repo}/contents/${path}`;
  const message = `decisions: ${CURRENT_DATE} (${decisions.items.length} items)`;
  const body = { message, content, branch: CFG.branch };

  const r = await fetch(url, {
    method: "PUT",
    headers: {
      "Authorization": `Bearer ${pat}`,
      "Accept": "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
    },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const txt = await r.text();
    throw new Error(`GitHub API ${r.status}: ${txt}`);
  }
  return await r.json();
}

async function onApply() {
  const items = collectSelected();
  if (items.length === 0) return;

  $("applyN").textContent = items.length;
  $("applyModal").hidden = false;

  // Si ya tenemos PAT embebido, ocultar sección de PAT
  const patSection = $("applyAuth");
  if (patSection) patSection.style.display = GH_PAT ? "none" : "block";
}

async function onApplyConfirm() {
  // Usar PAT embebido si disponible, sino tomar del campo manual
  const pat = GH_PAT || $("ghPat").value.trim();
  if (!pat) {
    $("applyStatus").innerHTML = '<span class="error">Falta el GitHub PAT. Contacta al administrador.</span>';
    return;
  }
  $("applyConfirm").disabled = true;
  $("applyStatus").textContent = "Commiteando decisiones…";

  try {
    const items = collectSelected();
    const decisions = {
      date: CURRENT_DATE,
      created_at: new Date().toISOString(),
      created_by: "dashboard",
      items,
    };
    await commitDecisions(pat, decisions);
    $("applyStatus").innerHTML = `
      <span style="color:#2e7d32">
        ✓ ${items.length} decisiones enviadas a Cowork.<br>
        Recibirás email de confirmación cuando se apliquen en Odoo (~minutos).
      </span>`;
    setTimeout(() => {
      $("applyModal").hidden = true;
      $("applyConfirm").disabled = false;
      document.querySelectorAll(".item input[type=checkbox]:checked").forEach((cb) => cb.checked = false);
      updateApplyBar();
    }, 4000);
  } catch (e) {
    $("applyStatus").innerHTML = `<span class="error">Error: ${escapeHtml(e.message)}</span>`;
    $("applyConfirm").disabled = false;
  }
}

// =========================
// Boot
// =========================
window.addEventListener("DOMContentLoaded", () => {
  // Auto-unlock si hay sessionStorage
  const cached = sessionStorage.getItem("dsync_pp");
  if (cached) {
    unlock(cached, false).catch((e) => {
      sessionStorage.removeItem("dsync_pp");
      $("loginError").hidden = false;
      $("loginError").textContent = e.message;
    });
  }

  $("loginForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    $("loginError").hidden = true;
    const pp = $("appPass").value.trim();
    const remember = $("rememberSession").checked;
    try {
      await unlock(pp, remember);
    } catch (err) {
      $("loginError").hidden = false;
      $("loginError").textContent =
        err.message.includes("decrypt") || err.name === "OperationError"
          ? "Passphrase incorrecta — comprueba el email de hoy"
          : err.message;
    }
  });

  $("dateSelect").addEventListener("change", async (e) => {
    if (!APP_PASS) return;
    const newDate = e.target.value;
    const blob = await (await fetch(
      `${CFG.dataPath}/${newDate}.json.enc?t=${Date.now()}`
    )).json();
    CURRENT_DATA = await decryptBlob(blob, APP_PASS);
    CURRENT_DATE = newDate;
    history.replaceState({}, "", `?d=${newDate}`);
    render();
  });

  $("lockBtn").addEventListener("click", () => {
    sessionStorage.removeItem("dsync_pp");
    GH_PAT = null;
    location.reload();
  });

  $("selectAllHigh").addEventListener("click", () => {
    document.querySelectorAll(".item.high input[type=checkbox]").forEach((cb) => cb.checked = true);
    updateApplyBar();
  });

  $("applyBtn").addEventListener("click", onApply);
  $("applyCancel").addEventListener("click", () => { $("applyModal").hidden = true; });
  $("applyConfirm").addEventListener("click", onApplyConfirm);
});
