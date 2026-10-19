from __future__ import annotations

import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "compositions/frames"
NEW = ROOT / "compositions/higgs-field"
NEW.mkdir(parents=True, exist_ok=True)

SCENES = [
    dict(id="h01", old="01-hidden-opportunity.html", pose="rest", label="RESTING",
         title="Possibility is already in the room.", eyebrow="THE HIGGS FIELD · A VISUAL ANALOGY",
         note="Research can hold relationships that no single document reveals.",
         elements=[("sheet", "SOURCE", "A result", "Evidence", "left:90px;top:180px"),
                   ("sheet", "SOURCE", "A method", "Observation", "left:650px;top:90px"),
                   ("sheet", "SOURCE", "A constraint", "Open question", "left:1210px;top:195px")],
         caption="A shared field of context — not a machine that creates answers."),
    dict(id="h02", old="02-scattered-room.html", pose="t_search", label="SEARCHING", title="But the clues sit apart.",
         eyebrow="THE ROOM BEFORE THE CONNECTION", note="Files, findings, and open questions rarely arrive as one view.",
         elements=[("sheet", "FILE 01", "Research record", "Finding", "left:70px;top:100px"),
                   ("sheet red", "FILE 02", "A separate study", "Different context", "left:650px;top:320px"),
                   ("sheet yellow", "QUESTION", "What is missing?", "Not yet linked", "left:1220px;top:95px")],
         caption="Separate sources make useful relationships easy to miss."),
    dict(id="h03", old="03-room-to-portfolio.html", pose="rf2", label="FOUND", title="Mindrian gives the room shared context.",
         eyebrow="FROM ISOLATED CLUES TO A TRACEABLE MAP", note="Sources connect through claims, questions, and relationships — with their origins kept visible.",
         elements=[("tile", "MATERIAL", "Source", "Traceable", "left:35px;top:205px"),
                   ("tile blue", "EVIDENCE", "Supported claim", "Source-linked", "left:455px;top:95px"),
                   ("tile yellow", "QUESTION", "Open assumption", "Needs checking", "left:875px;top:205px"),
                   ("tile", "LEAD", "Candidate", "For review", "left:1295px;top:95px")],
         caption="The relationship is a hypothesis until its evidence is checked."),
    dict(id="h04", old="04-frame-question.html", pose="t_listen", label="LISTENING", title="The user sets what matters.",
         eyebrow="A QUESTION SHAPES THE SEARCH", note="Objective · constraints · desired outcome",
         elements=[("tile user", "YOUR QUESTION", "What should change?", "You define the job", "left:45px;top:100px"),
                   ("tile", "RELEVANT", "Material to inspect", "Selected by the question", "left:640px;top:250px"),
                   ("tile quiet", "OUT OF SCOPE", "Other material", "Kept in the room", "left:1270px;top:105px")],
         caption="User intent guides the inquiry; the system does not choose the goal."),
    dict(id="h05", old="05-methods-fit.html", pose="t_search", label="EXPLORING", title="Choose methods for the job.",
         eyebrow="NO FIXED ENGINE PARADE", note="Use only the research steps that can move this question forward.",
         elements=[("tile", "BOTTLENECK", "Find what is lagging", "Reverse Salient", "left:20px;top:95px"),
                   ("tile blue", "CONNECTION", "Compare mechanisms", "Similarity / analogy", "left:440px;top:285px"),
                   ("tile yellow", "EVIDENCE", "Check outside sources", "Research", "left:860px;top:95px"),
                   ("tile red", "CHALLENGE", "Test the lead", "SME / BONO review", "left:1280px;top:285px")],
         caption="Methods are selected by fit. Their outputs keep their own limits."),
    dict(id="h06", old="06-inspect-the-lead.html", pose="challenge", label="CHALLENGING", title="A lead gains weight through evidence.",
         eyebrow="A HYPOTHESIS IS NOT A FINDING", note="Keep the source, supporting evidence, counterevidence, and unanswered questions together.",
         elements=[("tile blue", "SOURCE A", "What it shows", "Verified record", "left:25px;top:70px"),
                   ("tile blue", "SOURCE B", "What it shows", "Verified record", "left:25px;top:285px"),
                   ("tile", "CANDIDATE", "Possible connection", "Inference · review", "left:600px;top:175px"),
                   ("tile yellow", "COUNTERCHECK", "What could break it?", "Open question", "left:1220px;top:65px"),
                   ("tile red", "HUMAN DECISION", "Investigate · test · park", "Decision stays with you", "left:1220px;top:315px")],
         caption="Here the Higgs comparison stops: evidence and people do the work."),
    dict(id="h07", old="07-compounding-portfolio.html", pose="decision", label="YOUR DECISION", title="Keep a portfolio, not just one report.",
         eyebrow="SEVERAL LEADS CAN ADVANCE AT ONCE", note="Each candidate keeps its evidence, status, rationale, and next step.",
         elements=[("tile blue", "DEEPEN", "Promising lead", "Evidence to gather", "left:110px;top:125px"),
                   ("tile yellow", "TEST", "Open hypothesis", "Next experiment", "left:670px;top:255px"),
                   ("tile", "PARK", "Not now", "Reason retained", "left:1230px;top:125px")],
         caption="Illustrative portfolio — not live room data."),
    dict(id="h08", old="08-next-question.html", pose="t_handover", label="HANDING OVER", title="The next question starts further along.",
         eyebrow="A SHARED FIELD THAT CAN COMPOUND", note="Reviewed sources · decisions · rejected paths · new questions",
         elements=[("tile", "RETAIN", "Evidence + provenance", "Reusable in context", "left:25px;top:205px"),
                   ("tile blue", "REVISIT", "Earlier candidate", "Deepen when relevant", "left:445px;top:90px"),
                   ("tile yellow", "NEW QUESTION", "A fresh direction", "Human-framed", "left:865px;top:205px"),
                   ("tile", "MINDRIANOS", "Research workspace", "Not the Higgs field", "left:1285px;top:90px")],
         caption="The analogy is shared context. Mindrian organizes inquiry; it does not prove or automatically discover breakthroughs."),
]

TIMINGS = [
    (0.000, 5.264), (5.264, 7.693), (12.957, 5.264), (18.221, 4.859),
    (23.080, 8.503), (31.583, 10.527), (42.110, 5.669), (47.779, 11.318),
]
def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")

EXPECTED_SCENES = {f"{scene['id']}-{slug(scene['title'])}.html" for scene in SCENES}
for stale in NEW.glob("h*.html"):
    if stale.name not in EXPECTED_SCENES:
        stale.unlink()

def face_svg(file: str) -> str:
    source = (OLD / file).read_text()
    match = re.search(r'(<svg class="theo-face".*?</svg>)', source, re.S)
    if not match:
        raise RuntimeError(f"Theo face missing in {file}")
    return match.group(1)

def face_tweens(file: str) -> str:
    source = (OLD / file).read_text()
    script = re.search(r"<script>(.*?)</script>", source, re.S).group(1)
    lines = re.findall(r'tl\.to\("\.face-[^;]+;', script)
    if not lines:
        raise RuntimeError(f"Theo face motion missing in {file}")
    return "".join(re.sub(r",0\.75\);$", ",.72);", line) for line in lines)

def esc(text: str) -> str:
    return html.escape(text, quote=True)

def scene_filename(scene: dict) -> str:
    return f"{scene['id']}-{slug(scene['title'])}.html"

def render_scene(scene: dict, start: float, duration: float, page: int) -> str:
    ident = scene["id"]
    cards = []
    for ix, (kind, label, title, sub, pos) in enumerate(scene["elements"]):
        cards.append(f'<article class="{kind} tile-{ix+1}" style="{pos}"><div class="mono tiny">{esc(label)}</div><h3>{esc(title)}</h3><p>{esc(sub)}</p></article>')
    face = face_svg(scene["old"])
    morph = face_tweens(scene["old"])
    gridlines = ''.join(f'<div class="grid-v" style="left:{x}px"></div>' for x in range(96, 1720, 96))
    gridlines += ''.join(f'<div class="grid-h" style="top:{y}px"></div>' for y in range(96, 590, 96))
    links = {
        "h03": '<div class="line l1" style="left:22%;top:41%;width:27%"></div><div class="line v l2" style="left:49%;top:41%;height:18%"></div><div class="line l3" style="left:49%;top:59%;width:28%"></div>',
        "h04": '<div class="line l1" style="left:24%;top:41%;width:29%"></div>',
        "h05": '<div class="line l1" style="left:18%;top:40%;width:22%"></div><div class="line l2" style="left:42%;top:60%;width:23%"></div><div class="line yellowline l3" style="left:67%;top:40%;width:22%"></div>',
        "h06": '<div class="line l1" style="left:22%;top:31%;width:24%"></div><div class="line l2" style="left:22%;top:68%;width:24%"></div><div class="line v l3" style="left:46%;top:31%;height:37%"></div><div class="line yellowline l4" style="left:78%;top:32%;width:12%"></div>',
        "h08": '<div class="line l1" style="left:23%;top:54%;width:25%"></div><div class="line v l2" style="left:48%;top:39%;height:15%"></div><div class="line l3" style="left:48%;top:39%;width:25%"></div>',
    }.get(ident, '')
    line_motion = ''
    if links:
        line_motion = 'tl.fromTo(".line:not(.v)",{scaleX:0},{scaleX:1,duration:.38,stagger:.12,ease:"power2.out"},1.1);'
        if 'class="line v' in links:
            line_motion += 'tl.fromTo(".line.v",{scaleY:0},{scaleY:1,duration:.38,stagger:.12,ease:"power2.out"},1.1);'
    return f'''<!doctype html><html lang="en"><head><meta charset="UTF-8"><title>{esc(scene['title'])}</title></head><body><template>
<style>
@font-face{{font-family:Figtree;src:url(../../assets/fonts/figtree.woff2) format("woff2");font-weight:400 900;font-display:block}}
@font-face{{font-family:DMSans;src:url(../../assets/fonts/dm-sans-latin.woff2) format("woff2");font-weight:400 1000;font-display:block}}
@font-face{{font-family:JetBrains;src:url(../../assets/fonts/jetbrains-mono.ttf) format("truetype");font-weight:400;font-display:block}}
:root{{--paper:#F7F5EE;--ink:#111;--blue:#1F3FBF;--red:#D6281F;--yellow:#E4BD00;--muted:#55524B;--rule:#D5D2C9;--panel:#fff;}}
*{{box-sizing:border-box}}#{ident}-root{{position:absolute;inset:0;width:100%;height:100%;overflow:hidden;background:var(--paper);color:var(--ink);font-family:Figtree,DMSans,Arial,sans-serif}}
.mono{{font-family:JetBrains,monospace;letter-spacing:.07em}}.top{{position:absolute;left:112px;top:66px;z-index:3}}.eyebrow{{font-size:20px;color:var(--blue);text-transform:uppercase;letter-spacing:.12em}}.title{{font-size:68px;line-height:1.03;letter-spacing:-.055em;font-weight:850;margin-top:17px;max-width:1310px}}.note{{font-size:25px;line-height:1.25;margin-top:16px;color:#393832;max-width:1050px}}
.folio{{position:absolute;left:112px;top:1012px;color:var(--muted);font-size:15px}}.folio b{{color:var(--ink)}}.page{{position:absolute;right:112px;bottom:55px;font-size:15px}}
.field{{position:absolute;left:100px;right:100px;top:330px;height:590px;border:2px solid var(--ink);background:var(--paper);overflow:hidden}}
.grid-v,.grid-h{{position:absolute;z-index:0;background:var(--rule);opacity:.52}}.grid-v{{top:0;bottom:0;width:1px}}.grid-h{{left:0;right:0;height:1px}}
.field-label{{position:absolute;left:28px;top:20px;color:var(--muted);font-size:14px;z-index:1}}
.tile,.sheet{{position:absolute;z-index:2;width:350px;min-height:155px;padding:20px 22px;background:#fff;border:2px solid var(--ink)}}
.sheet{{width:380px;min-height:160px;border-width:2px 2px 2px 9px;padding:23px 25px}}.red{{border-left-color:var(--red)}}.yellow{{border-left-color:var(--yellow)}}.blue{{border-color:var(--blue)}}.user{{background:#E9EBF7;border-color:var(--blue)}}.quiet{{background:#EEECE5;color:#56534D;border-style:dashed}}
.tiny{{font-size:14px;color:var(--muted);text-transform:uppercase}}.tile h3,.sheet h3{{font-size:27px;line-height:1.08;margin-top:16px;letter-spacing:-.025em}}.tile p,.sheet p{{font-size:17px;margin-top:10px;color:#56534D}}
.line{{position:absolute;z-index:1;background:var(--blue);height:4px;transform-origin:left center}}.line.v{{width:4px;height:110px;transform-origin:center top}}.line.redline{{background:var(--red)}}.line.yellowline{{background:var(--yellow)}}
.field-key{{position:absolute;z-index:3;left:26px;bottom:14px;display:flex;gap:27px;color:var(--muted);font-size:12px}}.field-key span{{display:flex;align-items:center;gap:8px}}.key{{display:inline-block;width:10px;height:10px;border:2px solid var(--ink)}}.bluekey{{border-color:var(--blue)}}.yellowkey{{border-color:#A98A00}}.redkey{{border-color:var(--red)}}
.theo{{position:absolute;right:108px;top:55px;width:205px;z-index:4}}.theo-label{{font:13px JetBrains,monospace;letter-spacing:.06em;margin:0 0 6px 6px}}.theo-face{{width:100%;height:auto;display:block}}
.caption{{position:absolute;left:580px;right:330px;bottom:57px;text-align:center;font:13px JetBrains,monospace;color:var(--muted);letter-spacing:.03em}}
.callout{{position:absolute;z-index:3;left:1300px;top:230px;padding:9px 12px;background:var(--ink);color:white;font:13px JetBrains,monospace;letter-spacing:.05em}}
</style>
<div id="{ident}-root" data-composition-id="{ident}" data-width="1920" data-height="1080" data-duration="{duration}">
<div class="top intro"><div class="eyebrow mono">{esc(scene['eyebrow'])}</div><div class="title">{esc(scene['title'])}</div><div class="note">{esc(scene['note'])}</div></div>
<div class="field"><div class="field-label mono">MINDRIANOS · ROOM CONTEXT</div>{gridlines}
{''.join(cards)}
{links}
<div class="field-key mono"><span><i class="key bluekey"></i> EVIDENCE</span><span><i class="key yellowkey"></i> QUESTION</span><span><i class="key redkey"></i> ASSUMPTION / CONFLICT</span></div>
</div>
<div class="theo"><div class="theo-label">THEO · {esc(scene['label'])}</div>{face}</div>
<div class="folio mono"><b>MINDRIANOS</b> / OPPORTUNITY DISCOVERY</div><div class="page mono">{page:02d} / 08</div><div class="caption">{esc(scene['caption'])}</div>
</div>
<script>const tl=gsap.timeline({{paused:true}});tl.fromTo(".intro",{{y:22,opacity:0}},{{y:0,opacity:1,duration:.55,ease:"power3.out"}},.08);tl.fromTo(".theo",{{x:36,opacity:0}},{{x:0,opacity:1,duration:.48,ease:"power3.out"}},.2);{morph}tl.fromTo(".field",{{clipPath:"inset(0 100% 0 0)"}},{{clipPath:"inset(0 0% 0 0)",duration:.6,ease:"power2.out"}},.55);tl.fromTo(".tile-1,.tile-2,.tile-3,.tile-4,.tile-5",{{y:28,opacity:0}},{{y:0,opacity:1,duration:.45,stagger:.16,ease:"power3.out"}},.85);{line_motion}window.__timelines["{ident}"]=tl;</script>
</template></body></html>'''

for i, scene in enumerate(SCENES):
    start, duration = TIMINGS[i]
    (NEW / scene_filename(scene)).write_text(render_scene(scene, start, duration, i+1))

root = ['''<!doctype html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=1920,height=1080"><title>MindrianOS — A field of opportunity</title><script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script><style>*{margin:0;padding:0;box-sizing:border-box}html,body{width:1920px;height:1080px;overflow:hidden;background:#F7F5EE}#root{position:relative;width:100%;height:100%;overflow:hidden;background:#F7F5EE}.clip{position:absolute;inset:0;opacity:0}</style></head><body><div id="root" data-composition-id="main" data-start="0" data-duration="59.097" data-width="1920" data-height="1080">''']
for i, scene in enumerate(SCENES):
    start, duration = TIMINGS[i]
    name = scene_filename(scene)
    root.append(f'<div id="{scene["id"]}-host" class="clip" data-composition-id="{scene["id"]}" data-composition-src="compositions/higgs-field/{name}" data-start="{start:.3f}" data-duration="{duration:.3f}" data-track-index="{i}" data-width="1920" data-height="1080"></div>')
root.append('<audio id="narration" src="assets/audio/narration.mp3" data-start="0" data-duration="57.496" data-track-index="8" data-audio-group="voiceover"></audio></div><script>const tl=gsap.timeline({paused:true});')
for scene, (start, _) in zip(SCENES, TIMINGS):
    root.append(f'tl.fromTo("#{scene["id"]}-host",{{opacity:0}},{{opacity:1,duration:.2,ease:"power1.out"}},{start:.3f});')
root.append('window.__timelines["main"]=tl;</script></body></html>')
(ROOT / "index.html").write_text("\n".join(root))

print(f"Built {len(SCENES)} Higgs-field analogy frames in {NEW}")
