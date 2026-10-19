from pathlib import Path
import html
import re

ROOT = Path(__file__).resolve().parents[1]
FRAMES = [
    ("01-hidden-opportunity", "The hidden opportunity", 0.000, 5.264,
     "kinetic-type-beats", "Some of the most valuable opportunities are hiding in research we already have.",
     "Hook: make the viewer's gain the first thing they see."),
    ("02-scattered-room", "The scattered room", 5.264, 7.693,
     "spatial-pan-stations", "But sources sit in separate files. Connections get missed. And one report rarely becomes a growing body of work.",
     "Problem: three research artifacts remain apart as the camera travels across them."),
    ("03-room-to-portfolio", "Mindrian's purpose", 12.957, 5.264,
     "kinetic-type-beats", "Mindrian is being built to turn a research room into an opportunity portfolio.",
     "Value: one room becomes a place to develop a portfolio, not just produce a single report."),
    ("04-frame-question", "Frame the question", 18.221, 4.859,
     "prompt-type-submit-generate", "Bring in the material. Set the question, constraints, and outcome that matter.",
     "Mechanism: user intent determines the work to do."),
    ("05-methods-fit", "Fit the method to the job", 23.080, 8.503,
     "grid-card-assemble", "The goal is to use methods that fit the job: map bottlenecks, explore connections, gather evidence, and challenge a promising lead.",
     "Mechanism: distinct method families appear as options, not a mandatory engine pipeline."),
    ("06-inspect-the-lead", "Inspect the lead", 31.583, 10.527,
     "transcript-scroll-artifact-reveal", "Each candidate can stay linked to its sources, with uncertainty and counterevidence visible. You decide what to investigate, what to test, and what to set aside.",
     "Trust: sources, evidence, uncertainty, and a human decision stay visible together."),
    ("07-compounding-portfolio", "The portfolio grows", 42.110, 5.669,
     "grid-card-assemble", "Then the room keeps the useful work: evidence, open questions, decisions, and next experiments.",
     "Outcome: useful work accumulates in a portfolio."),
    ("08-next-question", "The next question", 47.779, 11.318,
     "kinetic-type-beats", "So each new question starts from what you've already learned. Mindrian helps turn scattered research into opportunities people can revisit, deepen, and act on.",
     "Close: the compounding effect is the lasting value."),
]

THEO_POSES = {
    "rest": ([312,120,52,52],[312,300,52,52],[110,205,18,250,36],[236,225],"white","ink","ink",False),
    "t_search": ([262,100,44,44],[340,320,44,44],[300,205,30,250,36],[214,225],"blue","ink","ink",False),
    "t_found": ([312,120,52,52],[312,300,52,52],[110,205,0,250,36],[236,225],"blue","ink","ink",False),
    "t_listen": ([300,120,68,68],[300,300,68,68],[110,205,10,250,36],[236,225],"white","ink","ink",False),
    "challenge": ([312,120,52,52],[312,312,52,14],[110,205,-32,262,36],[236,190],"red","ink","ink",False),
    "decision": ([312,120,52,52],[312,300,52,52],[110,205,0,250,36],[236,225],"ink","ink","ink",False),
    "t_handover": ([312,120,52,52],[312,300,52,52],[96,205,18,250,36],[236,225],"white","white","white",True),
}
THEO_FRAME_POSES = {"01-hidden-opportunity":"rest", "02-scattered-room":"t_search", "03-room-to-portfolio":"t_found", "04-frame-question":"t_listen", "05-methods-fit":"t_search", "06-inspect-the-lead":"challenge", "07-compounding-portfolio":"decision", "08-next-question":"t_handover"}
THEO_LAYOUT = {
    "01-hidden-opportunity":"right:100px;top:245px;width:360px",
    "02-scattered-room":"right:112px;top:76px;width:172px",
    "03-room-to-portfolio":"right:112px;top:75px;width:172px",
    "04-frame-question":"left:155px;right:auto;top:655px;width:150px",
    "05-methods-fit":"right:112px;top:76px;width:172px",
    "06-inspect-the-lead":"right:110px;top:72px;width:176px",
    "07-compounding-portfolio":"right:110px;top:72px;width:176px",
    "08-next-question":"right:150px;top:350px;width:270px",
}

def stage_pose(name):
    e1,e2,slash,rule,_plane,c1,c2,hollow = THEO_POSES[name]
    # FaceStill's stage face uses a white plane and turns paper eyes to ink.
    return e1,e2,slash,rule,"white",("ink" if c1 == "paper" else c1),("ink" if c2 == "paper" else c2),hollow

def theo_svg(start_name,target_name):
    e1,e2,(sx,sy,sa,sl,st),(rx,ry),_plane,c1,c2,hollow = stage_pose(start_name)
    colours={"ink":"#111111","paper":"#F7F5EE","white":"#FFFFFF","blue":"#1F3FBF","red":"#D6281F","yellow":"#F2C200","soft":"#4B4943"}
    def eye(e,c,cls):
        x,y,w,h=e; x-=w/2; y-=h/2
        attrs=f'class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}" fill="{colours["white"] if hollow else colours[c]}"'
        if hollow: attrs += ' stroke="#111111" stroke-width="8"'
        return f'<rect {attrs}/>'
    slash_fill=colours["white"] if hollow else colours["ink"]
    slash_outline=' stroke="#111111" stroke-width="8"' if hollow else ''
    state_label={"rest":"at rest","t_search":"searching","t_found":"found","t_listen":"listening","challenge":"challenging","decision":"holding for your decision","t_handover":"handing over"}[target_name]
    svg=(f'<svg class="theo-face" viewBox="0 0 400 400" role="img" aria-label="Theo, {state_label}" data-face-pose="{target_name}">'
      f'<rect width="400" height="400" fill="#F7F5EE"/><rect class="face-plane" x="{rx+7}" y="14" width="{max(0,379-rx)}" height="{max(0,ry-21)}" fill="#FFFFFF"/>'
      f'<rect class="face-v-rule" x="{rx-7}" y="14" width="14" height="372" fill="#111111"/><rect class="face-h-rule" x="{rx}" y="{ry-7}" width="{max(0,386-rx)}" height="14" fill="#111111"/>'
      f'<g class="face-slash" transform="translate({sx} {sy}) rotate({sa})"><rect x="{-st/2}" y="{-sl/2}" width="{st}" height="{sl}" fill="{slash_fill}"{slash_outline}/></g>'
      f'{eye(e1,c1,"face-eye-1")}{eye(e2,c2,"face-eye-2")}<rect x="7" y="7" width="386" height="386" fill="none" stroke="#111111" stroke-width="14"/></svg>')
    return svg

def pose_timeline(start_name,target_name):
    a=stage_pose(start_name); b=stage_pose(target_name)
    ae1,ae2,aslash,arule,*_=a; be1,be2,bslash,brule,*_,bhollow=b
    sx,sy,sa,sl,st=bslash; rx,ry=brule
    c1=("ink" if b[5] == "paper" else b[5]); c2=("ink" if b[6] == "paper" else b[6])
    colours={"ink":"#111111","paper":"#F7F5EE","white":"#FFFFFF","blue":"#1F3FBF","red":"#D6281F","yellow":"#F2C200","soft":"#4B4943"}
    def eye_attrs(e,c):
        x,y,w,h=e
        attrs={"x":x-w/2,"y":y-h/2,"width":w,"height":h,"fill":(colours["white"] if bhollow else colours[c]),"stroke":("#111111" if bhollow else "none"),"stroke-width":(8 if bhollow else 0)}
        return attrs
    plane={"x":rx+7,"y":14,"width":max(0,379-rx),"height":max(0,ry-21)}
    vrule={"x":rx-7,"y":14,"width":14,"height":372}
    hrule={"x":rx,"y":ry-7,"width":max(0,386-rx),"height":14}
    slash="translate(%s %s) rotate(%s)"%(sx,sy,sa)
    delay=.75
    return (f'tl.to(".face-plane",{{attr:{plane},duration:.62,ease:"power2.inOut"}},{delay});'
      f'tl.to(".face-v-rule",{{attr:{vrule},duration:.62,ease:"power2.inOut"}},{delay});'
      f'tl.to(".face-h-rule",{{attr:{hrule},duration:.62,ease:"power2.inOut"}},{delay});'
      f'tl.to(".face-slash",{{attr:{{transform:"{slash}"}},duration:.72,ease:"power2.inOut"}},{delay});'
      f'tl.to(".face-eye-1",{{attr:{eye_attrs(be1,c1)},duration:.62,ease:"power2.inOut"}},{delay});'
      f'tl.to(".face-eye-2",{{attr:{eye_attrs(be2,c2)},duration:.62,ease:"power2.inOut"}},{delay});')

BASE = r'''<style>
:root{--bg:#F7F5EE;--fg:#111111;--accent:#1F3FBF;--muted:#4B4943;--surface:#FFFFFF;--rule:#111111;--warm:#D6281F}
@font-face{font-family:Figtree;src:url(../../assets/fonts/figtree.woff2) format("woff2");font-weight:400 900;font-display:block}
@font-face{font-family:DM Sans;src:url(../../assets/fonts/dm-sans-latin.woff2) format("woff2");font-weight:400 1000;font-display:block}
@font-face{font-family:JetBrains Mono;src:url(../../assets/fonts/jetbrains-mono.ttf) format("truetype");font-weight:400;font-display:block}
#root{position:absolute;inset:0;width:100%;height:100%;overflow:hidden;background:var(--bg);color:var(--fg);font-family:Figtree,DM Sans,Arial,sans-serif}
*{box-sizing:border-box}
.mono{font-family:"JetBrains Mono",monospace;font-weight:400;letter-spacing:.06em}
.kicker{font-size:22px;color:var(--muted);text-transform:uppercase;letter-spacing:.12em}
.head{font-size:90px;line-height:1.03;font-weight:900;letter-spacing:-.055em}
.body{font-size:34px;line-height:1.3;font-weight:400;color:var(--fg)}
.small{font-size:22px;line-height:1.35;color:var(--muted)}
.rule{height:2px;background:var(--rule)}
.folio{position:absolute;left:96px;top:68px;font-size:20px;color:var(--muted)}
.page-no{position:absolute;right:96px;bottom:68px;font-size:20px;color:var(--fg)}
.eyebrow{font-size:20px;color:var(--accent);letter-spacing:.13em;text-transform:uppercase}
.card{background:var(--surface);border:2px solid var(--rule);border-radius:0;box-shadow:none}
.pill{display:inline-flex;align-items:center;border:2px solid var(--rule);padding:11px 16px;font-size:18px;color:var(--muted);border-radius:0}
.accent{color:var(--accent)}
</style>'''

SCENES = {
"01-hidden-opportunity": (r'''<div class="folio mono">MINDRIAN / OPPORTUNITY DISCOVERY</div>
<div class="copy"><div class="eyebrow mono">A useful connection may be closer than it looks</div><div class="hero"><span>THE NEXT</span><span class="accent">OPPORTUNITY</span></div><div class="sub body">may already be in your research.</div><div class="underline"></div></div><div class="page-no mono">01 / 08</div>''', r'''
.source{position:absolute;border:2px solid var(--rule);padding:20px 24px;background:#FFFFFF;color:var(--muted);font-size:21px;box-shadow:none}
.copy{position:absolute;left:125px;top:215px;width:980px;z-index:2}.hero{font-size:104px;line-height:.98;font-weight:900;letter-spacing:-.065em;margin-top:38px}.hero span{display:block}.sub{margin-top:30px}.underline{width:780px;height:7px;background:var(--accent);transform-origin:left;margin-top:36px}
''', r'''
tl.fromTo(".copy",{y:42,opacity:0},{y:0,opacity:1,duration:.8,ease:"power3.out"},.18);
tl.fromTo(".underline",{scaleX:0},{scaleX:1,duration:.65,ease:"power2.out"},1.5);
'''),
"02-scattered-room": (r'''<div class="folio mono">WHY OPPORTUNITIES GET MISSED</div>
<div class="headline"><span class="eyebrow mono">The material exists.</span><span class="head">The links are</span><span class="head accent">still missing.</span></div>
<div class="viewport"><div class="world" data-layout-allow-overflow>
<div class="station s1 card"><div class="mono eyebrow">SOURCE A · PAPER</div><div class="body">A result with a useful mechanism</div><div class="bottom mono">REFERENCE · 01</div></div>
<div class="station s2 card"><div class="mono eyebrow">SOURCE B · DISCLOSURE</div><div class="body">A different problem with a related constraint</div><div class="bottom mono">REFERENCE · 02</div></div>
<div class="station s3 card"><div class="mono eyebrow">SOURCE C · NOTES</div><div class="body">A question that still needs an answer</div><div class="bottom mono">OPEN QUESTION</div></div>
<svg class="broken" width="2200" height="210" viewBox="0 0 2200 210" aria-hidden="true"><path d="M120 105 H650 M740 105 H1320 M1410 105 H2070" stroke="#1F3FBF" stroke-width="4" stroke-dasharray="12 18" fill="none"/><rect x="678" y="93" width="24" height="24" fill="#F7F5EE" stroke="#1F3FBF" stroke-width="4"/><rect x="1348" y="93" width="24" height="24" fill="#F7F5EE" stroke="#1F3FBF" stroke-width="4"/></svg>
</div></div><div class="page-no mono">02 / 08</div>''', r'''
.headline{position:absolute;left:160px;top:155px;z-index:2}.head{font-size:76px;display:block;margin-top:14px}.viewport{position:absolute;left:0;right:0;bottom:80px;height:540px;overflow:hidden}.world{position:absolute;left:0;top:0;width:3000px;height:540px}.station{position:absolute;top:120px;width:590px;height:290px;padding:34px 40px}.station .body{margin-top:34px;max-width:510px;font-size:32px}.bottom{position:absolute;bottom:24px;right:30px;color:var(--muted);font-size:18px}.s1{left:170px}.s2{left:1050px}.s3{left:1930px}.broken{position:absolute;left:190px;top:330px;opacity:.85}
''', r'''
tl.fromTo(".headline",{x:-24,opacity:0},{x:0,opacity:1,duration:.6,ease:"power3.out"},.12);
tl.fromTo(".world",{x:300},{x:-1040,duration:5.5,ease:"power2.inOut"},.45);
tl.fromTo(".station",{y:35,opacity:0},{y:0,opacity:1,duration:.48,stagger:.45,ease:"power3.out"},.8);
tl.fromTo(".broken",{opacity:.2},{opacity:.85,duration:1.2,ease:"sine.inOut"},1.1);
'''),
"03-room-to-portfolio": (r'''<div class="folio mono">THE PRODUCT GOAL</div>
<div class="world" data-layout-allow-overflow>
<div class="focus-card card"><div class="mono eyebrow">ONE ROOM</div><div class="body">Sources, questions, and context</div><div class="mini-sources"><span>paper</span><span>disclosure</span><span>notes</span></div></div>
<div class="bridge"></div><div class="portfolio card"><div class="mono eyebrow">A GROWING PORTFOLIO</div><div class="portfolio-row"><i></i><span>Opportunity to investigate</span></div><div class="portfolio-row"><i></i><span>Evidence to gather</span></div><div class="portfolio-row"><i></i><span>Next experiment</span></div></div>
<div class="headline"><span class="head">FROM A ROOM</span><span class="head accent">TO A PORTFOLIO</span></div>
<div class="stamp mono">INTENDED WORKFLOW</div>
</div><div class="page-no mono">03 / 08</div>''', r'''
.world{position:absolute;inset:0;transform-origin:50% 51%;}.focus-card{position:absolute;left:205px;top:350px;width:500px;height:260px;padding:34px}.focus-card .body{margin-top:24px;font-size:31px}.mini-sources{display:flex;gap:14px;margin-top:24px}.mini-sources span{border:2px solid var(--rule);padding:10px 16px;color:var(--muted);font:18px "JetBrains Mono",monospace}.bridge{position:absolute;left:706px;top:477px;width:280px;height:4px;background:var(--accent);transform-origin:left}.portfolio{position:absolute;right:190px;top:302px;width:660px;padding:32px 38px}.portfolio-row{display:flex;align-items:center;gap:18px;margin-top:24px;font-size:27px}.portfolio-row i{width:16px;height:16px;background:var(--accent);display:block;border-radius:0}.headline{position:absolute;left:205px;top:130px}.headline .head{display:block;font-size:77px;margin-top:12px}.stamp{position:absolute;right:190px;bottom:128px;color:var(--warm);font-size:19px;border:2px solid var(--warm);padding:12px 18px}
''', r'''
tl.fromTo(".world",{scale:1.48},{scale:1,duration:1.55,ease:"expo.out"},.1);
tl.fromTo(".headline",{y:26,opacity:0},{y:0,opacity:1,duration:.58,ease:"power3.out"},1.15);
tl.fromTo(".focus-card",{y:18,opacity:0},{y:0,opacity:1,duration:.52,ease:"power3.out"},1.48);
tl.fromTo(".bridge",{scaleX:0},{scaleX:1,duration:.52,ease:"power2.out"},1.8);
tl.fromTo(".portfolio",{x:35,opacity:0},{x:0,opacity:1,duration:.58,ease:"power3.out"},2.0);
tl.fromTo(".portfolio-row",{x:-20,opacity:0},{x:0,opacity:1,duration:.32,stagger:.14,ease:"power2.out"},2.45);
tl.fromTo(".stamp",{opacity:0},{opacity:1,duration:.3},3.2);
'''),
"04-frame-question": (r'''<div class="folio mono">START WITH THE DECISION</div>
<div class="left"><div class="eyebrow mono">User-defined frame</div><div class="head">A sharper<br><span class="accent">question.</span></div><div class="body intro">The room is context.<br>The objective sets direction.</div></div>
<div class="brief card"><div class="brief-head mono"><span>RESEARCH BRIEF</span><span class="status">READY TO EXPLORE</span></div>
<div class="field"><div class="mono label">OBJECTIVE</div><div class="value">What needs to change?</div></div>
<div class="field"><div class="mono label">CONSTRAINTS</div><div class="value">What is fixed? What is assumed?</div></div>
<div class="field"><div class="mono label">SUCCESS</div><div class="value">What would a useful result enable?</div></div>
<div class="submit mono"><span>FRAME THE QUESTION</span><span class="arrow">→</span></div></div><div class="page-no mono">04 / 08</div>''', r'''
.left{position:absolute;left:150px;top:235px;width:700px}.left .head{font-size:92px;margin-top:28px}.intro{margin-top:32px;color:var(--muted)}.brief{position:absolute;right:160px;top:180px;width:730px;padding:30px 40px 22px}.brief-head{display:flex;justify-content:space-between;align-items:center;color:var(--muted);font-size:19px;padding-bottom:22px;border-bottom:2px solid var(--rule)}.status{color:var(--accent)}.field{padding:23px 0;border-bottom:2px solid var(--rule)}.label{font-size:18px;color:var(--muted);margin-bottom:9px}.value{font-size:29px}.submit{display:flex;justify-content:space-between;margin-top:24px;color:var(--accent);font-size:20px}.arrow{font-size:30px}
''', r'''
tl.fromTo(".left",{x:-28,opacity:0},{x:0,opacity:1,duration:.56,ease:"power3.out"},.12);
tl.fromTo(".brief",{x:42,opacity:0},{x:0,opacity:1,duration:.62,ease:"power3.out"},.3);
tl.fromTo(".field",{y:16,opacity:0},{y:0,opacity:1,duration:.34,stagger:.22,ease:"power2.out"},.8);
tl.fromTo(".status",{opacity:.35},{opacity:1,duration:.4,repeat:2,yoyo:true,ease:"sine.inOut"},1.8);
tl.fromTo(".arrow",{x:-8},{x:0,duration:.4,repeat:2,yoyo:true,ease:"sine.inOut"},2.05);
'''),
"05-methods-fit": (r'''<div class="folio mono">METHODS ARE CHOSEN FOR THE JOB</div>
<div class="heading"><div class="eyebrow mono">Different questions need different lenses</div><div class="head">FIT THE METHOD<br><span class="accent">TO THE JOB</span></div></div>
<div class="method-grid">
<div class="method-card"><span class="num mono">01</span><div><div class="method-title">Map bottlenecks</div><div class="method-sub">Where does progress get stuck?</div></div><span class="mark">↗</span></div>
<div class="method-card"><span class="num mono">02</span><div><div class="method-title">Explore connections</div><div class="method-sub">What mechanisms might transfer?</div></div><span class="mark">⟷</span></div>
<div class="method-card"><span class="num mono">03</span><div><div class="method-title">Gather evidence</div><div class="method-sub">What supports or weakens the lead?</div></div><span class="mark">⌕</span></div>
<div class="method-card"><span class="num mono">04</span><div><div class="method-title">Challenge the idea</div><div class="method-sub">Which assumptions could fail?</div></div><span class="mark">?</span></div>
</div><div class="concept mono">METHOD FAMILIES · ILLUSTRATIVE, NOT ENGINE NAMES</div><div class="page-no mono">05 / 08</div>''', r'''
.heading{position:absolute;left:145px;top:150px}.heading .head{font-size:75px;line-height:1.02;margin-top:18px}.method-grid{position:absolute;left:145px;right:145px;bottom:160px;display:grid;grid-template-columns:1fr 1fr;gap:20px}.method-card{height:132px;border:2px solid var(--rule);background:var(--surface);display:flex;align-items:center;padding:24px 28px;gap:22px;position:relative}.num{font-size:20px;color:var(--accent);align-self:flex-start}.method-title{font-size:29px;font-weight:700}.method-sub{font-size:22px;color:var(--muted);margin-top:7px}.mark{font-size:38px;color:var(--accent);margin-left:auto}.concept{position:absolute;left:145px;bottom:94px;color:var(--muted);font-size:18px}
''', r'''
tl.fromTo(".heading",{y:24,opacity:0},{y:0,opacity:1,duration:.58,ease:"power3.out"},.1);
tl.fromTo(".method-card",{y:42,opacity:0},{y:0,opacity:1,duration:.48,stagger:.26,ease:"power3.out"},.9);
tl.fromTo(".mark",{scale:.7,opacity:.3},{scale:1,opacity:1,duration:.35,stagger:.26,ease:"back.out(1.35)"},1.3);
tl.fromTo(".concept",{opacity:0},{opacity:1,duration:.35},3.25);
'''),
"06-inspect-the-lead": (r'''<div class="folio mono">A LEAD IS A HYPOTHESIS</div>
<div class="header"><div class="eyebrow mono">Inspect before you invest</div><div class="head">Keep the trail visible.</div></div>
<div class="source-stack"><div class="source-sheet sheet-one"><div class="mono label">SOURCE A · TRACEABLE</div><div class="line wide"></div><div class="line"></div><div class="line short"></div></div><div class="source-sheet sheet-two"><div class="mono label">SOURCE B · TRACEABLE</div><div class="line wide"></div><div class="line short"></div><div class="line"></div></div></div>
<div class="link-line"></div>
<div class="candidate card"><div class="candidate-top mono"><span>OPPORTUNITY HYPOTHESIS</span><span class="tag">REVIEW</span></div><div class="candidate-name">A possible connection<br>worth investigating</div><div class="candidate-foot mono">NOT A CONCLUSION · EVIDENCE REQUIRED</div></div>
<div class="evidence"><div class="evidence-row"><span class="dot good"></span><div><div class="mono label">SUPPORTING EVIDENCE</div><div class="ev-copy">Source-backed observations</div></div><span class="plus">+</span></div><div class="evidence-row"><span class="dot open"></span><div><div class="mono label">COUNTEREVIDENCE</div><div class="ev-copy">Conflicts and limitations</div></div><span class="plus">±</span></div><div class="evidence-row"><span class="dot open"></span><div><div class="mono label">OPEN QUESTIONS</div><div class="ev-copy">What still needs checking?</div></div><span class="plus">?</span></div></div>
<div class="decisions mono"><span>INVESTIGATE</span><span>TEST</span><span>SET ASIDE</span></div><div class="page-no mono">06 / 08</div>''', r'''
.header{position:absolute;left:150px;top:145px}.header .head{font-size:66px;margin-top:18px}.source-stack{position:absolute;left:145px;top:365px;width:450px;height:285px}.source-sheet{position:absolute;width:400px;height:195px;background:#FFFFFF;color:#111111;padding:25px 28px;box-shadow:none}.sheet-one{top:0;left:0;transform:rotate(-4deg)}.sheet-two{top:64px;left:38px;transform:rotate(3deg);background:#E9EBF7}.source-sheet .label{font-size:18px;color:#4B4943}.line{height:7px;background:#111111;opacity:.7;width:74%;margin-top:18px}.line.wide{width:92%}.line.short{width:53%}.link-line{position:absolute;left:568px;top:490px;width:165px;height:3px;background:var(--accent);transform-origin:left}.candidate{position:absolute;left:720px;top:350px;width:540px;height:315px;padding:28px 32px}.candidate-top{display:flex;justify-content:space-between;color:var(--muted);font-size:17px}.tag{color:var(--accent);border:2px solid var(--accent);padding:7px 10px}.candidate-name{font-size:37px;font-weight:700;line-height:1.18;margin-top:38px}.candidate-foot{position:absolute;left:32px;bottom:26px;color:var(--warm);font-size:16px}.evidence{position:absolute;right:130px;top:335px;width:420px}.evidence-row{height:105px;border-bottom:2px solid var(--rule);display:flex;align-items:center;gap:14px}.dot{width:15px;height:15px;border:3px solid var(--accent);border-radius:0;flex:none}.dot.open{border-color:var(--warm)}.label{font-size:16px;color:var(--muted)}.ev-copy{font-size:21px;margin-top:7px}.plus{margin-left:auto;color:var(--accent);font:24px "JetBrains Mono",monospace}.decisions{position:absolute;left:720px;bottom:150px;display:flex;gap:12px}.decisions span{padding:14px 17px;border:2px solid var(--rule);font-size:17px;color:var(--muted)}.decisions span:first-child{border-color:var(--accent);color:var(--accent)}
''', r'''
tl.fromTo(".header",{y:22,opacity:0},{y:0,opacity:1,duration:.5,ease:"power3.out"},.1);
tl.fromTo(".sheet-one",{x:-35,opacity:0,rotation:0},{x:0,opacity:1,rotation:-4,duration:.55,ease:"power3.out"},.55);
tl.fromTo(".sheet-two",{x:-35,opacity:0,rotation:0},{x:0,opacity:1,rotation:3,duration:.55,ease:"power3.out"},.82);
tl.fromTo(".candidate",{y:28,opacity:0},{y:0,opacity:1,duration:.58,ease:"power3.out"},1.15);
tl.fromTo(".link-line",{scaleX:0},{scaleX:1,duration:.42,ease:"power2.out"},1.45);
tl.fromTo(".evidence-row",{x:28,opacity:0},{x:0,opacity:1,duration:.38,stagger:.18,ease:"power2.out"},1.5);
tl.fromTo(".decisions span",{y:18,opacity:0},{y:0,opacity:1,duration:.32,stagger:.12,ease:"power2.out"},3.1);
'''),
"07-compounding-portfolio": (r'''<div class="folio mono">THE ROOM REMEMBERS USEFUL WORK</div>
<div class="title"><div class="eyebrow mono">Keep what earns another look</div><div class="head">A portfolio, not a one-off.</div></div>
<div class="portfolio-grid">
<div class="op-card card"><div class="mono card-head">OPPORTUNITY · A</div><div class="op-title">Evidence to gather</div><div class="op-state">INVESTIGATE</div><div class="trace"><i></i><i></i><i></i></div></div>
<div class="op-card card featured"><div class="mono card-head">OPPORTUNITY · B</div><div class="op-title">A connection to test</div><div class="op-state accent">NEXT EXPERIMENT</div><div class="trace"><i></i><i></i><i></i><i></i></div></div>
<div class="op-card card parked"><div class="mono card-head">OPPORTUNITY · C</div><div class="op-title">A lead to revisit</div><div class="op-state">PARKED · REASON RECORDED</div><div class="trace"><i></i><i></i></div></div>
</div><div class="concept mono">ILLUSTRATIVE PORTFOLIO · NOT LIVE ROOM DATA</div><div class="page-no mono">07 / 08</div>''', r'''
.title{position:absolute;left:145px;top:165px}.title .head{font-size:67px;margin-top:18px}.portfolio-grid{position:absolute;left:145px;right:145px;bottom:190px;display:grid;grid-template-columns:1fr 1.1fr 1fr;gap:20px;align-items:end}.op-card{position:relative;height:270px;padding:26px 28px}.featured{height:325px;border-color:var(--accent);background:#E9EBF7}.parked{opacity:.82}.card-head{font-size:17px;color:var(--muted)}.op-title{font-size:30px;font-weight:700;line-height:1.18;margin-top:36px}.op-state{position:absolute;left:28px;bottom:58px;font:17px "JetBrains Mono",monospace;color:var(--muted)}.trace{position:absolute;left:28px;bottom:24px;display:flex;gap:8px}.trace i{display:block;width:42px;height:5px;background:var(--accent);opacity:.85}.parked .trace i{background:var(--rule)}.concept{position:absolute;left:145px;bottom:106px;color:var(--muted);font-size:18px}
''', r'''
tl.fromTo(".title",{y:24,opacity:0},{y:0,opacity:1,duration:.5,ease:"power3.out"},.1);
tl.fromTo(".op-card",{y:58,opacity:0,scale:.97},{y:0,opacity:1,scale:1,duration:.58,stagger:.25,ease:"power3.out"},.72);
tl.fromTo(".trace i",{scaleX:0},{scaleX:1,duration:.28,stagger:.08,ease:"power2.out"},1.7);
tl.fromTo(".concept",{opacity:0},{opacity:1,duration:.35},3.2);
'''),
"08-next-question": (r'''<div class="folio mono">MINDRIANOS · OPPORTUNITY DISCOVERY</div>
<div class="close-copy"><div class="eyebrow mono">What you learn stays useful.</div><div class="brand">Mindrian<span class="accent">OS</span></div><div class="ruleline"></div><div class="sub body">Turn scattered research into<br>opportunities you can develop.</div></div>
<div class="orbit o1" data-layout-allow-overflow></div><div class="orbit o2" data-layout-allow-overflow></div><div class="orbit o3" data-layout-allow-overflow></div><div class="page-no mono">A GROWING OPPORTUNITY PORTFOLIO</div>''', r'''
.close-copy{position:absolute;left:185px;top:270px;width:1420px}.close-copy .eyebrow{font-size:23px}.brand{font-size:142px;font-weight:900;letter-spacing:-.07em;margin-top:44px}.ruleline{width:900px;height:6px;background:var(--accent);margin:35px 0 28px;transform-origin:left}.sub{font-size:36px}.orbit{position:absolute;border:2px solid #E9EBF7;border-radius:0;opacity:.4}.o1{width:500px;height:500px;right:-120px;top:115px}.o2{width:370px;height:370px;right:-56px;top:180px;border-style:dashed}.o3{width:240px;height:240px;right:10px;top:245px;border-color:var(--accent);opacity:.25}
''', r'''
tl.fromTo(".close-copy",{y:36,opacity:0},{y:0,opacity:1,duration:.75,ease:"power3.out"},.15);
tl.fromTo(".ruleline",{scaleX:0},{scaleX:1,duration:.65,ease:"power2.out"},1.0);
tl.fromTo(".orbit",{rotation:-14,scale:.92},{rotation:0,scale:1,duration:2.3,stagger:.18,ease:"power2.out"},.3);
tl.to(".orbit",{rotation:7,duration:5.5,repeat:0,ease:"sine.inOut"},3.0);
'''),
}

main_children=[]
previous_pose = "rest"
for i,(slug,title,start,duration,blueprint,vo,role) in enumerate(FRAMES,1):
    cid=f"s{i:02d}"
    src=f"compositions/frames/{slug}.html"
    main_children.append(f'''<div id="{cid}-host" class="clip" data-composition-id="{cid}" data-composition-src="{src}" data-start="{start:.3f}" data-duration="{duration:.3f}" data-track-index="{i-1}" data-width="1920" data-height="1080"></div>''')
    markup,css,timeline=SCENES[slug]
    if slug == "01-hidden-opportunity":
        markup = re.sub(r'<div class="source chip mono c[123]">.*?</div>', '', markup)
    pose = THEO_FRAME_POSES[slug]
    pose_label={"rest":"RESTING","t_search":"SEARCHING","t_found":"FOUND","t_listen":"LISTENING","challenge":"CHALLENGING","decision":"YOUR DECISION","t_handover":"HANDING OVER"}[pose]
    theo = f'<div class="theo-outside" style="{THEO_LAYOUT[slug]}"><div class="theo-label">THEO · {pose_label}</div>{theo_svg(previous_pose,pose)}</div>'
    markup = markup.replace('<div class="page-no mono">', theo + '<div class="page-no mono">')
    css += '.theo-outside{position:absolute;z-index:5}.theo-label{font:15px "JetBrains Mono",monospace;letter-spacing:.08em;color:var(--fg);margin-bottom:10px}.theo-face{display:block;width:100%;height:auto}'
    timeline = 'tl.fromTo(".theo-outside",{opacity:0},{opacity:1,duration:.26,ease:"power1.out"},.25);' + pose_timeline(previous_pose,pose) + timeline
    previous_pose = pose
    (ROOT/src).write_text(f'''<!doctype html><html lang="en"><head><meta charset="UTF-8"><title>{html.escape(title)}</title></head><body><template>{BASE.replace("#root", f"#{cid}-root")}<style>{css}</style><div id="{cid}-root" data-composition-id="{cid}" data-width="1920" data-height="1080" data-duration="{duration:.3f}">{markup}</div><script>const tl=gsap.timeline({{paused:true}});{timeline}window.__timelines["{cid}"]=tl;</script></template></body></html>''')

main='''<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8" />

<meta name="viewport" content="width=1920, height=1080" />
<title>MindrianOS — Opportunity Discovery</title>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>*{margin:0;padding:0;box-sizing:border-box}html,body{width:1920px;height:1080px;overflow:hidden;background:#F7F5EE}#root{position:relative;width:100%;height:100%;overflow:hidden;background:#F7F5EE}.clip{position:absolute;inset:0;opacity:0}</style>
</head><body>
<div id="root" data-composition-id="main" data-start="0" data-duration="59.097" data-width="1920" data-height="1080">
'''+"\n".join(main_children)+'''
<audio id="narration" src="assets/audio/narration.mp3" data-start="0" data-duration="57.496" data-track-index="8" data-audio-group="voiceover"></audio>
</div><script>
const tl=gsap.timeline({paused:true});
'''+"\n".join(f'tl.fromTo("#s{i:02d}-host",{{opacity:0}},{{opacity:1,duration:.22,ease:"power1.out"}},{start:.3f});' for i,(_,_,start,_,_,_,_) in enumerate(FRAMES,1))+'''
window.__timelines["main"]=tl;
</script></body></html>
'''
(ROOT/'index.html').write_text(main)

# Update the storyboard source to the composition's actual timeline and source files.
lines=["---","format: 1920x1080","duration: 59.097s","message: \"Mindrian turns scattered research into an opportunity portfolio people can revisit, deepen, and act on.\"","arc: \"Scattered research → framed question → purpose-fit methods → evidence-linked leads → compounding portfolio\"","audience: \"People exploring MindrianOS, research teams, and technology-transfer practitioners\"","mode: autonomous","---","","# Story direction","","This video tells people exploring MindrianOS that Mindrian is being built to turn scattered research into an opportunity portfolio they can revisit, deepen, and act on.","","Theo stays outside the problem space as its thinker. The actual Theo face system moves through rest, search, finding, listening, challenge, decision, and handover poses. Inside the space, paper planes and square tiles carry the work: source material, evidence, assumptions, contradictions, and the human decision gate. The storyboard is an illustrative product vision; no fabricated opportunity, score, customer, or live-room data is shown.",""]
for i,(slug,title,start,duration,blueprint,vo,role) in enumerate(FRAMES,1):
    end=start+duration
    lines += [f"## Frame {i} — {title}",f"- status: animated",f"- duration: {duration:.3f}s",f"- poster: {min(duration*.48,duration-.2):.2f}s",f"- transition_in: cut",f"- scene: {role}",f"- voiceover: \"{vo}\"",f"- src: compositions/frames/{slug}.html",f"- blueprint: {blueprint}",f"- start: {start:.3f}s",f"- end: {end:.3f}s", ""]
    lines += ["The scene uses the v5 Theo face system as an outside thinker, with geometric planes and square tiles carrying the work. The on-screen material is illustrative; source text is not presented as real JHTV evidence.",""]
(ROOT/'STORYBOARD.md').write_text("\n".join(lines))
print(f"Generated {len(FRAMES)} scenes, {sum(x[3] for x in FRAMES):.3f}s of scene time, with 1.6s final hold..")
