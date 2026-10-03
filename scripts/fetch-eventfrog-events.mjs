#!/usr/bin/env node
/**
 * Fetches the next upcoming events of the Historischer Verein Winterthur
 * (orgIds 4936116, 5116588, 5137433) from the Eventfrog Public API and
 * writes data/home-events.json for the homepage.
 *
 * Requires env EVENTFROG_API_KEY (Public API key). Optional local helper
 * for the prototype homepage — not scheduled. Nightly JSON for Coucou and
 * Museum Schaffen is written on Hostpoint (cronjobs/).
 *
 * Images: the Public API list endpoint often omits image URLs. When missing,
 * we enrich each event from the public event page's og:image.
 *
 * Usage:
 *   EVENTFROG_API_KEY=<key> node scripts/fetch-eventfrog-events.mjs
 */

import { writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const API_BASE = 'https://api.eventfrog.net';
const ORG_IDS = ['4936116', '5116588', '5137433'];
const EVENT_LIMIT = 3;
const OUTPUT_PATH = fileURLToPath(new URL('../data/home-events.json', import.meta.url));

const apiKey = (process.env.EVENTFROG_API_KEY || '').trim();
if (!apiKey) {
  console.error(
    'Error: EVENTFROG_API_KEY is not set.\n' +
      'Set the GitHub Actions secret EVENTFROG_API_KEY (Eventfrog Public API key).'
  );
  process.exit(1);
}

async function fetchJson(path, params) {
  const url = new URL(path, API_BASE);
  for (const [key, value] of Object.entries(params)) {
    if (Array.isArray(value)) {
      value.forEach((v) => url.searchParams.append(key, v));
    } else if (value !== undefined && value !== null) {
      url.searchParams.set(key, value);
    }
  }

  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${apiKey}` },
  });

  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(
      `Eventfrog API request failed (${res.status} ${res.statusText}) for ${url}\n${body}`
    );
  }

  return res.json();
}

function pickLang(field) {
  if (!field) return '';
  if (typeof field === 'string') return field;
  return field.de || field.en || field.fr || '';
}

/** OpenAPI: Event.image is { url, width?, height? } */
function pickImage(event) {
  if (!event || typeof event !== 'object') return '';

  const candidates = [
    event.image?.url,
    event.imageUrl,
    event.imageURL,
    event.flyerUrl,
    event.flyerURL,
    event.thumbnailUrl,
    typeof event.image === 'string' ? event.image : '',
    Array.isArray(event.images) ? event.images[0]?.url || event.images[0] : '',
    event.flyer?.url,
    event.media?.imageUrl,
  ];

  for (const value of candidates) {
    if (typeof value === 'string' && /^https?:\/\//.test(value)) {
      return value.split('?')[0];
    }
  }
  return '';
}

/** Fallback when the API list payload has no image — use the event page og:image. */
async function fetchOgImage(eventUrl) {
  if (!eventUrl || !/^https?:\/\//.test(eventUrl)) return '';

  try {
    const res = await fetch(eventUrl, {
      headers: {
        Accept: 'text/html',
        'User-Agent': 'HVW-homepage-events-bot/1.0 (+https://github.com/seidenraupe/hvw-website)',
      },
      redirect: 'follow',
    });
    if (!res.ok) return '';

    const html = await res.text();
    const match =
      html.match(/property=["']og:image["']\s+content=["']([^"']+)/i) ||
      html.match(/content=["']([^"']+)["']\s+property=["']og:image["']/i);

    const image = match?.[1]?.trim() || '';
    return /^https?:\/\//.test(image) ? image.split('?')[0] : '';
  } catch (err) {
    console.warn(`og:image fetch failed for ${eventUrl}:`, err.message || err);
    return '';
  }
}

async function main() {
  const today = new Date().toISOString().slice(0, 10);

  // perPage höher als EVENT_LIMIT: über mehrere Orgs genug Kandidaten holen
  const { events = [] } = await fetchJson('/public/v1/events', {
    orgId: ORG_IDS,
    perPage: Math.max(EVENT_LIMIT * 10, 30),
    country: 'CH',
    from: today,
  });

  const nextEvents = [...events]
    .sort((a, b) => String(a.begin || '').localeCompare(String(b.begin || '')))
    .slice(0, EVENT_LIMIT);

  const locationIds = [...new Set(nextEvents.flatMap((event) => event.locationIds || []))];
  let locationsById = {};
  if (locationIds.length) {
    const { locations = [] } = await fetchJson('/public/v1/locations', { id: locationIds });
    locationsById = Object.fromEntries(locations.map((loc) => [loc.id, loc]));
  }

  const result = [];
  let enrichedImages = 0;

  for (const event of nextEvents) {
    const location = locationsById[event.locationIds?.[0]];
    const locationLabel = location
      ? [pickLang(location.title), location.city].filter(Boolean).join(', ')
      : event.organizerName || '';

    let image = pickImage(event);
    if (!image && event.url) {
      image = await fetchOgImage(event.url);
      if (image) enrichedImages += 1;
    }

    result.push({
      id: String(event.id),
      title: pickLang(event.title),
      begin: event.begin,
      url: event.url,
      organizerName: event.organizerName || '',
      location: locationLabel,
      ...(image ? { image } : {}),
    });
  }

  const payload = {
    generatedAt: new Date().toISOString(),
    source: enrichedImages ? 'eventfrog-public-api+og-image' : 'eventfrog-public-api',
    events: result,
  };

  await writeFile(OUTPUT_PATH, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
  console.log(
    `Wrote ${result.length} event(s) to ${OUTPUT_PATH}` +
      (enrichedImages ? ` (${enrichedImages} image(s) from og:image)` : '')
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
