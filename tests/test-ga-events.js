#!/usr/bin/env node
const assert = require('assert');
const fs = require('fs');
const path = require('path');
const {
  clip,
  pageSurface,
  classifyClick,
  weblingInteract,
  weblingLoad,
  agendaFrameLoad,
  PARAM_MAX,
} = require('../js/ga-events.js');

const root = path.join(__dirname, '..');

function click(href, text, pathname) {
  return classifyClick({ href, text, pathname });
}

assert.strictEqual(pageSurface('/'), 'home');
assert.strictEqual(pageSurface('/index.html'), 'home');
assert.strictEqual(pageSurface('/agenda'), 'agenda');
assert.strictEqual(pageSurface('/agenda.html'), 'agenda');
assert.strictEqual(pageSurface('/mitmachen.html'), 'other');

const member = click('mitmachen.html', 'Mitglied werden', '/');
assert.strictEqual(member.name, 'mitglied_werden');
assert.strictEqual(member.params.link_text, 'Mitglied werden');
assert.strictEqual(member.params.link_url, 'mitmachen.html');

const join = click('mitmachen.html#anmeldeformular', '  Jetzt beitreten → ', '/mitmachen.html');
assert.strictEqual(join.name, 'mitglied_werden');
assert.strictEqual(join.params.link_text, 'Jetzt beitreten');

const beitreten = click('mitmachen.html#anmeldeformular', 'Beitreten', '/');
assert.strictEqual(beitreten.params.link_text, 'Beitreten');

assert.strictEqual(click('mitmachen.html', 'Mitmachen', '/'), null);
assert.strictEqual(click('agenda.html', 'Agenda ansehen', '/'), null);

const mail = click(
  'mailto:josip.spec@hvwinterthur.ch?subject=Mitarbeit&body=Guten%20Tag',
  'Interesse melden',
  '/mitmachen.html'
);
assert.strictEqual(mail.name, 'email_click');
assert.strictEqual(mail.params.email_address, 'josip.spec@hvwinterthur.ch');
assert.ok(!JSON.stringify(mail).includes('Guten'), 'Mailto-Text bleibt draussen');
assert.ok(!JSON.stringify(mail).includes('subject'), 'Mailto-Betreff bleibt draussen');

const phone = click('tel:+41525505128', '052 550 51 28', '/impressum.html');
assert.strictEqual(phone.name, 'phone_click');
assert.strictEqual(phone.params.phone_number, '+41525505128');

const homeTicket = click(
  'https://eventfrog.ch/de/p/example.html',
  'Details & Tickets',
  '/'
);
assert.strictEqual(homeTicket.name, 'eventfrog_click');
assert.strictEqual(homeTicket.params.surface, 'home');

const agendaTicket = click('https://www.eventfrog.ch/ticket', 'Tickets', '/agenda.html');
assert.strictEqual(agendaTicket.params.surface, 'agenda');

const otherTicket = click('https://embed.eventfrog.net/x', 'Details', '/museen.html');
assert.strictEqual(otherTicket.params.surface, 'other');

assert.strictEqual(click('https://example.org/tickets', 'Tickets', '/'), null);

const pdfCases = [
  ['Statuten.pdf', 'statuten_pdf'],
  ['/Statuten.pdf', 'statuten_pdf'],
  ['Sammlungskonzept.pdf', 'sammlungskonzept_pdf'],
  ['Jahresbericht-2025.pdf', 'jahresbericht_2025_pdf'],
  ['JB_2024_final.pdf', 'jahresbericht_2024_pdf'],
  ['/programm/Programm.pdf', 'programm_pdf'],
  ['dokumente/szenische-fuehrung-berta.pdf', 'szenische_fuehrung_pdf'],
  ['dokumente/historische-privat-fuehrungen.pdf', 'private_fuehrung_pdf'],
];
pdfCases.forEach((entry) => {
  const event = click(entry[0], 'Öffnen', '/ueber-uns.html');
  assert.ok(event, entry[0]);
  assert.strictEqual(event.name, entry[1], entry[0]);
});
assert.strictEqual(click('anderes.pdf', 'PDF', '/'), null);

const longUrl = 'https://eventfrog.ch/' + 'a'.repeat(200);
const clipped = click(longUrl, 'Details', '/');
assert.ok(clipped.params.link_url.length <= PARAM_MAX);
assert.strictEqual(clip('  abc  '), 'abc');

let form = { loads: 0, started: false, completed: false };
let step = weblingLoad(form);
form = step.state;
assert.deepStrictEqual(step.events, []);
step = weblingInteract(form);
form = step.state;
assert.strictEqual(step.events[0].name, 'webling_form_start');
step = weblingInteract(form);
assert.deepStrictEqual(step.events, []);
step = weblingLoad(form);
form = step.state;
assert.deepStrictEqual(step.events.map((event) => event.name), ['webling_form_complete']);
step = weblingLoad(form);
assert.deepStrictEqual(step.events, []);

let direct = { loads: 0, started: false, completed: false };
direct = weblingLoad(direct).state;
step = weblingLoad(direct);
assert.deepStrictEqual(step.events.map((event) => event.name), [
  'webling_form_start',
  'webling_form_complete',
]);

let agenda = { loads: 0 };
step = agendaFrameLoad(agenda);
agenda = step.state;
assert.deepStrictEqual(step.events, []);
step = agendaFrameLoad(agenda);
agenda = step.state;
assert.deepStrictEqual(step.events, [{ name: 'eventfrog_click', params: { surface: 'agenda' } }]);
step = agendaFrameLoad(agenda);
assert.strictEqual(step.events.length, 1);
assert.strictEqual(step.state.loads, 3);

const pages = [
  'index.html',
  'agenda.html',
  'museen.html',
  'lindengut.html',
  'moersburg.html',
  'sammlung.html',
  'partner.html',
  'ueber-uns.html',
  'mitmachen.html',
  'zitate.html',
  'impressum.html',
  'datenschutz.html',
];
pages.forEach((file) => {
  const html = fs.readFileSync(path.join(root, file), 'utf8');
  assert.ok(html.includes('G-8M4EZQDQ98'), file + ' behält die Measurement ID');
  assert.ok(html.includes('src="js/ga-events.js"'), file + ' lädt die Klickmessung');
});

const privacy = fs.readFileSync(path.join(root, 'datenschutz.html'), 'utf8');
assert.ok(privacy.includes('Ticket-Links'), 'Datenschutz nennt die Ticket-Messung');
assert.ok(privacy.includes('nicht'), 'Datenschutz grenzt Formularinhalte aus');
assert.ok(privacy.includes('E-Mail- und'), 'Datenschutz nennt E-Mail- und Telefon-Klicks');
assert.ok(privacy.includes('Führungs-PDFs'), 'Datenschutz nennt die PDF-Messung');

const build = fs.readFileSync(path.join(root, 'scripts/build-hostpoint-soft-launch.sh'), 'utf8');
assert.ok(
  build.includes('copy_dir "${ROOT}/js"'),
  'Soft-Launch kopiert js/ (inkl. ga-events.js)',
);
assert.ok(fs.existsSync(path.join(root, 'js/ga-events.js')), 'ga-events.js existiert im Quellbaum');

console.log('ga-events ok');
