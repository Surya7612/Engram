document.body.classList.add("js");

const canvas = document.querySelector("#scene");
const ctx = canvas?.getContext("2d");
const particles = [];
const particleCount = 90;
let width = window.innerWidth;
let height = window.innerHeight;
let pointerX = width * 0.5;
let pointerY = height * 0.5;
let darkTheme = true;
const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function resize() {
  width = window.innerWidth;
  height = window.innerHeight;
  if (!canvas || !ctx) return;
  canvas.width = width * Math.min(window.devicePixelRatio || 1, 2);
  canvas.height = height * Math.min(window.devicePixelRatio || 1, 2);
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;
  ctx.setTransform(canvas.width / width, 0, 0, canvas.height / height, 0, 0);
}

function initParticles() {
  particles.length = 0;
  for (let i = 0; i < particleCount; i += 1) {
    particles.push({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.3,
      r: Math.random() * 1.6 + 0.4
    });
  }
}

function draw() {
  if (!ctx) return;
  ctx.clearRect(0, 0, width, height);
  const color = darkTheme ? "122, 166, 255" : "90, 118, 176";
  const lineColor = darkTheme ? "120, 148, 220" : "130, 150, 195";
  for (const p of particles) {
    p.x += p.vx + (pointerX - width * 0.5) * 0.00001;
    p.y += p.vy + (pointerY - height * 0.5) * 0.00001;
    if (p.x < 0 || p.x > width) p.vx *= -1;
    if (p.y < 0 || p.y > height) p.vy *= -1;

    ctx.beginPath();
    ctx.fillStyle = `rgba(${color}, 0.55)`;
    ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
    ctx.fill();
  }

  for (let i = 0; i < particles.length; i += 1) {
    for (let j = i + 1; j < particles.length; j += 1) {
      const a = particles[i];
      const b = particles[j];
      const dx = a.x - b.x;
      const dy = a.y - b.y;
      const d = Math.sqrt(dx * dx + dy * dy);
      if (d < 95) {
        ctx.strokeStyle = `rgba(${lineColor}, ${(95 - d) / 520})`;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      }
    }
  }
  requestAnimationFrame(draw);
}

window.addEventListener("pointermove", (event) => {
  pointerX = event.clientX;
  pointerY = event.clientY;
});

window.addEventListener("resize", () => {
  resize();
  initParticles();
});

resize();
initParticles();
if (!prefersReducedMotion) {
  draw();
}

if ("IntersectionObserver" in window) {
  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      }
    },
    { threshold: 0.12 }
  );
  document.querySelectorAll(".reveal").forEach((el) => observer.observe(el));
} else {
  document.querySelectorAll(".reveal").forEach((el) => el.classList.add("is-visible"));
}

const themeToggle = document.querySelector("#themeToggle");
const root = document.body;
const savedTheme = localStorage.getItem("engram_theme");
if (savedTheme === "light") {
  root.dataset.theme = "light";
  darkTheme = false;
}

themeToggle?.addEventListener("click", () => {
  const next = root.dataset.theme === "light" ? "dark" : "light";
  if (next === "light") {
    root.dataset.theme = "light";
    darkTheme = false;
  } else {
    delete root.dataset.theme;
    darkTheme = true;
  }
  localStorage.setItem("engram_theme", next);
});

const accessModal = document.querySelector("#accessModal");
const openButtons = document.querySelectorAll(".open-access-modal");
const closeAccess = document.querySelector("#closeAccessModal");
const cancelAccess = document.querySelector("#cancelAccessModal");
const accessForm = document.querySelector("#accessForm");
const submitAccessBtn = document.querySelector("#submitAccessBtn");
const formStatus = document.querySelector("#formStatus");
let lastActiveElement = null;

function openModal() {
  if (!accessModal) return;
  lastActiveElement = document.activeElement;
  accessModal.classList.add("open");
  accessModal.setAttribute("aria-hidden", "false");
  if (formStatus) {
    formStatus.textContent = "";
    formStatus.classList.remove("success", "error");
  }
  const firstField = accessModal.querySelector("input, textarea, button");
  if (firstField) {
    setTimeout(() => firstField.focus(), 0);
  }
}

function closeModal() {
  if (!accessModal) return;
  accessModal.classList.remove("open");
  accessModal.setAttribute("aria-hidden", "true");
  if (lastActiveElement instanceof HTMLElement) {
    lastActiveElement.focus();
  }
}

openButtons.forEach((btn) => btn.addEventListener("click", openModal));
closeAccess?.addEventListener("click", closeModal);
cancelAccess?.addEventListener("click", closeModal);

accessModal?.addEventListener("click", (event) => {
  if (event.target === accessModal) closeModal();
});

window.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeModal();
  if (event.key === "Tab" && accessModal?.classList.contains("open")) {
    const focusable = accessModal.querySelectorAll(
      'button, [href], input, textarea, [tabindex]:not([tabindex="-1"])'
    );
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }
});

accessForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!submitAccessBtn || !formStatus || !accessForm) return;

  submitAccessBtn.disabled = true;
  const originalText = submitAccessBtn.textContent;
  submitAccessBtn.textContent = "Submitting...";
  formStatus.textContent = "Sending your request...";
  formStatus.classList.remove("success", "error");

  try {
    const formData = new FormData(accessForm);
    const response = await fetch(accessForm.action, {
      method: "POST",
      body: formData,
      headers: {
        Accept: "application/json"
      }
    });

    if (!response.ok) {
      throw new Error("Request failed");
    }

    formStatus.textContent = "Request submitted successfully. We will follow up soon.";
    formStatus.classList.add("success");
    accessForm.reset();
    setTimeout(() => {
      closeModal();
    }, 1200);
  } catch (error) {
    formStatus.textContent =
      "Could not submit right now. Please try again in a moment.";
    formStatus.classList.add("error");
  } finally {
    submitAccessBtn.disabled = false;
    submitAccessBtn.textContent = originalText;
  }
});

const liveRiskState = document.querySelector("#liveRiskState");
const livePrState = document.querySelector("#livePrState");
const liveIncidentState = document.querySelector("#liveIncidentState");

const liveStates = [
  { risk: "Risk: Medium", pr: "Review required", prClass: "review", incident: "Investigating", incidentClass: "warn" },
  { risk: "Risk: Medium-high", pr: "Owner review", prClass: "warn", incident: "Monitoring", incidentClass: "review" },
  { risk: "Risk: Medium", pr: "Approved", prClass: "ok", incident: "Resolved", incidentClass: "ok" }
];

let stateIndex = 0;
setInterval(() => {
  if (!liveRiskState || !livePrState || !liveIncidentState) return;
  stateIndex = (stateIndex + 1) % liveStates.length;
  const state = liveStates[stateIndex];

  liveRiskState.textContent = state.risk;
  livePrState.textContent = state.pr;
  liveIncidentState.textContent = state.incident;

  livePrState.className = `status-badge ${state.prClass}`;
  liveIncidentState.className = `status-badge ${state.incidentClass}`;
}, 3500);

const heroRight = document.querySelector(".hero-right");
const heroTiltCard = document.querySelector("#heroTiltCard");
const heroRiskCard = document.querySelector("#heroRiskCard");
if (heroRight && heroTiltCard && heroRiskCard && !prefersReducedMotion) {
  const setTilt = (xDeg, yDeg) => {
    heroTiltCard.style.setProperty("--tiltX", `${xDeg}deg`);
    heroTiltCard.style.setProperty("--tiltY", `${yDeg}deg`);
    heroRiskCard.style.setProperty("--tiltX", `${xDeg}deg`);
    heroRiskCard.style.setProperty("--tiltY", `${yDeg}deg`);
  };

  heroRight.addEventListener("pointermove", (event) => {
    const rect = heroRight.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width;
    const y = (event.clientY - rect.top) / rect.height;
    const rotateY = (x - 0.5) * 7.5;
    const rotateX = (0.5 - y) * 6.5;
    setTilt(rotateX, rotateY);
  });

  heroRight.addEventListener("pointerleave", () => {
    setTilt(0, 0);
  });
}

// Deterrent only: browser devtools cannot be truly disabled.
window.addEventListener("contextmenu", (event) => {
  event.preventDefault();
});

window.addEventListener("keydown", (event) => {
  const key = event.key.toLowerCase();
  const blocked =
    key === "f12" ||
    (event.ctrlKey && event.shiftKey && ["i", "j", "c"].includes(key)) ||
    (event.metaKey && event.altKey && ["i", "j", "c"].includes(key)) ||
    (event.ctrlKey && key === "u") ||
    (event.metaKey && key === "u");
  if (blocked) {
    event.preventDefault();
  }
});
