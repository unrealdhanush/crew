// Crew's guided tour: a spotlight walk through the real pages. No dependencies.
// crew.js loads this on demand. Progress is kept in localStorage so the tour carries from page to page.
const CrewTour = (() => {
  const KEY = "crew.tour";

  // One entry per page, in the order a first-time user needs them. `sel` is the element to highlight.
  const PAGES = [
    { path:"/", name:"Home", steps:[
      { sel:".cta", title:"Start here",
        text:"Running the event? Publish its agenda first. Going with a team? Connect your team. One laptop can do both." },
      { sel:"#status", title:"Your setup at a glance",
        text:"Three checks fill in as you go: the agenda, your team, and where they connect. The button on the right always shows what to do next." },
      { sel:".ask", title:"Ask the graph",
        text:"Pick a question to see the path Crew follows to answer it. Every answer shows its path, so you can check it yourself." },
    ] },
    { path:"/organizer", name:"Organizer", steps:[
      { sel:"#name", title:"Name your event",
        text:"The name appears on the door stickers and in the graph." },
      { sel:"#urls", title:"Add the agenda link",
        text:"Paste the link to the agenda page, one per line. Crew reads every session, speaker and technology on it." },
      { sel:"#publish", title:"Publish the agenda",
        text:"Crew reads the page and adds its sessions to the graph. Progress shows below the button while it works." },
      { sel:"#sample", title:"No agenda yet? Use the sample",
        text:"The sample agenda has four made-up sessions, so you can try the whole app without any links." },
      { sel:".graphpane", title:"Watch the graph grow",
        text:"Each session Crew finds appears here. This is the graph your whole team will share." },
    ] },
    { path:"/stickers", name:"Door stickers", steps:[
      { sel:"#base", title:"Set the address phones open",
        text:"Phones can't open 127.0.0.1 or localhost. Use your laptop's network address, like http://192.168.1.20:8765." },
      { sel:"#print", title:"Print the stickers",
        text:"Print one per session, or write each address to an NFC tag. Phones without NFC can scan the QR code." },
      { sel:"#sheet", title:"One sticker per session",
        text:"Each sticker shows the session, its time and room, and a QR code. Stick it next to the door." },
    ] },
    { path:"/team", name:"Team", steps:[
      { sel:"#teamname", title:"Name your team",
        text:"This labels your team in the graph and in the plan." },
      { sel:".member input[data-f=handle]", title:"Add a teammate",
        text:"Enter their GitHub username. Add one card for each person going to the conference." },
      { sel:".member [data-a=find]", title:"Find their repos",
        text:"Crew lists their public repos. Tick the ones they work on. Crew reads dependency lists only, never source code." },
      { sel:"details.private", title:"Private repos",
        text:"Add your GitHub org and a read-only token here to include private repos. The token is never saved." },
      { sel:"#add", title:"Add more teammates",
        text:"Repeat for everyone who is going. The more people you add, the better the plan covers the schedule." },
      { sel:"#build", title:"Build the team graph",
        text:"Crew reads the dependencies, joins them to the agenda and plans who goes where. The button turns on once a username is entered." },
      { sel:".graphpane", title:"See the connections",
        text:"Your repos and packages join the agenda here. Where they meet is where a session matters to you." },
    ] },
    { path:"/sim", name:"Tap demo", steps:[
      { sel:"#who", title:"Pick whose phone it is",
        text:"The demo acts out a teammate walking up to a door with their phone." },
      { sel:"#list", title:"Tap a door",
        text:"Click a session, or press 1 to 9. It works like holding a phone near a sticker." },
      { sel:".phone", title:"The check-in screen",
        text:"The phone shows why this session matters to that person, and a box to save one line from the room." },
      { sel:"#graph", title:"The path lights up",
        text:"The graph highlights the path behind what just happened, so you can see why Crew said it." },
    ] },
    { path:"/viz", name:"Graph", steps:[
      { sel:"#legend", title:"What the colors mean",
        text:"Each color is a type of thing: people, repos, packages, sessions, notes and more." },
      { sel:"#focus", title:"Bridges or everything",
        text:"By default the graph shows only bridges, the places where your code meets the conference. Switch to see all of it." },
      { sel:"#paths", title:"The latest answer",
        text:"The highlighted path is the latest answer. Tap a door or ask Crew a question to light one up. You're all set." },
    ] },
  ];

  const TOTAL = PAGES.reduce((n, p) => n + p.steps.length, 0);
  const before = p => PAGES.slice(0, p).reduce((n, x) => n + x.steps.length, 0);
  const here = () => PAGES.findIndex(x => x.path === (location.pathname.replace(/\/+$/, "") || "/"));
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(v, hi));

  // Progress survives page loads in localStorage. If storage is blocked, the next page is opened with ?tour=1 instead.
  let mem = null;
  const read = () => { try { return JSON.parse(localStorage.getItem(KEY)) || mem; } catch { return mem; } };
  const write = st => { mem = st; try { st ? localStorage.setItem(KEY, JSON.stringify(st)) : localStorage.removeItem(KEY); } catch {} };
  const storageWorks = () => { try { localStorage.setItem(KEY + ".t", "1"); localStorage.removeItem(KEY + ".t"); return true; } catch { return false; } };
  const valid = st => st && PAGES[st.p] && PAGES[st.p].steps[st.s];

  let ui = null, seq = 0, target = null, opener = null, inerted = [], raf = 0;

  function ensureUI() {
    if (ui) return;
    const root = document.createElement("div");
    root.className = "tour-root";
    root.innerHTML = `
      <div class="tour-shield"></div>
      <div class="tour-spot" hidden></div>
      <div class="tour-pop" role="dialog" aria-labelledby="tour-t" aria-describedby="tour-d">
        <div class="tour-meta"><span class="tour-where"></span><span class="tour-count"></span></div>
        <div class="tour-bar" aria-hidden="true"><i></i></div>
        <div aria-live="polite"><h2 id="tour-t"></h2><p id="tour-d"></p></div>
        <div class="tour-actions">
          <button type="button" class="link-btn tour-skip">Skip tour</button><span class="spacer"></span>
          <button type="button" class="btn small ghost tour-back">Back</button>
          <button type="button" class="btn small tour-next">Next</button>
        </div>
      </div>`;
    document.body.appendChild(root);
    const q = s => root.querySelector(s);
    ui = { root, shield:q(".tour-shield"), spot:q(".tour-spot"), pop:q(".tour-pop"), where:q(".tour-where"), count:q(".tour-count"),
           bar:q(".tour-bar i"), title:q("#tour-t"), text:q("#tour-d"), back:q(".tour-back"), next:q(".tour-next") };
    q(".tour-skip").onclick = () => close(true);
    ui.back.onclick = () => go(-1);
    ui.next.onclick = () => go(1);
    // Everything behind the tour is inert: no stray clicks, and Tab stays inside the card.
    inerted = [...document.body.children].filter(el => el !== root && !el.inert);
    inerted.forEach(el => { el.inert = true; });
    addEventListener("resize", schedule);
    addEventListener("scroll", schedule, true);
    document.addEventListener("keydown", onKey);
  }

  function onKey(e) {
    if (e.key === "Escape") { e.preventDefault(); close(true); }
    else if (e.key === "ArrowRight") { e.preventDefault(); go(1); }
    else if (e.key === "ArrowLeft") { e.preventDefault(); go(-1); }
  }
  function schedule() { cancelAnimationFrame(raf); raf = requestAnimationFrame(place); }

  function waitFor(sel, ms) {
    return new Promise(res => {
      const t0 = Date.now();
      (function tick() {
        const el = document.querySelector(sel);
        if (el && el.getClientRects().length) return res(el);
        if (Date.now() - t0 > ms) return res(null);
        setTimeout(tick, 100);
      })();
    });
  }

  async function show(st) {
    const my = ++seq, page = PAGES[st.p], step = page.steps[st.s];
    opener = opener || document.activeElement;
    ensureUI();
    const n = before(st.p) + st.s + 1, last = st.s === page.steps.length - 1, nextPage = PAGES[st.p + 1];
    ui.where.textContent = page.name;
    ui.count.textContent = `Step ${n} of ${TOTAL}`;
    ui.bar.style.width = `${(n / TOTAL) * 100}%`;
    ui.title.textContent = step.title;
    ui.text.textContent = step.text;
    ui.back.disabled = st.p === 0 && st.s === 0;
    ui.next.textContent = last ? (nextPage ? `Next: ${nextPage.name}` : "Finish") : "Next";
    target = await waitFor(step.sel, 2500);   // the page may still be loading data; if it never shows, explain without a highlight
    if (my !== seq) return;
    if (target) {
      target.scrollIntoView({ block:"center", inline:"nearest" });
      if (innerWidth < 640) {                   // on phones the card docks at the bottom: keep the target above it
        const room = innerHeight - ui.pop.offsetHeight - 24, r = target.getBoundingClientRect();
        if (r.bottom > room) scrollBy(0, Math.min(r.bottom - room, r.top - 72));
      }
    }
    place();
    ui.next.focus({ preventScroll:true });
  }

  function place() {
    if (!ui) return;
    const vw = innerWidth, vh = innerHeight, pop = ui.pop, dock = vw < 640, pad = 8, gap = 14;
    pop.style.left = pop.style.top = pop.style.right = pop.style.bottom = "";
    pop.style.width = dock ? "" : Math.min(360, vw - 24) + "px";
    ui.shield.classList.toggle("dim", !target);
    if (!target) {
      ui.spot.hidden = true;
      pop.style.left = (vw - pop.offsetWidth) / 2 + "px";
      pop.style.top = Math.max(12, (vh - pop.offsetHeight) / 2) + "px";
      return;
    }
    const r = target.getBoundingClientRect();
    ui.spot.hidden = false;
    Object.assign(ui.spot.style, { left:r.left - pad + "px", top:r.top - pad + "px", width:r.width + pad * 2 + "px", height:r.height + pad * 2 + "px" });
    if (dock) { pop.style.left = "12px"; pop.style.right = "12px"; pop.style.bottom = "12px"; return; }
    const pw = pop.offsetWidth, ph = pop.offsetHeight;
    const cx = clamp(r.left + r.width / 2 - pw / 2, 12, vw - pw - 12), cy = clamp(r.top + r.height / 2 - ph / 2, 12, vh - ph - 12);
    let x, y;
    if (vh - r.bottom - pad >= ph + gap) { x = cx; y = r.bottom + pad + gap; }          // below
    else if (r.top - pad >= ph + gap) { x = cx; y = r.top - pad - gap - ph; }            // above
    else if (vw - r.right - pad >= pw + gap) { x = r.right + pad + gap; y = cy; }        // right
    else if (r.left - pad >= pw + gap) { x = r.left - pad - gap - pw; y = cy; }          // left
    else { x = (vw - pw) / 2; y = vh - ph - 16; }                                        // a large target: dock at the bottom
    pop.style.left = x + "px"; pop.style.top = y + "px";
  }

  function go(delta) {
    const st = read();
    if (!valid(st)) return close(true);
    let { p, s } = st;
    s += delta;
    if (s < 0) { if (p === 0) return; p--; s = PAGES[p].steps.length - 1; }
    else if (s >= PAGES[p].steps.length) { if (p === PAGES.length - 1) return finish(); p++; s = 0; }
    write({ p, s });
    if (p !== st.p) { location.href = PAGES[p].path + (storageWorks() ? "" : "?tour=1"); return; }
    show({ p, s });
  }

  function close(clear) {
    seq++;
    if (clear) write(null);
    removeEventListener("resize", schedule);
    removeEventListener("scroll", schedule, true);
    document.removeEventListener("keydown", onKey);
    inerted.forEach(el => { el.inert = false; });
    inerted = [];
    if (ui) ui.root.remove();
    ui = null; target = null;
    if (opener && opener.isConnected) opener.focus({ preventScroll:true });
    opener = null;
  }
  function finish() {
    close(true);
    if (typeof Crew !== "undefined") Crew.toast("Tour finished. Choose Tour in the menu any time to see it again.");
  }

  // Start from the first step of the page you're on, or from Home if this page isn't part of the tour.
  function start() {
    if (/[?&]tour=1\b/.test(location.search)) history.replaceState(null, "", location.pathname + location.hash);
    const p = here();
    if (p < 0) { write({ p:0, s:0 }); location.href = "/"; return; }
    write({ p, s:0 });
    show({ p, s:0 });
  }
  // Pick up where the last page left off.
  function resume() {
    const st = read();
    if (!st) return;
    if (!valid(st) || st.p !== here()) { write(null); return; }   // the person left the tour another way
    show(st);
  }

  return { start, resume };
})();
window.CrewTour = CrewTour;
