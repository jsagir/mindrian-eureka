const app=window.HubApp;
if(args.view) app.go(args.view,{focus:false});
if(args.view==='graph' && app.data.graph.earned) {
  const deadline=performance.now()+20000;
  while(!['3d','fallback'].includes(app.graphView.mode)) {
    if(performance.now()>deadline) throw new Error('Review graph deadline exceeded');
    await new Promise(r=>setTimeout(r,16));
  }
}
if(args.panel) {
  if(args.panel==='record') app.select({type:'record',id:app.data.records[0].id});
  else app.select({type:'pair',key:app.data.pairs[0].key});
}
if(args.clear) app.clearSelection();
if(args.full) {
  const full=document.querySelector('.hub-panel-full');
  if(full) full.open=true;
}
await document.fonts.ready;
await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
if(args.scroll==='results') document.getElementById('hub-results').scrollIntoView();
if(args.scroll==='stage') document.getElementById('graph-stage').scrollIntoView();
if(args.scroll==='top') window.scrollTo(0,0);
if(args.opener) {
  app.select({type:'record',id:app.data.records[0].id},document.getElementById('graph-stage'));
  document.getElementById('hub-panel-close').click();
}
const hiddenFocusable=Array.from(document.querySelectorAll('[aria-hidden="true"] a[href],[aria-hidden="true"] button,[aria-hidden="true"] input,[aria-hidden="true"] [tabindex]')).filter(n=>n.tabIndex>=0&&n.getClientRects().length).map(n=>n.tagName);
const targets=[];
for(const node of document.querySelectorAll('button,input,select,summary,#hub-nav a')) {
  const box=node.getBoundingClientRect();
  if(box.width&&box.height&&(box.width<43.9||box.height<43.9)) targets.push({tag:node.tagName,id:node.id,width:box.width,height:box.height});
}
const controls=Array.from(document.querySelectorAll('#hub-nav a,.hub-button,.hub-field')).filter(n=>n.getClientRects().length).map(n=>({tag:n.tagName,name:n.textContent||n.getAttribute('aria-label')||n.id}));
const sourceGroups=Array.from(document.querySelectorAll('#hub-panel .hub-source-prose'));
const sourceRecord=app.state.selection?.type==='record' ? app.index.records.get(app.state.selection.id) : null;
const scene=document.querySelector(".hub-graph-scene")?.getBoundingClientRect();
const stage=document.getElementById("graph-stage")?.getBoundingClientRect();
const headerHeight=document.getElementById('hub-header')?.offsetHeight ?? null;
return {headerHeight,scene:scene ? {x:scene.x,width:scene.width}:null,stage:stage ? {height:stage.height}:null,sourceJoined:sourceGroups.map(n=>n.textContent).join(''),sourceText:sourceRecord?.text || '',
  paragraphWords:sourceGroups.flatMap(n=>Array.from(n.querySelectorAll('p')).map(p=>p.textContent.trim().split(/\s+/u).filter(Boolean).length)),
  view:app.state.view,h1:document.getElementById('hub-title').textContent,
  face:document.getElementById('hub-face').getAttribute('src'),mode:app.graphView.mode,
  panelOpen:app.state.panelOpen,focus:document.activeElement.id,hiddenFocusable,targets,controls,
  width:innerWidth,scrollWidth:document.documentElement.scrollWidth,
  forced:matchMedia('(forced-colors: active)').matches,reduced:app.motion.reduced};
