const app = window.HubApp;
const began = performance.now();
let readyAt = null;
let readyCount = 0;
app.on('graph-ready', () => {readyAt=performance.now(); readyCount++;});
app.go('graph', {focus:false});
while (!['3d','fallback'].includes(app.graphView.mode)) {
  if (performance.now()-began > 20000) throw new Error('graph-ready exceeded 20 seconds');
  await new Promise(r=>setTimeout(r,16));
}
await document.fonts.ready;
await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
const graph=app.graphView.instance;
const stage=document.getElementById('graph-stage');
if (args.scroll) stage.scrollIntoView();
const moves=[];
if (graph && args.trackCamera) {
  const original=graph.cameraPosition;
  graph.cameraPosition=function(...values) {
    if (values.length) moves.push({at:performance.now(),position:{...values[0]},aim:{...values[1]}});
    return original.apply(graph,values);
  };
}
function position() {return graph ? {x:graph.camera().position.x,y:graph.camera().position.y,z:graph.camera().position.z} : null;}
function coords() {return graph ? graph.graphData().nodes.map(n=>[n.id,n.x,n.y,n.z]) : [];}
const before=position();
const beforeCoords=coords();
const timeline=[];
let actionStarted=null;
if (graph && args.action) {
  const started=performance.now();
  actionStarted=started;
  if (args.action==='select') app.select({type:'record',id:args.id},stage);
  if (args.action==='fly') app.graphView.flyTo(args.id);
  if (args.action==='clear') app.clearSelection();
  if (args.action==='zoomIn') document.querySelectorAll('#graph-stage-buttons button')[0].click();
  if (args.action==='zoomOut') document.querySelectorAll('#graph-stage-buttons button')[1].click();
  if (args.action==='reset') document.querySelectorAll('#graph-stage-buttons button')[2].click();
  if (args.action==='tour') document.getElementById('graph-tour').click();
  if (args.action==='find') {
    document.getElementById('graph-find').value=args.id;
    document.getElementById('graph-find').closest('form').requestSubmit();
    document.querySelector('#graph-find-matches button').click();
  }
  if (args.action==='background') graph.onBackgroundClick()();
  for (const delay of (args.samples || [100,600,1200])) {
    await new Promise(r=>setTimeout(r,Math.max(0,started+delay-performance.now())));
    timeline.push({at:performance.now()-started,position:position(),aim:{...graph.controls().target},calls:moves.length});
  }
}
if (graph && args.nodeTip) {
  const node=graph.graphData().nodes.find(n=>n.record.title.includes('<script>')) || graph.graphData().nodes[0];
  graph.onNodeHover()(node);
}
if (graph && args.linkTip) graph.onLinkHover()(graph.graphData().links[0]);
if (args.wait) await new Promise(r=>setTimeout(r,args.wait));
function accessor(value,item) {return typeof value==='function' ? value(item) : value;}
const data=graph ? graph.graphData() : {nodes:[],links:[]};
const chips=Array.from(stage.querySelectorAll('[data-bridge-id]')).map(n=>({id:n.dataset.bridgeId,
  text:n.firstElementChild.textContent,status:n.querySelector('.hub-stage-chip-status').textContent,
  source:n.querySelector('a').getAttribute('href'),size:parseFloat(getComputedStyle(n).fontSize),hidden:n.hidden,
  x:n.getBoundingClientRect().x,y:n.getBoundingClientRect().y,width:n.getBoundingClientRect().width,height:n.getBoundingClientRect().height}));
const nodes=data.nodes.map(n=>{
  const shell=n.__threeObj?.children.find(c=>c.name==='hub-ink-shell');
  return {id:n.id,bridge:n.record.bridge,color:accessor(graph.nodeColor(),n),
    material:n.__threeObj?.material.color.getHexString(),hood:n.record.hood,
    source:n.record.source_link,shell:shell ? {color:shell.material.color.getHexString(),side:shell.material.side,
      scale:shell.scale.x,position:[shell.position.x,shell.position.y,shell.position.z]} : null};
});
const selectedNode=graph && app.state.selection?.type==='record'
  ? data.nodes.find(n=>n.id===app.state.selection.id) : null;
const selectedPoint=selectedNode ? graph.graph2ScreenCoords(selectedNode.x,selectedNode.y,selectedNode.z) : null;
const panelBox=document.getElementById('hub-panel').getBoundingClientRect();
const box=stage.getBoundingClientRect();
return {mode:app.graphView.mode,readyCount,readyMs:readyAt===null ? null : readyAt-began,
  role:stage.getAttribute('role'),aria:stage.getAttribute('aria-label'),tabindex:stage.getAttribute('tabindex'),
  class:stage.className,canvas:Boolean(stage.querySelector('canvas')),
  canvasTab:stage.querySelector('canvas')?.getAttribute('tabindex'),
  vendor:Array.from(document.scripts).map(n=>n.getAttribute('src')).filter(s=>s&&s.includes('3d-force-graph')),
  stageButtonsHidden:document.getElementById('graph-stage-buttons').hidden,
  buttons:Array.from(document.querySelectorAll('#graph-stage-buttons button')).map(n=>{
    const b=n.getBoundingClientRect();return {text:n.textContent,width:b.width,height:b.height};}),
  chips,nodes,links:data.links.map(l=>({color:accessor(graph.linkColor(),l),width:accessor(graph.linkWidth(),l),
    expected:l.pair.width,crosses:l.pair.crosses,label:l.pair.label})),
  particles:graph ? graph.linkDirectionalParticles() : null,
  nodeLabels:graph ? data.nodes.map(n=>accessor(graph.nodeLabel(),n)) : [],
  linkLabels:graph ? data.links.map(l=>accessor(graph.linkLabel(),l)) : [],
  position:position(),before,timeline,moves,actionStarted,beforeCoords,afterCoords:coords(),
  selected:app.state.selection,panelOpen:app.state.panelOpen,panel:document.getElementById('hub-panel').textContent,
  tooltip:document.getElementById('graph-tooltip')?.textContent || '',
  tooltipElements:document.getElementById('graph-tooltip')?.querySelectorAll('*').length || 0,
  selectedChip:{text:stage.querySelector('.hub-stage-chip--selected')?.textContent || '',
    hidden:stage.querySelector('.hub-stage-chip--selected')?.hidden ?? true,
    background:stage.querySelector('.hub-stage-chip--selected') ? getComputedStyle(stage.querySelector('.hub-stage-chip--selected')).backgroundColor : ''},
  stage:{x:box.x,y:box.y,width:box.width,height:box.height},selectedPoint,
  projected:data.nodes.map(n=>graph.graph2ScreenCoords(n.x,n.y,n.z)),
  panelBounds:{x:panelBox.x,y:panelBox.y,width:panelBox.width,height:panelBox.height},
  expectedNodes:app.data.graph.visible_records,expectedLinks:app.data.pairs.filter(p=>!p.weak).length,
  scrollWidth:document.documentElement.scrollWidth,width:innerWidth,
  fallback:document.getElementById('graph-fallback')?.textContent || '',
  listInStage:Boolean(stage.querySelector('#graph-list')),
  injected:typeof window.__pwned!=='undefined' || Boolean(stage.querySelector('img[onerror],svg[onload]')),
  unwantedControls:Array.from(document.querySelectorAll('button,input')).filter(n=>/^(pause|play|still|motion)$/i.test(n.textContent.trim())).length,
  duration:app.motion.ms('--mos-time-reframe')};
