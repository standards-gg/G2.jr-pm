"""Slides 1-2 of the AKG deck: the report to the Senior Partnership Manager, numbers first.

Every figure comes from the KPI set (build.py) or the models (campaign.py). Bar lengths and target markers are
percentages of a per-row scale, rounded to whole numbers and drawn with the .pw-N / .pl-N classes in akg.css
(the page's CSP allows no inline styles)."""
from __future__ import annotations

from charts import fmt_num, fmt_pct


def b(en: str, de: str | None = None) -> str:
    if de is None or de == en:
        return en
    return f'<span lang="en">{en}</span><span lang="de">{de}</span>'


def num(x: float, digits: int = 0) -> str:
    """A plain number in both locales (1,234.5 / 1.234,5)."""
    en = f'{x:,.{digits}f}'
    return b(en, en.replace(',', 'X').replace('.', ',').replace('X', '.'))


def short(x: float) -> str:
    return b(fmt_num(x, 'en'), fmt_num(x, 'de'))


def pct(x: float, digits: int = 1, sign: bool = False) -> str:
    return b(fmt_pct(x, 'en', digits, sign), fmt_pct(x, 'de', digits, sign))


def eur(x: float, digits: int = 2) -> str:
    en = f'€{x:,.{digits}f}'
    de = f'{x:,.{digits}f}'.replace(',', 'X').replace('.', ',').replace('X', '.') + '\u00a0€'
    return b(en, de)


def times(x: float, digits: int = 1) -> str:
    return b(f'×{x:.{digits}f}', f'×{x:.{digits}f}'.replace('.', ','))


def w(x: float) -> int:
    return max(0, min(100, round(x)))


# ---------------------------------------------------------------- slide 1 · results
SCALE = 1.25  # every bullet bar runs from 0 to 125% of its own target, so all target ticks line up at 80%


def score_row(label: str, ratio: float, shown: str, target_shown: str, delta: str, state: str) -> str:
    """One bullet bar on the shared scale: bar = result as a share of target, white tick = the target (always at 80%)."""
    return (f'<li class="{state}"><span class="sl">{label}</span><b>{shown}</b>'
            f'<span class="bullet" aria-hidden="true"><i class="pw-{w(min(ratio, SCALE) / SCALE * 100)}"></i><em class="pl-{w(100 / SCALE)}"></em></span>'
            f'<small>{b("target", "Ziel")} {target_shown} · <span class="delta">{delta}</span></small></li>')


def pts(diff: float, digits: int = 0) -> str:
    """A difference in percentage points, with a word for its direction."""
    v = abs(diff) * 100
    en_n, de_n = f'{v:.{digits}f}', f'{v:.{digits}f}'.replace('.', ',')
    if round(v, digits) == 0:
        return b('on target', 'im Ziel')
    unit_en = 'pt' if en_n == '1' else 'pts'
    return b(f'{en_n} {unit_en} {"above" if diff > 0 else "below"}', f'{de_n} Pkt. {"darüber" if diff > 0 else "darunter"}')


def slide_results(r: dict, k: dict) -> str:
    freq = k['impressions'] / k['reach']
    per_person = k['fee'] / k['reach']
    completed = k['views'] * k['completion']
    funnel = (
        '<ol class="flow rv">'
        f'<li><b>{short(k["impressions"])}</b><span>{b("impressions", "Impressionen")}</span></li>'
        f'<li class="rate"><em>≈{freq:.0f}×</em><span>{b("seen per person", "pro Person gesehen")}</span></li>'
        f'<li><b>{short(k["reach"])}</b><span>{b("different people", "verschiedene Personen")}</span></li>'
        f'<li class="rate"><em>{pct(k["er"])}</em><span>{b("interactions per impression", "Interaktionen pro Impression")}</span></li>'
        f'<li><b>{short(k["engagements"])}</b><span>{b("likes, comments, shares", "Likes, Kommentare, Shares")}</span></li>'
        f'<li class="rate"><em>{pct(k["ctr_lp"])}</em><span>{b("clicks per person reached", "Klicks pro erreichter Person")}</span></li>'
        f'<li class="hot"><b>{short(k["clicks"])}</b><span>{b("clicks to AKG", "Klicks zu AKG")}</span></li>'
        '</ol>')
    reach_t = 1_500_000
    above = (k['reach'] / reach_t - 1) * 100
    aud = ''.join([
        score_row(b('Different people reached', 'Erreichte Personen'), k['reach'] / reach_t, short(k['reach']), short(reach_t),
                  b(f'{above:.0f}% above', f'{above:.0f} % darüber'), 'ok'),
        score_row(b('Impressions with a like, comment or share', 'Impressionen mit Like, Kommentar oder Share'), k['er'] / .04, pct(k['er']), pct(.04), pts(k['er'] - .04, 1), 'ok'),
        score_row(b('Videos watched to the end', 'Videos bis zum Ende gesehen'), k['completion'] / .6, pct(k['completion'], 0), pct(.6, 0), pts(k['completion'] - .6), 'ok'),
        score_row(b('Clicks to AKG per person reached', 'Klicks zu AKG pro erreichter Person'), k['ctr_lp'] / .05, pct(k['ctr_lp']), pct(.05), pts(k['ctr_lp'] - .05, 1), 'ok'),
    ])
    below = (1 - k['on_time_rate']) * 100
    dlv = ''.join([
        score_row(b('Assets delivered', 'Assets geliefert'), 1, f'{k["assets"]}/{k["assets"]}', str(k['assets']), b('on target · 0 missed', 'im Ziel · 0 verpasst'), 'ok'),
        score_row(b('Live on the planned day', 'Am Plantag live'), k['on_time_rate'], pct(k['on_time_rate'], 0), pct(1, 0),
                  b(f'{below:.0f} pts below · {k["late"]} late, 1 agreed with AKG', f'{below:.0f} Pkt. darunter · {k["late"]} später, 1 vereinbart'), 'warn'),
        score_row(b('Content AKG accepted without changes', 'Von AKG ohne Änderungen angenommen'), k['fr_rate'] / .85, pct(k['fr_rate'], 0), pct(.85, 0), pts(k['fr_rate'] - .85), 'ok'),
        score_row(b('Agreed to-dos closed', 'Vereinbarte Aufgaben erledigt'), k['action_rate'] / .95, pct(k['action_rate'], 0), pct(.95, 0),
                  b(f'{k["actions_done"]} of {k["actions_total"]} · ', f'{k["actions_done"]} von {k["actions_total"]} · ') + pts(k['action_rate'] - .95), 'ok'),
    ])
    key = ('<span class="k-bar" aria-hidden="true"></span>' + b('result', 'Ergebnis')
           + '<span class="k-tick" aria-hidden="true"></span>' + b('target (same spot on every bar)', 'Ziel (bei jedem Balken an derselben Stelle)'))
    costs = ''.join(f'<li><b>{v}</b><span>{lab}</span></li>' for v, lab in [
        (eur(per_person), b('per person reached', 'pro erreichter Person')),
        (eur(k['cpe']), b('per interaction', 'pro Interaktion')),
        (eur(k['cpc']), b('per click to AKG', 'pro Klick zu AKG')),
        (eur(k['fee'] / completed, 3), b('per video watched to the end', 'pro komplett gesehenem Video')),
    ])
    return f'''
  <section tabindex="-1" class="slide dash sum1" data-title="Results" data-de-data-title="Ergebnisse">
    <div class="inner wide">
      <header class="dash-head rv">
        <div>
          <div class="kicker">{b('Closeout report · 1 of 2 · for the Senior Partnership Manager · fictional case study', 'Abschlussreport · 1 von 2 · für den Senior Partnership Manager · fiktive Fallstudie')}</div>
          <h1 class="dash-title"><span class="wm-akg">AKG</span> <span class="x" aria-hidden="true">×</span><span class="sr-only">{b("and", "und")}</span> <span class="wm-g2">G2</span> <span class="dash-sub">{b('Every asset delivered. Every audience target beaten.', 'Jedes Asset geliefert. Jedes Reichweitenziel übertroffen.')}</span></h1>
        </div>
        <dl class="meta-list">
          <div><dt>{b('Period', 'Zeitraum')}</dt><dd>04.05.–28.06.2026 · {b('8 weeks', '8 Wochen')}</dd></div>
          <div><dt>{b('Budget (hypothetical)', 'Budget (hypothetisch)')}</dt><dd>{eur(k['fee'], 0)}</dd></div>
          <div><dt>{b('My role', 'Meine Rolle')}</dt><dd>Junior Partnerships Manager</dd></div>
        </dl>
      </header>
      {funnel}
      <div class="score-grid rv">
        <div class="score"><p class="group-label">{b('Audience · result vs. target', 'Publikum · Ergebnis vs. Ziel')}</p><p class="scale-key">{key}</p><ul class="bullets">{aud}</ul></div>
        <div class="score"><p class="group-label">{b('Delivery · result vs. target', 'Lieferung · Ergebnis vs. Ziel')}</p><p class="scale-key">{key}</p><ul class="bullets">{dlv}</ul></div>
        <div class="score"><p class="group-label">{b(f'What €{k["fee"]:,.0f} bought', f'Was {k["fee"]:,.0f} € gekauft haben'.replace(',', '.'))}</p><ul class="costs">{costs}</ul></div>
      </div>
      <p class="disclaimer rv">{b('Fictional case study for a job application. All figures are hypothetical and simulated; they are not real G2 Esports or AKG data. Not affiliated with or endorsed by G2 Esports or AKG. Concept and design © 2026 Christian Balan, all rights reserved.',
                                  'Fiktive Fallstudie für eine Bewerbung. Alle Zahlen sind hypothetisch und simuliert, keine echten Daten von G2 Esports oder AKG. Nicht verbunden mit oder unterstützt von G2 Esports oder AKG. Konzept und Design © 2026 Christian Balan, alle Rechte vorbehalten.')}</p>
    </div>
  </section>'''


# ---------------------------------------------------------------- slide 2 · what drove it, what next
def slide_drivers(r: dict, k: dict) -> str:
    sc = r['scenario']
    fc, act, iv = k['fc78']['engagements'], k['act78']['engagements'], r['interval']['engagements']
    f6 = r['forecast'].set_index('week').loc[6]
    a6 = r['weeks'].set_index('week').loc[6]
    # A · model effect: static post = 1, creator-led video post = factor, whisker = 95% range
    lo, hi = sc['lo'], sc['hi']
    rng = b(f'Likely range ×{lo:.1f} to ×{hi:.1f} (95%). Same reach, paid support and post age.',
            f'Wahrscheinlicher Bereich ×{lo:.1f} bis ×{hi:.1f} (95 %). Gleiche Reichweite, Paid Support und Post-Alter.'.replace('.', ',', 2))
    top = sc['hi'] / .9
    effect = (f'<ul class="vbars" aria-hidden="true">'
              f'<li><span class="bl">{b("Static post", "Statischer Post")}</span><span class="vtrack"><i class="pw-{w(100 / top)}"></i></span><b>{times(1, 2)}</b></li>'
              f'<li class="hot"><span class="bl">{b("Creator-led video post", "Creator-Video-Post")}</span><span class="vtrack"><i class="pw-{w(sc["factor"] / top * 100)}"></i>'
              f'<em class="range pl-{w(sc["lo"] / top * 100)} pr-{w(100 - sc["hi"] / top * 100)}"></em></span><b>{times(sc["factor"], 2)}</b></li></ul>'
              f'<p class="fine">{rng}</p>')
    # B · forecast vs actual, weeks 7-8
    top = act / .9
    lift = (f'<ul class="vbars" aria-hidden="true">'
            f'<li><span class="bl">{b("Forecast · old plan", "Prognose · alter Plan")}</span><span class="vtrack"><i class="pw-{w(fc / top * 100)}"></i>'
            f'<em class="range pl-{w(iv[0] / top * 100)} pr-{w(100 - iv[1] / top * 100)}"></em></span><b>{short(fc)}</b></li>'
            f'<li class="hot"><span class="bl">{b("Actual · new plan", "Ist · neuer Plan")}</span><span class="vtrack"><i class="pw-{w(act / top * 100)}"></i></span><b>{short(act)}</b></li></ul>'
            f'<p class="fine">{b("Interactions, weeks 7–8. Clicks ", "Interaktionen, Wochen 7–8. Klicks ")}{pct(k["lift_clicks"], 0, True)} · {b("people reached ", "Reichweite ")}{pct(k["lift_reach"], 0, True)} · '
            f'{b("videos finished ", "Videos zu Ende ")}{pct(k["fc78"]["completion"], 0)} → {pct(k["act78"]["completion"], 0)}</p>')
    # C · the forecast was tested on week 6 before anyone relied on it
    checks = [(b('Interactions', 'Interaktionen'), f6.engagements, a6.engagements), (b('Clicks', 'Klicks'), f6.clicks, a6.clicks), (b('People reached', 'Reichweite'), f6.reach, a6.reach)]
    test = ('<ul class="checks">' + ''.join(
        f'<li><span class="bl">{lab}</span><span class="cmp">{num(f_)} → {num(a_)}</span><b>{pct(a_ / f_ - 1, 1, True)}</b></li>' for lab, f_, a_ in checks)
        + '</ul>'
        + f'<p class="fine">{b("Week 6: forecast made in week 5 → what actually happened.", "Woche 6: Prognose aus Woche 5 → tatsächliches Ergebnis.")}</p>')
    err = max(abs(k['w6_eng']), abs(k['w6_clicks']), abs(k['w6_reach']))
    asks = ''.join(f'<li><b>{t}</b><small>{s}</small></li>' for t, s in [
        (b('Make creator-led video the core format', 'Creator-Video zum Kernformat machen'),
         b(f'+{fmt_num(sc["extra_eng"], "en")} interactions on the 6 static slots ({fmt_num(sc["extra_lo"], "en")}–{fmt_num(sc["extra_hi"], "en")})',
           f'+{fmt_num(sc["extra_eng"], "de")} Interaktionen auf den 6 statischen Slots ({fmt_num(sc["extra_lo"], "de")}–{fmt_num(sc["extra_hi"], "de")})')),
        (b('Build a control group into the renewal', 'Kontrollgruppe in die Verlängerung einbauen'),
         b('turns a strong signal into proof', 'macht aus einem starken Signal einen Beweis')),
        (b('Agree brand-lift and retailer tracking before launch', 'Brand Lift und Händler-Tracking vor dem Start vereinbaren'),
         b(f'today: {fmt_num(k["actions"], "en")} site actions, no sales data', f'heute: {fmt_num(k["actions"], "de")} Website-Aktionen, keine Verkaufsdaten')),
    ])
    return f'''
  <section tabindex="-1" class="slide dash sum2" data-title="What drove it" data-de-data-title="Was es getrieben hat">
    <div class="inner wide">
      <header class="dash-head rv"><div>
        <div class="kicker">{b('Closeout report · 2 of 2 · what drove the result, what I recommend', 'Abschlussreport · 2 von 2 · was das Ergebnis getrieben hat, was ich empfehle')}</div>
        <h2>{b('Creator-led video won. Switching to it in week 6 paid off', 'Creator-Video hat gewonnen. Der Wechsel in Woche 6 hat sich gelohnt')}<span class="accent">.</span></h2>
      </div></header>
      <div class="drivers rv">
        <div class="driver"><p class="big">{times(sc["factor"], 1)}</p><p class="dl">{b('interactions per post: creator-led video vs. static post', 'Interaktionen pro Post: Creator-Video vs. statischer Post')}</p>{effect}</div>
        <div class="driver"><p class="big">{pct(k["lift_eng"], 0, True)}</p><p class="dl">{b('interactions in weeks 7–8 above the forecast for the old plan', 'Interaktionen in Wochen 7–8 über der Prognose für den alten Plan')}</p>{lift}</div>
        <div class="driver quiet"><p class="big">{b(f"±{err * 100:.0f}%", f"±{err * 100:.0f} %")}</p><p class="dl">{b('forecast error when tested on week 6, before we relied on it', 'Prognosefehler beim Test an Woche 6, bevor wir uns darauf verlassen haben')}</p>{test}</div>
      </div>
      <div class="asks-wrap rv">
        <p class="group-label">{b('For the renewal · your call', 'Für die Verlängerung · deine Entscheidung')}</p>
        <ol class="asks">{asks}</ol>
      </div>
      <p class="disclaimer rv">{b('Fictional case study: all figures are hypothetical and simulated. Model results show strong signals, not proof of cause.', 'Fiktive Fallstudie: Alle Zahlen sind hypothetisch und simuliert. Die Modellergebnisse sind starke Signale, kein Kausalitätsbeweis.')}</p>
    </div>
  </section>'''
