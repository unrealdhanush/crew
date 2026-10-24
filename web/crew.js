// Shared helpers for Crew's app pages.
const Crew = (() => {
  const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[c]));

  async function api(url, body) {
    const opts = body === undefined ? {} : { method:"POST", headers:{ "Content-Type":"application/json" }, body:JSON.stringify(body) };
    const r = await fetch(url, opts);
    return r.json();
  }

  const LINKS = [["/", "Home"], ["/organizer", "Organizer"], ["/team", "Team"], ["/sim", "Tap demo"], ["/viz", "Graph"]];
  function nav(active) {
    const el = document.createElement("nav");
    el.className = "top";
    el.innerHTML = `<a class="brand" href="/"><i></i>Crew</a>` +
      LINKS.slice(1).map(([href, label]) => `<a href="${href}" class="${href === active ? "on" : ""}">${label}</a>`).join("");
    document.body.prepend(el);
  }

  // Start a server-side build and stream its progress lines into `feed`. Resolves with the result.
  async function runBuild(kind, payload, feed) {
    feed.innerHTML = "";
    const started = await api("/api/build", { kind, payload });
    if (started.error) throw new Error(started.error);
    let since = 0;
    for (;;) {
      await new Promise(r => setTimeout(r, 400));
      const s = await api(`/api/build?since=${since}`);
      since = s.next;
      for (const e of s.events) {
        const line = document.createElement("div");
        line.className = e.level;
        line.textContent = (e.level === "ok" ? "✓ " : e.level === "warn" ? "! " : e.level === "error" ? "✗ " : "· ") + e.message;
        feed.appendChild(line);
        feed.scrollTop = feed.scrollHeight;
      }
      if (s.state === "done") return s.result;
      if (s.state === "error") throw new Error("Build failed: see the log above");
    }
  }

  return { esc, api, nav, runBuild };
})();
