#!/usr/bin/env node
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const {
  upcomingEvents,
  tickerLabel,
  nextHeroIndex,
  shuffleHeroOrder,
  heroCreditLines,
  HERO_SLIDER_MS,
} = require('../js/main.js');

const html = fs.readFileSync(path.join(__dirname, '../index.html'), 'utf8');
const mitmachen = fs.readFileSync(path.join(__dirname, '../mitmachen.html'), 'utf8');
assert.ok(!html.includes('Freund:in Museum Schaffen'), 'Titelseite ohne Freund:in Museum Schaffen');
assert.ok(!mitmachen.includes('Freund:in Museum Schaffen'), 'Mitmachen ohne Freund:in Museum Schaffen');
assert.ok(html.includes('lg:grid-cols-3'), 'Mitgliedschaft auf der Titelseite in drei Spalten');
assert.ok(mitmachen.includes('id="jugend"') && mitmachen.includes('id="einzel"') && mitmachen.includes('id="paar"'), 'Jugend, Einzel und Paar bleiben');
const ticker = html.slice(html.indexOf('class="hvw-ticker'), html.indexOf('</header>'));
assert.ok(ticker.includes('hvw-ticker'), 'Ticker bleibt vorhanden');
assert.ok(!ticker.includes('Mitgliedschaft'), 'alter Tickertext Mitgliedschaft');
assert.ok(!ticker.includes('Träger von Museum'), 'alter Tickertext Träger');
assert.ok(!ticker.includes('museumschaffen.ch'), 'alter Tickertext Initiative');
assert.ok(ticker.includes('aria-label="Nächste Veranstaltung"'), 'Ticker-Beschriftung');

const css = fs.readFileSync(path.join(__dirname, '../css/site.css'), 'utf8');
assert.ok(css.includes('font-size: 1.125rem'), 'Tickerschrift grösser');

const events = [
  { title: 'Später', begin: '2026-11-02T18:00:00+01:00', location: 'Lindengut' },
  { title: 'Als Nächstes', begin: '2026-10-01T19:00:00+02:00', location: 'Museum Schaffen, Winterthur' },
  { title: 'Vergangen', begin: '2026-08-01T10:00:00+02:00', location: 'Mörsburg' },
];
const next = upcomingEvents(events, '2026-09-25');
assert.strictEqual(next[0].title, 'Als Nächstes');
assert.strictEqual(next.length, 2);
const label = tickerLabel(next[0]);
assert.ok(label.includes('Als Nächstes'), label);
assert.ok(label.includes('Museum Schaffen, Winterthur'), label);
assert.ok(label.includes('01.10.2026'), label);
assert.ok(!label.includes('Mitgliedschaft'), label);
assert.strictEqual(tickerLabel(null), '');

const withOpeningHours = upcomingEvents(
  [
    {
      title: 'Ausstellung: Erinnerungstank Haldengut',
      begin: '2026-09-25T10:00:00+02:00',
      location: 'Museum Schaffen, Winterthur',
    },
    {
      title: 'Käfele mit der Kuratorin der Ausstellung',
      begin: '2026-09-25T14:00:00+02:00',
      location: 'Museum Schaffen, Winterthur',
    },
    {
      title: 'Ausstellung: Erinnerungstank Haldengut',
      begin: '2026-09-26T10:00:00+02:00',
      location: 'Museum Schaffen, Winterthur',
    },
  ],
  '2026-09-25'
);
assert.strictEqual(withOpeningHours.length, 1);
assert.strictEqual(withOpeningHours[0].title, 'Käfele mit der Kuratorin der Ausstellung');

const hero = html.slice(html.indexOf('data-hero-slider'), html.indexOf('hvw-hero__shade'));
assert.strictEqual((hero.match(/<img/g) || []).length, 4, 'vier Herobilder');
[
  'hero-turner.jpg',
  'hero-schichtwechsel.jpg',
  'hero-maschinenhalle.jpg',
  'hero-spinnsaal.jpg',
].forEach((name) => {
  assert.ok(hero.includes(name), name);
  assert.ok(fs.existsSync(path.join(__dirname, '../images', name)), name + ' Datei');
});
assert.ok(!html.includes('hero-textilfabrik.jpg'), 'Spinnerei entfernt');
assert.ok(!html.includes('hero-tram.jpg'), 'Tram-Datei entfernt');
assert.ok(!hero.includes('hero-schmiede.jpg'), 'Schmiede entfernt');
assert.ok(!hero.includes('hero-textilmaschine.jpg'), 'alte Textilmaschine entfernt');
assert.ok(!hero.includes('FotLb_006215'), 'Spinnerei-Signatur entfernt');
assert.ok(!hero.includes('Winterthurer Bibliotheken, 150785'), 'Tram-Signatur entfernt');
assert.ok(hero.includes('hero-maschinenhalle.jpg'), 'Maschinenhalle');
assert.ok(hero.includes('hero-spinnsaal.jpg'), 'Spinnsaal');
assert.ok(hero.includes('Heinz Baumann, Januar 1967, Winterthur'), 'Nachweis Maschinenhalle');
assert.ok(hero.includes('Com_L16-0078-0003-0001'), 'Signatur Maschinenhalle');
assert.ok(hero.includes('data-credit="Turner am Barren"'), 'Turner beschriftet');
assert.ok(hero.includes('data-credit="Menschen auf dem Fabrikweg"'), 'Fabrikweg beschriftet');
assert.ok(hero.includes('data-credit="Frau im Spinnsaal"'), 'Spinnsaal beschriftet');
assert.ok(!hero.includes('data-credit="Turner am Barren|Winterthurer Bibliotheken"'), 'Turner ohne Bibliothekszeile');
assert.ok(!hero.includes('data-credit="Menschen auf dem Fabrikweg|Winterthurer Bibliotheken"'), 'Fabrikweg ohne Bibliothekszeile');
assert.ok(!hero.includes('data-credit="Frau im Spinnsaal|Winterthurer Bibliotheken"'), 'Spinnsaal ohne Bibliothekszeile');
assert.ok(html.includes('Historischer Verein Winterthur'), 'Vereinsname mit Grossbuchstaben');
assert.ok(!html.includes('lowercase tracking-tight'), 'Hero-Marke nicht mehr erzwungen klein');
assert.ok(!html.includes('historischer verein winterthur'), 'keine Kleinschreibung des Vereinsnamens');
assert.strictEqual(HERO_SLIDER_MS, 5000);
assert.strictEqual(nextHeroIndex(0, 4), 1);
assert.strictEqual(nextHeroIndex(3, 4), 0);

const mainSrc = fs.readFileSync(path.join(__dirname, '../js/main.js'), 'utf8');
const sliderConst = mainSrc.indexOf('const HERO_SLIDER_MS');
const pageStart = mainSrc.indexOf('function startPage');
assert.ok(sliderConst >= 0 && pageStart > sliderConst, 'Seitenstart erst nach HERO_SLIDER_MS');
assert.ok(mainSrc.indexOf('loadHomeEvents();') > mainSrc.indexOf('catch (err)'), 'Veranstaltungen laden auch wenn der Slider scheitert');

const shuffled = shuffleHeroOrder(5, () => 0);
assert.deepStrictEqual(shuffled.slice().sort((a, b) => a - b), [0, 1, 2, 3, 4]);
assert.notDeepStrictEqual(shuffled, [0, 1, 2, 3, 4]);
const creditSlide = { getAttribute: () => 'A| B |' };
assert.deepStrictEqual(heroCreditLines(creditSlide), ['A', 'B']);
assert.deepStrictEqual(heroCreditLines({ getAttribute: () => '' }), []);
console.log('home ticker ok:', label);
