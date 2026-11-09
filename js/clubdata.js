// Shared loading for the club map and the club area editor.
//
// Player figures:  data/players/manifest.json lists one CSV per county and code,
//                  each with a "club" column then one column per year.
// Club areas:      data/clubs/<county>_eds.topo.json   electoral divisions + population by sex
//                  data/clubs/<county>_areas.json      electoral division id -> club
//                  data/clubs/<county>_anchors.json    places each club is centred on
const ClubData = (() => {
  const SEX = { hurling: "m", football: "m", camogie: "f", ladies: "f" };
  const CODE_NAMES = { hurling: "Hurling", football: "Gaelic football", camogie: "Camogie", ladies: "Ladies football" };

  function parseCSV(text) {
    const rows = [];
    for (const line of text.replace(/\r/g, "").split("\n")) {
      if (!line.trim()) continue;
      const cells = []; let cur = "", q = false;
      for (const ch of line) {
        if (ch === '"') q = !q;
        else if (ch === "," && !q) { cells.push(cur); cur = ""; }
        else cur += ch;
      }
      cells.push(cur); rows.push(cells.map(s => s.trim()));
    }
    return rows;
  }

  async function json(url) {
    const r = await fetch(url, { cache: "no-store" });
    if (!r.ok) throw new Error(`${url}: ${r.status}`);
    return r.json();
  }

  async function manifest() {
    try { return await json("data/players/manifest.json"); } catch { return []; }
  }

  async function loadPlayers(entry) {
    const r = await fetch(`data/players/${entry.file}`, { cache: "no-store" });
    if (!r.ok) throw new Error(`${entry.file}: ${r.status}`);
    const [head, ...rows] = parseCSV(await r.text());
    const years = head.slice(1).map(Number);
    const players = {};
    rows.forEach(r => { players[r[0]] = Object.fromEntries(years.map((y, i) => [y, +r[i + 1] || 0])); });
    return { years, players };
  }

  async function loadAreas(county) {
    const c = county.toLowerCase();
    const [topo, areas, anchors] = await Promise.all([
      json(`data/clubs/${c}_eds.topo.json`), json(`data/clubs/${c}_areas.json`), json(`data/clubs/${c}_anchors.json`),
    ]);
    return { topo, areas, anchors, eds: topo.objects.eds.geometries };
  }

  // Sum population and list electoral divisions for each club.
  function clubStats(eds, assignments) {
    const out = {};
    eds.forEach(g => {
      const club = assignments[g.properties.id];
      if (!club) return;
      const s = out[club] ||= { eds: [], f: 0, m: 0 };
      s.eds.push(g); s.f += g.properties.f; s.m += g.properties.m;
    });
    return out;
  }

  return { SEX, CODE_NAMES, manifest, loadPlayers, loadAreas, clubStats };
})();
