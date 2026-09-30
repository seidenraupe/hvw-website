/**
 * GA4-Klickmessung für Mitgliedschaft, Webling, Eventfrog, E-Mail und Telefon.
 * Reine Funktionen sind in Node testbar. Im Browser sendet gtag per Beacon,
 * damit der Treffer beim Seitenwechsel erhalten bleibt.
 */
(function (factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }
  if (typeof document !== 'undefined') {
    api.install(document, window);
  }
})(function gaEventsFactory() {
  const PARAM_MAX = 100;
  const MEMBERSHIP_LABELS = {
    'mitglied werden': 'Mitglied werden',
    'jetzt beitreten': 'Jetzt beitreten',
    beitreten: 'Beitreten',
  };

  function clip(value) {
    const text = String(value == null ? '' : value).trim();
    return text.length > PARAM_MAX ? text.slice(0, PARAM_MAX) : text;
  }

  function pageSurface(pathname) {
    const path = String(pathname || '/').split('?')[0].split('#')[0];
    const file = path.replace(/\/+$/, '') || '/';
    if (file === '/' || /(^|\/)index(\.html)?$/i.test(file)) return 'home';
    if (/(^|\/)agenda(\.html)?$/i.test(file)) return 'agenda';
    return 'other';
  }

  function visibleLabel(text) {
    return String(text || '')
      .replace(/[→←]/g, '')
      .replace(/\s+/g, ' ')
      .trim()
      .toLowerCase();
  }

  function emailAddress(href) {
    const value = String(href || '').trim();
    if (!/^mailto:/i.test(value)) return '';
    const raw = value.slice('mailto:'.length).split('?')[0].split('#')[0].trim();
    if (!raw) return '';
    try {
      return clip(decodeURIComponent(raw.replace(/\+/g, '%20')));
    } catch (err) {
      return clip(raw);
    }
  }

  function phoneNumber(href) {
    const value = String(href || '').trim();
    if (!/^tel:/i.test(value)) return '';
    return clip(value.slice('tel:'.length).split('?')[0].split('#')[0]);
  }

  function isEventfrogHref(href) {
    const value = String(href || '').trim();
    if (!value || /^(mailto:|tel:|javascript:)/i.test(value)) return false;
    try {
      const url = new URL(value, 'https://www.hvwinterthur.ch');
      return /(^|\.)eventfrog\.(ch|net)$/i.test(url.hostname);
    } catch (err) {
      return false;
    }
  }

  function classifyClick(input) {
    const href = input && input.href ? String(input.href) : '';
    const text = input && input.text ? String(input.text) : '';
    const surface = pageSurface(input && input.pathname);
    const mail = emailAddress(href);
    if (mail) {
      return { name: 'email_click', params: { email_address: mail } };
    }
    const phone = phoneNumber(href);
    if (phone) {
      return { name: 'phone_click', params: { phone_number: phone } };
    }
    const label = MEMBERSHIP_LABELS[visibleLabel(text)];
    if (label) {
      return {
        name: 'mitglied_werden',
        params: { link_text: label, link_url: clip(href) },
      };
    }
    if (isEventfrogHref(href)) {
      return {
        name: 'eventfrog_click',
        params: { surface: surface, link_url: clip(href) },
      };
    }
    return null;
  }

  function weblingInteract(state) {
    const current = state || { loads: 0, started: false, completed: false };
    if (current.started) return { state: current, events: [] };
    return {
      state: { loads: current.loads, started: true, completed: current.completed },
      events: [{ name: 'webling_form_start', params: { form: 'mitgliedschaft' } }],
    };
  }

  function weblingLoad(state) {
    const current = state || { loads: 0, started: false, completed: false };
    const loads = current.loads + 1;
    if (loads === 1) {
      return {
        state: { loads: 1, started: current.started, completed: current.completed },
        events: [],
      };
    }
    const events = [];
    let started = current.started;
    let completed = current.completed;
    if (!started) {
      started = true;
      events.push({ name: 'webling_form_start', params: { form: 'mitgliedschaft' } });
    }
    if (!completed) {
      completed = true;
      events.push({ name: 'webling_form_complete', params: { form: 'mitgliedschaft' } });
    }
    return { state: { loads: loads, started: started, completed: completed }, events: events };
  }

  function agendaFrameLoad(state) {
    const current = state || { loads: 0 };
    const loads = current.loads + 1;
    if (loads === 1) return { state: { loads: 1 }, events: [] };
    return {
      state: { loads: loads },
      events: [{ name: 'eventfrog_click', params: { surface: 'agenda' } }],
    };
  }

  function sendEvent(win, event) {
    if (!win || typeof win.gtag !== 'function' || !event) return;
    const params = { transport_type: 'beacon' };
    const source = event.params || {};
    Object.keys(source).forEach((key) => {
      const value = source[key];
      if (value == null || value === '') return;
      params[key] = typeof value === 'string' ? clip(value) : value;
    });
    win.gtag('event', event.name, params);
  }

  function isWeblingFrame(frame) {
    const src = frame.getAttribute('src') || '';
    return /webling\.ch/i.test(src) || Boolean(frame.closest && frame.closest('.webling-embed'));
  }

  function isEventfrogFrame(frame) {
    const src = frame.getAttribute('src') || '';
    return /eventfrog\.(ch|net)/i.test(src) || Boolean(frame.closest && frame.closest('.eventfrog-wrapper'));
  }

  function bindFrames(doc, win, frameLoads) {
    doc.querySelectorAll('iframe').forEach((frame) => {
      if (frame.dataset && frame.dataset.hvwGaBound === '1') return;
      const webling = isWeblingFrame(frame);
      const eventfrog = !webling && isEventfrogFrame(frame);
      if (!webling && !eventfrog) return;
      if (frame.dataset) frame.dataset.hvwGaBound = '1';

      let state = webling
        ? { loads: 0, started: false, completed: false }
        : { loads: 0 };
      const reduce = webling ? weblingLoad : agendaFrameLoad;
      let handled = 0;

      function onLoad() {
        handled += 1;
        const result = reduce(state);
        state = result.state;
        result.events.forEach((event) => sendEvent(win, event));
      }

      frame.__hvwGaOnLoad = onLoad;
      const pending = (frameLoads.get(frame) || 0) - handled;
      for (let i = 0; i < pending; i += 1) onLoad();

      if (!webling) return;

      function interact() {
        const result = weblingInteract(state);
        state = result.state;
        result.events.forEach((event) => sendEvent(win, event));
      }

      frame.addEventListener('pointerdown', interact, true);
      win.addEventListener('blur', () => {
        if (doc.activeElement === frame) interact();
      });
    });
  }

  function install(doc, win) {
    if (!doc || !doc.documentElement || doc.documentElement.dataset.hvwGaEvents === '1') return;
    doc.documentElement.dataset.hvwGaEvents = '1';
    const frameLoads = new WeakMap();

    doc.addEventListener('load', (ev) => {
      const frame = ev.target;
      if (!frame || String(frame.tagName || '').toUpperCase() !== 'IFRAME') return;
      frameLoads.set(frame, (frameLoads.get(frame) || 0) + 1);
      if (typeof frame.__hvwGaOnLoad === 'function') frame.__hvwGaOnLoad();
    }, true);

    function onActivate(ev) {
      if (ev.type === 'auxclick' && ev.button !== 1) return;
      const target = ev.target;
      const anchor = target && target.closest ? target.closest('a[href]') : null;
      if (!anchor) return;
      const event = classifyClick({
        href: anchor.getAttribute('href'),
        text: anchor.textContent,
        pathname: win.location.pathname,
      });
      if (event) sendEvent(win, event);
    }

    doc.addEventListener('click', onActivate, true);
    doc.addEventListener('auxclick', onActivate, true);

    const bind = () => bindFrames(doc, win, frameLoads);
    if (doc.readyState === 'loading') doc.addEventListener('DOMContentLoaded', bind);
    else bind();
  }

  return {
    PARAM_MAX,
    clip,
    pageSurface,
    classifyClick,
    weblingInteract,
    weblingLoad,
    agendaFrameLoad,
    install,
  };
});
