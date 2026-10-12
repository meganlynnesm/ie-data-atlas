/*
  map.js : what the page DOES
  ============================
  The plan, in order:
    1. Settings      : sizes, colours, the list of layers
    2. Load data     : read the GeoJSON files 
    3. Projection    : turn longitude/latitude into x/y pixels
    4. Draw layers   : one SVG "plane" per layer
    5. Poles         : vertical lines through key places
    6. Legend        : built from the same layer list
    7. Animation     : move the --t dial from 0 (flat) to 1 (axo)

  JavaScript basics used below:
    const x = 5;          a named value that won't be reassigned
    let y = 5;            a named value that CAN change later
    [a, b, c]             an array (a list)
    { key: value }        an object (like a Python dictionary)
    (a) => a * 2          an "arrow function": takes a, returns a * 2
    `text ${x}`           a template string: ${x} is filled in (like Python f"")
*/


// =====================================================================
// 1. SETTINGS
// =====================================================================

// Size of each map plane in pixels.
const WIDTH = 520;
const HEIGHT = 640;

// The project palette (same as the CSS variables).
const C = {
  oat:        "#F1EDE0",
  dustyBlush: "#ECCBD1",
  pistache:   "#B9AC39",
  olive:      "#433B0C",
  berry:      "#D6338A",
  offBlack:   "#15120F",
};

// Colours that change with the Day/Night theme are NOT written here.
// Instead we point at the CSS role variables, e.g. "var(--ink)", and set
// them with .style() rather than .attr(), because only CSS styles
// understand var(). Switch the theme and these update by themselves.
const INK = "var(--ink)";
const LAND = "var(--land)";

// Peat types from the Irish Peat Soils Map, keyed by the code in the data.
// The palette has one soft pink (dusty blush), so the five types are
// lighter and deeper shades of it, with "other peat" a greyer blush.
const PEAT_TYPES = {
  1: { name: "Raised bog",           colour: "#C47F8E" },  // deep blush
  2: { name: "Lowland blanket bog",  colour: "#D9A3AE" },  // mid blush
  3: { name: "Mountain blanket bog", colour: "#ECCBD1" },  // dusty blush
  4: { name: "Fen",                  colour: "#9E5469" },  // darkest blush
  5: { name: "Other peat soil",      colour: "#B9A7A2" },  // grey blush
};

// Where the data lives (relative to index.html).
const DATA = "data/processed/";

// THE LAYER LIST. Order = bottom to top in the stack.
// Everything else (planes, legend, labels) is built from this list,
// so to add a layer later you add one entry here and write its draw().
// Each draw() gets: g (the SVG group to draw into), path (the shape drawer),
// projection (lon/lat -> x/y) and d (all the loaded data).
const LAYERS = [
  {
    id: "base",
    name: "Island & counties",
    desc: "The island of Ireland, with county lines drawn. Northern Ireland is part of the base map, so it is always visible.",
    // Where the data comes from. Shown as clickable links in the legend.
    sources: [{ label: "Natural Earth", url: "https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-1-states-provinces/" }],
    draw: (g, path, projection, d) => {
      // Fill the island faintly, then draw county lines on top.
      g.append("path")
        .datum(d.outline)                // .datum() attaches one piece of data
        .attr("d", path)                 // "d" is the SVG attribute for a shape's outline
        .style("fill", LAND)
        .style("stroke", INK)
        .attr("stroke-width", 0.8);

      // .selectAll().data().join() is D3's core pattern:
      // "for every feature in the data, make one <path>".
      g.selectAll("path.county")
        .data(d.counties.features)
        .join("path")
        .attr("class", "county")
        .attr("d", path)
        .attr("fill", "none")
        .style("stroke", INK)
        .attr("stroke-opacity", 0.22)
        .attr("stroke-width", 0.5);
    },
    key: () => `<svg width="28" height="12"><rect x="1" y="1" width="26" height="10" style="fill:var(--land);stroke:var(--ink)" stroke-width=".8"/></svg> county lines`,
  },

  {
    id: "peat",
    name: "Peat soils",
    sources: [
      { label: "Gilet et al. 2024, Geoderma", url: "https://www.sciencedirect.com/science/article/pii/S0016706124001629" },
      { label: "IPSM data (CC BY 4.0)", url: "https://osf.io/27hj3/" },
      { label: "OpenStreetMap (NI)", url: "https://www.openstreetmap.org/copyright" },
    ],
    desc: "Main peat type in each ~1.3 km square, from the Irish Peat Soils Map by IPCC " +
          "(Gilet et al. 2024). Brighter = more of the square is peat. " +
          "This only covers the Republic of Ireland, Northern Ireland shown with OpenStreetMap bogs as outlines TBA.",
    draw: (g, path, projection, d) => {
      // The IPSM squares and the OSM (Northern Ireland) squares are drawn
      // differently, so we split them with .filter() first.
      const ipsm = d.peat.features.filter((f) => f.properties.source === "ipsm");
      const osm = d.peat.features.filter((f) => f.properties.source === "osm");

      g.selectAll("path.ipsm")
        .data(ipsm)
        .join("path")
        .attr("class", "ipsm")
        .attr("d", path)
        // Look up this square's colour from its peat type code.
        .attr("fill", (f) => PEAT_TYPES[f.properties.type_code].colour)
        // An arrow function as the value: D3 calls it once per feature (f),
        // so each square gets its own opacity from its "coverage" value.
        .attr("fill-opacity", (f) => 0.2 + 0.8 * f.properties.coverage);

      // OSM squares: outline only, to show they come from a weaker source.
      g.selectAll("path.osm")
        .data(osm)
        .join("path")
        .attr("class", "osm")
        .attr("d", path)
        .attr("fill", "none")
        .attr("stroke", PEAT_TYPES[1].colour)
        .attr("stroke-width", 0.6);
    },
    // Object.values() turns the PEAT_TYPES object into a list we can loop over.
    key: () => Object.values(PEAT_TYPES).map((t) =>
      `<span style="display:inline-flex;align-items:center;gap:4px;margin-right:6px">
         <svg width="10" height="10"><rect width="10" height="10" fill="${t.colour}"/></svg>${t.name}</span>`
    ).join("") +
      `<span style="display:inline-flex;align-items:center;gap:4px">
         <svg width="10" height="10"><rect x=".5" y=".5" width="9" height="9" fill="none" stroke="${PEAT_TYPES[1].colour}"/></svg>NI bog (OSM)</span>`,
  },

  {
    id: "wind",
    name: "Wind farms",
    sources: [{ label: "OpenStreetMap (ODbL)", url: "https://www.openstreetmap.org/copyright" }],
    desc: "Wind farms sourced from OpenStreetMap Data and sized by total capacity (MW).",
    draw: (g, path, projection, d) => {
      // A square-root scale: circle AREA (not radius) grows with MW,
      // which is how our eyes judge circle size.
      const r = d3.scaleSqrt().domain([0, 200]).range([1.5, 13]);

      g.selectAll("circle")
        .data(d.wind.features)
        .join("circle")
        // projection([lon, lat]) returns [x, y] in pixels.
        .attr("cx", (f) => projection(f.geometry.coordinates)[0])
        .attr("cy", (f) => projection(f.geometry.coordinates)[1])
        // "??" means: use the left value, but if it's missing use the right one.
        .attr("r", (f) => r(f.properties.mw ?? 5))
        .attr("fill", "none")
        .style("stroke", INK)
        .attr("stroke-opacity", 0.75)
        .attr("stroke-width", 0.8);
    },
    key: () => [5, 50, 190].map((mw) => {
      const r = d3.scaleSqrt().domain([0, 200]).range([1.5, 13])(mw);
      return `<svg width="${2 * r + 2}" height="28"><circle cx="${r + 1}" cy="14" r="${r}" fill="none" style="stroke:var(--ink)"/></svg>`;
    }).join("") + " 5 · 50 · 190 MW",
  },

  {
    id: "broadband",
    name: "Broadband speed",
    sources: [{ label: "Speedtest® by Ookla®, Q2 2026 (CC BY-NC-SA 4.0)", url: "https://github.com/teamookla/ookla-open-data" }],
    desc: "Average fixed download speed from Ookla speed tests. Slower speeds are drawn bigger and in dark green.",
    draw: (g, path, projection, d) => {
      // speed_class goes 1 (slowest, under 30 Mbps) to 5 (fastest, 500+).
      // Colour ramp: olive (slow, dark end) -> pistache (fast, light end).
      // Size runs the other way so SLOW areas still stand out.
      const size = d3.scaleLinear().domain([1, 5]).range([2.4, 0.7]);
      const colour = d3.scaleLinear().domain([1, 5]).range([C.olive, C.pistache]);

      g.selectAll("circle")
        .data(d.broadband.features)
        .join("circle")
        // path.centroid() finds the middle of each square, in pixels.
        .attr("cx", (f) => path.centroid(f)[0])
        .attr("cy", (f) => path.centroid(f)[1])
        .attr("r", (f) => size(f.properties.speed_class))
        .attr("fill", (f) => colour(f.properties.speed_class));
    },
    key: () => {
      const size = d3.scaleLinear().domain([1, 5]).range([2.4, 0.7]);
      const colour = d3.scaleLinear().domain([1, 5]).range([C.olive, C.pistache]);
      const labels = ["&lt;30", "30–100", "100–250", "250–500", "500+ Mbps"];
      // One dot + label per speed group.
      return labels.map((label, i) =>
        `<span style="display:inline-flex;align-items:center;gap:3px;margin-right:4px">
           <svg width="8" height="12"><circle cx="4" cy="6" r="${size(i + 1)}" fill="${colour(i + 1)}"/></svg>${label}</span>`
      ).join("");
    },
  },

  {
    id: "datacentres",
    name: "Data centres",
    sources: [{ label: "OpenStreetMap (ODbL)", url: "https://www.openstreetmap.org/copyright" }],
    desc: "Data centres mapped using OpenStreetMap Data.",
    draw: (g, path, projection, d) => {
      const pts = d.dc.features.map((f) => projection(f.geometry.coordinates));
      // A soft dusty-blush glow first, then a berry dot with an oat ring.
      g.selectAll("circle.halo").data(pts).join("circle")
        .attr("class", "halo")
        .attr("cx", (p) => p[0]).attr("cy", (p) => p[1])
        .attr("r", 9).attr("fill", C.dustyBlush).attr("fill-opacity", 0.55);
      g.selectAll("circle.dot").data(pts).join("circle")
        .attr("class", "dot")
        .attr("cx", (p) => p[0]).attr("cy", (p) => p[1])
        .attr("r", 3.2).attr("fill", C.berry)
        .attr("stroke", C.oat).attr("stroke-width", 0.8);
    },
    key: () => `<svg width="16" height="16"><circle cx="8" cy="8" r="7" fill="${C.dustyBlush}" fill-opacity=".5"/><circle cx="8" cy="8" r="2.8" fill="${C.berry}" stroke="${C.oat}" stroke-width=".8"/></svg> one site`,
  },
];

// Places where a vertical line pierces every layer (like the reference).
// [longitude, latitude] and a label. The count for Dublin is calculated later.
// "side" says which side of the line the text goes, so labels don't collide.
const POLES = [
  { lonlat: [-6.38, 53.36], label: "Dublin", side: "right" },
  { lonlat: [-9.55, 54.15], label: "Oweninny, Mayo · 192 MW capacity wind farmon bog", side: "left" },
  { lonlat: [-9.06, 53.28], label: "Galway", side: "left" },
  { lonlat: [-7.90, 53.43], label: "Athlone", side: "right" },
  { lonlat: [-8.47, 51.90], label: "Cork", side: "right" },
];


// =====================================================================
// 2. LOAD DATA
// d3.json() fetches a file. It is "asynchronous": the file takes time to
// arrive, so it returns a Promise (an IOU). Promise.all waits for ALL of
// them, then hands us the results in the same order.
// "async" / "await" let us write that waiting as if it were normal code.
// =====================================================================
async function loadData() {
  const files = ["ireland_outline", "counties", "peatland_grid",
                 "wind_farms", "broadband_grid", "data_centres"];
  const [outline, counties, peat, wind, broadband, dc] =
    await Promise.all(files.map((f) => d3.json(`${DATA}${f}.geojson`)));

  // Fix the "winding order" of polygon shapes (see fixWinding below).
  [outline, counties, peat, broadband].forEach(fixWinding);
  return { outline, counties, peat, wind, broadband, dc };
}

// A well-known D3 gotcha.
// A polygon is a ring of points, and the ring can run clockwise or
// anticlockwise. Python tools save outer rings ANTICLOCKWISE (the GeoJSON
// standard). D3 works on a sphere and expects CLOCKWISE, otherwise it thinks
// you mean "the whole Earth EXCEPT this shape", and the map comes out blank
// or filled solid. If a shape's area is more than half the globe (2π), it
// must be backwards, so we reverse its rings.
function fixWinding(geojson) {
  for (const f of geojson.features) {
    const g = f.geometry;
    if (d3.geoArea(f) > 2 * Math.PI) {
      const polys = g.type === "Polygon" ? [g.coordinates] : g.coordinates;
      polys.forEach((rings) => rings.forEach((ring) => ring.reverse()));
    }
  }
}


// =====================================================================
// 3 to 7: BUILD EVERYTHING once the data has arrived
// =====================================================================
async function main() {
  const d = await loadData();

  // ---- 3. PROJECTION -------------------------------------------------
  // The Earth is round; the screen is flat. A projection is the rule for
  // flattening. We copy Irish Transverse Mercator (EPSG:2157): a transverse
  // Mercator centred on 8°W, 53.5°N. fitExtent() then picks the zoom so
  // the island fills our box with a 30 px margin.
  const projection = d3.geoTransverseMercator()
    .rotate([8, -53.5])
    .fitExtent([[30, 30], [WIDTH - 30, HEIGHT - 30]], d.outline);

  // geoPath turns GeoJSON shapes into SVG drawing instructions,
  // using our projection.
  const path = d3.geoPath(projection);

  // ---- 4. PLANES -----------------------------------------------------
  const stack = d3.select("#stack")
    .style("width", `${WIDTH}px`)
    .style("height", `${HEIGHT}px`);

  // forEach runs the function once per layer; i is its position (0, 1, 2...).
  LAYERS.forEach((layer, i) => {
    const plane = stack.append("div")
      .attr("class", "plane")
      .attr("data-layer", layer.id)
      .style("--i", i);                      // the CSS uses --i to lift this plane

    plane.append("div").attr("class", "frame");
    plane.append("div").attr("class", "label")
      .text(`${String(i + 1).padStart(2, "0")}  ${layer.name}`);

    const svg = plane.append("svg")
      .attr("viewBox", `0 0 ${WIDTH} ${HEIGHT}`)
      .attr("width", WIDTH)
      .attr("height", HEIGHT);

    layer.draw(svg.append("g"), path, projection, d);
  });

  // ---- 5. POLES ------------------------------------------------------
  // Count data centres near Dublin, to put the number in its label.
  // d3.geoDistance gives the angle between two points in radians;
  // multiply by Earth's radius (6371 km) for kilometres.
  const nearDublin = d.dc.features.filter(
    (f) => d3.geoDistance(f.geometry.coordinates, POLES[0].lonlat) * 6371 < 30
  ).length;
  POLES[0].label = `Dublin · ${nearDublin} mapped data centres`;

  const topZ = (LAYERS.length - 1);          // number of gaps between layers
  POLES.forEach((pole, k) => {
    // Each label sits a bit higher than the last so they don't overlap.
    const extra = 30 + k * 40;
    const [x, y] = projection(pole.lonlat);

    // The line: starts at the bottom plane, stands up through all layers.
    stack.append("div")
      .attr("class", "pole")
      .style("left", `${x}px`)
      .style("top", `${y}px`)
      .style("height", `calc((${topZ} * var(--gap) + ${extra}px) * var(--t))`);

    // The label: lifted to the top, then turned to face the viewer by
    // undoing the stack's rotations in reverse order (see style.css).
    stack.append("div")
      .attr("class", "pole-label")
      .style("left", `${x}px`)
      .style("top", `${y}px`)
      .style("transform",
        `translateZ(calc((${topZ} * var(--gap) + ${extra + 4}px) * var(--t)))
         rotateZ(calc(var(--t) * var(--spin) * -1))
         rotateX(calc(var(--t) * var(--tilt) * -1))
         scale(calc(1 / (1 - var(--t) * var(--shrink))))`)
      // The text goes in an inner <span> so we can push it to one side.
      .append("span")
      .attr("class", pole.side)
      .text(pole.label);
  });

  // ---- 6. LEGEND -----------------------------------------------------
  // .slice().reverse() copies the list and flips it, so the legend reads
  // top layer first, matching the stack.
  const legend = d3.select("#legend");
  LAYERS.slice().reverse().forEach((layer) => {
    const n = LAYERS.indexOf(layer) + 1;
    // The plane on the map that belongs to this legend item.
    const plane = stack.select(`.plane[data-layer="${layer.id}"]`);

    const item = legend.append("li")
      // role/tabindex/aria-pressed make the item work like a button for
      // keyboard users and screen readers, not just for mouse clicks.
      .attr("role", "button")
      .attr("tabindex", 0)
      .attr("aria-pressed", "true")
      .html(`<span class="box" aria-hidden="true"></span>
             <span class="name"><span class="num">${String(n).padStart(2, "0")}</span>${layer.name}</span>
             <span class="desc">${layer.desc}</span>
             <span class="key">${layer.key()}</span>
             <span class="src">Source: ${layer.sources.map((src) =>
               `<a href="${src.url}" target="_blank" rel="noopener">${src.label}</a>`).join(" · ")}</span>`);

    // CLICK = turn the layer on or off.
    // classed("off", ...) adds the class "off" when the second value is true.
    function toggle() {
      const nowOff = !plane.classed("off");
      plane.classed("off", nowOff);
      item.classed("off", nowOff).attr("aria-pressed", String(!nowOff));
    }
    item.on("click", toggle);
    item.on("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();       // stop the page scrolling
        e.stopPropagation();      // stop the Space bar also replaying the animation
        toggle();
      }
    });
    // Clicking a source link opens it, without also switching the layer.
    item.selectAll("a").on("click", (e) => e.stopPropagation());

    // HOVER = isolate this layer (fade the others) while the mouse is over it.
    item.on("mouseenter", () => {
      stack.classed("isolate", true);
      stack.selectAll(".plane").classed("on", function () {
        return this.dataset.layer === layer.id;
      });
    });
    item.on("mouseleave", () => stack.classed("isolate", false));
  });

  // ---- 7. ANIMATION --------------------------------------------------
  fitToScreen();
  window.addEventListener("resize", fitToScreen);   // re-fit if the window changes
  setupAnimation();
}


// Shrink the whole drawing on small screens. The exploded stack needs
// about 980 x 940 px; if the stage is smaller, scale down to fit.
function fitToScreen() {
  const stage = document.querySelector(".stage");
  const fit = Math.min(1, stage.clientWidth / 980, stage.clientHeight / 940);
  document.documentElement.style.setProperty("--fit", fit);
}


// =====================================================================
// 7. ANIMATION
// Everything 3D in the CSS reads one variable, --t. So animating the whole
// drawing = changing one number smoothly from 0 to 1.
// =====================================================================
function setupAnimation() {
  const root = document.documentElement;      // the <html> element
  const scrub = document.getElementById("scrub");
  let t = 0;            // where we are now
  let frame = null;     // id of the running animation, so we can cancel it

  // Set the dial: update the CSS variable and the slider together.
  function setT(value) {
    t = value;
    root.style.setProperty("--t", t);
    scrub.value = t;
  }

  // Smoothly move from the current t to a target over "ms" milliseconds.
  // requestAnimationFrame asks the browser to call us before the next
  // screen refresh (about 60 times per second).
  function animateTo(target, ms = 2600) {
    cancelAnimationFrame(frame);
    const start = t;
    const startTime = performance.now();

    function step(now) {
      // progress goes 0 -> 1 over the duration. Math.min stops it at 1.
      const progress = Math.min((now - startTime) / ms, 1);
      // easeCubicInOut starts slow, speeds up, then slows down at the end,
      // which feels more natural than a constant speed.
      const eased = d3.easeCubicInOut(progress);
      setT(start + (target - start) * eased);
      if (progress < 1) frame = requestAnimationFrame(step);
    }
    frame = requestAnimationFrame(step);
  }

  // "Play": snap to flat, pause a moment, then expand.
  function play() {
    cancelAnimationFrame(frame);
    setT(0);
    setTimeout(() => animateTo(1), 900);
  }

  // Connect buttons to functions. "click" fires when a button is pressed.
  document.getElementById("btn-play").addEventListener("click", play);
  document.getElementById("btn-flat").addEventListener("click", () => animateTo(0, 1600));
  document.getElementById("btn-axon").addEventListener("click", () => animateTo(1, 1600));

  // "input" fires continuously while the slider is dragged.
  scrub.addEventListener("input", () => {
    cancelAnimationFrame(frame);
    setT(Number(scrub.value));
  });

  // Day / Night theme. Setting data-theme on <html> switches the CSS
  // role colours (see the top of style.css).
  document.getElementById("btn-theme").addEventListener("click", (e) => {
    const night = root.dataset.theme !== "night";
    root.dataset.theme = night ? "night" : "day";
    e.target.textContent = night ? "Day" : "Night";
  });

  // Space bar replays.
  document.addEventListener("keydown", (e) => {
    if (e.code === "Space") { e.preventDefault(); play(); }
  });

  // Start automatically when the page opens: flat for 1.5 s, then expand.
  setT(0);
  setTimeout(() => animateTo(1), 1500);
}

// Run main(). If anything fails (e.g. files not found), show why on screen.
main().catch((err) => {
  console.error(err);
  document.getElementById("stack").innerHTML =
    `<p style="max-width:420px;color:#FF88BE;font-family:monospace">
       Could not load the data files. Open this page through a local server
       (VS Code: right-click index.html → "Open with Live Server").<br><br>${err}</p>`;
});
