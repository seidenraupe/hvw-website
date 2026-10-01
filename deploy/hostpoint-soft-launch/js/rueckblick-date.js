/**
 * Vergangene Veranstaltungen nach Datum im Kicker absteigend sortieren.
 * Versteht «Führung · Juli 2026», «Nov. 2025», «NOV:2025» und «25.09.2026».
 */
(function (root) {
  const MONTHS = [
    ["september", 9],
    ["november", 11],
    ["dezember", 12],
    ["februar", 2],
    ["januar", 1],
    ["oktober", 10],
    ["august", 8],
    ["maerz", 3],
    ["märz", 3],
    ["april", 4],
    ["juni", 6],
    ["juli", 7],
    ["sept", 9],
    ["nov", 11],
    ["dez", 12],
    ["feb", 2],
    ["jan", 1],
    ["okt", 10],
    ["aug", 8],
    ["mär", 3],
    ["mae", 3],
    ["mar", 3],
    ["apr", 4],
    ["jun", 6],
    ["jul", 7],
    ["mai", 5],
    ["sep", 9],
  ];

  function normalize(text) {
    return String(text || "")
      .toLowerCase()
      .replace(/\./g, " ")
      .replace(/[:/|-]+/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function monthAt(text) {
    for (let i = 0; i < MONTHS.length; i += 1) {
      const name = MONTHS[i][0];
      const month = MONTHS[i][1];
      const re = new RegExp("(?:^|[^a-zäöü])" + name + "(?![a-zäöü])");
      const match = re.exec(text);
      if (!match) continue;
      return { month: month, index: match.index + match[0].length - name.length };
    }
    return null;
  }

  function parseRueckblickDate(text) {
    const raw = String(text || "");
    const norm = normalize(raw);
    const named = monthAt(norm);
    if (named) {
      const after = norm.slice(named.index);
      const year = /(?:^|[^0-9])((?:19|20)\d{2})(?![0-9])/.exec(after) || /((?:19|20)\d{2})/.exec(norm);
      if (year) return Number(year[1]) * 12 + named.month;
    }
    const dmy = /(\d{1,2})\s+(\d{1,2})\s+((?:19|20)\d{2})/.exec(norm);
    if (dmy) {
      const month = Number(dmy[2]);
      if (month >= 1 && month <= 12) return Number(dmy[3]) * 12 + month;
    }
    const my = /(?:^|[^0-9])(\d{1,2})\s+((?:19|20)\d{2})(?![0-9])/.exec(norm);
    if (my) {
      const month = Number(my[1]);
      if (month >= 1 && month <= 12) return Number(my[2]) * 12 + month;
    }
    return null;
  }

  function kickerOf(card) {
    const el = card.querySelector("[data-content$='.kicker']");
    return el ? el.textContent || "" : "";
  }

  function sortRueckblickCards(doc) {
    const scope = doc || (typeof document !== "undefined" ? document : null);
    if (!scope) return;
    const grid = scope.querySelector("[data-rueckblick-grid]");
    if (!grid) return;
    const cards = Array.prototype.slice.call(grid.children).filter((el) => el.tagName === "ARTICLE");
    const ranked = cards.map((card, index) => {
      const parsed = parseRueckblickDate(kickerOf(card));
      return { card: card, index: index, rank: parsed == null ? -1 : parsed };
    });
    ranked.sort((a, b) => b.rank - a.rank || a.index - b.index);
    ranked.forEach((item) => grid.appendChild(item.card));
  }

  root.hvwParseRueckblickDate = parseRueckblickDate;
  root.hvwSortRueckblick = sortRueckblickCards;
})(typeof window !== "undefined" ? window : globalThis);
