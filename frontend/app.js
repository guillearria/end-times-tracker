"use strict";

// Fixed display order; any unknown category is appended after these.
const CATEGORY_ORDER = [
  "cosmic", "geological", "nuclear", "biological",
  "climate", "technological", "resource", "societal",
];

const CATEGORY_LABELS = {
  cosmic: "Cosmic", geological: "Geological", nuclear: "Nuclear",
  biological: "Biological", climate: "Climate", technological: "Technological",
  resource: "Resource", societal: "Societal",
};

function el(tag, attrs, children) {
  const node = document.createElement(tag);
  if (attrs) {
    for (const [k, v] of Object.entries(attrs)) {
      if (k === "class") node.className = v;
      else if (k === "text") node.textContent = v;
      else node.setAttribute(k, v);
    }
  }
  for (const child of children || []) {
    if (child) node.appendChild(child);
  }
  return node;
}

function badge(text, cls) {
  return el("span", { class: `badge ${cls}`, text });
}

function dateOnly(iso) {
  return (iso || "").slice(0, 10);
}

function claimNode(claim) {
  const src = el("div", { class: "claim-src" });
  const status = claim.verification_status || "unverified";
  src.appendChild(badge(status, `badge-${status}`));
  if (claim.source_url) {
    src.appendChild(el("a", {
      href: claim.source_url, target: "_blank", rel: "noopener noreferrer",
      text: claim.source_name || claim.source_url,
    }));
  } else if (claim.source_name) {
    src.appendChild(el("span", { text: claim.source_name }));
  }
  if (claim.retrieved_date) {
    src.appendChild(el("span", { text: `retrieved ${claim.retrieved_date}` }));
  }
  return el("div", { class: "claim" }, [
    el("p", { class: "claim-text", text: claim.text || "" }),
    src,
  ]);
}

function cardNode(rec, { review }) {
  const a = rec.assessment || {};
  const prob = (a.probability || {}).estimate || "unknown";
  const sev = a.severity || "unknown";
  const v = rec.verification || {};

  const badges = el("div", { class: "badges" }, [
    review ? badge("under review", "badge-review")
           : badge(v.status || "unverified", `badge-${v.status || "unverified"}`),
    badge(`severity: ${sev}`, "badge-sev"),
    badge(`probability: ${prob}`, "badge-prob"),
    v.confidence ? badge(`confidence: ${v.confidence}`, "badge-conf") : null,
  ]);

  const head = el("div", { class: "card-head" }, [
    el("h3", { text: rec.name || rec.id }),
    badges,
  ]);

  const claims = rec.claims || [];
  const details = el("details", { class: "claims" }, [
    el("summary", { text: `${claims.length} cited claim${claims.length === 1 ? "" : "s"}` }),
    ...claims.map(claimNode),
  ]);

  return el("article", { class: "card" }, [
    head,
    el("p", { class: "card-summary", text: a.summary || rec.description || "" }),
    details,
    el("p", { class: "card-meta", text: `Last updated ${dateOnly(rec.last_updated)}` }),
  ]);
}

function compositeOf(rec) {
  return (rec.sort_keys && typeof rec.sort_keys.composite === "number")
    ? rec.sort_keys.composite : 0;
}

function renderPublished(records) {
  const groups = new Map();
  for (const rec of records) {
    const cat = rec.category || "other";
    if (!groups.has(cat)) groups.set(cat, []);
    groups.get(cat).push(rec);
  }
  const cats = [...groups.keys()].sort((x, y) => {
    const ix = CATEGORY_ORDER.indexOf(x), iy = CATEGORY_ORDER.indexOf(y);
    return (ix === -1 ? 99 : ix) - (iy === -1 ? 99 : iy);
  });

  const out = [];
  for (const cat of cats) {
    const recs = groups.get(cat).sort((x, y) => compositeOf(y) - compositeOf(x));
    out.push(el("section", { class: "category" }, [
      el("h2", { text: CATEGORY_LABELS[cat] || cat }),
      ...recs.map((r) => cardNode(r, { review: false })),
    ]));
  }
  return out;
}

function renderUnderReview(records) {
  if (!records.length) return [];
  return [el("section", { class: "review-section" }, [
    el("h2", { text: "Under review" }),
    el("div", {
      class: "review-banner",
      text: "These threats failed automated verification — no authoritative source has been " +
            "confirmed for their headline claims. They are shown for transparency and must not " +
            "be read as established facts.",
    }),
    ...records.map((r) => cardNode(r, { review: true })),
  ])];
}

async function main() {
  const app = document.getElementById("app");
  try {
    const res = await fetch(`./data/threats.json?t=${Date.now()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const published = data.published || [];
    const underReview = data.under_review || [];

    app.replaceChildren(...renderPublished(published), ...renderUnderReview(underReview));

    const fresh = document.getElementById("freshness");
    fresh.textContent = data.last_updated
      ? `${published.length} tracked threat${published.length === 1 ? "" : "s"}, ` +
        `${underReview.length} under review · latest update ${dateOnly(data.last_updated)}`
      : "";
  } catch (err) {
    app.replaceChildren(el("p", { class: "error", text: `Could not load threat data: ${err.message}` }));
  }
}

main();
