"""AKG x G2 "Game Audio, Studio Quality": a fictional 8-week partnership, simulated end to end.

Everything here is hypothetical and made up for a job-application case study. No figure is real G2 or AKG data.

Two kinds of data live in this module:
  1. Authored operational facts (deliverables, approvals, risks, stakeholders, weekly log). They are written by hand
     so they read like a real partnership log, then every headline KPI is *derived* from them and checked.
  2. Audience performance, simulated per asset and week (asset-week panel) from a generative model with noise,
     then calibrated so the campaign totals and the week-7/8 uplift match the brief exactly.

The week-5 analysis is reproduced with the same data a Junior Partnerships Manager would have had on Friday of
week 5: an OLS model of engagement and a binomial GLM of click-through, fitted on weeks 1-5 only. The fitted models
forecast weeks 6-8 under the original plan (the counterfactual). Week 6 still ran on the original plan, so it is
an out-of-sample check of the forecast; weeks 7-8 ran on the reallocated, video-first plan.
"""
from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf

SEED = 20260504
START = date(2026, 5, 4)  # Monday of week 1
WEEKS = 8
FEE_EUR = 150_000

# Headline campaign results from the brief (the calibration targets).
TARGETS = dict(impressions=8_400_000, views=3_100_000, reach=1_700_000, engagements=412_000, clicks=86_000,
               completion=0.62, watch_minutes=1_900_000, giveaway_entries=18_400)
# Final-two-week improvement versus the week-5 forecast of the original plan.
LIFTS = dict(engagements=0.38, completion=0.27, clicks=0.41, reach=0.22)


def week_of(d: date) -> int:
    return (d - START).days // 7 + 1


def d(s: str) -> date:
    day, month = (int(x) for x in s.split('.')[:2])
    return date(2026, month, day)


def bdays(a: date, b: date) -> int:
    """Business days from a to b (a excluded, b included), like an approval clock."""
    return int(np.busday_count(a + timedelta(days=1), b + timedelta(days=1)))


def add_bdays(a: date, n: int) -> date:
    return np.busday_offset(np.datetime64(a), n, roll='forward').astype(date)


# ---------------------------------------------------------------------------------------------------------------------
# 1. Authored facts
# ---------------------------------------------------------------------------------------------------------------------

# type code -> (EN name, DE name, workstream EN, workstream DE)
TYPES = {
    'CV': ('Creator video', 'Creator-Video', 'Creators', 'Creator'),
    'SP': ('Social post', 'Social Post', 'Social', 'Social'),
    'SF': ('Short-form video', 'Short-Form-Video', 'Social video', 'Social Video'),
    'LS': ('Livestream integration', 'Livestream-Integration', 'Broadcast', 'Broadcast'),
    'GA': ('Giveaway', 'Gewinnspiel', 'Community', 'Community'),
    'HV': ('Hero campaign video', 'Hero-Kampagnenvideo', 'Production', 'Produktion'),
    'PH': ('Product photography package', 'Produktfoto-Paket', 'Production', 'Produktion'),
    'NL': ('Newsletter integration', 'Newsletter-Integration', 'CRM', 'CRM'),
    'PP': ('Product placement', 'Produktplatzierung', 'Brand placement', 'Brand Placement'),
}
CONTRACT = {'CV': 3, 'SP': 8, 'SF': 4, 'LS': 2, 'GA': 1, 'HV': 1, 'PH': 1, 'NL': 2, 'PP': 9}

# Deliverable log. due = internal plan date agreed with AKG; live = actual go-live / hand-over.
# approval: 'R1' first round, 'R2'/'R3' after client revision rounds, 'ESC' approved after escalation.
# rev_int / rev_cli = internal (brand, legal, team) and client-requested revision rounds.
# risk: L/M/H.  unit: approval submission (product placements are submitted in batches).
ASSETS = [
    # id,    title EN,                                   title DE,                                        owner,                stakeholder,              due,     live,    appr,  rev_int, rev_cli, risk, unit
    ('NL-01', 'Newsletter #1 · campaign teaser',        'Newsletter #1 · Kampagnen-Teaser',            'CRM Manager',        'AKG Brand Manager',       '08.05', '08.05', 'R1', 0, 0, 'L', 'NL-01'),
    ('SP-01', 'Social post #1 · partnership reveal',    'Social Post #1 · Partnerschafts-Reveal',       'Social Media Manager', 'AKG Brand Manager',     '11.05', '11.05', 'R1', 0, 0, 'L', 'SP-01'),
    ('SF-01', 'Short-form #1 · “Hear the footsteps”',   'Short-Form #1 · „Hör die Schritte“',          'Video Producer',     'Creator A',               '14.05', '14.05', 'R1', 1, 0, 'M', 'SF-01'),
    ('PP-01', 'Placement #1 · player cam, scrims',      'Placement #1 · Spieler-Cam, Scrims',           'Broadcast Producer', 'Player A',                '15.05', '15.05', 'R1', 0, 0, 'L', 'PP-B1'),
    ('PP-02', 'Placement #2 · team vlog',               'Placement #2 · Team-Vlog',                     'Broadcast Producer', 'Player B',                '15.05', '15.05', 'R1', 0, 0, 'L', 'PP-B1'),
    ('PH-01', 'Product photography package',            'Produktfoto-Paket',                            'Brand Designer',     'AKG Product Specialist',  '13.05', '19.05', 'R1', 1, 0, 'H', 'PH-01'),
    ('SP-02', 'Social post #2 · product hero shot',     'Social Post #2 · Produkt-Hero-Shot',           'Social Media Manager', 'AKG Brand Manager',     '18.05', '18.05', 'R1', 1, 0, 'L', 'SP-02'),
    ('CV-01', 'Creator video #1 · studio setup tour',   'Creator-Video #1 · Studio-Setup-Tour',         'Creator Manager',    'Creator A',               '20.05', '20.05', 'R1', 2, 0, 'M', 'CV-01'),
    ('LS-01', 'Livestream #1 · ranked night',           'Livestream #1 · Ranked-Abend',                 'Broadcast Producer', 'Creator B',               '21.05', '21.05', 'R1', 1, 0, 'M', 'LS-01'),
    ('PP-03', 'Placement #3 · match-day broadcast desk', 'Placement #3 · Matchday-Broadcast-Desk',      'Broadcast Producer', 'Player A',                '22.05', '22.05', 'R1', 0, 0, 'L', 'PP-B2'),
    ('PP-04', 'Placement #4 · bootcamp content',        'Placement #4 · Bootcamp-Content',              'Broadcast Producer', 'Player B',                '22.05', '22.05', 'R1', 0, 0, 'L', 'PP-B2'),
    ('SP-03', 'Social post #3 · match-day',             'Social Post #3 · Matchday',                    'Social Media Manager', 'AKG Brand Manager',     '25.05', '25.05', 'R1', 0, 0, 'M', 'SP-03'),
    ('HV-01', 'Hero video · “Game Audio, Studio Quality”', 'Hero-Video · „Game Audio, Studio Quality“', 'Video Producer',     'AKG Brand Manager',       '26.05', '26.05', 'ESC', 3, 2, 'H', 'HV-01'),
    ('GA-01', 'Giveaway · 5 AKG headsets',              'Gewinnspiel · 5 AKG-Headsets',                 'Community Manager',  'AKG Legal & Compliance',  '27.05', '27.05', 'ESC', 1, 0, 'H', 'GA-01'),
    ('SF-02', 'Short-form #2 · clutch audio cues',      'Short-Form #2 · Clutch-Audio-Cues',            'Video Producer',     'Creator C',               '28.05', '28.05', 'R1', 0, 0, 'L', 'SF-02'),
    ('PP-05', 'Placement #5 · player cam, officials',   'Placement #5 · Spieler-Cam, Offizielle',       'Broadcast Producer', 'Player A',                '29.05', '29.05', 'R1', 0, 0, 'L', 'PP-B3'),
    ('NL-02', 'Newsletter #2 · giveaway push',          'Newsletter #2 · Gewinnspiel-Push',             'CRM Manager',        'AKG Brand Manager',       '01.06', '01.06', 'R1', 0, 0, 'L', 'NL-02'),
    ('SP-04', 'Social post #4 · giveaway reminder',     'Social Post #4 · Gewinnspiel-Reminder',        'Social Media Manager', 'AKG Brand Manager',     '01.06', '01.06', 'R1', 0, 0, 'L', 'SP-04'),
    ('SF-03', 'Short-form #3 · mic check',              'Short-Form #3 · Mic-Check',                    'Video Producer',     'Creator A',               '04.06', '04.06', 'R2', 1, 1, 'M', 'SF-03'),
    ('CV-02', 'Creator video #2 · “Music to game to”',  'Creator-Video #2 · „Music to game to“',        'Creator Manager',    'Creator B',               '03.06', '05.06', 'R3', 1, 2, 'H', 'CV-02'),
    ('PP-06', 'Placement #6 · team house tour',         'Placement #6 · Teamhaus-Tour',                 'Broadcast Producer', 'Player B',                '05.06', '05.06', 'R1', 0, 0, 'L', 'PP-B3'),
    ('SP-05', 'Social post #5 · studio quality',        'Social Post #5 · Studioqualität',              'Social Media Manager', 'AKG Brand Manager',     '08.06', '08.06', 'R1', 1, 0, 'L', 'SP-05'),
    ('PP-07', 'Placement #7 · match-day walkout',       'Placement #7 · Matchday-Walkout',              'Broadcast Producer', 'Player A',                '10.06', '10.06', 'R1', 0, 0, 'L', 'PP-B4'),
    ('SP-06', 'Social post #6 · player quote card',     'Social Post #6 · Spieler-Zitatkarte',          'Social Media Manager', 'AKG Brand Manager',     '11.06', '11.06', 'R1', 0, 0, 'L', 'SP-06'),
    ('PP-08', 'Placement #8 · creator stream overlay',  'Placement #8 · Creator-Stream-Overlay',        'Broadcast Producer', 'Creator C',               '12.06', '12.06', 'R1', 0, 0, 'L', 'PP-B4'),
    ('SF-04', 'Short-form #4 · soundstage test',        'Short-Form #4 · Soundstage-Test',              'Video Producer',     'Creator D',               '16.06', '16.06', 'R1', 0, 0, 'L', 'SF-04'),
    ('LS-02', 'Livestream #2 · community cup',          'Livestream #2 · Community-Cup',                'Broadcast Producer', 'Creator C',               '17.06', '17.06', 'R1', 0, 0, 'M', 'LS-02'),
    ('SP-07', 'Social post #7 · creator-led video post', 'Social Post #7 · Creator-Video-Post',         'Social Media Manager', 'Creator D',             '18.06', '18.06', 'R1', 0, 0, 'M', 'SP-07'),
    ('PP-09', 'Placement #9 · final-week vlog',         'Placement #9 · Vlog der Finalwoche',           'Broadcast Producer', 'Player B',                '19.06', '19.06', 'R1', 0, 0, 'L', 'PP-B5'),
    ('CV-03', 'Creator video #3 · pro vs. creator duel', 'Creator-Video #3 · Pro-vs.-Creator-Duell',    'Creator Manager',    'Creator D',               '23.06', '23.06', 'R1', 1, 0, 'M', 'CV-03'),
    ('SP-08', 'Social post #8 · creator-led wrap-up',   'Social Post #8 · Creator-Wrap-up',             'Social Media Manager', 'Creator A',             '25.06', '25.06', 'R1', 0, 0, 'L', 'SP-08'),
]
# SP-07 / SP-08 were planned as static posts; the week-5 decision turned them into creator-led video posts
# (still "social posts" under the contract, format change approved by AKG on 09.06.).
CONVERTED = {'SP-07', 'SP-08'}

# Approval clock per submission: business days from submission to final approval, business days to the first AKG
# feedback, number of rounds, whether it met the 3-business-day feedback SLA, whether it was escalated.
APPROVAL = {
    # unit:   (total, first_feedback, rounds, sla_met, escalated, buffer before go-live in business days)
    'NL-01': (1, 1, 1, True, False, 1), 'SP-01': (1, 1, 1, True, False, 2), 'SF-01': (2, 2, 1, True, False, 1),
    'PP-B1': (1, 1, 1, True, False, 2), 'PH-01': (2, 2, 1, True, False, 1), 'SP-02': (1, 1, 1, True, False, 2),
    'CV-01': (2, 2, 1, True, False, 2), 'LS-01': (2, 2, 1, True, False, 1), 'PP-B2': (1, 1, 1, True, False, 2),
    'SP-03': (1, 1, 1, True, False, 1), 'HV-01': (10, 6, 3, False, True, 1), 'GA-01': (3, 3, 1, True, True, 2),
    'SF-02': (1, 1, 1, True, False, 2), 'PP-B3': (2, 2, 1, True, False, 1), 'NL-02': (1, 1, 1, True, False, 1),
    'SP-04': (2, 2, 1, True, False, 1), 'SF-03': (4, 2, 2, True, False, 1), 'CV-02': (7, 2, 3, True, False, 1),
    'SP-05': (1, 1, 1, True, False, 2), 'PP-B4': (1, 1, 1, True, False, 2), 'SP-06': (1, 1, 1, True, False, 1),
    'SF-04': (1, 1, 1, True, False, 1), 'LS-02': (2, 2, 1, True, False, 1), 'SP-07': (2, 2, 1, True, False, 1),
    'PP-B5': (1, 1, 1, True, False, 2), 'CV-03': (3, 2, 1, True, False, 1), 'SP-08': (1, 1, 1, True, False, 2),
}
# Creative briefs (approval requests 1-4): submitted, approved, rounds.
BRIEFS = [
    ('BR-1', 'Creator & livestream brief', 'Creator- & Livestream-Briefing', '04.05', '06.05', 1),
    ('BR-2', 'Hero video brief', 'Hero-Video-Briefing', '04.05', '08.05', 2),
    ('BR-3', 'Social & short-form brief', 'Social- & Short-Form-Briefing', '05.05', '06.05', 1),
    ('BR-4', 'Giveaway & newsletter brief', 'Gewinnspiel- & Newsletter-Briefing', '06.05', '08.05', 1),
]

STAKEHOLDERS = [
    # name EN, name DE, group, influence 1-5, interest 1-5, touchpoints
    ('Partnerships Director (line manager)', 'Partnerships Director (Vorgesetzter)', 'G2', 5, 4, 34),
    ('Head of Content', 'Head of Content', 'G2', 4, 3, 26),
    ('Social Media Manager', 'Social Media Manager', 'G2', 3, 5, 41),
    ('Creator Manager', 'Creator Manager', 'G2', 3, 5, 38),
    ('Video Producer', 'Video Producer', 'G2', 3, 4, 36),
    ('Brand Designer', 'Brand Designer', 'G2', 2, 3, 17),
    ('Broadcast Producer', 'Broadcast Producer', 'G2', 3, 4, 24),
    ('Community Manager', 'Community Manager', 'G2', 2, 4, 15),
    ('CRM / Newsletter Manager', 'CRM-/Newsletter-Manager', 'G2', 2, 3, 9),
    ('Legal Counsel', 'Legal Counsel', 'G2', 4, 2, 11),
    ('Finance (invoicing)', 'Finance (Rechnungsstellung)', 'G2', 3, 2, 5),
    ('Esports Team Manager', 'Esports-Teammanager', 'G2', 4, 2, 7),
    ('AKG Brand Manager (main contact)', 'AKG Brand Manager (Hauptkontakt)', 'AKG', 5, 5, 29),
    ('AKG Marketing Manager Gaming', 'AKG Marketing Manager Gaming', 'AKG', 5, 3, 11),
    ('AKG Product Specialist', 'AKG Produktspezialist', 'AKG', 2, 4, 7),
    ('AKG Legal & Compliance', 'AKG Legal & Compliance', 'AKG', 4, 2, 5),
    ('Creator A', 'Creator A', 'Creators', 2, 5, 19),
    ('Creator B', 'Creator B', 'Creators', 2, 4, 21),
    ('Creator C', 'Creator C', 'Creators', 2, 4, 14),
    ('Creator D', 'Creator D', 'Creators', 2, 4, 15),
    ('Player A', 'Player A', 'Creators', 3, 3, 8),
    ('Player B', 'Player B', 'Creators', 3, 3, 8),
    ('Hero video production agency', 'Produktionsagentur Hero-Video', 'Production', 3, 4, 21),
    ('Photo studio', 'Fotostudio', 'Production', 2, 3, 9),
    ('Post-production house', 'Postproduktion', 'Production', 2, 3, 7),
]
# Per group: meetings, messages, follow-ups, escalations, my avg response (business hours),
# their avg response (business hours), action items done / total.
GROUPS = {
    'AKG':        dict(meetings=14, messages=38, followups=11, escalations=1, my_resp=2.6, their_resp=19.5, done=29, total=30),
    'G2':         dict(meetings=22, messages=241, followups=24, escalations=1, my_resp=3.4, their_resp=6.2, done=58, total=61),
    'Creators':   dict(meetings=7, messages=78, followups=13, escalations=0, my_resp=4.1, their_resp=14.8, done=21, total=22),
    'Production': dict(meetings=3, messages=34, followups=5, escalations=0, my_resp=3.0, their_resp=8.7, done=10, total=10),
}

# Weekly log that is not derived from the deliverable/approval records.
WEEKLY_LOG = dict(
    meetings=[8, 6, 5, 6, 6, 5, 5, 5],
    akg_meetings=[3, 2, 1, 2, 2, 1, 1, 2],
    client_comms=[7, 5, 5, 4, 6, 4, 4, 3],
    internal_tasks=[12, 10, 9, 9, 10, 8, 8, 7],
    internal_tasks_sla=[11, 9, 8, 8, 9, 8, 7, 7],
    messages=[64, 52, 49, 47, 55, 44, 42, 38],
    actions_opened=[22, 17, 15, 14, 17, 13, 13, 12],
    actions_closed=[19, 17, 15, 13, 16, 13, 13, 12],
    dependencies=[5, 3, 2, 1, 1, 1, 1, 0],
    reports=[1, 1, 1, 1, 2, 1, 1, 2],  # 8 weekly status reports + week-5 optimisation memo + week-8 closeout
)

RISKS = [
    # id, EN risk, DE risk, prob 1-5, impact 1-5, owner, week identified, resolution business days, materialised
    ('R1', 'Delayed creative feedback on the hero video', 'Verzögertes Creative-Feedback zum Hero-Video', 3, 4,
     'Me', 3, 6, True),
    ('R2', 'Creator scheduling conflict (tournament travel)', 'Terminkonflikt Creator (Turnierreise)', 3, 3,
     'Creator Manager', 2, 8, True),
    ('R3', 'Product shipment delay for the photo shoot', 'Lieferverzug der Produkte fürs Fotoshooting', 2, 3,
     'Me', 1, 9, True),
    ('R4', 'Legal approval dependency: giveaway T&Cs', 'Rechtliche Freigabe: Gewinnspiel-Teilnahmebedingungen', 3, 4,
     'G2 Legal Counsel', 1, 4, False),
    ('R5', 'Conflicting campaign deadlines on match weekend', 'Kollidierende Kampagnen-Deadlines am Matchwochenende', 3, 2,
     'Social Media Manager', 3, 2, False),
    ('R6', 'Revision loop on creator video #2 (product claims)', 'Revisionsschleife Creator-Video #2 (Produktclaims)', 4, 3,
     'Video Producer', 4, 5, True),
]


# ---------------------------------------------------------------------------------------------------------------------
# 2. Derived operational records
# ---------------------------------------------------------------------------------------------------------------------

def deliverables() -> pd.DataFrame:
    rows = []
    for (aid, en, de, owner, stakeholder, due, live, appr, ri, rc, risk, unit) in ASSETS:
        t = aid[:2]
        due_d, live_d = d(due), d(live)
        total, first, rounds, sla, esc, buffer = APPROVAL[unit]
        approved = add_bdays(live_d, -buffer)
        submitted = add_bdays(approved, -total)
        rows.append(dict(
            id=aid, type=t, title_en=en, title_de=de, workstream_en=TYPES[t][2], workstream_de=TYPES[t][3],
            owner=owner, stakeholder=stakeholder, due=due_d, live=live_d, week=week_of(live_d),
            on_time=live_d <= due_d, days_late=max(0, (live_d - due_d).days), approval=appr, unit=unit,
            submitted=submitted, approved=approved, approval_bdays=total, first_feedback_bdays=first, rounds=rounds,
            sla_met=sla, escalated=esc, rev_internal=ri, rev_client=rc, revisions=ri + rc, risk=risk,
            creator_led=t in ('CV', 'LS') or aid in ('SF-01', 'SF-03') or aid in CONVERTED,
            video=t in ('CV', 'SF', 'LS', 'HV') or aid in CONVERTED,
        ))
    return pd.DataFrame(rows)


def approvals(dl: pd.DataFrame) -> pd.DataFrame:
    units = dl.groupby('unit', sort=False).agg(assets=('id', lambda s: ' + '.join(s)), submitted=('submitted', 'first'),
                                               approved=('approved', 'first'), rounds=('rounds', 'first'),
                                               approval_bdays=('approval_bdays', 'first'),
                                               first_feedback_bdays=('first_feedback_bdays', 'first'),
                                               sla_met=('sla_met', 'first'), escalated=('escalated', 'first'),
                                               revisions_client=('rev_client', 'sum')).reset_index()
    units['kind'] = 'asset'
    briefs = pd.DataFrame([dict(unit=b[0], assets=b[1], submitted=d(b[3]), approved=d(b[4]), rounds=b[5],
                                approval_bdays=bdays(d(b[3]), d(b[4])), first_feedback_bdays=min(2, bdays(d(b[3]), d(b[4]))),
                                sla_met=True, escalated=False, revisions_client=0, kind='brief') for b in BRIEFS])
    out = pd.concat([briefs, units], ignore_index=True)
    out['week'] = out['submitted'].map(week_of)
    return out


def risks() -> pd.DataFrame:
    rows = []
    for rid, en, de, p, i, owner, wk, res, mat in RISKS:
        identified = START + timedelta(days=7 * (wk - 1) + 1)
        rows.append(dict(id=rid, risk_en=en, risk_de=de, probability=p, impact=i, score=p * i, owner=owner,
                         week=wk, identified=identified, resolved=add_bdays(identified, res), resolution_bdays=res,
                         materialised=mat))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------------------------------
# 3. Audience performance: generative model -> asset-week panel
# ---------------------------------------------------------------------------------------------------------------------

# Base weekly impressions in the go-live week, decay per following week, view rate, completion, viewed length (min).
FMT = {
    'CV': dict(base=520e3, decay=.45, vr=.46, comp=.42, length=3.2),
    'SF': dict(base=640e3, decay=.40, vr=.52, comp=.70, length=.55),
    'LS': dict(base=360e3, decay=.30, vr=.40, comp=.50, length=1.6),
    'HV': dict(base=980e3, decay=.50, vr=.41, comp=.55, length=1.3),
    'SPV': dict(base=300e3, decay=.40, vr=.45, comp=.66, length=.5),   # creator-led video post (converted SP)
    'SP': dict(base=190e3, decay=.35, vr=0, comp=0, length=0),
    'PH': dict(base=230e3, decay=.45, vr=0, comp=0, length=0),
    'PP': dict(base=150e3, decay=.50, vr=0, comp=0, length=0),
    'NL': dict(base=95e3, decay=.05, vr=0, comp=0, length=0),
    'GA': dict(base=430e3, decay=.55, vr=0, comp=0, length=0),
}
# Paid amplification (G2 media support): original plan boosted static posts in weeks 6-8,
# the reallocation moved the week-7/8 support to creator/video assets.
BOOST_PLAN = {'SP-05', 'SP-06', 'SP-07', 'SP-08', 'PH-01', 'HV-01'}
BOOST_ACTUAL = {'SP-05', 'SP-06', 'PH-01', 'HV-01', 'SP-07', 'SP-08', 'LS-02', 'SF-04', 'CV-03'}


def fmt_key(row, plan: bool) -> str:
    if row['type'] == 'SP' and row['id'] in CONVERTED and not plan:
        return 'SPV'
    return row['type']


@dataclass
class Panel:
    df: pd.DataFrame
    scale: dict = field(default_factory=dict)


def simulate(dl: pd.DataFrame, plan: bool, rng: np.random.Generator, noise: bool = True) -> pd.DataFrame:
    """One row per asset and week from go-live to week 8. plan=True simulates the original (static-heavy) plan."""
    rows = []
    boost = BOOST_PLAN if plan else BOOST_ACTUAL
    for _, a in dl.iterrows():
        f = fmt_key(a, plan)
        p = FMT[f]
        creator = bool(a['creator_led']) and not (plan and a['id'] in CONVERTED)
        video = f in ('CV', 'SF', 'LS', 'HV', 'SPV')
        boosted = a['id'] in boost and (a['week'] >= 6 or a['id'] in ('PH-01', 'HV-01'))
        # the same number of draws for every asset and row, so the plan and the actual run share their noise
        asset_noise = math.exp(rng.normal(0, .18) if noise else 0.0)
        for w in range(a['week'], WEEKS + 1):
            z = rng.normal(size=6) if noise else np.zeros(6)
            age = w - a['week']
            # a mid-week go-live only has part of its first week
            share = (7 - a['live'].weekday()) / 7 if age == 0 else 1.0
            impr = p['base'] * asset_noise * share * (p['decay'] ** age) * (1.45 if boosted else 1.0) * math.exp(.10 * z[0])
            if impr < 2_000:
                continue
            # engagement and click propensity: log-linear in format features (what the week-5 model tries to recover)
            log_er = math.log(.021) + .52 * video + .34 * creator + .10 * boosted - .07 * age
            log_cr = math.log(.0042) + .38 * video + .41 * creator - .09 * age
            if f == 'NL':
                log_er, log_cr = math.log(.034), math.log(.031)
            if f == 'GA':
                log_er, log_cr = math.log(.105), math.log(.019)
            if f == 'PP':
                log_er, log_cr = log_er - .25, log_cr - .30
            er, cr = math.exp(log_er + .10 * z[1]), math.exp(log_cr + .12 * z[2])
            views = impr * p['vr'] * math.exp(.06 * z[3]) if video else 0.0
            comp = min(.95, p['comp'] * (1.05 if creator else 1.0) * (1 - .03 * age) * math.exp(.04 * z[4])) if video else 0.0
            reach_rate = .31 * (.9 ** (w - 1)) * (1.12 if boosted else 1.0) * math.exp(.05 * z[5])
            rows.append(dict(id=a['id'], type=a['type'], fmt=f, week=w, age=age, creator_led=int(creator),
                             video=int(video), boosted=int(boosted), impressions=impr, views=views,
                             engagements=impr * er, clicks=impr * cr, reach=impr * reach_rate, completion=comp,
                             length=p['length']))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------------------------------
# 4. Week-5 models
# ---------------------------------------------------------------------------------------------------------------------

MODEL_FMTS = ('CV', 'SF', 'LS', 'HV', 'SPV', 'SP', 'PH', 'PP')  # content assets; newsletter + giveaway excluded


def fit_models(panel: pd.DataFrame, upto_week: int = 5):
    train = panel[(panel.week <= upto_week) & panel.fmt.isin(MODEL_FMTS)].copy()
    train['log_eng'] = np.log(train.engagements)
    train['log_impr'] = np.log(train.impressions)
    eng = smf.ols('log_eng ~ log_impr + creator_led + video + boosted + age', data=train).fit(cov_type='HC1')
    # click-through as a binomial GLM on counts (clicks out of impressions)
    X = sm.add_constant(train[['creator_led', 'video', 'boosted', 'age']].astype(float))
    y = np.column_stack([train.clicks.round(), (train.impressions - train.clicks).round()])
    # quasi-binomial: counts this large are over-dispersed, so the scale is estimated (Pearson chi2 / df)
    # (scale='X2' mis-scales two-column count data in statsmodels, so the Pearson dispersion is passed explicitly)
    glm = sm.GLM(y, X, family=sm.families.Binomial())
    first = glm.fit()
    ctr = glm.fit(scale=float(first.pearson_chi2 / first.df_resid))
    # reach per impression decays with frequency (week) and rises with paid support
    train['log_rr'] = np.log(train.reach / train.impressions)
    rch = smf.ols('log_rr ~ week + boosted', data=train).fit()
    vid = train[train.video == 1].copy()
    vid['logit_c'] = np.log(vid.completion / (1 - vid.completion))
    cmp_ = smf.ols('logit_c ~ C(fmt) + creator_led + age', data=vid).fit()
    vr = (vid.views.sum() / vid.impressions.sum(), vid.groupby('fmt').apply(lambda g: g.views.sum() / g.impressions.sum()))
    return dict(eng=eng, ctr=ctr, reach=rch, comp=cmp_, view_rate=vr, n=len(train), n_video=len(vid))


def predict(models, rows: pd.DataFrame, nl_ga: pd.DataFrame | None = None) -> dict:
    """Forecast the totals of `rows` (planned asset-weeks) with the week-5 models."""
    r = rows[rows.fmt.isin(MODEL_FMTS)].copy()
    r['log_impr'] = np.log(r.impressions)
    smear = np.mean(np.exp(models['eng'].resid))  # Duan smearing for the log model
    eng = float(np.exp(models['eng'].predict(r)).mul(smear).sum())
    X = sm.add_constant(r[['creator_led', 'video', 'boosted', 'age']].astype(float), has_constant='add')
    clicks = float((models['ctr'].predict(X) * r.impressions).sum())
    reach = float((np.exp(models['reach'].predict(r)) * np.mean(np.exp(models['reach'].resid)) * r.impressions).sum())
    v = r[r.video == 1].copy()
    known = set(models['comp'].model.data.frame.fmt)
    v = v[v.fmt.isin(known)]
    rates = models['view_rate'][1]
    v['pviews'] = v.impressions * v.fmt.map(rates).fillna(models['view_rate'][0])
    lc = models['comp'].predict(v)
    v['pcomp'] = 1 / (1 + np.exp(-lc))
    completion = float((v.pviews * v.pcomp).sum() / v.pviews.sum())
    out = dict(engagements=eng, clicks=clicks, reach=reach, completion=completion)
    if nl_ga is not None and len(nl_ga):  # newsletter / giveaway tails are carried over at their observed rates
        out['engagements'] += float(nl_ga.engagements.sum())
        out['clicks'] += float(nl_ga.clicks.sum())
        out['reach'] += float(nl_ga.reach.sum())
    return out


def bootstrap_interval(train_panel: pd.DataFrame, plan_rows: pd.DataFrame, nl_ga, n: int = 400, seed: int = 7):
    """80% interval for the week-7/8 forecast: refit on resampled asset-weeks (case bootstrap)."""
    rng = np.random.default_rng(seed)
    base = train_panel[(train_panel.week <= 5)]
    ids = base.id.unique()
    sims = {k: [] for k in ('engagements', 'clicks', 'reach', 'completion')}
    for _ in range(n):
        pick = rng.choice(ids, size=len(ids), replace=True)
        boot = pd.concat([base[base.id == i] for i in pick], ignore_index=True)
        if boot[boot.video == 1].fmt.nunique() < 2:
            continue
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')  # some resamples are rank-deficient; they are skipped below
                m = fit_models(boot)
                p = predict(m, plan_rows, nl_ga)
        except Exception:
            continue
        if not all(np.isfinite(list(p.values()))):
            continue
        for k in sims:
            sims[k].append(p[k])
    return {k: (float(np.percentile(v, 10)), float(np.percentile(v, 90))) for k, v in sims.items()}


# ---------------------------------------------------------------------------------------------------------------------
# 5. Calibration: hit the brief's totals exactly and the week-7/8 uplift against the week-5 forecast
# ---------------------------------------------------------------------------------------------------------------------

def calibrate(actual: pd.DataFrame, plan: pd.DataFrame):
    act, pln = actual.copy(), plan.copy()
    late = act.week >= 7
    for _ in range(40):
        models = fit_models(act)
        plan78 = pln[pln.week >= 7]
        nlga78 = act[(act.week >= 7) & ~act.fmt.isin(MODEL_FMTS)]
        cf = predict(models, plan78, nlga78)
        # week-7/8 actuals = forecast x (1 + lift)
        for k in ('engagements', 'clicks', 'reach'):
            act.loc[late, k] *= cf[k] * (1 + LIFTS[k]) / act.loc[late, k].sum()
        v78 = late & (act.video == 1)
        w = act.loc[v78, 'views']
        act.loc[v78, 'completion'] *= cf['completion'] * (1 + LIFTS['completion']) / ((w * act.loc[v78, 'completion']).sum() / w.sum())
        # campaign totals: scale every week (both panels share the impression and view scale so the forecast follows)
        for k in ('impressions', 'views', 'engagements', 'clicks', 'reach'):
            f = TARGETS[k] / act[k].sum()
            act[k] *= f
            if k in ('impressions', 'views'):
                pln[k] *= f
        early = (act.week <= 6) & (act.video == 1)
        wv = act.views
        need = TARGETS['completion'] * wv[act.video == 1].sum() - (wv[v78] * act.completion[v78]).sum()
        act.loc[early, 'completion'] *= need / (wv[early] * act.completion[early]).sum()
    # watch time: views x viewed length x completion, lengths scaled once so the total matches
    raw = (act.views * act.length * act.completion).sum()
    k = TARGETS['watch_minutes'] / raw
    act['watch_minutes'] = act.views * act.length * k * act.completion
    act['viewed_length'] = act.length * k
    act['actions'] = act.clicks * .21
    return act, pln, models


def giveaway_entries() -> list[int]:
    # giveaway ran 27.05.-10.06. (weeks 4-6); entries per week
    return [0, 0, 0, 7_150, 8_320, 2_930, 0, 0]


# ---------------------------------------------------------------------------------------------------------------------
# 6. Everything together
# ---------------------------------------------------------------------------------------------------------------------

def build() -> dict:
    rng = np.random.default_rng(SEED)
    dl = deliverables()
    ap = approvals(dl)
    rk = risks()
    actual_raw = simulate(dl, plan=False, rng=rng)
    plan_raw = simulate(dl, plan=True, rng=np.random.default_rng(SEED))
    # the original plan, same assets and same random draws: only the week-7/8 format and paid-support choices differ
    act, pln, models = calibrate(actual_raw, plan_raw)

    weeks = pd.DataFrame({'week': range(1, WEEKS + 1)})
    weeks['start'] = [START + timedelta(days=7 * (w - 1)) for w in weeks.week]
    agg = act.groupby('week').agg(impressions=('impressions', 'sum'), views=('views', 'sum'),
                                  engagements=('engagements', 'sum'), clicks=('clicks', 'sum'),
                                  reach=('reach', 'sum'), watch_minutes=('watch_minutes', 'sum'),
                                  actions=('actions', 'sum')).reset_index()
    comp = act[act.video == 1].groupby('week').apply(lambda g: (g.views * g.completion).sum() / g.views.sum())
    agg['completion'] = agg.week.map(comp)
    weeks = weeks.merge(agg, on='week', how='left')
    weeks['giveaway_entries'] = giveaway_entries()

    # week-5 forecast for weeks 6-8 under the original plan (week 6 = out-of-sample check)
    m5 = fit_models(act)
    fc = []
    for w in (6, 7, 8):
        rows = pln[pln.week == w]
        nlga = act[(act.week == w) & ~act.fmt.isin(MODEL_FMTS)]
        fc.append(dict(week=w, **predict(m5, rows, nlga)))
    forecast = pd.DataFrame(fc)
    interval = bootstrap_interval(act, pln[pln.week >= 7], act[(act.week >= 7) & ~act.fmt.isin(MODEL_FMTS)])

    # operational weekly breakdown (derived + log)
    ops = pd.DataFrame({'week': range(1, WEEKS + 1)})
    for k, v in WEEKLY_LOG.items():
        ops[k] = v
    ops['deliverables'] = ops.week.map(dl.groupby('week').size()).fillna(0).astype(int)
    ops['on_time'] = ops.week.map(dl[dl.on_time].groupby('week').size()).fillna(0).astype(int)
    ops['approvals_submitted'] = ops.week.map(ap.groupby('week').size()).fillna(0).astype(int)
    ap['approved_week'] = ap.approved.map(week_of)
    ops['approvals_completed'] = ops.week.map(ap.groupby('approved_week').size()).fillna(0).astype(int)
    rev = dl.assign(rev_week=dl.submitted.map(week_of)).groupby('rev_week').revisions.sum()
    ops['revisions'] = ops.week.map(rev).fillna(0).astype(int)
    ops['risks_identified'] = ops.week.map(rk.groupby('week').size()).fillna(0).astype(int)
    rk['resolved_week'] = rk.resolved.map(week_of)
    ops['risks_closed'] = ops.week.map(rk.groupby('resolved_week').size()).fillna(0).astype(int)
    esc = ap[ap.escalated].assign(esc_week=lambda x: x.submitted.map(lambda s: week_of(add_bdays(s, 3))))
    ops['escalations'] = ops.week.map(esc.groupby('esc_week').size()).fillna(0).astype(int)
    pod_per = {'CV': 3, 'SF': 3, 'LS': 3, 'HV': 3, 'GA': 3, 'SP': 2, 'PH': 2, 'NL': 2, 'PP': 2}
    dl['evidence_items'] = dl.type.map(pod_per)
    ops['pod_items'] = ops.week.map(dl.groupby('week').evidence_items.sum()).fillna(0).astype(int)
    ops['client_touchpoints'] = ops.client_comms + ops.akg_meetings
    ops['interactions'] = ops.messages + ops.meetings

    # asset-level performance for the tracker
    perf = act.groupby('id').agg(impressions=('impressions', 'sum'), views=('views', 'sum'),
                                 engagements=('engagements', 'sum'), clicks=('clicks', 'sum')).reset_index()
    dl = dl.merge(perf, on='id', how='left')

    # format comparison: weeks 1-5 evidence and weeks 7-8 result
    def by_fmt(rows):
        g = rows.groupby('fmt')
        out = g.agg(assets=('id', 'nunique'), reach=('reach', 'sum'), impressions=('impressions', 'sum'),
                    views=('views', 'sum'), engagements=('engagements', 'sum'), clicks=('clicks', 'sum'),
                    actions=('actions', 'sum'))
        out['completion'] = rows[rows.video == 1].groupby('fmt').apply(lambda x: (x.views * x.completion).sum() / x.views.sum())
        out['er'] = out.engagements / out.impressions
        out['ctr'] = out.clicks / out.impressions
        out['action_rate'] = out.actions / out.reach
        return out.reset_index()
    before = by_fmt(act[act.week <= 5])
    after = by_fmt(act[act.week >= 7])

    nlga78 = act[(act.week >= 7) & ~act.fmt.isin(MODEL_FMTS)]
    cf78 = predict(m5, pln[pln.week >= 7], nlga78)

    # Renewal projection: what the week-5 engagement model says about running the 8 social-post slots as creator-led
    # video posts (the two converted ones already were). Effect = exp(b_creator + b_video) with a delta-method 95% CI.
    b, cov = m5['eng'].params, m5['eng'].cov_params()
    est = b['creator_led'] + b['video']
    se = math.sqrt(cov.loc['creator_led', 'creator_led'] + cov.loc['video', 'video'] + 2 * cov.loc['creator_led', 'video'])
    static_sp = act[(act.fmt == 'SP')]
    scenario = dict(factor=math.exp(est), lo=math.exp(est - 1.96 * se), hi=math.exp(est + 1.96 * se),
                    base_eng=float(static_sp.engagements.sum()), posts=int(static_sp.id.nunique()))
    scenario['extra_eng'] = scenario['base_eng'] * (scenario['factor'] - 1)
    scenario['extra_lo'] = scenario['base_eng'] * (scenario['lo'] - 1)
    scenario['extra_hi'] = scenario['base_eng'] * (scenario['hi'] - 1)

    return dict(deliverables=dl, approvals=ap, risks=rk, panel=act, plan=pln, weeks=weeks, ops=ops,
                forecast=forecast, forecast_78=cf78, forecast_completion_78=cf78['completion'], interval=interval,
                models=m5, before=before, after=after, scenario=scenario)
