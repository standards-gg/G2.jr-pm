"""Build the AKG x G2 dashboard (projects/akg/): datasets, charts and page.

    python -m venv .venv && .venv/bin/pip install -r tools/akg/requirements.txt
    .venv/bin/python tools/akg/build.py

Every KPI is derived from the records in campaign.py and checked against the brief before anything is written,
so a changed input either stays consistent everywhere or stops the build.
"""
from __future__ import annotations

import json
import os
import sys
import warnings

warnings.filterwarnings('ignore')
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)

import campaign as c  # noqa: E402
import charts  # noqa: E402
import page  # noqa: E402

OUT = os.path.join(ROOT, 'projects', 'akg')


def kpis(r: dict) -> dict:
    dl, ap, rk, ops, wk = r['deliverables'], r['approvals'], r['risks'], r['ops'], r['weeks']
    act = r['panel']
    k = dict(fee=c.FEE_EUR)
    # delivery
    k['assets'] = len(dl)
    k['on_time'] = int(dl.on_time.sum())
    k['late'] = k['assets'] - k['on_time']
    k['on_time_rate'] = k['on_time'] / k['assets']
    # approvals
    k['approval_requests'] = len(ap)
    k['briefs'] = int((ap.kind == 'brief').sum())
    k['submissions'] = int((ap.kind == 'asset').sum())
    k['first_round'] = int(((ap.kind == 'asset') & (ap.rounds == 1)).sum())
    k['fr_rate'] = k['first_round'] / k['submissions']
    k['escalated'] = int(ap.escalated.sum())
    k['approved_normal'] = k['approval_requests'] - k['escalated']
    k['sla_met'] = int(ap.sla_met.sum())
    k['sla_rate'] = k['sla_met'] / k['approval_requests']
    k['avg_approval'] = float(ap.approval_bdays.mean())
    k['longest_delay'] = int(ap.first_feedback_bdays.max())
    k['revisions'] = int(dl.revisions.sum())
    k['rev_internal'] = int(dl.rev_internal.sum())
    k['rev_client'] = int(dl.rev_client.sum())
    # operations
    k['meetings'] = int(ops.meetings.sum())
    k['client_comms'] = int(ops.client_comms.sum())
    k['internal_tasks'] = int(ops.internal_tasks.sum())
    k['internal_sla'] = int(ops.internal_tasks_sla.sum())
    k['messages'] = int(ops.messages.sum())
    k['actions_total'] = int(ops.actions_opened.sum())
    k['actions_done'] = int(ops.actions_closed.sum())
    k['action_rate'] = k['actions_done'] / k['actions_total']
    k['dependencies'] = int(ops.dependencies.sum())
    k['reports'] = int(ops.reports.sum())
    k['weekly_reports'] = c.WEEKS
    k['pod_items'] = int(ops.pod_items.sum())
    k['risks'] = len(rk)
    k['issues'] = int(rk.materialised.sum())
    k['avg_issue'] = float(rk[rk.materialised].resolution_bdays.mean())
    k['deadline_shifts'] = 1  # PH-01, agreed with AKG in writing (R3)
    k['risks_before_impact'] = k['risks'] - k['deadline_shifts']
    g = c.GROUPS
    k['touchpoints'] = sum(v['meetings'] + v['messages'] for v in g.values())
    k['followups'] = sum(v['followups'] for v in g.values())
    k['my_resp'] = sum(v['my_resp'] * (v['meetings'] + v['messages']) for v in g.values()) / k['touchpoints']
    # audience
    for key in ('impressions', 'views', 'engagements', 'clicks', 'reach', 'watch_minutes', 'actions', 'giveaway_entries'):
        k[key] = float(wk[key].sum())
    v = act[act.video == 1]
    k['completion'] = float((v.views * v.completion).sum() / v.views.sum())
    k['er'] = k['engagements'] / k['impressions']
    k['ctr_lp'] = k['clicks'] / k['reach']
    k['cpm'] = k['fee'] / k['impressions'] * 1000
    k['cpe'] = k['fee'] / k['engagements']
    k['cpc'] = k['fee'] / k['clicks']
    k['cpcv'] = k['fee'] / (k['views'] * k['completion'])
    # optimisation
    fc, w = r['forecast_78'], wk.set_index('week')
    v78 = v[v.week >= 7]
    k['fc78'] = fc
    k['act78'] = dict(engagements=float(w.loc[[7, 8], 'engagements'].sum()), clicks=float(w.loc[[7, 8], 'clicks'].sum()),
                      reach=float(w.loc[[7, 8], 'reach'].sum()),
                      completion=float((v78.views * v78.completion).sum() / v78.views.sum()))
    for m in ('engagements', 'clicks', 'reach', 'completion'):
        k['lift_' + {'engagements': 'eng', 'clicks': 'clicks', 'reach': 'reach', 'completion': 'comp'}[m]] = k['act78'][m] / fc[m] - 1
    f6 = r['forecast'].set_index('week').loc[6]
    k['w6_eng'] = w.loc[6, 'engagements'] / f6.engagements - 1
    k['w6_clicks'] = w.loc[6, 'clicks'] / f6.clicks - 1
    k['w6_reach'] = w.loc[6, 'reach'] / f6.reach - 1
    return k


def check(k: dict, r: dict) -> None:
    """The brief, as assertions. A failing line names the number that drifted."""
    dl = r['deliverables']
    rounded = lambda x, d=0: round(x * 100, d)  # noqa: E731
    checks = [
        ('31 content assets', k['assets'] == 31),
        ('deliverable mix', dl.type.value_counts().to_dict() == c.CONTRACT),
        ('12 / 4 / 6 / 3 stakeholders', [sum(1 for s in c.STAKEHOLDERS if s[2] == g) for g in ('G2', 'AKG', 'Creators', 'Production')] == [12, 4, 6, 3]),
        ('stakeholder touchpoints add up per group', all(sum(s[5] for s in c.STAKEHOLDERS if s[2] == g) == v['meetings'] + v['messages'] for g, v in c.GROUPS.items())),
        ('8.4M impressions', round(k['impressions']) == 8_400_000),
        ('3.1M video views', round(k['views']) == 3_100_000),
        ('1.7M unique reach', round(k['reach']) == 1_700_000),
        ('412K engagements', round(k['engagements']) == 412_000),
        ('4.9% engagement rate', rounded(k['er'], 1) == 4.9),
        ('86K link clicks', round(k['clicks']) == 86_000),
        ('5.1% landing-page CTR', rounded(k['ctr_lp'], 1) == 5.1),
        ('18,400 giveaway entries', k['giveaway_entries'] == 18_400),
        ('62% completion', rounded(k['completion']) == 62),
        ('1.9M watch minutes', round(k['watch_minutes']) == 1_900_000),
        ('46 meetings', k['meetings'] == 46),
        ('73 internal coordination tasks', k['internal_tasks'] == 73),
        ('38 client communications', k['client_comms'] == 38),
        ('AKG messages = client communications', c.GROUPS['AKG']['messages'] == k['client_comms']),
        ('group meetings = weekly meetings', sum(v['meetings'] for v in c.GROUPS.values()) == k['meetings']),
        ('AKG meetings per week', sum(c.WEEKLY_LOG['akg_meetings']) == c.GROUPS['AKG']['meetings']),
        ('group messages = weekly messages', sum(v['messages'] for v in c.GROUPS.values()) == k['messages']),
        ('group action items = weekly log', sum(v['done'] for v in c.GROUPS.values()) == k['actions_done'] and sum(v['total'] for v in c.GROUPS.values()) == k['actions_total']),
        ('27 creative approval cycles', k['submissions'] == 27),
        ('19 asset revisions', k['revisions'] == 19),
        ('31 approval requests', k['approval_requests'] == 31),
        ('29 approvals completed + 2 escalated', k['approved_normal'] == 29 and k['escalated'] == 2),
        ('14 dependencies', k['dependencies'] == 14),
        ('6 risks, 5 before impact', k['risks'] == 6 and k['risks_before_impact'] == 5),
        ('1 deadline shift, 0 missed', dl[dl.id == 'PH-01'].days_late.iloc[0] > 0 and k['late'] == 2),
        ('94% on/before deadline', rounded(k['on_time_rate']) == 94),
        ('97% approval SLA', rounded(k['sla_rate']) == 97),
        ('89% first-round approval', rounded(k['fr_rate']) == 89),
        ('96% action items', rounded(k['action_rate']) == 96),
        ('92% internal tasks in SLA', rounded(k['internal_sla'] / k['internal_tasks']) == 92),
        ('7 business days issue resolution', round(k['avg_issue'], 1) == 7.0),
        ('+38% engagement', rounded(k['lift_eng']) == 38),
        ('+27% completion', rounded(k['lift_comp']) == 27),
        ('+41% link clicks', rounded(k['lift_clicks']) == 41),
        ('+22% reach', rounded(k['lift_reach']) == 22),
        ('week-6 forecast within 5%', abs(k['w6_eng']) < .05 and abs(k['w6_clicks']) < .05 and abs(k['w6_reach']) < .05),
        ('weeks 7-8 above the 80% interval', k['act78']['engagements'] > r['interval']['engagements'][1]),
        ('every asset approved before going live', (dl.approved <= dl.live).all()),
        ('approval clock ends before go-live', (dl.submitted < dl.approved).all()),
    ]
    bad = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(('  ✓ ' if ok else '  ✗ ') + name)
    if bad:
        sys.exit(f'Inconsistent with the brief: {", ".join(bad)}')


def write_data(r: dict, k: dict) -> None:
    d = os.path.join(OUT, 'data')
    os.makedirs(d, exist_ok=True)
    wk = r['weeks'].copy()
    wk['start'] = wk.start.map(lambda x: x.strftime('%d.%m.%Y'))
    wk['engagement_rate'] = wk.engagements / wk.impressions
    wk.round(4).to_csv(os.path.join(d, 'weekly_performance.csv'), index=False)
    r['ops'].to_csv(os.path.join(d, 'weekly_operations.csv'), index=False)
    import pandas as pd
    pd.DataFrame([('Impressions', k['impressions']), ('Video views', k['views']), ('Engagements', k['engagements']),
                  ('Link clicks', k['clicks']), ('Landing-page actions', round(k['actions']))],
                 columns=['stage', 'value']).to_csv(os.path.join(d, 'funnel.csv'), index=False)
    dl = r['deliverables'].copy()
    for col in ('due', 'live', 'submitted', 'approved'):
        dl[col] = dl[col].map(lambda x: x.strftime('%d.%m.%Y'))
    dl.round(0).to_csv(os.path.join(d, 'deliverables.csv'), index=False)
    ap = r['approvals'].copy()
    for col in ('submitted', 'approved'):
        ap[col] = ap[col].map(lambda x: x.strftime('%d.%m.%Y'))
    ap.to_csv(os.path.join(d, 'approvals.csv'), index=False)
    pd.DataFrame(c.STAKEHOLDERS, columns=['name_en', 'name_de', 'group', 'influence', 'interest', 'touchpoints']).to_csv(
        os.path.join(d, 'stakeholders.csv'), index=False)
    rk = r['risks'].copy()
    for col in ('identified', 'resolved'):
        rk[col] = rk[col].map(lambda x: x.strftime('%d.%m.%Y'))
    rk.to_csv(os.path.join(d, 'risks.csv'), index=False)
    fb = r['before'].assign(period='weeks 1-5')
    fa = r['after'].assign(period='weeks 7-8')
    pd.concat([fb, fa]).round(5).to_csv(os.path.join(d, 'format_before_after.csv'), index=False)
    fc = r['forecast'].merge(r['weeks'][['week', 'engagements', 'clicks', 'reach', 'completion']], on='week', suffixes=('_forecast', '_actual'))
    fc.round(4).to_csv(os.path.join(d, 'forecast.csv'), index=False)
    r['panel'].round(4).to_csv(os.path.join(d, 'asset_week_panel.csv'), index=False)
    with open(os.path.join(d, 'model_summary.txt'), 'w') as f:
        f.write('AKG x G2 (fictional case study) - week-5 models, fitted on weeks 1-5 of the simulated asset-week panel.\n\n')
        f.write(str(r['models']['eng'].summary()) + '\n\n' + str(r['models']['ctr'].summary()) + '\n\n')
        f.write(str(r['models']['reach'].summary()) + '\n\n' + str(r['models']['comp'].summary()) + '\n')
    out = {key: (round(v, 6) if isinstance(v, float) else v) for key, v in k.items() if not isinstance(v, dict)}
    out['forecast_weeks_7_8'] = {a: round(b_, 4) for a, b_ in k['fc78'].items()}
    out['actual_weeks_7_8'] = {a: round(b_, 4) for a, b_ in k['act78'].items()}
    out['forecast_interval_80'] = {a: [round(x, 4) for x in b_] for a, b_ in r['interval'].items()}
    out['note'] = 'Fictional case study. All figures are hypothetical and simulated; not real G2 Esports or AKG data.'
    with open(os.path.join(d, 'kpis.json'), 'w') as f:
        json.dump(out, f, indent=2, ensure_ascii=False)


def main() -> None:
    print('Simulating and fitting…')
    r = c.build()
    k = kpis(r)
    print('Checks against the brief')
    check(k, r)
    write_data(r, k)
    charts.register_fonts(os.path.join(ROOT, 'assets', 'fonts'))
    charts.setup_style()
    made = charts.render_all(r, os.path.join(OUT, 'charts'), c.STAKEHOLDERS)
    with open(os.path.join(OUT, 'index.html'), 'w') as f:
        f.write(page.build_page(r, k))
    print(f'Wrote projects/akg/index.html, {len(made)} charts, data/*')


if __name__ == '__main__':
    main()
