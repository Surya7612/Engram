const $ = (id) => document.getElementById(id);

function configuredApiBase() {
  const cfg = window.ENGRAM_CONFIG || {};
  return String(cfg.apiBase || "")
    .trim()
    .replace(/\/$/, "");
}

function isLocalHost() {
  const host = (location.hostname || "").toLowerCase();
  return host === "localhost" || host === "127.0.0.1" || host === "::1";
}

function defaultApiBase() {
  const configured = configuredApiBase();
  if (configured) return configured;
  if (typeof location !== "undefined" && /^https?:$/i.test(location.protocol)) {
    if (location.port === "8080") return "http://127.0.0.1:8000";
    // Same-origin when Try is served by the API host (/site/try.html).
    return location.origin;
  }
  return "http://127.0.0.1:8000";
}

function apiBase() {
  const raw = ($("apiBase").value || defaultApiBase()).trim();
  return raw.replace(/\/$/, "");
}

function showText(el, text) {
  el.hidden = false;
  el.textContent = text;
}

function showHtml(el, html) {
  el.hidden = false;
  el.innerHTML = html;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function formatEvidence(items, limit = 8) {
  if (!items || !items.length) return "<p class='try-muted'>No evidence returned.</p>";
  const rows = items.slice(0, limit).map((item) => {
    const label = escapeHtml(item.label || item.artifact_id || "evidence");
    const snippet = escapeHtml(item.snippet || "");
    return `<li><strong>${label}</strong><span>${snippet}</span></li>`;
  });
  return `<ul class="try-evidence">${rows.join("")}</ul>`;
}

function formatHealth(data) {
  return [
    `Status: ${data.status}`,
    `Version: ${data.version}`,
    `Graph: ${data.neo4j ? "ok" : "down"}`,
    `Vectors: ${data.qdrant ? "ok" : "down"}`,
  ].join("\n");
}

function formatIngest(data) {
  const lines = [
    `Ingested ${data.repo} as “${data.service}”.`,
    `Pull requests: ${data.pull_requests}  ·  Commits: ${data.commits}  ·  Limit: ${data.limit}`,
    `Embeddings: ${data.embedding_backend}`,
  ];
  if (data.note) lines.push(data.note);
  lines.push("Next: ask a question or run preflight for this service.");
  return lines.join("\n");
}

function formatQuery(data) {
  const answer = escapeHtml(data.answer || "(no answer)");
  return `
    <div class="try-answer">${answer.replace(/\n/g, "<br>")}</div>
    <h3>Evidence</h3>
    ${formatEvidence(data.evidence)}
  `;
}

function formatPreflight(data) {
  const service = data.service || {};
  const reasoning = (data.reasoning || [])
    .map((line) => `<li>${escapeHtml(line)}</li>`)
    .join("");
  const checks = (data.manual_checks || [])
    .map((line) => `<li>${escapeHtml(line)}</li>`)
    .join("");
  return `
    <p class="try-kicker">${escapeHtml(service.name || "Service")} · gate <strong>${escapeHtml(data.policy_outcome)}</strong> · risk <strong>${escapeHtml(data.risk_level)}</strong> · confidence ${escapeHtml(data.confidence)}</p>
    <div class="try-answer">${escapeHtml(data.summary || "").replace(/\n/g, "<br>")}</div>
    ${reasoning ? `<h3>Why</h3><ul class="try-bullets">${reasoning}</ul>` : ""}
    ${checks ? `<h3>Manual checks</h3><ul class="try-bullets">${checks}</ul>` : ""}
    <h3>Evidence</h3>
    ${formatEvidence(data.evidence)}
  `;
}

function formatRun(data) {
  const priors = (data.priors || [])
    .map((p) => {
      const note = p.human_note ? ` — ${escapeHtml(p.human_note)}` : "";
      return `<li><code>${escapeHtml(p.id)}</code> ${escapeHtml(p.human_decision)}${note}</li>`;
    })
    .join("");
  const violations = ((data.risk || {}).violations || [])
    .map((v) => `<li>${escapeHtml(v.detail)} <code>${escapeHtml(v.evidence_id || "")}</code></li>`)
    .join("");
  const findings = ((data.review && data.review.findings) || [])
    .slice(0, 4)
    .map((f) => {
      const ids = (f.evidence_ids || []).join(", ") || "unlinked";
      return `<li><strong>[${escapeHtml(f.severity)}]</strong> ${escapeHtml(f.claim)} <code>${escapeHtml(ids)}</code></li>`;
    })
    .join("");
  const cand = data.candidate || {};
  const diff = cand.diff ? `<pre class="try-diff">${escapeHtml(cand.diff)}</pre>` : "";
  const human = data.human_required ? " · human required" : "";
  return `
    <p class="try-kicker">gate <strong>${escapeHtml(data.gate)}</strong>${human} · org ${escapeHtml((data.instantiated || []).join(", ") || "none")}</p>
    ${data.manager_overridden ? `<p class="try-muted">Manager proposed ${(data.manager_proposed_roles || []).join(", ") || "none"} → Engram overrode.</p>` : ""}
    ${priors ? `<h3>Priors</h3><ul class="try-bullets">${priors}</ul>` : ""}
    ${violations ? `<h3>Violations</h3><ul class="try-bullets">${violations}</ul>` : ""}
    ${findings ? `<h3>Reviewer</h3><ul class="try-bullets">${findings}</ul>` : ""}
    <h3>Sandbox</h3>
    <p class="try-muted">${escapeHtml(cand.kind || "sandbox")} ${escapeHtml(cand.branch || "")} · source ${escapeHtml(cand.source_repo || "fixture")} · ${cand.applied_to_origin ? "ORIGIN MUTATED" : "origin unchanged"} · nothing merged</p>
    ${diff}
    <p class="try-muted">outcome <code>${escapeHtml(data.outcome_id || "")}</code> · ${escapeHtml(data.human_decision || "")}</p>
  `;
}

let lastOutcomeId = null;
let capabilities = {
  github_ingest: true,
  query: true,
  preflight: true,
  sample_risk_run: true,
  clone_run: true,
  eval: true,
  accept_client_github_token: true,
};

function explainFetchError(err, base) {
  const msg = String(err && err.message ? err.message : err);
  if (/failed to fetch|networkerror|load failed/i.test(msg)) {
    return [
      `Cannot reach API at ${base}.`,
      "Open https://engram-cjph.onrender.com/try (same origin), or set website/config.js apiBase.",
      "Local builder: source .venv/bin/activate && python main.py serve → http://127.0.0.1:8000/try",
      "See docs/HOSTED_TRY.md",
    ].join("\n");
  }
  return msg;
}

async function api(path, options = {}) {
  const base = apiBase();
  let response;
  try {
    response = await fetch(`${base}${path}`, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
  } catch (err) {
    throw new Error(explainFetchError(err, base));
  }
  const text = await response.text();
  let body;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  if (!response.ok) {
    const detail = body && body.detail ? body.detail : body;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return body;
}

function applyCapabilities(caps) {
  capabilities = { ...capabilities, ...(caps || {}) };
  const clone = $("clone-run");
  if (clone) clone.hidden = capabilities.clone_run === false;
  const guideClone = $("guideClone");
  if (guideClone) guideClone.hidden = capabilities.clone_run === false;
  const tokenWrap = $("tokenWrap");
  if (tokenWrap) tokenWrap.hidden = capabilities.accept_client_github_token === false;
  const limitInput = $("limit");
  if (limitInput && capabilities.accept_client_github_token === false) {
    limitInput.value = Math.min(Number(limitInput.value || 30), 30);
    limitInput.max = 30;
  }
  const scope = $("scopeNote");
  if (scope && capabilities.clone_run === false) {
    scope.hidden = false;
  }
}

function watchGuide() {
  const cards = [...document.querySelectorAll(".try-guide-card[data-guide-for]")];
  if (!cards.length || !("IntersectionObserver" in window)) return;
  const sections = cards
    .map((card) => document.getElementById(card.getAttribute("data-guide-for")))
    .filter(Boolean);
  const observer = new IntersectionObserver(
    (entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (!visible) return;
      const id = visible.target.id;
      cards.forEach((card) => {
        card.classList.toggle("is-active", card.getAttribute("data-guide-for") === id);
      });
    },
    { rootMargin: "-20% 0px -55% 0px", threshold: [0.1, 0.35, 0.6] }
  );
  sections.forEach((section) => observer.observe(section));
}

async function boot() {
  $("apiBase").value = defaultApiBase();
  try {
    const meta = await api("/meta");
    applyCapabilities(meta.capabilities || {});
    const banner = $("hostedBanner");
    if (banner) banner.hidden = true;
    if (meta.scope && $("scopeNote")) {
      $("scopeNote").textContent = meta.scope;
      $("scopeNote").hidden = false;
    }
  } catch (err) {
    const banner = $("hostedBanner");
    if (banner && !isLocalHost() && !configuredApiBase()) {
      banner.hidden = false;
    }
    showText($("ingestOut"), String(err.message || err));
  }
}

$("healthBtn").addEventListener("click", async () => {
  try {
    showText($("ingestOut"), formatHealth(await api("/health")));
  } catch (err) {
    showText($("ingestOut"), String(err.message || err));
  }
});

$("ingestBtn").addEventListener("click", async () => {
  const payload = {
    repo: $("repo").value.trim(),
    limit: Number($("limit").value || 30),
  };
  const service = $("service").value.trim();
  const token = $("token") ? $("token").value.trim() : "";
  if (service) payload.service = service;
  if (token && capabilities.accept_client_github_token !== false) payload.token = token;
  try {
    showText($("ingestOut"), "Ingesting…");
    const result = await api("/ingest/github", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    showText($("ingestOut"), formatIngest(result));
    if (result.service) {
      $("askService").value = result.service;
      if ($("cloneService")) $("cloneService").value = result.service;
    }
  } catch (err) {
    showText($("ingestOut"), String(err.message || err));
  }
});

$("queryBtn").addEventListener("click", async () => {
  const service = $("askService").value.trim();
  try {
    showText($("askOut"), "Querying…");
    const result = await api("/query", {
      method: "POST",
      body: JSON.stringify({
        question: $("question").value.trim(),
        service: service || null,
        mode: "adaptive",
      }),
    });
    showHtml($("askOut"), formatQuery(result));
  } catch (err) {
    showText($("askOut"), String(err.message || err));
  }
});

$("preflightBtn").addEventListener("click", async () => {
  const service = $("askService").value.trim();
  if (!service) {
    showText($("askOut"), "Set a service name (from ingest) before preflight.");
    return;
  }
  try {
    showText($("askOut"), "Running preflight…");
    const result = await api("/preflight", {
      method: "POST",
      body: JSON.stringify({
        service,
        task: $("task").value.trim(),
        mode: "adaptive",
      }),
    });
    showHtml($("askOut"), formatPreflight(result));
  } catch (err) {
    showText($("askOut"), String(err.message || err));
  }
});

$("seedBtn").addEventListener("click", async () => {
  try {
    showText($("runOut"), "Seeding sample org…");
    $("resolveBox").hidden = true;
    const result = await api("/ingest/sample", { method: "POST", body: "{}" });
    showText(
      $("runOut"),
      `Sample org loaded (${result.store || "local"}). Next: Run agents on the Auth TTL task.`
    );
  } catch (err) {
    showText($("runOut"), String(err.message || err));
  }
});

$("runBtn").addEventListener("click", async () => {
  try {
    showText($("runOut"), "Running sample risk loop…");
    $("resolveBox").hidden = true;
    $("resolveOut").hidden = true;
    const result = await api("/run", {
      method: "POST",
      body: JSON.stringify({
        service: "Auth Service",
        task: $("riskTask").value.trim(),
        mode: "adaptive",
      }),
    });
    lastOutcomeId = result.outcome_id || null;
    showHtml($("runOut"), formatRun(result));
    $("resolveBox").hidden = !(result.human_required && lastOutcomeId);
  } catch (err) {
    showText($("runOut"), String(err.message || err));
  }
});

async function resolveDecision(decision) {
  if (!lastOutcomeId) {
    showText($("resolveOut"), "Run agents first so there is an outcome to resolve.");
    return;
  }
  try {
    showText($("resolveOut"), `Recording ${decision}…`);
    const result = await api(`/outcomes/${lastOutcomeId}/resolve`, {
      method: "POST",
      body: JSON.stringify({
        decision,
        note: $("resolveNote").value.trim(),
      }),
    });
    showText(
      $("resolveOut"),
      `${result.id}  ${result.gate}  ${result.human_decision}  merged=${result.merged}  ${result.human_note || ""}\nRun agents again to see this prior.`
    );
  } catch (err) {
    showText($("resolveOut"), String(err.message || err));
  }
}

$("rejectBtn").addEventListener("click", () => resolveDecision("rejected"));
$("approveBtn").addEventListener("click", () => resolveDecision("approved"));

if ($("cloneRunBtn")) {
  $("cloneRunBtn").addEventListener("click", async () => {
    const service = ($("cloneService").value || $("askService").value).trim();
    if (!service) {
      showText($("cloneOut"), "Ingest a repo first (or set the service name).");
      return;
    }
    const token = $("token") ? $("token").value.trim() : "";
    const payload = {
      service,
      task: $("cloneTask").value.trim(),
      mode: "adaptive",
    };
    if (token) payload.token = token;
    try {
      showText($("cloneOut"), "Cloning (if needed) and running… this may take a minute.");
      const result = await api("/run", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      showHtml($("cloneOut"), formatRun(result));
    } catch (err) {
      showText($("cloneOut"), String(err.message || err));
    }
  });
}

boot();
watchGuide();
