// When Try is served from the API host (/try), empty apiBase uses same-origin.
// Set explicitly so Vercel marketing/static Try can still reach the hosted API.
window.ENGRAM_CONFIG = {
  apiBase: "https://engram-cjph.onrender.com",
};
