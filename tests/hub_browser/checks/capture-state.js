// Eval body for the Phase 2.3.1 look capture (plan 09). Arguments: hash (a route such as
// "/pair/unusual_pairs/3"; set and wait for hashchange), view (HubApp.go), panel (pair or
// record, as review-state.js does it), clear, scroll (top or results), theme (light or dark:
// set the data-theme attribute of the root element and emit the theme event). Then wait for
// the fonts and two animation frames. The panel and scroll handling copy review-state.js.
const app=window.HubApp||null;
if(args.theme==='dark' || args.theme==='light') {
  document.documentElement.setAttribute('data-theme',args.theme);
  if(app && typeof app.emit==='function') app.emit('theme',args.theme);
}
if(args.hash) {
  const target='#'+args.hash;
  if(window.location.hash!==target) {
    await new Promise(resolve=>{
      let done=false;
      const finish=()=>{ if(done) return; done=true; window.removeEventListener('hashchange',finish); resolve(); };
      window.addEventListener('hashchange',finish);
      setTimeout(finish,5000);
      window.location.hash=target;
    });
  }
}
if(args.view) app.go(args.view,{focus:false});
if(args.view==='graph' && app.data.graph.earned) {
  const deadline=performance.now()+20000;
  while(!['3d','fallback'].includes(app.graphView.mode)) {
    if(performance.now()>deadline) throw new Error('Capture graph deadline exceeded');
    await new Promise(r=>setTimeout(r,16));
  }
}
if(args.panel) {
  if(args.panel==='record') app.select({type:'record',id:app.data.records[0].id});
  else app.select({type:'pair',key:app.data.pairs[0].key});
}
if(args.clear) app.clearSelection();
await document.fonts.ready;
await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
if(args.scroll==='results') document.getElementById('hub-results').scrollIntoView();
if(args.scroll==='top') window.scrollTo(0,0);
await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
return {view:app?app.state.view:null,page:app?app.state.page:null,title:document.title,
  hash:window.location.hash,theme:document.documentElement.getAttribute('data-theme'),
  focus:document.activeElement.id,width:innerWidth,scrollWidth:document.documentElement.scrollWidth,
  scrollY:window.scrollY,panelOpen:app?app.state.panelOpen:null};
