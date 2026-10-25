if(args.negative) {
  const node=document.createElement('p');node.id='review-clipped';node.textContent=window.HUB_COPY.Gr07;
  node.style.inlineSize='40px';node.style.blockSize='20px';node.style.overflow='hidden';
  document.body.appendChild(node);
}
const style=document.createElement('style');
style.textContent='*{line-height:1.5!important;letter-spacing:.12em!important;word-spacing:.16em!important}p{margin-block-end:2em!important}';
document.head.appendChild(style);
await document.fonts.ready;
await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
const clipped=[];
for(const node of document.body.querySelectorAll('*')) {
  const rect=node.getBoundingClientRect(),css=getComputedStyle(node);
  if(!rect.width||!rect.height||css.visibility==='hidden'||css.display==='none') continue;
  if(node.closest('.hub-visually-hidden,.hub-skip')) continue;
  if(css.clipPath==='inset(50%)'&&css.position==='absolute'&&rect.width<=1&&rect.height<=1) continue;
  const horizontal=['hidden','clip'].includes(css.overflowX)&&node.scrollWidth>node.clientWidth+1;
  const vertical=['hidden','clip'].includes(css.overflowY)&&node.scrollHeight>node.clientHeight+1;
  if((horizontal||vertical)&&node.textContent.trim()) clipped.push({tag:node.tagName,id:node.id,class:node.className,horizontal,vertical});
}
return {clipped,width:innerWidth,scrollWidth:document.documentElement.scrollWidth};
