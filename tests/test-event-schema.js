#!/usr/bin/env node
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { buildEventJsonLd } = require('../js/main.js');

const mainSrc = fs.readFileSync(path.join(__dirname, '../js/main.js'), 'utf8');
assert.ok(!mainSrc.includes('itemtype="https://schema.org/Event"'), 'Event-Microdata entfernen (nur JSON-LD)');
assert.ok(mainSrc.includes('buildEventJsonLd'), 'buildEventJsonLd fehlt');

const sample = buildEventJsonLd({
  title: 'Testführung',
  begin: '2026-11-01T14:00:00+01:00',
  end: '2026-11-01T16:00:00+01:00',
  url: 'https://eventfrog.ch/de/p/example.html',
  organizerName: 'Museum Schaffen',
  location: 'Museum Schaffen, Winterthur',
  streetAddress: 'Lagerplatz 1',
  postalCode: '8400',
  description: 'Kurzbeschreibung aus Eventfrog.',
});

assert.strictEqual(sample['@type'], 'Event');
assert.ok(sample.endDate, 'endDate');
assert.ok(sample.description, 'description');
assert.ok(sample.offers && sample.offers.url, 'offers');
assert.ok(sample.performer && sample.performer.name, 'performer');
assert.ok(sample.organizer && sample.organizer.name, 'organizer');
assert.ok(sample.location.address.streetAddress, 'location.address');

const fallback = buildEventJsonLd({
  title: 'Vortrag',
  begin: '2026-12-01T19:00:00+01:00',
  location: 'Museum Lindengut',
});
assert.ok(fallback.endDate, 'endDate-Fallback');
assert.ok(fallback.description.includes('Vortrag'), 'description-Fallback');

console.log('event-schema ok');
