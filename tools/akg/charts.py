"""Charts for the AKG x G2 dashboard: matplotlib + seaborn, rendered to SVG in the site's fonts and colours.

Every chart is drawn twice (English and German); the page shows the one matching <html lang>.
Text is converted to outlines so the SVGs look identical everywhere and need no web fonts.
"""
from __future__ import annotations

import os
import tempfile
from glob import glob

import logging
import re

import matplotlib

matplotlib.use('Agg')
logging.getLogger('matplotlib.font_manager').setLevel(logging.ERROR)  # JetBrains Mono ships one weight
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402
from fontTools.ttLib import TTFont  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

# site tokens (css/deck.css)
BG, SURFACE, SURFACE2, LINE = '#000000', '#0f0f10', '#19191b', '#2a2a2d'
TEXT, MUTED, ACCENT, GOLD = '#ffffff', '#a6a6ad', '#ee3d23', '#e3b94f'
ACCENT_DARK, GOLD_DARK, GREY = '#8f2413', '#8a6d2a', '#5c5c63'
GROUP_COLORS = {'G2': ACCENT, 'AKG': GOLD, 'Creators': TEXT, 'Production': MUTED}


def register_fonts(font_dir: str) -> None:
    """The site ships WOFF2 only; matplotlib needs TTF, so convert once into a temp folder."""
    tmp = tempfile.mkdtemp(prefix='akg-fonts-')
    for f in glob(os.path.join(font_dir, '*.woff2')):
        t = TTFont(f)
        t.flavor = None
        out = os.path.join(tmp, os.path.basename(f).replace('.woff2', '.ttf'))
        t.save(out)
        font_manager.fontManager.addfont(out)


def setup_style() -> None:
    sns.set_theme(style='dark', rc={
        'figure.facecolor': 'none', 'axes.facecolor': 'none', 'savefig.facecolor': 'none',
        'axes.edgecolor': LINE, 'axes.labelcolor': MUTED, 'xtick.color': MUTED, 'ytick.color': MUTED,
        'text.color': TEXT, 'grid.color': LINE, 'axes.grid': True, 'grid.linewidth': .6,
        'font.family': 'Inter', 'font.size': 9, 'axes.labelsize': 9, 'xtick.labelsize': 8.5, 'ytick.labelsize': 8.5,
        'legend.fontsize': 8.5, 'legend.frameon': False, 'axes.spines.top': False, 'axes.spines.right': False,
        'svg.fonttype': 'path', 'svg.hashsalt': 'akg-g2', 'patch.edgecolor': 'none', 'patch.force_edgecolor': False,
    })


T = {
    'en': dict(
        impressions='Impressions', views='Video views', engagements='Interactions', clicks='Clicks to AKG',
        actions='Actions on the AKG site', reach='People reached', week='Week', w='W', forecast='Forecast made in week 5 (old plan)',
        actual='Actual', band='Likely range (80%)', analysis='Week-5 analysis', realloc='Reallocation live',
        eng_per_week='Interactions per week', bdays='Working days until AKG signed off', sla='Agreed limit: 3 working days', first='First answer from AKG',
        rounds='Extra change rounds', escalated='I escalated', influence='Influence on the campaign',
        interest='Interest in day-to-day detail', touch='Contacts (meetings + messages)', prob='How likely (1–5)', impact='How much damage (1–5)',
        materialised='Happened, then solved', contained='Prevented', due='Planned date', live='Went live',
        late='Late', video_asset='Video asset', er='Interactions per 100 impressions', ctr='Clicks per 100 impressions', creator='Creator-led / video',
        static='Static / placement / other', effect='Multiplier on the rate (×1 = no effect; bar = 95% likely range)', eng_model='What drives interactions',
        ctr_model='What drives clicks', vs_fc='vs. forecast', completion='Videos watched to the end',
        compl='Watched to the end', lift='Weeks 7–8: actual vs. week-5 forecast',
        creator_led='Made by a creator', video='Video format', boosted='Paid promotion', age='Each extra week online',
        log_impr='Twice the impressions',
        ops=['Meetings', 'Messages & calls with AKG', 'Internal tasks I coordinated', 'Messages (all)', 'Agreed to-dos closed',
             'Sent to AKG for sign-off', 'Signed off by AKG', 'Content changes', 'Assets gone live', 'Proof items (links, screenshots)',
             'Hand-offs between teams', 'Risks spotted', 'Escalations', 'Reports sent'],
        fmts={'CV': 'Creator video', 'SF': 'Short-form video', 'LS': 'Livestream', 'HV': 'Hero video', 'SPV': 'Creator video post',
              'SP': 'Static social post', 'PH': 'Photo package', 'PP': 'Product placement', 'NL': 'Newsletter', 'GA': 'Giveaway'},
        groups={'G2': 'G2 internal', 'AKG': 'AKG', 'Creators': 'Creators & players', 'Production': 'Production partners'},
    ),
    'de': dict(
        impressions='Impressionen', views='Video-Views', engagements='Interaktionen', clicks='Klicks zu AKG',
        actions='Aktionen auf der AKG-Seite', reach='Erreichte Personen', week='Woche', w='W', forecast='Prognose aus Woche 5 (alter Plan)',
        actual='Ist', band='Wahrscheinlicher Bereich (80 %)', analysis='Analyse Woche 5', realloc='Umschichtung live',
        eng_per_week='Interaktionen pro Woche', bdays='Werktage bis zur AKG-Freigabe', sla='Vereinbartes Limit: 3 Werktage', first='Erste Antwort von AKG',
        rounds='Weitere Änderungsrunden', escalated='Von mir eskaliert', influence='Einfluss auf die Kampagne',
        interest='Interesse an operativen Details', touch='Kontakte (Meetings + Nachrichten)', prob='Wie wahrscheinlich (1–5)', impact='Wie groß der Schaden (1–5)',
        materialised='Eingetreten, dann gelöst', contained='Verhindert', due='Plantermin', live='Live gegangen',
        late='Verspätet', video_asset='Video-Asset', er='Interaktionen pro 100 Impressionen', ctr='Klicks pro 100 Impressionen', creator='Creator-geführt / Video',
        static='Statisch / Placement / Sonstiges', effect='Faktor auf die Rate (×1 = kein Effekt; Balken = 95-%-Bereich)', eng_model='Was Interaktionen treibt',
        ctr_model='Was Klicks treibt', vs_fc='vs. Prognose', completion='Videos bis zum Ende gesehen',
        compl='Bis zum Ende gesehen', lift='Wochen 7–8: Ist vs. Prognose aus Woche 5',
        creator_led='Von einem Creator gemacht', video='Videoformat', boosted='Bezahlte Promotion', age='Jede weitere Woche online',
        log_impr='Doppelte Impressionen',
        ops=['Meetings', 'Nachrichten & Calls mit AKG', 'Interne Aufgaben koordiniert', 'Nachrichten (alle)', 'Vereinbarte Aufgaben erledigt',
             'An AKG zur Freigabe', 'Von AKG freigegeben', 'Inhaltliche Änderungen', 'Assets live gegangen', 'Nachweise (Links, Screenshots)',
             'Übergaben zwischen Teams', 'Risiken erkannt', 'Eskalationen', 'Reports verschickt'],
        fmts={'CV': 'Creator-Video', 'SF': 'Short-Form-Video', 'LS': 'Livestream', 'HV': 'Hero-Video', 'SPV': 'Creator-Video-Post',
              'SP': 'Statischer Social Post', 'PH': 'Fotopaket', 'PP': 'Produktplatzierung', 'NL': 'Newsletter', 'GA': 'Gewinnspiel'},
        groups={'G2': 'G2 intern', 'AKG': 'AKG', 'Creators': 'Creator & Spieler', 'Production': 'Produktionspartner'},
    ),
}


def fmt_num(x: float, lang: str, short: bool = True) -> str:
    if short and abs(x) >= 1e6:
        s = f'{x / 1e6:.1f}'
        return (s + 'M') if lang == 'en' else (s.replace('.', ',') + '\u00a0Mio.')
    if short and abs(x) >= 1e4:
        return f'{x / 1e3:.0f}K' if lang == 'en' else f'{x / 1e3:.0f}\u00a0Tsd.'
    s = f'{x:,.0f}'
    return s if lang == 'en' else s.replace(',', '.')


def fmt_pct(x: float, lang: str, digits: int = 1, sign: bool = False) -> str:
    s = f'{x * 100:+.{digits}f}' if sign else f'{x * 100:.{digits}f}'
    s = s.replace('-', '−')  # a real minus sign, not a hyphen
    return s + '%' if lang == 'en' else s.replace('.', ',') + '\u00a0%'


def save(fig, path: str) -> None:
    fig.savefig(path, format='svg', bbox_inches='tight', pad_inches=.05, transparent=True, metadata={'Date': None})
    plt.close(fig)
    # drop matplotlib's DOCTYPE: not needed by browsers, and some hosts refuse SVGs with DTD declarations
    with open(path, encoding='utf-8') as f:
        svg = re.sub(r'<!DOCTYPE[^>]*>\s*', '', f.read(), count=1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(svg)


# ---------------------------------------------------------------------------------------------------------------------

def weekly_forecast(r, lang, path):
    t = T[lang]
    w = r['weeks']
    fc = r['forecast'].set_index('week')
    lo, hi = r['interval']['engagements']
    total = fc.loc[[7, 8], 'engagements'].sum()
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    ax.bar(w.week, w.engagements, color=[GREY if k <= 6 else ACCENT for k in w.week], width=.62, label=t['actual'], zorder=2)
    xs = [5] + list(fc.index)
    ys = [w.set_index('week').loc[5, 'engagements']] + list(fc.engagements)
    ax.plot(xs, ys, color=GOLD, lw=2, marker='o', ms=4, label=t['forecast'], zorder=3)
    band_lo = [ys[0], fc.loc[6, 'engagements']] + list(fc.loc[[7, 8], 'engagements'] * lo / total)
    band_hi = [ys[0], fc.loc[6, 'engagements']] + list(fc.loc[[7, 8], 'engagements'] * hi / total)
    ax.fill_between(xs, band_lo, band_hi, color=GOLD, alpha=.18, lw=0, label=t['band'], zorder=1)
    ax.axvline(5.5, color=MUTED, lw=.8, ls=':')
    ax.axvline(6.5, color=ACCENT, lw=.8, ls=':')
    top = w.engagements.max() * 1.18
    ax.text(5.45, top, t['analysis'], ha='right', va='top', color=MUTED, fontsize=7.5, family='JetBrains Mono')
    ax.text(6.55, top, t['realloc'], ha='left', va='top', color=ACCENT, fontsize=7.5, family='JetBrains Mono')
    ax.set_ylim(0, top * 1.02)
    ax.set_xticks(w.week, [f"{t['w']}{k}" for k in w.week])
    ax.yaxis.set_major_formatter(lambda v, _: fmt_num(v, lang))
    ax.set_ylabel(t['eng_per_week'])
    ax.legend(loc='upper left', ncols=3, bbox_to_anchor=(0, -.12))
    save(fig, path)


def ops_heatmap(r, lang, path):
    t = T[lang]
    o = r['ops']
    cols = ['meetings', 'client_comms', 'internal_tasks', 'messages', 'actions_closed', 'approvals_submitted',
            'approvals_completed', 'revisions', 'deliverables', 'pod_items', 'dependencies', 'risks_identified',
            'escalations', 'reports']
    m = o.set_index('week')[cols].T
    norm = m.div(m.max(axis=1).replace(0, 1), axis=0)
    cmap = LinearSegmentedColormap.from_list('g2', [SURFACE2, ACCENT_DARK, ACCENT])
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    sns.heatmap(norm, ax=ax, cmap=cmap, cbar=False, linewidths=1.2, linecolor=BG, annot=m.values, fmt='d',
                annot_kws=dict(fontsize=8, family='JetBrains Mono', color=TEXT))
    ax.set_yticks(np.arange(len(cols)) + .5, t['ops'], rotation=0)
    ax.set_xticks(np.arange(8) + .5, [f"{t['w']}{k}" for k in range(1, 9)])
    ax.set_xlabel('')
    ax.set_ylabel('')
    ax.tick_params(length=0)
    ax.grid(False)
    save(fig, path)


def stakeholder_map(r, lang, path, stakeholders):
    """Power / interest grid: every stakeholder listed in their quadrant, coloured by group, with touchpoints."""
    t = T[lang]
    df = pd.DataFrame(stakeholders, columns=['en', 'de', 'group', 'influence', 'interest', 'touch'])
    df['name'] = (df.en if lang == 'en' else df.de).str.split(' \\(').str[0]
    quads = {'en': [('Keep satisfied', True, False), ('Manage closely', True, True), ('Monitor', False, False), ('Keep informed', False, True)],
             'de': [('Zufriedenstellen', True, False), ('Eng steuern', True, True), ('Beobachten', False, False), ('Informieren', False, True)]}[lang]
    fig, axes = plt.subplots(2, 2, figsize=(5.6, 4.6), gridspec_kw=dict(hspace=.08, wspace=.06))
    for ax, (title, hi_inf, hi_int) in zip(axes.flat, quads):
        sub = df[((df.influence >= 4) == hi_inf) & ((df.interest >= 4) == hi_int)].sort_values('touch', ascending=False)
        ax.set_facecolor(SURFACE2 if hi_inf and hi_int else 'none')
        ax.set_xticks([])
        ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_visible(True)
            sp.set_color(ACCENT if hi_inf and hi_int else LINE)
        ax.text(.04, .93, title.upper(), transform=ax.transAxes, fontsize=7.5, color=ACCENT if hi_inf and hi_int else MUTED,
                family='JetBrains Mono', va='top')
        for i, (_, row) in enumerate(sub.iterrows()):
            y = .78 - i * .066
            ax.scatter(.06, y, s=16, color=GROUP_COLORS[row.group], transform=ax.transAxes, clip_on=False)
            ax.text(.11, y, row['name'], transform=ax.transAxes, fontsize=7.2, color=TEXT, va='center')
            ax.text(.95, y, str(row.touch), transform=ax.transAxes, fontsize=6.8, color=MUTED, va='center', ha='right',
                    family='JetBrains Mono')
        ax.grid(False)
    axes[1, 0].set_xlabel(t['interest'], loc='left')
    axes[1, 1].set_xlabel(t['touch'], loc='right')
    axes[0, 0].set_ylabel(t['influence'], loc='top')
    h = [plt.Line2D([], [], marker='o', ls='', color=GROUP_COLORS[g], label=t['groups'][g]) for g in ('G2', 'AKG', 'Creators', 'Production')]
    fig.legend(handles=h, loc='lower center', bbox_to_anchor=(.5, -.04), ncols=4, handletextpad=.2)
    save(fig, path)


def timeline(r, lang, path):
    t = T[lang]
    dl = r['deliverables'].copy()
    order = ['NL', 'SP', 'SF', 'PP', 'PH', 'CV', 'LS', 'HV', 'GA']
    names = {'en': {'NL': 'Newsletter', 'SP': 'Social posts', 'SF': 'Short-form', 'PP': 'Placements', 'PH': 'Photography',
                    'CV': 'Creator videos', 'LS': 'Livestreams', 'HV': 'Hero video', 'GA': 'Giveaway'},
             'de': {'NL': 'Newsletter', 'SP': 'Social Posts', 'SF': 'Short-Form', 'PP': 'Placements', 'PH': 'Fotografie',
                    'CV': 'Creator-Videos', 'LS': 'Livestreams', 'HV': 'Hero-Video', 'GA': 'Gewinnspiel'}}[lang]
    y = {k: i for i, k in enumerate(order)}
    fig, ax = plt.subplots(figsize=(10.5, 3.9))
    start = pd.Timestamp('2026-05-04')
    for k in range(8):
        ax.axvspan(start + pd.Timedelta(days=7 * k), start + pd.Timedelta(days=7 * k + 7),
                   color=SURFACE2 if k % 2 else 'none', lw=0, zorder=0)
    for _, a in dl.iterrows():
        yy = y[a.type]
        due, live = pd.Timestamp(a.due), pd.Timestamp(a.live)
        if a.days_late:
            ax.plot([due, live], [yy, yy], color=ACCENT, lw=1.6, zorder=2)
            ax.scatter(due, yy, s=34, facecolor='none', edgecolor=MUTED, lw=1, zorder=3)
        ax.scatter(live, yy, s=40, color=ACCENT if a.days_late else (GOLD if a.video else TEXT), edgecolor=BG,
                   lw=.6, zorder=4)
    ax.set_yticks(range(len(order)), [names[k] for k in order])
    ax.invert_yaxis()
    ticks = [start + pd.Timedelta(days=7 * k) for k in range(9)]
    ax.set_xticks(ticks, [f"{t['w']}{k + 1}\n{d:%d.%m.}" if k < 8 else f"{d:%d.%m.}" for k, d in enumerate(ticks)])
    ax.set_xlim(start - pd.Timedelta(days=1), start + pd.Timedelta(days=57))
    ax.grid(axis='y', visible=False)
    h = [plt.Line2D([], [], marker='o', ls='', color=TEXT, label=t['live']),
         plt.Line2D([], [], marker='o', ls='', color=GOLD, label=t['video_asset']),
         plt.Line2D([], [], marker='o', ls='-', color=ACCENT, label=t['late']),
         plt.Line2D([], [], marker='o', ls='', markerfacecolor='none', markeredgecolor=MUTED, label=t['due'])]
    ax.legend(handles=h, loc='upper center', bbox_to_anchor=(.5, -.2), ncols=4)
    save(fig, path)


def approval_cycles(r, lang, path):
    t = T[lang]
    ap = r['approvals'].copy()
    ap = ap.sort_values('submitted').reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(10.5, 3.7))
    x = np.arange(len(ap))
    first = ap.first_feedback_bdays
    rest = ap.approval_bdays - ap.first_feedback_bdays
    ax.bar(x, first, color=[ACCENT if not s else (GOLD if k == 'brief' else MUTED) for s, k in zip(ap.sla_met, ap.kind)],
           width=.7, zorder=2)
    ax.bar(x, rest, bottom=first, color=GREY, width=.7, zorder=2)
    esc = ap[ap.escalated]
    ax.scatter(esc.index, esc.approval_bdays + .55, marker='v', s=46, color=ACCENT, zorder=4)
    ax.axhline(3, color=ACCENT, lw=1, ls='--', zorder=3)
    ax.set_xticks(x, ap.unit, rotation=90, fontsize=7, family='JetBrains Mono')
    ax.set_ylabel(t['bdays'])
    ax.set_ylim(0, ap.approval_bdays.max() + 1.5)
    h = [plt.Rectangle((0, 0), 1, 1, color=MUTED), plt.Rectangle((0, 0), 1, 1, color=GOLD),
         plt.Rectangle((0, 0), 1, 1, color=ACCENT), plt.Rectangle((0, 0), 1, 1, color=GREY),
         plt.Line2D([], [], color=ACCENT, ls='--'), plt.Line2D([], [], marker='v', ls='', color=ACCENT)]
    names = {'en': ['First answer from AKG', 'Content plan (brief)', 'Answer later than 3 days', 'Extra change rounds', 'Agreed limit: 3 working days', 'I escalated'],
             'de': ['Erste Antwort von AKG', 'Content-Plan (Briefing)', 'Antwort nach mehr als 3 Tagen', 'Weitere Änderungsrunden', 'Vereinbartes Limit: 3 Werktage', 'Von mir eskaliert']}[lang]
    ax.legend(h, names, loc='upper right', ncols=3)
    ax.grid(axis='x', visible=False)
    save(fig, path)


def risk_matrix(r, lang, path):
    t = T[lang]
    rk = r['risks']
    fig, ax = plt.subplots(figsize=(3.9, 3.5))
    grid = np.add.outer(np.arange(1, 6), np.arange(1, 6))
    cmap = LinearSegmentedColormap.from_list('risk', [SURFACE2, '#3a1a14', ACCENT_DARK])
    ax.imshow(grid, origin='lower', cmap=cmap, extent=(.5, 5.5, .5, 5.5), alpha=.9)
    offsets = {'R1': (-.18, .16), 'R4': (.18, -.16), 'R2': (-.16, .12), 'R5': (.16, -.12)}
    for _, k in rk.iterrows():
        dx, dy = offsets.get(k.id, (0, 0))
        ax.scatter(k.probability + dx, k.impact + dy, s=260, color=ACCENT if k.materialised else GOLD, edgecolor=BG, lw=1, zorder=3)
        ax.text(k.probability + dx, k.impact + dy, k.id, ha='center', va='center', fontsize=7.5, color=BG,
                family='JetBrains Mono', fontweight='bold', zorder=4)
    ax.set_xticks(range(1, 6))
    ax.set_yticks(range(1, 6))
    ax.set_xlabel(t['prob'])
    ax.set_ylabel(t['impact'])
    ax.grid(False)
    h = [plt.Line2D([], [], marker='o', ls='', color=ACCENT, ms=8, label=t['materialised']),
         plt.Line2D([], [], marker='o', ls='', color=GOLD, ms=8, label=t['contained'])]
    ax.legend(handles=h, loc='upper center', bbox_to_anchor=(.5, -.16), ncols=2)
    save(fig, path)


def format_rates(r, lang, path):
    t = T[lang]
    b = r['before'].copy()
    b = b[~b.fmt.isin(['GA', 'NL'])]
    b['name'] = b.fmt.map(t['fmts'])
    b['group'] = np.where(b.fmt.isin(['CV', 'SF', 'LS', 'HV', 'SPV']), t['creator'], t['static'])
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 3.6), sharey=True)
    b = b.sort_values('er', ascending=False)
    for ax, col, label in ((axes[0], 'er', t['er']), (axes[1], 'ctr', t['ctr'])):
        colors = [GOLD if g == t['creator'] else GREY for g in b.group]
        ax.barh(b.name, b[col], color=colors, height=.66, zorder=2)
        for i, v in enumerate(b[col]):
            ax.text(v, i, ' ' + fmt_pct(v, lang, 2 if col == 'ctr' else 1), va='center', fontsize=7.5, color=MUTED,
                    family='JetBrains Mono')
        ax.set_title(label, fontsize=9, color=TEXT, loc='left', family='Inter')
        ax.xaxis.set_major_formatter(lambda v, _: fmt_pct(v, lang, 0 if col == 'er' else 1))
        ax.set_xlim(0, b[col].max() * 1.35)
        ax.grid(axis='y', visible=False)
    axes[0].invert_yaxis()
    h = [plt.Rectangle((0, 0), 1, 1, color=GOLD, label=t['creator']), plt.Rectangle((0, 0), 1, 1, color=GREY, label=t['static'])]
    fig.legend(handles=h, loc='lower center', bbox_to_anchor=(.5, -.06), ncols=2)
    save(fig, path)


def forest(r, lang, path):
    t = T[lang]
    m = r['models']
    rows = []
    for name, res in ((t['eng_model'], m['eng']), (t['ctr_model'], m['ctr'])):
        ci = res.conf_int()
        for p in ('creator_led', 'video', 'boosted', 'age'):
            rows.append((name, t[p], np.exp(res.params[p]), np.exp(ci.loc[p, 0]), np.exp(ci.loc[p, 1])))
    df = pd.DataFrame(rows, columns=['model', 'term', 'eff', 'lo', 'hi'])
    fig, ax = plt.subplots(figsize=(5.6, 3.2))
    ys = []
    y = 0
    for k, (model, sub) in enumerate(df.groupby('model', sort=False)):
        ax.text(.5, y - .1, model, fontsize=8, color=TEXT, va='bottom', transform=ax.get_yaxis_transform())
        y += .85
        for _, row in sub.iterrows():
            c = GOLD if row.term in (t['creator_led'], t['video']) else MUTED
            ax.plot([row.lo, row.hi], [y, y], color=c, lw=2, solid_capstyle='round')
            ax.scatter(row.eff, y, color=c, s=30, zorder=3, edgecolor=BG)
            ax.text(row.hi + .03, y, f'×{row.eff:.2f}'.replace('.', ',' if lang == 'de' else '.'), va='center',
                    fontsize=7.5, color=MUTED, family='JetBrains Mono')
            ys.append((y, row.term))
            y += 1
        y += .4
    ax.axvline(1, color=LINE, lw=1)
    ax.set_yticks([a for a, _ in ys], [b for _, b in ys])
    ax.invert_yaxis()
    ax.set_xlabel(t['effect'])
    ax.set_xlim(.7, 2.25)
    ax.grid(axis='y', visible=False)
    save(fig, path)


def lift(r, lang, path):
    t = T[lang]
    w = r['weeks'].set_index('week')
    fc = r['forecast'].set_index('week')
    a = r['panel']
    v78 = a[(a.video == 1) & (a.week >= 7)]
    comp_act = (v78.views * v78.completion).sum() / v78.views.sum()
    fc_comp = r['forecast_completion_78']
    items = [(t['engagements'], fc.loc[[7, 8], 'engagements'].sum(), w.loc[[7, 8], 'engagements'].sum(), False),
             (t['clicks'], fc.loc[[7, 8], 'clicks'].sum(), w.loc[[7, 8], 'clicks'].sum(), False),
             (t['reach'], fc.loc[[7, 8], 'reach'].sum(), w.loc[[7, 8], 'reach'].sum(), False),
             (t['compl'], fc_comp, comp_act, True)]
    fig, axes = plt.subplots(1, 4, figsize=(7.2, 2.6))
    for ax, (label, f, act, is_rate) in zip(axes, items):
        ax.bar([0, 1], [f, act], color=[GREY, ACCENT], width=.62, zorder=2)
        for x, v in ((0, f), (1, act)):
            ax.text(x, v, fmt_pct(v, lang, 0) if is_rate else fmt_num(v, lang), ha='center', va='bottom', fontsize=7.5,
                    color=MUTED, family='JetBrains Mono')
        ax.set_title(f'{label}\n{fmt_pct(act / f - 1, lang, 0, sign=True)} {t["vs_fc"]}', fontsize=8.5, color=TEXT)
        ax.set_xticks([0, 1], ['Forecast', t['actual']] if lang == 'en' else ['Prognose', t['actual']])
        ax.set_yticks([])
        ax.set_ylim(0, max(f, act) * 1.22)
        ax.spines['left'].set_visible(False)
        ax.grid(False)
    save(fig, path)


def render_all(r, outdir: str, stakeholders) -> list[str]:
    os.makedirs(outdir, exist_ok=True)
    made = []
    for lang in ('en', 'de'):
        for name, fn in (('weekly-forecast', weekly_forecast), ('ops-heatmap', ops_heatmap),
                         ('timeline', timeline), ('approval-cycles', approval_cycles), ('risk-matrix', risk_matrix),
                         ('format-rates', format_rates), ('model-effects', forest), ('lift', lift)):
            p = os.path.join(outdir, f'{name}-{lang}.svg')
            fn(r, lang, p)
            made.append(p)
        p = os.path.join(outdir, f'stakeholder-map-{lang}.svg')
        stakeholder_map(r, lang, p, stakeholders)
        made.append(p)
    return made
