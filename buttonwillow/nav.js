// Site navigation bar shared by every page. Load it with a plain <script src="nav.js"></script>
// right after an explicit <body> tag (without one, the parser would put the script in <head>); it replaces its own script tag, so the bar renders before the page.
(() => {
  const PAGES = [
    ["index.html", "#619 stints"],
    ["field.html", "Top 20 &amp; class B gap"],
  ];
  const EXTERNAL = [["https://speedhive.mylaps.com/sessions/12906863", "Official results ↗"]];
  const file = location.pathname.split("/").pop();
  const current = PAGES.some(([h]) => h === file) ? file : PAGES[0][0];
  const css = `
.topnav{position:sticky;top:0;z-index:10;background:var(--ink);color:var(--bg)}
.topnav .in{max-width:1180px;margin:0 auto;padding:0 16px;display:flex;flex-wrap:wrap;align-items:center;gap:0 20px;min-height:46px}
.topnav a{color:inherit;text-decoration:none}
.topnav .brand{font:700 18px "Barlow Condensed",sans-serif;text-transform:uppercase;letter-spacing:.04em;padding-block:10px;white-space:nowrap}
.topnav .brand span{opacity:.6;font-weight:600;margin-left:.35em}
.topnav .links{display:flex;flex-wrap:wrap;margin-left:auto}
.topnav .links a{font:600 14px "Barlow Condensed",sans-serif;letter-spacing:.07em;text-transform:uppercase;padding:13px 10px 10px;border-bottom:3px solid transparent;opacity:.72;white-space:nowrap}
.topnav .links a:hover{opacity:1}
.topnav .links a[aria-current="page"]{opacity:1;border-bottom-color:currentColor}
@media (max-width:560px){.topnav .links{margin-left:-10px}}`;
  const style = document.createElement("style");
  style.textContent = css;
  document.head.appendChild(style);
  const nav = document.createElement("nav");
  nav.className = "topnav";
  nav.setAttribute("aria-label", "Site");
  nav.innerHTML = `<div class="in"><a class="brand" href="${PAGES[0][0]}">Lemons<span>Buttonwillow 2026</span></a><div class="links">` +
    PAGES.map(([h, t]) => `<a href="${h}"${h === current ? ' aria-current="page"' : ""}>${t}</a>`).join("") +
    EXTERNAL.map(([h, t]) => `<a href="${h}">${t}</a>`).join("") + `</div></div>`;
  document.currentScript.replaceWith(nav);
})();
