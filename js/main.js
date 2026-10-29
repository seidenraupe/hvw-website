/**
 * Historischer Verein Winterthur — Prototyp
 * Event-Karten aus /home-events.json (Hostpoint-Cron, wie Coucou/MuS).
 */

const HERO_SLIDER_MS = 5000;

function nextHeroIndex(current, count) {
  if (!count) return 0;
  return (current + 1) % count;
}

function shuffleHeroOrder(count, random) {
  const rand = typeof random === 'function' ? random : Math.random;
  const order = [];
  for (let i = 0; i < count; i += 1) order.push(i);
  for (let i = order.length - 1; i > 0; i -= 1) {
    const j = Math.floor(rand() * (i + 1));
    const swap = order[i];
    order[i] = order[j];
    order[j] = swap;
  }
  return order;
}

function heroCreditLines(slide) {
  if (!slide) return [];
  return String(slide.getAttribute('data-credit') || '')
    .split('|')
    .map((line) => line.trim())
    .filter(Boolean);
}

function initHeroSlider() {
  const root = document.querySelector('[data-hero-slider]');
  if (!root) return;
  const slides = Array.prototype.slice.call(root.querySelectorAll('img'));
  const credit = document.querySelector('.hvw-hero__credit');
  if (slides.length < 2) return;

  const order = shuffleHeroOrder(slides.length);
  let step = 0;
  const show = (nextStep) => {
    step = nextStep;
    const index = order[step];
    slides.forEach((slide, i) => {
      const active = i === index;
      slide.classList.toggle('is-active', active);
      if (active) {
        slide.removeAttribute('aria-hidden');
        slide.setAttribute('fetchpriority', 'high');
      } else {
        slide.setAttribute('aria-hidden', 'true');
        slide.removeAttribute('fetchpriority');
      }
    });
    if (credit) {
      const lines = heroCreditLines(slides[index]);
      credit.replaceChildren();
      lines.forEach((line) => {
        const span = document.createElement('span');
        span.textContent = line;
        credit.appendChild(span);
      });
      credit.hidden = lines.length === 0;
    }
  };

  show(0);
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  window.setInterval(() => {
    show(nextHeroIndex(step, order.length));
  }, HERO_SLIDER_MS);
}

function initNav() {
  const toggle = document.querySelector('[data-nav-toggle]');
  const mobileNav = document.querySelector('[data-nav-mobile]');
  if (!toggle || !mobileNav) return;

  const setOpen = (isOpen) => {
    mobileNav.classList.toggle('hidden', !isOpen);
    mobileNav.classList.toggle('block', isOpen);
    toggle.setAttribute('aria-expanded', String(isOpen));
    toggle.textContent = isOpen ? 'Schliessen' : 'Menü';
  };

  toggle.addEventListener('click', () => {
    const willOpen = mobileNav.classList.contains('hidden');
    setOpen(willOpen);
  });

  mobileNav.querySelectorAll('a').forEach((link) => {
    link.addEventListener('click', () => setOpen(false));
  });
}

/**
 * Perspektiven: zufällige Person mit allen drei Antworten aus data/stimmen.json.
 */
async function initStimmenRandom() {
  const root = document.querySelector('[data-stimmen-random]');
  if (!root) return;

  const imageEl = root.querySelector('[data-stimmen-image]');
  const nameEl = root.querySelector('[data-stimmen-name]');
  const roleEl = root.querySelector('[data-stimmen-role]');
  const answersEl = root.querySelector('[data-stimmen-answers]');
  if (!imageEl || !nameEl || !answersEl) return;

  let people = [];
  try {
    const response = await fetch('data/stimmen.json', { cache: 'no-cache' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    people = Array.isArray(data.people) ? data.people.filter((p) => (p.statements || []).length) : [];
  } catch (err) {
    console.error('Stimmen konnten nicht geladen werden:', err);
    return;
  }

  if (!people.length) return;

  const person = people[Math.floor(Math.random() * people.length)];
  const wrapQuote = (text) => {
    const trimmed = String(text || '').trim();
    if (!trimmed) return '';
    if (trimmed.startsWith('«') || trimmed.startsWith('"') || trimmed.startsWith('„')) {
      return trimmed;
    }
    return `«${trimmed}»`;
  };

  imageEl.src = person.image || 'images/placeholder-quote.svg';
  imageEl.alt = person.name || '';
  nameEl.textContent = person.name || '';
  if (roleEl) roleEl.textContent = person.role || '';

  answersEl.innerHTML = (person.statements || [])
    .map(
      (statement) => `
      <div>
        <p class="text-sm font-semibold uppercase tracking-wide text-hvw-mute">${escapeHtml(statement.question || '')}</p>
        <p class="mt-3 text-lg leading-relaxed text-hvw-ink md:text-xl">${escapeHtml(wrapQuote(statement.text || ''))}</p>
      </div>
    `
    )
    .join('');
}

async function loadHomeEvents() {
  const container = document.getElementById('home-events');
  const ticker = document.querySelector('.hvw-ticker');
  if (!container && !ticker) return;
  await renderEvents(container, { limit: 3 });
}

/**
 * Live und Vorschau: Hostpoint-Datei im Webroot (Cron).
 * Lokal: Fallback auf data/home-events.json aus dem Repo.
 */
async function loadHomeEventsJson() {
  const urls = ['/home-events.json', '/data/home-events.json', 'data/home-events.json'];
  let lastError = null;
  for (const url of urls) {
    try {
      const response = await fetch(url, { cache: 'no-cache' });
      if (response.ok) {
        return response.json();
      }
      lastError = new Error('HTTP ' + response.status);
    } catch (err) {
      lastError = err;
    }
  }
  throw lastError || new Error('home-events.json fehlt');
}

function isOpeningHoursListing(event) {
  const title = String((event && event.title) || '')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase();
  if (!title) return false;
  if (title.includes('erinnerungstank haldengut')) return true;
  return title.startsWith('ausstellung:');
}

function upcomingEvents(events, todayZurich) {
  return (Array.isArray(events) ? events : [])
    .filter((event) => String(event.begin || '').slice(0, 10) >= todayZurich)
    .filter((event) => !isOpeningHoursListing(event))
    .sort((a, b) => String(a.begin || '').localeCompare(String(b.begin || '')));
}

function tickerLabel(event) {
  if (!event) return '';
  const date = formatEventDate(event.begin);
  const location = event.location || event.organizerName || '';
  const title = event.title || '';
  return [date, location, title].filter(Boolean).join(' · ');
}

function renderHomeTicker(event) {
  const ticker = document.querySelector('.hvw-ticker');
  const track = ticker ? ticker.querySelector('.hvw-ticker__track') : null;
  if (!ticker || !track) return;
  const label = tickerLabel(event);
  if (!label) {
    ticker.hidden = true;
    track.textContent = '';
    return;
  }
  ticker.hidden = false;
  ticker.setAttribute('aria-label', label);
  const repeats = 6;
  const half = Array.from({ length: repeats }, () => `<span>${escapeHtml(label)}</span>`).join('');
  track.innerHTML = half + half;
}

async function renderEvents(container, { limit = 3 } = {}) {
  try {
    const data = await loadHomeEventsJson();
    const todayZurich = new Date().toLocaleDateString('en-CA', { timeZone: 'Europe/Zurich' });
    const events = upcomingEvents(data.events, todayZurich);
    renderHomeTicker(events[0] || null);
    const shown = events.slice(0, limit);

    if (!container) return;
    if (!shown.length) {
      container.innerHTML = statusMessage('Aktuell sind keine Veranstaltungen geplant.');
      return;
    }

    container.innerHTML = shown
      .map((event, index) => renderEventCard(event, index))
      .join('');

    injectEventJsonLd(shown);
  } catch (err) {
    console.error('Veranstaltungen konnten nicht geladen werden:', err);
    renderHomeTicker(null);
    if (!container) return;
    container.innerHTML = statusMessage(
      'Veranstaltungen konnten nicht geladen werden. Alle Termine finden Sie auf der Agenda-Seite.'
    );
  }
}

function statusMessage(text) {
  return `<p class="col-span-full rounded-none border border-hvw-ink/15 bg-hvw-fog px-5 py-8 text-center text-hvw-mute">${escapeHtml(text)}</p>`;
}

/**
 * Event-Karte — Tailwind, Mobile First:
 * 1 Spalte (default) · ab md 2 · ab lg 3 (Grid am Container)
 * Nutzt event.image aus JSON, falls vorhanden; sonst Platzhalter mit Wasserzeichen.
 */
function renderEventCard(event, index = 0) {
  const date = formatEventDate(event.begin);
  const iso = event.begin || '';
  const href = event.url || 'agenda.html';
  const external = Boolean(event.url && /^https?:\/\//.test(event.url));
  const location = event.location || event.organizerName || 'Winterthur';
  const imageIndex = (index % 6) + 1;
  const hasRealImage = Boolean(event.image);
  const imageSrc = hasRealImage
    ? event.image
    : `images/placeholder-event-${imageIndex}.svg`;
  const watermark = hasRealImage
    ? ''
    : `<div class="event-card__watermark" aria-hidden="true"><span>finales Bild fehlt</span></div>`;

  const targetAttrs = external
    ? ' target="_blank" rel="noopener noreferrer"'
    : '';

  return `
    <article class="event-card group flex flex-col border border-hvw-ink bg-white transition-colors duration-200 hover:bg-hvw-fog focus-within:bg-hvw-fog">
      <a href="${escapeHtml(href)}" class="flex h-full flex-col text-inherit no-underline outline-none"${targetAttrs} aria-label="${escapeHtml(event.title || 'Veranstaltung')}: Details öffnen">
        <div class="event-card__media aspect-[4/3]">
          <img
            src="${escapeHtml(imageSrc)}"
            alt="${escapeHtml(hasRealImage ? (event.title || '') : '')}"
            width="1200"
            height="900"
            loading="lazy"
            decoding="async">
          ${watermark}
        </div>
        <div class="flex flex-1 flex-col gap-3 p-5 sm:p-6">
          <time
            class="text-sm font-semibold uppercase tracking-[0.08em] text-hvw-mute"
            datetime="${escapeHtml(iso)}">
            ${escapeHtml(date)}
          </time>
          <h3 class="text-xl font-semibold leading-snug text-hvw-ink sm:text-2xl">
            ${escapeHtml(event.title || '')}
          </h3>
          <p class="text-base text-hvw-mute">
            ${escapeHtml(location)}
          </p>
          <span class="mt-auto inline-flex min-h-12 items-center pt-2 text-base font-semibold text-hvw-ink underline decoration-transparent underline-offset-4 transition group-hover:decoration-hvw-ink group-focus-within:decoration-hvw-ink">
            Details &amp; Tickets
            <span aria-hidden="true" class="ml-2 transition-transform duration-200 group-hover:translate-x-1">→</span>
          </span>
        </div>
      </a>
    </article>
  `;
}

function formatEventDate(isoString) {
  if (!isoString) return '';
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return '';

  const datePart = date.toLocaleDateString('de-CH', {
    weekday: 'short',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    timeZone: 'Europe/Zurich',
  });
  const timePart = date.toLocaleTimeString('de-CH', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Europe/Zurich',
  });

  return `${datePart} · ${timePart}`;
}

function defaultEventEndDate(beginIso) {
  if (!beginIso) return undefined;
  const start = new Date(beginIso);
  if (Number.isNaN(start.getTime())) return undefined;
  const end = new Date(start.getTime());
  end.setHours(end.getHours() + 2);
  return end.toISOString();
}

function eventDescriptionText(event) {
  const raw = String(event.description || '').replace(/\s+/g, ' ').trim();
  if (raw) return raw.slice(0, 500);
  const location = event.location || event.organizerName || 'Winterthur';
  const title = String(event.title || 'Veranstaltung').trim();
  return `${title} — ${location}, Historischer Verein Winterthur`.slice(0, 500);
}

function organizerUrl(organizerName) {
  const name = String(organizerName || '').toLowerCase();
  if (name.includes('schaffen')) return 'https://www.museumschaffen.ch/';
  return 'https://www.hvwinterthur.ch/';
}

function eventLocationJsonLd(event) {
  const name = event.location || event.organizerName || 'Winterthur';
  const address = {
    '@type': 'PostalAddress',
    addressLocality: event.addressLocality || 'Winterthur',
    addressRegion: 'ZH',
    addressCountry: 'CH',
  };
  if (event.streetAddress) {
    address.streetAddress = event.streetAddress;
  }
  if (event.postalCode) {
    address.postalCode = event.postalCode;
  }
  return {
    '@type': 'Place',
    name,
    address,
  };
}

/** Schema.org Event für JSON-LD (Google Search Console / Rich Results). */
function buildEventJsonLd(event) {
  const organizerName = event.organizerName || 'Historischer Verein Winterthur';
  const ticketUrl = event.url || 'https://www.hvwinterthur.ch/agenda.html';
  const endDate = event.end || defaultEventEndDate(event.begin);

  const item = {
    '@type': 'Event',
    name: event.title,
    description: eventDescriptionText(event),
    startDate: event.begin,
    endDate,
    url: ticketUrl,
    image: event.image || undefined,
    eventAttendanceMode: 'https://schema.org/OfflineEventAttendanceMode',
    eventStatus: 'https://schema.org/EventScheduled',
    location: eventLocationJsonLd(event),
    organizer: {
      '@type': 'Organization',
      name: organizerName,
      url: organizerUrl(organizerName),
    },
    performer: {
      '@type': 'Organization',
      name: organizerName,
    },
    offers: {
      '@type': 'Offer',
      url: ticketUrl,
      availability: 'https://schema.org/InStock',
      validFrom: event.begin,
    },
  };

  Object.keys(item).forEach((key) => {
    if (item[key] === undefined) delete item[key];
  });
  return item;
}

function injectEventJsonLd(events) {
  const existing = document.getElementById('events-jsonld');
  if (existing) existing.remove();

  const graph = events.map((event) => buildEventJsonLd(event));

  const script = document.createElement('script');
  script.type = 'application/ld+json';
  script.id = 'events-jsonld';
  script.textContent = JSON.stringify({
    '@context': 'https://schema.org',
    '@graph': graph,
  });
  document.head.appendChild(script);
}

function escapeHtml(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function startPage() {
  initNav();
  initStimmenRandom();
  try {
    initHeroSlider();
  } catch (err) {
    console.error(err);
  }
  loadHomeEvents();
}

if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startPage);
  } else {
    startPage();
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    upcomingEvents,
    tickerLabel,
    formatEventDate,
    buildEventJsonLd,
    isOpeningHoursListing,
    nextHeroIndex,
    shuffleHeroOrder,
    heroCreditLines,
    HERO_SLIDER_MS,
  };
}
