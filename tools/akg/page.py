"""Writes projects/akg/index.html: 5 slides, every number taken from the simulation (campaign.py) and the KPI set (build.py)."""
from __future__ import annotations

import re
from datetime import timedelta
from html import escape

from charts import fmt_num, fmt_pct
from summary import slide_drivers, slide_results


# ---------- bilingual helpers ----------
def b(en: str, de: str | None = None) -> str:
    """A text in both languages (the page shows the one matching <html lang>)."""
    if de is None or de == en:
        return en
    return f'<span lang="en">{en}</span><span lang="de">{de}</span>'


def n(x, short=False) -> str:
    return b(fmt_num(x, 'en', short), fmt_num(x, 'de', short))


def p(x, digits=1, sign=False) -> str:
    return b(fmt_pct(x, 'en', digits, sign), fmt_pct(x, 'de', digits, sign))


def eur(x, digits=0) -> str:
    en = f'€{x:,.{digits}f}'
    de = f'{x:,.{digits}f}'.replace(',', 'X').replace('.', ',').replace('X', '.') + '\u00a0€'
    return b(en, de)


def de_num(x, digits=2) -> str:
    return f'{x:.{digits}f}'.replace('.', ',')


def dec(x, digits=1) -> str:
    return b(f'{x:.{digits}f}', f'{x:.{digits}f}'.replace('.', ','))


def dt(d, year=False) -> str:
    return d.strftime('%d.%m.%Y' if year else '%d.%m.')


def chart(name: str, alt_en: str, alt_de: str, cls: str = '') -> str:
    return (f'<figure class="chart {cls}">'
            f'<img lang="en" src="charts/{name}-en.svg" alt="{escape(alt_en)}" loading="lazy" decoding="async">'
            f'<img lang="de" src="charts/{name}-de.svg" alt="{escape(alt_de)}" loading="lazy" decoding="async">'
            f'</figure>')


def chip(status: str, en: str, de: str | None = None) -> str:
    return f'<span class="st {status}">{b(en, de)}</span>'


def tabs(name_en, name_de, items, active=None) -> str:
    """items: list of (key, label_en, label_de, html)."""
    active = active or items[0][0]
    bar = ''.join(f'<button type="button" class="tab-btn" data-tab="{k}" aria-pressed="{str(k == active).lower()}">{b(le, ld)}</button>'
                  for k, le, ld, _ in items)
    panels = ''.join(f'<div class="tab-panel" data-for="{k}">{h}</div>' for k, _, _, h in items)
    return (f'<div class="tabset rv" data-select="tab" data-tab="{active}">'
            f'<div class="tab-bar" role="group" aria-label="{name_en}" data-de-aria-label="{name_de}">{bar}</div>'
            f'<div class="tab-panels">{panels}</div></div>')


def table(head: list[str], rows: list[list[str]], cls='', label_en='', label_de='') -> str:
    th = ''.join(f'<th scope="col">{h}</th>' for h in head)
    def cell(i, c):
        return f'<th scope="row">{c}</th>' if i == 0 else f'<td>{c}</td>'
    body = ''.join('<tr>' + ''.join(cell(i, c) for i, c in enumerate(r)) + '</tr>' for r in rows)
    cap = f'<caption class="sr-only">{b(label_en, label_de)}</caption>' if label_en else ''
    # a focusable, labelled section so keyboard users can scroll wide tables
    return (f'<section class="scroll-x table-wrap {cls}" tabindex="0" aria-label="{escape(label_en)}" '
            f'data-de-aria-label="{escape(label_de)}"><table class="dt">{cap}<thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></section>')


def kpi(value: str, label: str, note: str = '', hl=False) -> str:
    return (f'<div class="kpi{" hl" if hl else ""}"><b>{value}</b><span>{label}</span>'
            + (f'<small>{note}</small>' if note else '') + '</div>')


# ---------- authored narrative (weekly log, client reports, risks, proof of delivery) ----------
WEEK_TEXT = [
    dict(obj=('Kick-off, briefs and production plan', 'Kick-off, Briefings und Produktionsplan'),
         tasks=('Kick-off with AKG, 4 creative briefs, RACI and timeline, deliverable tracker set up, creator availability check',
                'Kick-off mit AKG, 4 Creative-Briefings, RACI und Zeitplan, Deliverable-Tracker aufgesetzt, Verfügbarkeit der Creator geprüft'),
         who=('AKG Brand & Marketing, Partnerships Director, Head of Content, Creator Manager, Legal',
              'AKG Brand & Marketing, Partnerships Director, Head of Content, Creator Manager, Legal'),
         issues=('Product samples not shipped yet; giveaway T&Cs need both legal teams',
                 'Produktmuster noch nicht versendet; Gewinnspiel-AGB brauchen beide Rechtsabteilungen'),
         actions=('Chased shipment with the AKG product specialist; started the T&Cs two weeks early; agreed the weekly report format',
                  'Versand beim AKG-Produktspezialisten nachverfolgt; AGB zwei Wochen früher gestartet; Format des Wochenreports abgestimmt'),
         outcome=('Briefs approved, first newsletter live', 'Briefings freigegeben, erster Newsletter live')),
    dict(obj=('First wave live', 'Erste Welle live'),
         tasks=('Partnership reveal, first short-form, placement batch 1, hero video pre-production with the agency',
                'Partnerschafts-Reveal, erstes Short-Form, Placement-Batch 1, Hero-Video-Vorproduktion mit der Agentur'),
         who=('Social, Video Producer, Broadcast, production agency, Creator A, Players A/B',
              'Social, Video Producer, Broadcast, Produktionsagentur, Creator A, Spieler A/B'),
         issues=('Headphone shipment delayed, photo shoot at risk; Creator B travels to a tournament during the CV-02 slot',
                 'Kopfhörer-Lieferung verspätet, Fotoshooting gefährdet; Creator B reist im CV-02-Slot zu einem Turnier'),
         actions=('Agreed a new photo date (19.05.) with AKG in writing; moved the CV-02 recording before the trip',
                  'Neuen Fototermin (19.05.) schriftlich mit AKG vereinbart; CV-02-Aufnahme vor die Reise gelegt'),
         outcome=('1 documented deadline shift, rest on plan', '1 dokumentierte Terminverschiebung, Rest im Plan')),
    dict(obj=('Creator content and first livestream', 'Creator-Content und erster Livestream'),
         tasks=('Studio tour video, ranked-night livestream, photography delivered, hero video first cut submitted',
                'Studio-Tour-Video, Ranked-Livestream, Fotopaket geliefert, erster Schnitt des Hero-Videos eingereicht'),
         who=('Creator A/B, Broadcast Producer, photo studio, AKG Brand Manager, AKG Marketing Manager',
              'Creator A/B, Broadcast Producer, Fotostudio, AKG Brand Manager, AKG Marketing Manager'),
         issues=('Hero video feedback overdue (SLA 3 days); match weekend clashes with two social slots',
                 'Feedback zum Hero-Video überfällig (SLA 3 Tage); Matchwochenende kollidiert mit zwei Social-Slots'),
         actions=('Reminder on day 3, escalation to the AKG Marketing Manager on day 4 with a timestamped review link; re-sequenced the social calendar',
                  'Erinnerung an Tag 3, Eskalation an den AKG Marketing Manager an Tag 4 mit Review-Link und Zeitmarken; Social-Kalender umgeplant'),
         outcome=('Feedback received on day 6; calendar clash closed', 'Feedback an Tag 6 erhalten; Kalenderkonflikt gelöst')),
    dict(obj=('Hero launch and giveaway', 'Hero-Launch und Gewinnspiel'),
         tasks=('Hero video launch after 3 rounds, giveaway launch after a joint legal call, match-day social',
                'Hero-Video-Launch nach 3 Runden, Gewinnspiel-Start nach gemeinsamem Legal-Call, Matchday-Social'),
         who=('Video Producer, agency, G2 Legal, AKG Legal & Compliance, Community Manager',
              'Video Producer, Agentur, G2 Legal, AKG Legal & Compliance, Community Manager'),
         issues=('Product-claim wording on creator video #2; giveaway T&Cs sign-off stalled between legal teams',
                 'Produktclaims im Creator-Video #2; AGB-Freigabe hängt zwischen den Rechtsabteilungen'),
         actions=('Consolidated all hero feedback in one tracker, capped rounds per contract; set up a joint legal call',
                  'Hero-Feedback in einem Tracker gebündelt, Runden laut Vertrag begrenzt; gemeinsamen Legal-Call aufgesetzt'),
         outcome=('Hero video and giveaway live on date', 'Hero-Video und Gewinnspiel pünktlich live')),
    dict(obj=('Mid-campaign review and analysis', 'Zwischenbilanz und Analyse'),
         tasks=('Mid-campaign report, format analysis of weeks 1–5, optimisation memo, creator video #2 final revisions',
                'Zwischenreport, Formatanalyse Wochen 1–5, Optimierungsmemo, finale Revisionen Creator-Video #2'),
         who=('Partnerships Director, Head of Content, Social Media Manager, AKG Brand Manager',
              'Partnerships Director, Head of Content, Social Media Manager, AKG Brand Manager'),
         issues=('Creator video #2 two days after its plan date (still inside the contract window)',
                 'Creator-Video #2 zwei Tage nach Plantermin (noch im Vertragsfenster)'),
         actions=('Analysed asset-level data, fitted engagement and click models, proposed the reallocation to my manager first, then AKG',
                  'Daten auf Asset-Ebene analysiert, Engagement- und Klickmodelle geschätzt, Umschichtung erst intern, dann AKG vorgeschlagen'),
         outcome=('Recommendation: shift weeks 7–8 to creator/video', 'Empfehlung: Wochen 7–8 auf Creator/Video umschichten')),
    dict(obj=('Sign-off and preparation of the reallocation', 'Freigabe und Vorbereitung der Umschichtung'),
         tasks=('AKG sign-off (09.06.), SP-07/08 turned into creator-led video posts, Creator D re-briefed, paid support moved; giveaway closed, winners drawn',
                'AKG-Freigabe (09.06.), SP-07/08 als Creator-Video-Posts umgesetzt, Creator D neu gebrieft, Paid Support verschoben; Gewinnspiel beendet, Gewinner gezogen'),
         who=('AKG Brand Manager, Social Media Manager, Creator Manager, Creator D, Community Manager',
              'AKG Brand Manager, Social Media Manager, Creator Manager, Creator D, Community Manager'),
         issues=('The format change needed written AKG approval and a new brief within 5 days',
                 'Der Formatwechsel brauchte eine schriftliche AKG-Freigabe und ein neues Briefing binnen 5 Tagen'),
         actions=('Change note with the numbers behind it; revised brief to Creator D within 24 hours',
                  'Change Note mit den Zahlen dahinter; überarbeitetes Briefing an Creator D binnen 24 Stunden'),
         outcome=('Plan updated at no extra cost; week 6 within 3% of the forecast', 'Plan ohne Mehrkosten angepasst; Woche 6 innerhalb von 3 % der Prognose')),
    dict(obj=('Video-first final push', 'Video-first-Schlussphase'),
         tasks=('Community cup livestream, short-form #4, creator-led post #7, final placement',
                'Community-Cup-Livestream, Short-Form #4, Creator-Post #7, letztes Placement'),
         who=('Creator C/D, Broadcast Producer, Social Media Manager, AKG Brand Manager',
              'Creator C/D, Broadcast Producer, Social Media Manager, AKG Brand Manager'),
         issues=('Livestream VOD analytics delayed by the platform', 'VOD-Analytics des Livestreams von der Plattform verzögert'),
         actions=('Collected interim screenshots as evidence and re-pulled the export on 24.06.',
                  'Zwischenzeitlich Screenshots als Nachweis gesichert, Export am 24.06. neu gezogen'),
         outcome=('Engagement well above the week-5 forecast', 'Engagement deutlich über der Prognose aus Woche 5')),
    dict(obj=('Final deliverables and closeout', 'Letzte Deliverables und Abschluss'),
         tasks=('Creator video #3, wrap-up post, proof-of-delivery pack completed, closeout report, renewal pre-read',
                'Creator-Video #3, Wrap-up-Post, Proof-of-Delivery-Paket komplett, Abschlussreport, Pre-Read zur Verlängerung'),
         who=('Creator D, Player B, AKG Brand Manager, Partnerships Director, Finance',
              'Creator D, Spieler B, AKG Brand Manager, Partnerships Director, Finance'),
         issues=('5 action items still open at close (none contractual)', '5 Action Items bei Abschluss offen (keines vertraglich)'),
         actions=('Handed open items over with owners and dates; proof of delivery countersigned by AKG',
                  'Offene Punkte mit Verantwortlichen und Terminen übergeben; Proof of Delivery von AKG gegengezeichnet'),
         outcome=('31/31 delivered, closeout sent', '31/31 geliefert, Abschlussreport versendet')),
]

CLIENT_REPORT = [
    (('Kick-off done, 4 briefs submitted', 'Kick-off erledigt, 4 Briefings eingereicht'),
     ('Product samples not shipped', 'Produktmuster nicht versendet'),
     ('Shipment tracking shared with AKG product team', 'Sendungsverfolgung mit AKG-Produktteam geteilt'),
     ('First wave live from 11.05.', 'Erste Welle ab 11.05. live')),
    (('Partnership reveal and first short-form live', 'Partnerschafts-Reveal und erstes Short-Form live'),
     ('Photo shoot moved to 19.05. (shipment)', 'Fotoshooting auf 19.05. verschoben (Lieferung)'),
     ('New date confirmed in writing, no knock-on to other assets', 'Neuer Termin schriftlich bestätigt, keine Folgen für andere Assets'),
     ('Hero video first cut for review 13.05.', 'Erster Schnitt des Hero-Videos zur Freigabe am 13.05.')),
    (('Studio tour video and first livestream live', 'Studio-Tour-Video und erster Livestream live'),
     ('Hero video feedback overdue', 'Feedback zum Hero-Video überfällig'),
     ('Asked for a 30-minute review call; escalated to Marketing Manager on day 4', '30-minütigen Review-Call angefragt; an Tag 4 an Marketing Manager eskaliert'),
     ('Hero launch 26.05., giveaway 27.05.', 'Hero-Launch 26.05., Gewinnspiel 27.05.')),
    (('Hero video and giveaway live on date', 'Hero-Video und Gewinnspiel pünktlich live'),
     ('Product claims in creator video #2 need AKG legal wording', 'Produktclaims im Creator-Video #2 brauchen AKG-Legal-Formulierung'),
     ('Claim sheet sent, creator re-records two lines', 'Claim-Sheet geschickt, Creator nimmt zwei Sätze neu auf'),
     ('Mid-campaign review 05.06.', 'Zwischenbilanz am 05.06.')),
    (('Mid-campaign review: creator/video outperforms static', 'Zwischenbilanz: Creator/Video schlägt statische Formate'),
     ('Creator video #2 two days after plan date', 'Creator-Video #2 zwei Tage nach Plantermin'),
     ('Proposed moving weeks 7–8 to creator/video formats', 'Vorschlag: Wochen 7–8 auf Creator/Video-Formate umstellen'),
     ('AKG decision by 09.06.', 'AKG-Entscheidung bis 09.06.')),
    (('Reallocation approved; giveaway closed with 18,400 entries', 'Umschichtung freigegeben; Gewinnspiel mit 18.400 Teilnahmen beendet'),
     ('Tight turnaround for the new creator brief', 'Knapper Vorlauf für das neue Creator-Briefing'),
     ('Revised brief sent within 24 hours', 'Überarbeitetes Briefing binnen 24 Stunden verschickt'),
     ('Video-first push from 15.06.', 'Video-first-Phase ab 15.06.')),
    (('Community cup livestream and creator-led post live', 'Community-Cup-Livestream und Creator-Post live'),
     ('Livestream VOD analytics delayed by the platform', 'VOD-Analytics des Livestreams von der Plattform verzögert'),
     ('Interim screenshots shared, full export follows', 'Zwischen-Screenshots geteilt, voller Export folgt'),
     ('Final assets 23.06. and 25.06.', 'Letzte Assets am 23.06. und 25.06.')),
    (('All 31 deliverables live and verified', 'Alle 31 Deliverables live und verifiziert'),
     ('None open with AKG', 'Keine offenen Punkte mit AKG'),
     ('Proof-of-delivery pack countersigned', 'Proof-of-Delivery-Paket gegengezeichnet'),
     ('Closeout meeting and renewal conversation', 'Abschlussmeeting und Gespräch zur Verlängerung')),
]

RISK_TEXT = {
    'R1': (('Pre-booked review slots; reminder on day 3; escalated to the AKG Marketing Manager on day 4',
            'Review-Slots vorab gebucht; Erinnerung an Tag 3; an Tag 4 an den AKG Marketing Manager eskaliert'),
           ('Closed: SLA breached once', 'Geschlossen: SLA einmal verfehlt'),
           ('Hero video live on date; 1 approval outside SLA', 'Hero-Video pünktlich live; 1 Freigabe außerhalb des SLA')),
    'R2': (('Recorded before the trip, edit slot swapped with CV-03', 'Vor der Reise aufgenommen, Schnitt-Slot mit CV-03 getauscht'),
           ('Closed: 2-day slip', 'Geschlossen: 2 Tage Verzug'),
           ('Live 2 days after plan date, inside the contract window', '2 Tage nach Plantermin live, im Vertragsfenster')),
    'R3': (('Tracked the shipment daily; agreed a new shoot date with AKG in writing', 'Lieferung täglich verfolgt; neuen Shooting-Termin schriftlich mit AKG vereinbart'),
           ('Closed: deadline shifted', 'Geschlossen: Termin verschoben'),
           ('The one documented deadline shift (+6 days), no contractual impact', 'Die einzige dokumentierte Terminverschiebung (+6 Tage), ohne Vertragsfolgen')),
    'R4': (('Started T&Cs two weeks early; joint call with both legal teams', 'AGB zwei Wochen früher begonnen; gemeinsamer Call beider Rechtsabteilungen'),
           ('Closed before impact', 'Vor Eintritt geschlossen'),
           ('Giveaway launched on date (escalated internally, within SLA)', 'Gewinnspiel pünktlich gestartet (intern eskaliert, im SLA)')),
    'R5': (('Re-sequenced the social calendar with the Social Media Manager', 'Social-Kalender mit dem Social Media Manager umgeplant'),
           ('Closed before impact', 'Vor Eintritt geschlossen'),
           ('No slot lost, match-day content unaffected', 'Kein Slot verloren, Matchday-Content unberührt')),
    'R6': (('Claim sheet from AKG Legal; one consolidated feedback round per contract', 'Claim-Sheet von AKG Legal; eine gebündelte Feedbackrunde laut Vertrag'),
           ('Closed: 2 client rounds', 'Geschlossen: 2 Kundenrunden'),
           ('Approved in round 3; added to the lessons learned', 'In Runde 3 freigegeben; in die Lessons Learned aufgenommen')),
}

POD_TEXT = {
    'CV': ('Live URLs, screenshots at 24 h, platform analytics export', 'Live-URLs, Screenshots nach 24 h, Analytics-Export'),
    'SP': ('Post URLs, screenshots, native insights', 'Post-URLs, Screenshots, native Insights'),
    'SF': ('Live URLs, screenshots, retention graphs', 'Live-URLs, Screenshots, Retention-Kurven'),
    'LS': ('VOD links, overlay screenshots, concurrent-viewer export', 'VOD-Links, Overlay-Screenshots, Export gleichzeitiger Zuschauer'),
    'GA': ('Approved T&Cs, entry export, draw protocol', 'Freigegebene AGB, Teilnahme-Export, Ziehungsprotokoll'),
    'HV': ('Master file, live URLs, analytics export', 'Masterdatei, Live-URLs, Analytics-Export'),
    'PH': ('Delivery receipt, usage log', 'Lieferschein, Nutzungsprotokoll'),
    'NL': ('Send report, rendered screenshot', 'Versandreport, Screenshot der Ausgabe'),
    'PP': ('Timestamped clips, screenshots', 'Clips mit Zeitmarken, Screenshots'),
}


def build_page(r: dict, k: dict) -> str:
    dl, ap, rk, ops, wk = r['deliverables'], r['approvals'], r['risks'], r['ops'], r['weeks']
    before, after = r['before'].set_index('fmt'), r['after'].set_index('fmt')
    FMTN = {'CV': ('Creator video', 'Creator-Video'), 'SF': ('Short-form video', 'Short-Form-Video'),
            'LS': ('Livestream', 'Livestream'), 'HV': ('Hero video', 'Hero-Video'),
            'SPV': ('Creator-led video post', 'Creator-Video-Post'), 'SP': ('Static social post', 'Statischer Social Post'),
            'PH': ('Photo package', 'Fotopaket'), 'PP': ('Product placement', 'Produktplatzierung'),
            'NL': ('Newsletter', 'Newsletter'), 'GA': ('Giveaway', 'Gewinnspiel')}
    CHIP = {'L': ('ok', 'Low', 'Niedrig'), 'M': ('warn', 'Medium', 'Mittel'), 'H': ('bad', 'High', 'Hoch')}

    # ================================================================ slide 2 · operations
    tot = ops.sum(numeric_only=True)
    ops_kpis = ('<div class="kpis mini row8">'
                + kpi(str(k['meetings']), b('meetings I ran or joined', 'Meetings geleitet oder dabei'), b('14 of them with AKG', 'davon 14 mit AKG'))
                + kpi(str(k['client_comms']), b('messages & calls with AKG', 'Nachrichten & Calls mit AKG'), b('my average reply: 2.6 h', 'meine Ø Antwort: 2,6 h'))
                + kpi(str(k['internal_tasks']), b('internal tasks I coordinated', 'interne Aufgaben koordiniert'), b(f'{k["internal_sla"]} done in the agreed time ({fmt_pct(k["internal_sla"] / k["internal_tasks"], "en", 0)})', f'{k["internal_sla"]} in der vereinbarten Zeit ({fmt_pct(k["internal_sla"] / k["internal_tasks"], "de", 0)})'))
                + kpi(f'{k["actions_done"]}/{k["actions_total"]}', b('agreed to-dos closed', 'vereinbarte Aufgaben erledigt'), b('5 open at the end, none in the contract', '5 am Ende offen, keine vertraglich'))
                + kpi(str(k['approval_requests']), b('sign-off requests to AKG', 'Freigabeanfragen an AKG'), b(f'{k["sla_met"]} answered within 3 working days', f'{k["sla_met"]} binnen 3 Werktagen beantwortet'))
                + kpi(str(k['revisions']), b('content changes', 'inhaltliche Änderungen'), b(f'{k["rev_internal"]} ours, {k["rev_client"]} asked by AKG', f'{k["rev_internal"]} von uns, {k["rev_client"]} von AKG gewünscht'))
                + kpi(str(k['dependencies']), b('hand-offs I tracked', 'Übergaben verfolgt'), b('e.g. product shipped → photo shoot', 'z. B. Produkt geliefert → Fotoshooting'))
                + kpi(str(int(tot['pod_items'])), b('proofs that content went live', 'Nachweise für Go-lives'), b('links, screenshots, exports', 'Links, Screenshots, Exporte'))
                + '</div>')
    activity_html = ops_kpis + chart('ops-heatmap', 'Heatmap of 14 activity metrics per week, weeks 1 to 8, with counts in each cell',
                                     'Heatmap von 14 Aktivitätskennzahlen pro Woche, Wochen 1 bis 8, mit Anzahl in jeder Zelle', 'wide-chart')
    wrows = []
    for i, t in enumerate(WEEK_TEXT):
        w = i + 1
        o = ops.iloc[i]
        live = dl[dl.week == w]
        wk_row = wk.iloc[i]
        dels = ', '.join(live.id) or '–'
        risks_w = ', '.join(rk[rk.week == w].id) or '–'
        kpi_en = f'{int(o.on_time)} of {int(o.deliverables)} live on the planned day' if o.deliverables else '3 of 4 content plans accepted as sent'
        kpi_de = f'{int(o.on_time)} von {int(o.deliverables)} am Plantag live' if o.deliverables else '3 von 4 Content-Plänen ohne Änderung angenommen'
        if wk_row.impressions > 50_000:
            kpi_en += f' · {fmt_pct(wk_row.engagements / wk_row.impressions, "en")} of impressions interacted'
            kpi_de += f' · {fmt_pct(wk_row.engagements / wk_row.impressions, "de")} der Impressionen interagierten'
        wrows.append([f'<span class="wk">W{w}</span><small>{dt(wk_row.start)}</small>', b(*t['obj']),
                      b(f'{int(o.internal_tasks + o.client_comms)} tasks · ', f'{int(o.internal_tasks + o.client_comms)} Aufgaben · ') + b(*t['tasks']),
                      b(*t['who']), f'<span class="mono">{dels}</span>',
                      b(f'{int(o.approvals_submitted)} sent · {int(o.approvals_completed)} signed off', f'{int(o.approvals_submitted)} geschickt · {int(o.approvals_completed)} freigegeben'),
                      f'<span class="mono">{risks_w}</span>', b(*t['issues']), b(*t['actions']), b(*t['outcome']), b(kpi_en, kpi_de)])
    weekly_html = table([b('Week', 'Woche'), b('Main objective', 'Hauptziel'), b('Tasks handled', 'Aufgaben'), 'Stakeholder', 'Deliverables',
                         b('AKG sign-offs', 'AKG-Freigaben'), b('New risks', 'Neue Risiken'), b('Problems', 'Probleme'), b('Actions taken', 'Maßnahmen'),
                         b('Outcome', 'Ergebnis'), b('Key number', 'Kennzahl')], wrows, cls='weekly',
                        label_en='Weekly operations table', label_de='Wöchentliche Operations-Tabelle')
    from campaign import GROUPS, STAKEHOLDERS
    gnames = {'AKG': ('AKG', 'AKG'), 'G2': ('G2 internal', 'G2 intern'), 'Creators': ('Creators & players', 'Creator & Spieler'),
              'Production': ('Agency & production', 'Agentur & Produktion')}
    grows = []
    for g, v in GROUPS.items():
        people = sum(1 for s in STAKEHOLDERS if s[2] == g)
        grows.append([b(*gnames[g]), str(people), str(v['meetings'] + v['messages']), str(v['meetings']), str(v['followups']),
                      str(v['escalations']), b(f'{v["my_resp"]:.1f} h / {v["their_resp"]:.1f} h', f'{de_num(v["my_resp"], 1)} h / {de_num(v["their_resp"], 1)} h'),
                      b(f'{v["done"]}/{v["total"]} ({fmt_pct(v["done"] / v["total"], "en", 0)})', f'{v["done"]}/{v["total"]} ({fmt_pct(v["done"] / v["total"], "de", 0)})')])
    grows.append([b('<b>Total</b>', '<b>Gesamt</b>'), '25', str(k['touchpoints']), str(k['meetings']), str(k['followups']), '2',
                  b(f'{k["my_resp"]:.1f} h / –', f'{de_num(k["my_resp"], 1)} h / –'),
                  b(f'{k["actions_done"]}/{k["actions_total"]} ({fmt_pct(k["action_rate"], "en", 0)})', f'{k["actions_done"]}/{k["actions_total"]} ({fmt_pct(k["action_rate"], "de", 0)})')])
    stake_html = ('<div class="split-2 stk">'
                  + table([b('Group', 'Gruppe'), b('People', 'Personen'), b('Contacts', 'Kontakte'), 'Meetings', b('Reminders I sent', 'Erinnerungen von mir'), b('Escalations', 'Eskalationen'),
                           b('Average reply: me / them', 'Ø Antwort: ich / sie'), b('To-dos closed', 'Aufgaben erledigt')],
                          grows, cls='compact', label_en='Stakeholder management metrics', label_de='Kennzahlen Stakeholder-Management')
                  + chart('stakeholder-map', 'Stakeholder map: 25 stakeholders by influence and interest, bubble size = touchpoints',
                          'Stakeholder-Map: 25 Stakeholder nach Einfluss und Interesse, Blasengröße = Touchpoints')
                  + '</div><p class="note">' + b('Reply times in working hours. Contacts = meetings + messages; for AKG that is 14 meetings + 38 messages and calls.',
                                                 'Antwortzeiten in Arbeitsstunden. Kontakte = Meetings + Nachrichten; bei AKG 14 Meetings + 38 Nachrichten und Calls.') + '</p>')
    crows = []
    for i, (ach, iss, act, nxt) in enumerate(CLIENT_REPORT):
        w = wk.iloc[i]
        o = ops.iloc[i]
        if w.impressions > 50_000:
            kk = b(f'{fmt_num(w.impressions, "en")} impressions · {fmt_pct(w.engagements / w.impressions, "en")} interacted · {fmt_num(w.clicks, "en")} clicks to AKG',
                   f'{fmt_num(w.impressions, "de")} Impressionen · {fmt_pct(w.engagements / w.impressions, "de")} interagierten · {fmt_num(w.clicks, "de")} Klicks zu AKG')
        else:
            kk = b(f'{int(o.approvals_submitted)} sent for sign-off · {int(o.deliverables)} live', f'{int(o.approvals_submitted)} zur Freigabe geschickt · {int(o.deliverables)} live')
        crows.append([f'<span class="wk">W{i + 1}</span><small>{dt(w.start + timedelta(days=4))}</small>', b(*ach), kk, b(*iss), b(*act), b(*nxt)])
    client_html = (table([b('Report', 'Report'), b('Key achievement', 'Wichtigster Erfolg'), b('Key numbers', 'Kennzahlen'), b('Problem', 'Problem'), b('Action', 'Maßnahme'),
                          b('Next step', 'Nächster Schritt')], crows, cls='reports', label_en='Weekly AKG report', label_de='Wöchentlicher AKG-Report')
                   + '<p class="note">' + b('Sent every Friday to the AKG Brand Manager, copy to my line manager. Same structure every week so changes stand out.',
                                            'Jeden Freitag an den AKG Brand Manager, in Kopie an meinen Vorgesetzten. Jede Woche gleiche Struktur, damit Veränderungen auffallen.') + '</p>')
    s2 = f'''
  <section tabindex="-1" class="slide dash" data-title="Operations" data-de-data-title="Operations">
    <div class="inner wide">
      <header class="dash-head rv"><div>
        <div class="kicker"><span lang="en">03 · Detail · day-to-day management, week by week</span><span lang="de">03 · Detail · Tagesgeschäft, Woche für Woche</span></div>
        <h2>{b('What I managed, week by week', 'Was ich gesteuert habe, Woche für Woche')}<span class="accent">.</span></h2>
      </div></header>
      {tabs('Operations sections', 'Abschnitte', [
          ('act', 'Activity dashboard', 'Aktivitäts-Dashboard', activity_html),
          ('ops', 'Weekly operations', 'Wöchentliche Operations', weekly_html),
          ('stk', 'Stakeholders', 'Stakeholder', stake_html),
          ('rep', 'Client reporting', 'Kunden-Reporting', client_html)])}
    </div>
  </section>'''

    # ================================================================ slide 3 · delivery control
    trows = []
    for _, a in dl.iterrows():
        st = chip('ok', 'Live on time', 'Pünktlich live') if a.on_time else chip('warn', f'Live, {a.days_late} days late', f'Live, {a.days_late} Tage später')
        appr = {'R1': ('Signed off as sent', 'Ohne Änderung freigegeben'), 'R2': ('Signed off after 1 change', 'Nach 1 Änderung freigegeben'),
                'R3': ('Signed off after 2 changes', 'Nach 2 Änderungen freigegeben'),
                'ESC': ('Signed off after I escalated', 'Nach meiner Eskalation freigegeben')}[a.approval]
        c, le, ld = CHIP[a.risk]
        if a.type == 'GA':
            perf = b('18,400 entries', '18.400 Teilnahmen')
        elif a.type == 'NL':
            perf = b(f'{fmt_num(a.clicks, "en")} clicks · {fmt_pct(a.clicks / a.impressions, "en")} of opens clicked', f'{fmt_num(a.clicks, "de")} Klicks · {fmt_pct(a.clicks / a.impressions, "de")} der Öffnungen klickten')
        elif a.views > 0:
            perf = b(f'{fmt_num(a.views, "en")} views · {fmt_pct(a.engagements / a.impressions, "en")} interacted', f'{fmt_num(a.views, "de")} Views · {fmt_pct(a.engagements / a.impressions, "de")} interagierten')
        else:
            perf = b(f'{fmt_num(a.impressions, "en")} impressions · {fmt_pct(a.engagements / a.impressions, "en")} interacted', f'{fmt_num(a.impressions, "de")} Impressionen · {fmt_pct(a.engagements / a.impressions, "de")} interagierten')
        pod = b(f'✓ {a.evidence_items} proofs', f'✓ {a.evidence_items} Nachweise')
        trows.append([f'<span class="mono">{a.id}</span> {b(escape(a.title_en), escape(a.title_de))}', b(a.workstream_en, a.workstream_de),
                      escape(a.owner), escape(a.stakeholder), dt(a.due), st, b(*appr), str(a.revisions), chip(c, le, ld), dt(a.live), pod, perf])
    tracker_html = ('<div class="chips-row">' + chip('ok', f'{k["assets"]} of {k["assets"]} live', f'{k["assets"]} von {k["assets"]} live')
                    + chip('ok', f'{k["on_time"]} on the planned day', f'{k["on_time"]} am Plantag')
                    + chip('warn', '2 later: photo shoot +6 days (agreed with AKG), creator video 2 +2 days', '2 später: Fotoshooting +6 Tage (mit AKG vereinbart), Creator-Video 2 +2 Tage')
                    + chip('neutral', f'{k["revisions"]} content changes: {k["rev_internal"]} ours, {k["rev_client"]} asked by AKG', f'{k["revisions"]} inhaltliche Änderungen: {k["rev_internal"]} von uns, {k["rev_client"]} von AKG')
                    + '</div>'
                    + table(['Deliverable', 'Workstream', b('Owner at G2', 'Owner bei G2'), b('Contact', 'Ansprechpartner'), b('Planned day', 'Plantag'), 'Status',
                             b('AKG sign-off', 'AKG-Freigabe'), b('Changes (ours + AKG)', 'Änderungen (G2 + AKG)'), b('Risk', 'Risiko'), b('Went live', 'Live seit'),
                             b('Proof it went live', 'Nachweis'), 'Performance'], trows, cls='tracker', label_en='Deliverable tracker', label_de='Deliverable-Tracker'))
    timeline_html = (chart('timeline', 'Timeline of all 31 deliverables by type: plan date and go-live, two late items highlighted',
                           'Zeitplan aller 31 Deliverables nach Typ: Plantermin und Go-live, zwei verspätete hervorgehoben', 'wide-chart')
                     + '<p class="note">' + b('Plan dates are the internal dates agreed with AKG in week 1. Contract windows ran 5 working days beyond them.',
                                              'Plantermine sind die in Woche 1 mit AKG vereinbarten internen Termine. Die Vertragsfenster lagen 5 Werktage dahinter.') + '</p>')
    appr_kpis = ('<div class="kpis mini row8">'
                 + kpi(f'{k["briefs"]}/{k["briefs"]}', b('content plans signed off by AKG', 'Content-Pläne von AKG freigegeben'), b('before production · 3 accepted as sent', 'vor der Produktion · 3 ohne Änderung'))
                 + kpi(str(k['submissions']), b('finished pieces sent to AKG', 'fertige Inhalte an AKG geschickt'), b('covers all 31 assets; placements went in batches', 'deckt alle 31 Assets ab; Placements gebündelt'))
                 + kpi(f'{k["first_round"]}/{k["submissions"]}', b('accepted by AKG without changes', 'von AKG ohne Änderungen angenommen'), p(k['fr_rate'], 0))
                 + kpi(str(k['submissions'] - k['first_round']), b('needed changes from AKG', 'brauchten Änderungen von AKG'), b(f'{k["rev_client"]} change rounds in total', f'{k["rev_client"]} Änderungsrunden insgesamt'))
                 + kpi(b(f'{k["avg_approval"]:.1f} days', f'{k["avg_approval"]:.1f} Tage'.replace('.', ',')), b('average wait for AKG sign-off', 'Ø Wartezeit auf AKG-Freigabe'), b('working days', 'Werktage'))
                 + kpi(b(f'{k["longest_delay"]} days', f'{k["longest_delay"]} Tage'), b('longest wait for AKG feedback', 'längste Wartezeit auf AKG-Feedback'), b('hero video · agreed limit: 3', 'Hero-Video · vereinbart: 3'))
                 + kpi(f'{k["sla_met"]}/{k["approval_requests"]}', b('answered within 3 working days', 'binnen 3 Werktagen beantwortet'), p(k['sla_rate'], 0), hl=True)
                 + kpi(f'{k["approved_normal"]} + {k["escalated"]}', b('signed off normally + after I escalated', 'normal freigegeben + nach Eskalation'), b('no escalation was critical', 'keine Eskalation war kritisch'))
                 + '</div>')
    approvals_html = appr_kpis + chart('approval-cycles', 'Approval time per submission in business days against the 3-day SLA, escalations marked',
                                       'Freigabedauer je Einreichung in Werktagen gegen das 3-Tage-SLA, Eskalationen markiert', 'wide-chart')
    rrows = []
    for _, x in rk.iterrows():
        mit, stat, out = RISK_TEXT[x.id]
        c = 'warn' if x.materialised else 'ok'
        rrows.append([f'<span class="mono">{x.id}</span> {b(x.risk_en, x.risk_de)}', f'{x.probability} × {x.impact} = {x.score}', escape(x.owner),
                      b(*mit), chip(c, *stat), b(f'{x.resolution_bdays} days', f'{x.resolution_bdays} Tage'), b(*out)])
    risks_html = ('<div class="split-2 risks">'
                  + table([b('Risk', 'Risiko'), b('Likelihood × damage (1–5 each)', 'Wahrsch. × Schaden (je 1–5)'), 'Owner', b('What we did', 'Was wir getan haben'), 'Status',
                           b('Days to solve', 'Tage bis gelöst'), b('Final outcome', 'Ergebnis')], rrows, cls='compact', label_en='Risks and issues', label_de='Risiken und Issues')
                  + chart('risk-matrix', 'Risk matrix: six risks by probability and impact; four materialised as issues',
                          'Risikomatrix: sechs Risiken nach Wahrscheinlichkeit und Auswirkung; vier traten als Issue ein')
                  + '</div><p class="note">' + b(f'4 of 6 risks actually happened; each was solved in {k["avg_issue"]:.0f} working days on average. 5 of 6 never touched the contract; R3 caused the one deadline move, agreed with AKG in writing.',
                                                 f'4 von 6 Risiken traten ein; jedes wurde im Schnitt in {k["avg_issue"]:.0f} Werktagen gelöst. 5 von 6 berührten den Vertrag nie; R3 verursachte die einzige Terminverschiebung, schriftlich mit AKG vereinbart.') + '</p>')
    from campaign import CONTRACT, TYPES
    prows = []
    for t_, cnt in CONTRACT.items():
        sub = dl[dl.type == t_]
        status = chip('ok', 'Verified', 'Verifiziert')
        if t_ == 'LS':
            status = chip('warn', 'Verified · export re-pulled 24.06.', 'Verifiziert · Export 24.06. neu gezogen')
        prows.append([b(TYPES[t_][0], TYPES[t_][1]), str(cnt), str(len(sub)), b(*POD_TEXT[t_]), dt(sub.live.max()),
                      f'<span class="mono">[G2 Drive]/AKG-2026/PoD/{t_}/</span>', b('Me · countersigned by AKG Brand Manager', 'Ich · gegengezeichnet vom AKG Brand Manager'), status])
    prows.append([b('<b>Total</b>', '<b>Gesamt</b>'), '31', '31', b(f'{int(tot["pod_items"])} evidence items', f'{int(tot["pod_items"])} Nachweise'), '25.06.', '–', '–',
                  chip('ok', '100% coverage', '100 % Abdeckung')])
    pod_html = table([b('Deliverable', 'Deliverable'), b('Promised', 'Zugesagt'), b('Delivered', 'Geliefert'), b('Evidence collected', 'Gesammelte Nachweise'),
                      b('Last date', 'Letztes Datum'), b('Location (placeholder)', 'Ablage (Platzhalter)'), b('Verified by', 'Verifiziert von'), 'Status'],
                     prows, cls='compact', label_en='Proof of delivery', label_de='Proof of Delivery')
    s3 = f'''
  <section tabindex="-1" class="slide dash" data-title="Delivery control" data-de-data-title="Liefersteuerung">
    <div class="inner wide">
      <header class="dash-head rv"><div>
        <div class="kicker"><span lang="en">04 · Detail · deliverables, approvals, risks, proof</span><span lang="de">04 · Detail · Deliverables, Freigaben, Risiken, Nachweise</span></div>
        <h2>{b('Keeping 31 assets on track', '31 Assets auf Kurs halten')}<span class="accent">.</span></h2>
      </div></header>
      {tabs('Delivery sections', 'Abschnitte', [
          ('trk', 'Deliverable tracker', 'Deliverable-Tracker', tracker_html),
          ('tml', 'Timeline', 'Zeitplan', timeline_html),
          ('apr', 'Approval workflow', 'Freigabe-Workflow', approvals_html),
          ('rsk', 'Risks & issues', 'Risiken & Issues', risks_html),
          ('pod', 'Proof of delivery', 'Proof of Delivery', pod_html)])}
    </div>
  </section>'''

    # ================================================================ slide 4 · optimisation
    order = ['CV', 'SF', 'LS', 'HV', 'SP', 'PH', 'PP', 'NL']
    frows = []
    for f in order:
        x = before.loc[f]
        frows.append([b(*FMTN[f]), str(int(x.assets)), n(x.reach, True), n(x.views, True) if x.views else '–', p(x.er),
                      p(x.ctr, 2), p(x.completion, 0) if x.completion == x.completion else '–', p(x.action_rate, 2)])
    evidence_html = ('<div class="split-2 evidence">'
                     + table([b('Format (weeks 1–5)', 'Format (Wochen 1–5)'), b('Pieces', 'Anzahl'), b('People reached', 'Erreichte Personen'), b('Video views', 'Video-Views'),
                              b('Interactions per 100 impressions', 'Interaktionen pro 100 Impressionen'),
                              b('Clicks per 100 impressions', 'Klicks pro 100 Impressionen'), b('Watched to the end', 'Bis zum Ende gesehen'), b('Site actions per 100 people', 'Website-Aktionen pro 100 Personen')], frows, cls='compact',
                             label_en='Format performance, weeks 1 to 5', label_de='Formatleistung, Wochen 1 bis 5')
                     + chart('format-rates', 'Interactions and clicks per 100 impressions by format, weeks 1 to 5: creator-led and video formats lead',
                             'Interaktionen und Klicks pro 100 Impressionen nach Format, Wochen 1 bis 5: Creator- und Videoformate vorn')
                     + '</div><p class="note">' + b('Site actions = tracked sign-ups and product-page visits on the AKG landing page. The newsletter row counts email opens, so it is not comparable with social formats.',
                                                    'Website-Aktionen = getrackte Anmeldungen und Produktseitenbesuche auf der AKG-Landingpage. Die Newsletter-Zeile zählt E-Mail-Öffnungen und ist nicht mit Social-Formaten vergleichbar.') + '</p>')
    m = r['models']
    eng, ctr = m['eng'], m['ctr']
    import math
    ce, cc = math.exp(eng.params['creator_led']), math.exp(ctr.params['creator_led'])
    ve, vc = math.exp(eng.params['video']), math.exp(ctr.params['video'])
    nobs = m['n']
    stats = ('<div class="model-stats">'
             + f'<div><b>{b("What drives interactions", "Was Interaktionen treibt")}</b><span class="mono">log(eng) ~ log(impr) + creator + video + paid + age</span>'
             + f'<small>{b(f"Fitted on {nobs} asset-weeks (weeks 1–5) · explains {eng.rsquared * 100:.0f}% of the ups and downs", f"Geschätzt auf {nobs} Asset-Wochen (Wochen 1–5) · erklärt {eng.rsquared * 100:.0f} % der Schwankungen")} · OLS, R² = {dec(eng.rsquared, 3)}</small></div>'
             + f'<div><b>{b("What drives clicks", "Was Klicks treibt")}</b><span class="mono">clicks / impr ~ creator + video + paid + age</span>'
             + f'<small>{b(f"Same {nobs} asset-weeks · allows for the extra noise in click data", f"Dieselben {nobs} Asset-Wochen · berücksichtigt das zusätzliche Rauschen in Klickdaten")} · {b("quasi-binomial GLM", "quasi-binomiales GLM")}, φ = {dec(ctr.scale, 1)}</small></div>'
             + f'<div><b>{b("Tested before we trusted it", "Getestet, bevor wir ihm vertrauten")}</b><span class="mono">{b("forecast for week 6, made in week 5", "Prognose für Woche 6, erstellt in Woche 5")}</span>'
             + f'<small>{b("Actual vs. forecast", "Ist vs. Prognose")}: {b("interactions", "Interaktionen")} {p(k["w6_eng"], 1, True)} · {b("clicks", "Klicks")} {p(k["w6_clicks"], 1, True)} · {b("people reached", "Reichweite")} {p(k["w6_reach"], 1, True)}</small></div>'
             + '</div>')
    model_html = ('<div class="split-2 model">'
                  + '<div>' + stats + chart('model-effects', 'Model effects with 95% confidence intervals: creator-led and video formats raise engagement and click-through',
                                          'Modelleffekte mit 95-%-Konfidenzintervallen: Creator- und Videoformate erhöhen Engagement und Klickrate') + '</div>'
                  + chart('weekly-forecast', 'Interactions per week: actual bars against the week-5 forecast for the old plan, with its likely range (80%)',
                          'Interaktionen pro Woche: Ist gegen die Prognose aus Woche 5 für den alten Plan, mit wahrscheinlichem Bereich (80 %)')
                  + '</div><p class="note">' + b(
                      f'Made by a creator: ×{ce:.2f} interactions and ×{cc:.2f} odds of a click. Video: ×{ve:.2f} and ×{vc:.2f}. Always compared like for like: same reach, same paid promotion, same weeks online. The forecast range comes from re-running the model 400 times on resampled data.',
                      f'Von einem Creator gemacht: ×{de_num(ce)} Interaktionen und ×{de_num(cc)} Klick-Chance. Video: ×{de_num(ve)} und ×{de_num(vc)}. Immer fair verglichen: gleiche Reichweite, gleiche bezahlte Promotion, gleich lange online. Der Prognosebereich stammt aus 400 Neuberechnungen auf neu gezogenen Daten.') + '</p>')
    cv, sp = before.loc['CV'], before.loc['SP']
    fc = k['fc78']
    act78 = k['act78']
    lift_rows = [
        [b('Interactions', 'Interaktionen'), n(fc['engagements']), n(act78['engagements']), p(k['lift_eng'], 0, True)],
        [b('Clicks to AKG', 'Klicks zu AKG'), n(fc['clicks']), n(act78['clicks']), p(k['lift_clicks'], 0, True)],
        [b('Additional people reached', 'Zusätzlich erreichte Personen'), n(fc['reach']), n(act78['reach']), p(k['lift_reach'], 0, True)],
        [b('Videos watched to the end', 'Videos bis zum Ende gesehen'), p(fc['completion'], 0), p(act78['completion'], 0), p(k['lift_comp'], 0, True) + b(f' ({(act78["completion"] - fc["completion"]) * 100:+.0f} pts)', f' ({(act78["completion"] - fc["completion"]) * 100:+.0f} Pkt.)')],
    ]
    decision_html = ('<div class="split-2 decision">'
                     + '<div class="decision-text">'
                     + f'<h3>{b("The operational decision", "Die operative Entscheidung")}</h3><ol>'
                     + '<li>' + b(f'Weeks 1–5 by format: creator videos got {cv.er * 100:.1f} interactions and {cv.ctr * 100:.2f} clicks per 100 impressions; static posts only {sp.er * 100:.1f} and {sp.ctr * 100:.2f}.',
                                  f'Wochen 1–5 nach Format: Creator-Videos bekamen {de_num(cv.er * 100, 1)} Interaktionen und {de_num(cv.ctr * 100)} Klicks pro 100 Impressionen; statische Posts nur {de_num(sp.er * 100, 1)} und {de_num(sp.ctr * 100)}.') + '</li>'
                     + f'<li>{b("The models showed the gap stays when you compare like for like (same reach, paid promotion and weeks online), so it was not just bigger audiences.", "Die Modelle zeigten: Der Abstand bleibt auch im fairen Vergleich (gleiche Reichweite, Promotion und Zeit online) – es lag also nicht nur an größeren Audiences.")}</li>'
                     + f'<li>{b("Proposal to my line manager, then AKG (05.06.): run SP-07/08 as creator-led video posts, move paid support from static posts to LS-02, SF-04, CV-03. Same deliverable count, no extra cost.", "Vorschlag an meinen Vorgesetzten, dann an AKG (05.06.): SP-07/08 als Creator-Video-Posts, Paid Support von statischen Posts auf LS-02, SF-04, CV-03. Gleiche Deliverable-Anzahl, keine Mehrkosten.")}</li>'
                     + f'<li>{b("AKG approved on 09.06. I re-briefed Creator D and updated the tracker and the contract annex (format change note).", "AKG gab am 09.06. frei. Ich habe Creator D neu gebrieft und Tracker sowie Vertragsanhang (Change Note) aktualisiert.")}</li>'
                     + '</ol></div>'
                     + '<div>' + table([b('Weeks 7–8', 'Wochen 7–8'), b('Forecast (original plan)', 'Prognose (ursprünglicher Plan)'), b('Actual', 'Ist'), b('Change', 'Veränderung')],
                                       lift_rows, cls='compact', label_en='Weeks 7 and 8: actual against forecast', label_de='Wochen 7 und 8: Ist gegen Prognose')
                     + chart('lift', 'Weeks 7 and 8 against the forecast: interactions +38%, clicks +41%, people reached +22%, videos watched to the end +27%',
                             'Wochen 7 und 8 gegen die Prognose: Interaktionen +38 %, Klicks +41 %, Reichweite +22 %, Videos bis zum Ende +27 %') + '</div>'
                     + '</div><p class="note">' + b(f'The actual result is far above the forecast’s likely range ({fmt_num(r["interval"]["engagements"][0], "en")}–{fmt_num(r["interval"]["engagements"][1], "en")} interactions, 80%). There was no control group, so this is a strong signal, not proof.',
                                                    f'Das Ist-Ergebnis liegt weit über dem wahrscheinlichen Bereich der Prognose ({fmt_num(r["interval"]["engagements"][0], "de")}–{fmt_num(r["interval"]["engagements"][1], "de")} Interaktionen, 80 %). Ohne Kontrollgruppe ist das ein starkes Signal, kein Beweis.') + '</p>')
    # ================================================================ slide 5 · value
    sc = r['scenario']
    lv, ss = before.loc['LS'], after.loc['LS']
    opps = [
        (('Creator-led video as the core format', 'Creator-Video als Kernformat'),
         b(f'A creator-led video post gets ×{sc["factor"]:.2f} the interactions of a static post (likely range ×{sc["lo"]:.2f}–×{sc["hi"]:.2f}). Had the {sc["posts"]} static post slots run that way: about +{fmt_num(sc["extra_eng"], "en")} interactions ({fmt_num(sc["extra_lo"], "en")}–{fmt_num(sc["extra_hi"], "en")}).',
           f'Ein Creator-Video-Post bekommt ×{de_num(sc["factor"])} die Interaktionen eines statischen Posts (wahrscheinlich ×{de_num(sc["lo"])}–×{de_num(sc["hi"])}). Wären die {sc["posts"]} statischen Slots so gelaufen: rund +{fmt_num(sc["extra_eng"], "de")} Interaktionen ({fmt_num(sc["extra_lo"], "de")}–{fmt_num(sc["extra_hi"], "de")}).'),
         b('A higher creator/video share, tested against a control group.', 'Ein höherer Creator/Video-Anteil, getestet gegen eine Kontrollgruppe.')),
        (('Livestream segments as a series', 'Livestream-Segmente als Serie'),
         b(f'Livestreams: {lv.er * 100:.1f} interactions per 100 impressions in weeks 1–5, {ss.er * 100:.1f} in weeks 7–8, and {fmt_pct(ss.completion, "en", 0)} watched to the end.',
           f'Livestreams: {de_num(lv.er * 100, 1)} Interaktionen pro 100 Impressionen in Wochen 1–5, {de_num(ss.er * 100, 1)} in Wochen 7–8, und {fmt_pct(ss.completion, "de", 0)} bis zum Ende gesehen.'),
         b('A recurring monthly segment instead of two one-offs.', 'Ein wiederkehrendes Monatsformat statt zwei Einzeltermine.')),
        (('Consent-based audience from the giveaway', 'Einwilligungsbasierte Audience aus dem Gewinnspiel'),
         b(f'18,400 entries in 15 days; {fmt_pct(before.loc["NL"].ctr, "en")} of newsletter opens led to a click.', f'18.400 Teilnahmen in 15 Tagen; {fmt_pct(before.loc["NL"].ctr, "de")} der Newsletter-Öffnungen führten zu einem Klick.'),
         b('An opt-in for AKG product news, checked with both legal teams.', 'Ein Opt-in für AKG-Produktnews, mit beiden Rechtsabteilungen geprüft.')),
        (('Fewer, better-integrated placements', 'Weniger, besser integrierte Placements'),
         b(f'Placements did worst: {before.loc["PP"].er * 100:.1f} interactions and {before.loc["PP"].ctr * 100:.2f} clicks per 100 impressions.', f'Placements schnitten am schwächsten ab: {de_num(before.loc["PP"].er * 100, 1)} Interaktionen und {de_num(before.loc["PP"].ctr * 100)} Klicks pro 100 Impressionen.'),
         b('Fewer, story-led placements, measured by brand lift rather than clicks.', 'Weniger, storybasierte Placements, gemessen per Brand Lift statt Klicks.')),
        (('Measurement beyond clicks', 'Messung über Klicks hinaus'),
         b(f'Only {fmt_num(k["actions"], "en")} tracked actions on the AKG site; no sales data and no survey of brand perception.', f'Nur {fmt_num(k["actions"], "de")} getrackte Aktionen auf der AKG-Seite; keine Verkaufsdaten und keine Umfrage zur Markenwahrnehmung.'),
         b('Agree a brand-lift study and retailer tracking before launch.', 'Brand-Lift-Studie und Händler-Tracking vor dem Start vereinbaren.')),
    ]
    opp_html = ('<div class="opps">' + ''.join(
        f'<div class="opp"><span class="num">0{i + 1}</span><h3>{b(*t)}</h3><p><b>{b("Evidence", "Evidenz")}:</b> {ev}</p><p><b>{b("To discuss", "Zu besprechen")}:</b> {nx}</p></div>'
        for i, (t, ev, nx) in enumerate(opps)) + '</div>'
        + '<p class="note">' + b('Framed as questions for the review with AKG, not as a pitch. Projections come from 8 weeks of hypothetical data and are indicative only.',
                                 'Als Fragen fürs Review mit AKG formuliert, nicht als Pitch. Projektionen beruhen auf 8 Wochen hypothetischer Daten und sind nur ein Richtwert.') + '</p>')
    files = [
        ('kpis.json', ('All KPI cards and headline figures', 'Alle KPI-Karten und Kennzahlen'), ('KPI cards', 'KPI-Karten')),
        ('weekly_performance.csv', ('Audience metrics per week', 'Audience-Kennzahlen pro Woche'), ('Line charts', 'Liniendiagramme')),
        ('weekly_operations.csv', ('My activity per week (14 metrics)', 'Meine Aktivität pro Woche (14 Kennzahlen)'), ('Bar charts, heatmap', 'Balkendiagramme, Heatmap')),
        ('funnel.csv', ('Impressions to landing-page actions', 'Impressionen bis Landingpage-Aktionen'), ('Funnel on slide 1', 'Funnel auf Folie 1')),
        ('deliverables.csv', ('31 deliverables with dates, status, performance', '31 Deliverables mit Terminen, Status, Performance'), ('Tracker, status chart, timeline', 'Tracker, Statuschart, Zeitplan')),
        ('approvals.csv', ('31 approval requests with clock and rounds', '31 Freigabeanfragen mit Dauer und Runden'), ('Approval-cycle chart', 'Freigabezyklen')),
        ('stakeholders.csv', ('25 stakeholders with influence, interest, touchpoints', '25 Stakeholder mit Einfluss, Interesse, Touchpoints'), ('Stakeholder map', 'Stakeholder-Map')),
        ('risks.csv', ('6 risks with scores and resolution', '6 Risiken mit Bewertung und Lösung'), ('Risk dashboard', 'Risiko-Dashboard')),
        ('format_before_after.csv', ('Format rates, weeks 1–5 and 7–8', 'Formatraten, Wochen 1–5 und 7–8'), ('Before/after charts', 'Vorher/Nachher')),
        ('forecast.csv', ('Week-5 forecast vs. actual, weeks 6–8', 'Prognose aus Woche 5 vs. Ist, Wochen 6–8'), ('Forecast chart', 'Prognosechart')),
        ('asset_week_panel.csv', ('Model data: one row per asset and week', 'Modelldaten: eine Zeile pro Asset und Woche'), ('Regression input', 'Regressions-Input')),
        ('model_summary.txt', ('Full statsmodels output', 'Vollständiger statsmodels-Output'), ('Model appendix', 'Modellanhang')),
    ]
    data_html = ('<div class="files">' + ''.join(
        f'<a class="file" href="data/{fn}" download><span class="mono">{fn}</span><span>{b(*desc)}</span><small>{b(*use)}</small></a>'
        for fn, desc, use in files) + '</div>'
        + '<p class="note">' + b('Generated by <span class="mono">tools/akg/build.py</span> (pandas, statsmodels, matplotlib, seaborn). The build checks every total against the brief before it writes a file.',
                                 'Erzeugt von <span class="mono">tools/akg/build.py</span> (pandas, statsmodels, matplotlib, seaborn). Der Build prüft jede Summe gegen das Briefing, bevor er eine Datei schreibt.') + '</p>')
    s5 = f'''
  <section tabindex="-1" class="slide dash final" data-title="Optimisation &amp; renewal" data-de-data-title="Optimierung &amp; Verlängerung">
    <div class="inner wide">
      <header class="dash-head rv"><div>
        <div class="kicker"><span lang="en">05 · Detail · the analysis, the decision, the renewal</span><span lang="de">05 · Detail · die Analyse, die Entscheidung, die Verlängerung</span></div>
        <h2>{b('Creator-led video wins: move weeks 7–8', 'Creator-Video gewinnt: Wochen 7–8 umschichten')}<span class="accent">.</span></h2>
      </div></header>
      {tabs('Optimisation sections', 'Abschnitte', [
          ('evi', 'Week-5 evidence', 'Evidenz Woche 5', evidence_html),
          ('mod', 'Model & forecast', 'Modell & Prognose', model_html),
          ('dec', 'Decision & impact', 'Entscheidung & Wirkung', decision_html),
          ('opp', 'Renewal & expansion', 'Verlängerung & Ausbau', opp_html),
          ('dat', 'Datasets', 'Datensätze', data_html)])}
      <div class="links rv">
        <a class="chip cv-chip" href="../../#1">{b('Back to the CV', 'Zurück zum Lebenslauf')}</a>
        <a class="chip" href="../../#11">{b('Back to the overview', 'Zurück zur Übersicht')}</a>
        <a class="chip" href="mailto:in@chrisbalan.com">in@chrisbalan.com</a>
      </div>
    </div>
  </section>'''

    # authored texts use plain '&' (T&Cs, Legal & Compliance): encode every one that is not already an entity
    slides = re.sub(r'&(?!(?:[a-zA-Z]+|#\d+);)', '&amp;', slide_results(r, k) + slide_drivers(r, k) + s2 + s3 + s5)
    # German numbers keep their unit on the same line (50 €, 72 %, 1,2 Mio.)
    slides = re.sub(r'(\d) (€|%|Mio\.|Tsd\.|Pkt\.|Tage|T\b)', '\\1&nbsp;\\2', slides)
    return TEMPLATE.replace('{{SLIDES}}', slides)


TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; font-src 'self'; base-uri 'none'; form-action 'none'; object-src 'none'">
<meta name="referrer" content="strict-origin-when-cross-origin">
<title>AKG × G2 · Partnership dashboard</title>
<meta name="description" content="Fictional case study by Christian Balan: day-to-day partnership management, campaign closeout and data-driven optimisation for a hypothetical 8-week AKG × G2 partnership.">
<meta name="author" content="Christian Balan">
<meta name="robots" content="noindex, nofollow, noarchive, nosnippet, noimageindex, noai, noimageai">
<meta name="copyright" content="© 2026 Christian Balan. All rights reserved.">
<meta name="theme-color" content="#000000">
<link rel="canonical" href="https://g2.chrisbalan.com/projects/akg/">
<link rel="icon" href="../../assets/favicon.svg" type="image/svg+xml">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Christian Balan">
<meta property="og:title" content="AKG × G2 · Partnership dashboard (fictional case study)">
<meta property="og:description" content="Day-to-day partnership management, campaign closeout and data-driven optimisation for a hypothetical 8-week partnership.">
<meta property="og:url" content="https://g2.chrisbalan.com/projects/akg/">
<link rel="preload" href="../../assets/fonts/barlow-condensed-800-italic.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="../../assets/fonts/inter-variable.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="../../css/deck.css">
<link rel="stylesheet" href="../../css/project.css">
<link rel="stylesheet" href="akg.css">
<noscript><link rel="stylesheet" href="../../css/no-js.css"><link rel="stylesheet" href="no-js.css"></noscript>
<script src="../../js/lang.js"></script>
<script src="../../js/project.js" defer></script>
</head>
<body class="project akg" data-page-title="AKG × G2 · Partnership dashboard" data-de-data-page-title="AKG × G2 · Partnerschafts-Dashboard">
<!-- Generated by tools/akg/build.py. Edit the generator, not this file. -->
<div class="progress" id="progress"></div>

<main class="deck">{{SLIDES}}
</main>

<footer class="hud">
  <span class="brand" aria-hidden="true">Christian Balan · <span lang="en">G2 Application</span><span lang="de">G2-Bewerbung</span> · <span id="slideTitle"></span></span>
  <div class="lang-switch" role="group" aria-label="Sprache / Language">
    <button class="lang-btn" type="button" data-set-lang="de" lang="de" aria-pressed="false" aria-label="Deutsch"><svg class="flag" viewBox="0 0 5 3" aria-hidden="true"><rect width="5" height="1" fill="#000"/><rect y="1" width="5" height="1" fill="#dd0000"/><rect y="2" width="5" height="1" fill="#ffce00"/></svg><span class="code" aria-hidden="true">DE</span></button>
    <button class="lang-btn" type="button" data-set-lang="en" lang="en" aria-pressed="true" aria-label="English"><svg class="flag" viewBox="0 0 60 30" aria-hidden="true"><clipPath id="uk-clip"><path d="M30,15h30v15zv15H0zH0V0zV0h30z"/></clipPath><path d="M0,0v30h60V0z" fill="#012169"/><path d="M0,0 60,30M60,0 0,30" stroke="#fff" stroke-width="6"/><path d="M0,0 60,30M60,0 0,30" clip-path="url(#uk-clip)" stroke="#c8102e" stroke-width="4"/><path d="M30,0v30M0,15h60" stroke="#fff" stroke-width="10"/><path d="M30,0v30M0,15h60" stroke="#c8102e" stroke-width="6"/></svg><span class="code" aria-hidden="true">EN</span></button>
  </div>
  <nav class="crumbs" aria-label="Site" data-de-aria-label="Website">
    <a class="crumb" href="../../#11"><span aria-hidden="true">←</span> <span class="crumb-label"><span lang="en">Overview</span><span lang="de">Übersicht</span></span></a>
    <a class="crumb" href="../../#1">CV</a>
  </nav>
  <nav class="nav" aria-label="Slides" data-de-aria-label="Folien">
    <div class="dots" id="dots"></div>
    <button class="icon-btn" type="button" id="prev" aria-label="Previous slide" data-de-aria-label="Vorherige Folie">‹</button>
    <span class="counter" id="counter" aria-hidden="true">1 / 5</span>
    <button class="icon-btn" type="button" id="next" aria-label="Next slide" data-de-aria-label="Nächste Folie">›</button>
  </nav>
  <div class="sr-only" id="announcer" aria-live="polite" aria-atomic="true"></div>
</footer>
</body>
</html>
'''
