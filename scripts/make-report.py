"""Create the concise PDF brief from the measured evaluation artifacts."""
from pathlib import Path
import json
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics.charts.barcharts import VerticalBarChart

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/pdf/RecycleGuard-Technical-Brief.pdf"
OUT.parent.mkdir(parents=True, exist_ok=True)
summary = json.loads((ROOT/"artifacts/heldout-evaluation/summary.json").read_text())
green=colors.HexColor('#146454'); ink=colors.HexColor('#19332b'); muted=colors.HexColor('#5c7168'); light=colors.HexColor('#edf3ee'); orange=colors.HexColor('#ce7849')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='TitleRG',fontName='Helvetica-Bold',fontSize=30,leading=34,textColor=ink,spaceAfter=12))
styles.add(ParagraphStyle(name='SubtitleRG',fontName='Helvetica',fontSize=14,leading=20,textColor=muted,spaceAfter=18))
styles.add(ParagraphStyle(name='H1RG',fontName='Helvetica-Bold',fontSize=18,leading=22,textColor=green,spaceAfter=12))
styles.add(ParagraphStyle(name='H2RG',fontName='Helvetica-Bold',fontSize=11,leading=15,textColor=ink,spaceBefore=11,spaceAfter=6))
styles.add(ParagraphStyle(name='BodyRG',fontName='Helvetica',fontSize=9.5,leading=14,textColor=ink,spaceAfter=8))
styles.add(ParagraphStyle(name='SmallRG',fontName='Helvetica',fontSize=8,leading=11,textColor=muted,spaceAfter=6))
styles.add(ParagraphStyle(name='CellRG',fontName='Helvetica',fontSize=8,leading=11,textColor=ink))
story=[]
def p(text,style='BodyRG'): story.append(Paragraph(text,styles[style]))
def h(text): p(text,'H2RG')
def table(rows,widths):
    data=[[Paragraph(str(v),styles['CellRG']) for v in row] for row in rows]
    t=Table(data,colWidths=widths,hAlign='LEFT',repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),light),('LINEBELOW',(0,0),(-1,0),1,green),('LINEBELOW',(0,1),(-1,-1),.3,colors.HexColor('#d9e3dc')),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),('LEFTPADDING',(0,0),(-1,-1),7)]))
    story.append(t);story.append(Spacer(1,9))
def page_title(n,title): p(f'0{n} / TECHNICAL BRIEF','SmallRG');p(title,'H1RG')

p('RESEARCH PROTOTYPE / VERSION 1.1 / 12 NOVEMBER 2026','SmallRG')
p('RecycleGuard','TitleRG')
p('Evidence-aware decision support<br/>with a human in control','SubtitleRG')
h('Purpose')
p('A small, inspectable resource-recovery incident simulator explores how explicit constraints and current evidence affect action validity. Operators can accept, reject, modify or request alternatives to advice. The setting and all hazard/resource values are fictional training abstractions.')
h('What is delivered and what is verified')
table([['Component','Release status'],['Shared C# incident model','Compiled; invariants, deterministic replay and resource rules tested.'],['Python adviser + browser interface','End-to-end tested, including the portable Windows executable.'],['Unity 3D client','Built with Unity 6000.6.8f1 and run as a Windows player on one machine: automated check, real-click test and recorded walkthrough. Not tested on other hardware or Unity versions.'],['Model evaluation','Offline fault-injection fixtures evaluated. No real-LLM results.']],[145,365])
h('Architecture: one simulation implementation')
d=Drawing(510,112)
for x,w,t,sub in [(0,155,'C# world','Unity or headless host'),(178,154,'Python adviser','Observation-only interface'),(355,155,'Human operator','Accept / reject / modify')]:
    d.add(Rect(x,43,w,57,fillColor=light,strokeColor=colors.HexColor('#c7d8cd'),radius=5))
    d.add(String(x+10,78,t,fontName='Helvetica-Bold',fontSize=10,fillColor=ink));d.add(String(x+10,60,sub,fontSize=8,fillColor=muted))
for a,b in [(156,176),(333,353)]: d.add(Line(a,72,b,72,strokeColor=green,strokeWidth=1.5))
d.add(String(0,18,'Observations -> proposal -> constraints -> approval -> C# revalidation -> state + audit log',fontSize=8.7,fillColor=green))
story.append(d)
h('Scope of the evidence')
p('1,200 held-out episodes and 5,458 equal-state probes support the behaviour of this synthetic software system. They do not establish real-world safety, improved human decisions or LLM reasoning. The demo has no Deakin/FRV validation or endorsement.')
story.append(PageBreak())

page_title(2,'Model, constraints and human authority')
p('Four zones: battery intake, sorting hall, materials store and loading yard. Each has heat, occupants and an isolation flag. Two crews, 18 suppression units and a 32-tick horizon create simple resource constraints.')
h('Transparent discrete dynamics')
p('Heat is an integer from 0 to 100. At heat >=25, powered zones grow by 3-5 units per tick and isolated zones by 1-3. Otherwise they cool by one. An adjacent zone at heat >=75 adds five growth units. Heat >=80 accumulates synthetic damage. Containment requires all occupants cleared and every zone below 25. Damage >=45 or tick 32 terminates an unresolved episode.')
table([['Action','Prerequisites and modelled effect'],['Inspect','Refresh one zone with reconnaissance evidence for three post-action ticks.'],['Evacuate','Confirmed occupants and one crew; clear occupants; crew reserved until tick+2.'],['Isolate','Confirmed powered zone; set isolation flag and slow modelled growth.'],['Suppress','Empty, isolated, actionable zone; one crew and two resource units; heat decreases by 38.'],['Wait','Advance one decision tick without committing resources.']],[85,425])
p('Invalid current decisions cost one tick but do not consume action resources. Stale revisions and rejected recommendations consume no time. Every executed action is independently validated by C#, including manual overrides.','SmallRG')
h('Observation and policy design')
p('Reliable sensors are current. Delayed sensors lag three ticks after warm-up. Dropout combines intermittent missing zones with one-tick lag elsewhere. Unknown values are explicit (-1); the adviser cannot read hidden simulator truth. Inspection can restore current evidence.')
p('The raw fixture intentionally mixes poor and valid proposals. The permissive checker allows evidence aged up to two ticks, matching the execution guard\'s observation rule. The strict checker requires age-zero evidence for operational actions and repairs invalid proposals using a transparent priority heuristic. Conditional subgoals are replanned after each action; they are not queued for autonomous execution.')
h('Why the freshness ablation matters')
p('Development tests exposed duplicate evacuation/isolation suggestions from recently aged observations. The world had already changed, while the old observation still met the permissive check. Requiring current evidence removed these failures in the final test set, at the cost of additional inspection decisions.')
h('Human oversight and replay')
p('Advice records the raw proposal, any replacement, violated constraints, observations, timestamps, missing evidence and revision. No confidence percentage is fabricated. Replays rerun all actions and compare stored snapshots before playback. Debrief displays recorded truth, explicitly distinguished from live observations.')
story.append(PageBreak())

page_title(3,'Measured results and interpretation')
p('Final evaluation: seeds 2000-2099, three telemetry conditions, four policies, 1,200 episodes. Development seeds 1000-1029 were used to refine the checker and were excluded from the final set. All completed episodes were retained and replay-verified.')
groups={(r['scenario'],r['mode']):r for r in summary['groups']}
d=Drawing(510,200);chart=VerticalBarChart();chart.x=38;chart.y=34;chart.width=455;chart.height=143
chart.data=[[groups[(s,m)]['attempted_invalid_pct'] for s in ['reliable','delayed','dropout']] for m in ['offline_raw','offline_checked_permissive','offline_checked']]
chart.categoryAxis.categoryNames=['Reliable','Delayed','Dropout'];chart.valueAxis.valueMin=0;chart.valueAxis.valueMax=80;chart.valueAxis.valueStep=20
chart.bars[0].fillColor=orange;chart.bars[1].fillColor=colors.HexColor('#91ae9d');chart.bars[2].fillColor=green
chart.categoryAxis.labels.fontSize=9;chart.valueAxis.labels.fontSize=8;chart.barSpacing=2;chart.groupSpacing=22
chart.valueAxis.visibleGrid=1;chart.valueAxis.gridStrokeColor=colors.HexColor('#dce5df');d.add(chart)
d.add(String(0,188,'Attempted invalid actions (%)',fontSize=9,fillColor=muted))
for x,c,t in [(55,orange,'Raw fixture'),(202,colors.HexColor('#91ae9d'),'Permissive check'),(372,green,'Strict check')]:
    d.add(Rect(x,8,8,8,fillColor=c,strokeColor=c));d.add(String(x+13,8,t,fontSize=8,fillColor=ink))
story.append(d)
rows=[['Scenario','Raw invalid','Permissive','Strict invalid','Strict ticks']]
for s in ['reliable','delayed','dropout']:
    rows.append([s.title(),f"{groups[(s,'offline_raw')]['attempted_invalid_pct']:.1f}%",f"{groups[(s,'offline_checked_permissive')]['attempted_invalid_pct']:.1f}%",f"{groups[(s,'offline_checked')]['attempted_invalid_pct']:.1f}%",f"{groups[(s,'offline_checked')]['mean_steps']:.1f}"])
table(rows,[100,100,100,110,100])
p('The strict checker contained 100% of these episodes. Raw fixture containment was 100%, 0% and 91% under reliable, delayed and dropout conditions. Under dropout, strict checking took 15.6 ticks on average versus 10.7 for permissive checking. Inspection has a measurable time cost.')
p(f"Equal-state probes: <b>{summary['equal_state_probe_count']:,}</b> identical observation/proposal pairs; raw invalid proposals <b>{summary['raw_invalid_probes']:,}</b>, strict-check invalid proposals <b>{summary['checked_invalid_probes']}</b>.")
h('Paired effect sizes')
for r in summary['paired_episode_differences']:
    p(f"{r['scenario'].title()}: strict minus raw invalid rate {r['checked_minus_raw_invalid_rate_pp']:.2f} percentage points; paired bootstrap 95% interval [{r['bootstrap_95_ci_pp'][0]:.2f}, {r['bootstrap_95_ci_pp'][1]:.2f}].",'SmallRG')
p('Table rates pool decisions; intervals use per-episode paired rates and 2,000 seed-level resamples. Initial conditions are paired, but policy-dependent random draw consumption can diverge. Offline policy timings exclude rendering, C# IPC and model latency.','SmallRG')
h('What these results do not show')
p('Zero invalidity is partly by construction: the checker encodes the model\'s rules. Fixtures are not LLM error distributions, and the basic script is not an expert baseline. All arms reject invalid execution. No claims about physical fidelity, human trust, real-world safety or AI novelty follow from these numbers.')
story.append(PageBreak())

page_title(4,'Verification, reproducibility and provenance')
h('Executed verification')
p('The automated suite contains 52 passing tests covering deterministic replay, the observation-timestamp panel logic, resource invariants, stale requests, unknown evidence, Python/C# constraint parity across generated trajectories, human rejection and alternatives, and real HTTP adapter contracts against a local stub. No live model was used.')
p('Browser automation exercised initial rendering, missing evidence, recommendations, alternatives, rejection without time advance, invalid manual actions, a complete 17-step checked episode, replay export/import/verification, mobile overflow and JavaScript errors. The same flow passed against the portable Windows executable. The browser walkthrough video is browser footage.')
h('Unity client: verified and pending')
p('The client was built in batch mode with Unity 6000.6.8f1 on Windows 10 (GeForce 920M, Direct3D 11). An observation-timestamp panel shows what was observed in each zone, when, and whether it is current, aged, stale or missing; its logic is shared C# tested outside Unity. The player passed its automated check in all three telemetry scenarios, responded correctly to real mouse clicks, and exchanged live advice with the Python service. A captioned walkthrough was recorded from frames the player rendered itself.')
p('The first build passed its automated check while every scene object rendered magenta and labels were unreadable; both were found by inspecting screenshots, fixed, and the check extended. Still pending: reject, alternative and replay-slider controls by click, window resizing, a second machine, and any GitHub workflow run.')
h('Reproduce the evaluation')
p('<font face="Courier" size="8">scripts/build-core.ps1<br/>python -m pytest -q<br/>python -m experiments.run --seeds 100 --seed-start 2000<br/>  --output artifacts/heldout-evaluation</font>')
p('The repository includes per-episode CSV, raw JSONL traces, equal-state probes, source SHA-256 manifests, replay examples, test XML, browser screenshots, build scripts and the complete research protocol. Direct Python dependencies are pinned. The Windows package runs offline without Python or Unity installation; .NET Framework 4.x is required.')
h('Development provenance')
p('The initial implementation and local verification used substantial Codex assistance. Development provenance and contribution guidelines are recorded in docs/CONTRIBUTIONS.md; validation evidence and outstanding checks are tracked in docs/VALIDATION.md.')
h('Next research steps')
p('Evaluate real model outputs on identical cached observations; strengthen scripted/search baselines; introduce sensor noise and delayed command acknowledgements; review scenarios with domain experts; and design an appropriate human study before making claims about decision quality or trust.')
h('Implementation references')
p('<link href="https://docs.unity.com/en-us/engine/6000.3/manual/unity-editor/command-line-arguments/run-unity" color="#146454">Unity command-line builds</link> | <link href="https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Networking.UnityWebRequest.html" color="#146454">UnityWebRequest</link> | <link href="https://docs.unity3d.com/6000.0/Documentation/ScriptReference/JsonUtility.html" color="#146454">JsonUtility</link><br/><link href="https://docs.ollama.com/api/openai-compatibility" color="#146454">Ollama compatible endpoint</link> | <link href="https://playwright.dev/docs/videos" color="#146454">Playwright video recording</link>','SmallRG')
p('Full definitions and limitations: docs/TECHNICAL_REPORT.md and docs/EXPERIMENT_PROTOCOL.md. No FRV data, operational protocols or external endorsements were used.','SmallRG')

def decorate(canvas,doc):
    canvas.setTitle('RecycleGuard - Technical Brief');canvas.setAuthor('RecycleGuard')
    canvas.setStrokeColor(colors.HexColor('#d7e1da'));canvas.line(42,40,553,40)
    canvas.setFont('Helvetica',8);canvas.setFillColor(muted);canvas.drawString(42,27,'RECYCLEGUARD / RESEARCH PROTOTYPE / 12 NOVEMBER 2026')
    canvas.drawRightString(553,27,f'{doc.page}')

SimpleDocTemplate(str(OUT),pagesize=A4,rightMargin=42,leftMargin=42,topMargin=38,bottomMargin=53).build(story,onFirstPage=decorate,onLaterPages=decorate)
print(OUT)
