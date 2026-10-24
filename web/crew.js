// Shared helpers for Crew's pages.
// Fonts load without blocking the page, so a bad venue network can't stall it. Without them the system font is used.
try {
  const f = document.createElement("link");
  f.rel = "stylesheet";
  f.href = "https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&display=swap";
  document.head.appendChild(f);
} catch (e) { /* fonts are optional */ }

const Crew = (() => {
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[c]));

  // Never throws: a server that is restarting or unreachable comes back as { error }.
  async function api(url, body) {
    const opts = body === undefined ? {} : { method:"POST", headers:{ "Content-Type":"application/json" }, body:JSON.stringify(body) };
    try {
      const r = await fetch(url, opts);
      if (r.status === 401) return { error:"Crew needs its access token. Open any Crew page once with ?token=<token> on the end of the address, then come back." };
      return await r.json();
    } catch (e) {
      return { error:"Can't reach Crew. Check that `crew serve` is running, then try again." };
    }
  }

  // Order follows the journey: event side, then team side, then the demo.
  const LINKS = [["/", "Home"], ["/organizer", "Organizer"], ["/team", "Team"],
                 ["/sim", "Tap demo"], ["/viz", "Graph"]];
  function nav(active) {
    const el = document.createElement("nav");
    el.className = "top";
    el.setAttribute("aria-label", "Main");
    el.innerHTML =
      `<a class="brand" href="/" aria-label="Crew home"><span class="dots" aria-hidden="true"><i></i><i></i><i></i><i></i></span>Crew</a>
       <button class="menu" type="button" aria-expanded="false" aria-controls="navlinks">Menu</button>
       <div class="links" id="navlinks">${LINKS.map(([href, label]) =>
         `<a href="${href}"${href === active ? ' aria-current="page"' : ""}>${label}</a>`).join("")}</div>`;
    const btn = el.querySelector(".menu");
    btn.onclick = () => btn.setAttribute("aria-expanded", String(el.classList.toggle("open")));
    document.body.prepend(el);
    const skip = document.createElement("a");
    skip.className = "skip"; skip.href = "#main"; skip.textContent = "Skip to content";
    document.body.prepend(skip);
  }

  let toastTimer;
  function toast(message) {
    document.querySelectorAll(".toast").forEach(t => t.remove());
    const t = document.createElement("div");
    t.className = "toast"; t.setAttribute("role", "status"); t.textContent = message;
    document.body.appendChild(t);
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.remove(), 3500);
  }

  // Start a server-side build and stream its progress lines into `feed`. Resolves with the result.
  async function runBuild(kind, payload, feed) {
    feed.innerHTML = "";
    feed.setAttribute("role", "log");
    const started = await api("/api/build", { kind, payload });
    if (started.error) throw new Error(started.error);
    let since = 0;
    for (;;) {
      await new Promise(r => setTimeout(r, 400));
      const s = await api(`/api/build?since=${since}`);
      if (s.error) throw new Error(s.error);
      since = s.next;
      for (const e of s.events) {
        const line = document.createElement("div");
        line.className = e.level;
        line.textContent = (e.level === "ok" ? "✓ " : e.level === "warn" ? "! " : e.level === "error" ? "✗ " : "· ") + e.message;
        feed.appendChild(line);
        feed.scrollTop = feed.scrollHeight;
      }
      if (s.state === "done") return s.result;
      if (s.state === "error") throw new Error("The build stopped. The log above shows where.");
    }
  }

  return { esc, api, nav, toast, runBuild };
})();
