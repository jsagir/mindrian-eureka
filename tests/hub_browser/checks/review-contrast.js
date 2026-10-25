await document.fonts.ready;
function rgba(value) {
  const srgb=value.match(/^color\(srgb\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)(?:\s*\/\s*([\d.]+))?\)$/);
  if(srgb) return [Number(srgb[1])*255,Number(srgb[2])*255,Number(srgb[3])*255,Number(srgb[4]||1)];
  const match=value.match(/^rgba?\(([^)]+)\)$/);
  if (!match) return null;
  const parts=match[1].split(/[,\s/]+/).filter(Boolean).map(Number);
  return [parts[0],parts[1],parts[2],parts.length>3 ? parts[3] : 1];
}
function blend(front,back) {
  return front.slice(0,3).map((c,i)=>c*front[3]+back[i]*(1-front[3])).concat(1);
}
function background(node) {
  const layers=[];
  for(let current=node;current;current=current.parentElement) {
    const color=rgba(getComputedStyle(current).backgroundColor);
    if(color && color[3]>0) layers.push(color);
    if(color && color[3]===1) break;
  }
  let result=[247,245,238,1];
  for(const layer of layers.reverse()) result=blend(layer,result);
  return result;
}
function luminance(color) {
  const linear=color.slice(0,3).map(c=>{const n=c/255;return n<=.04045?n/12.92:((n+.055)/1.055)**2.4;});
  return linear[0]*.2126+linear[1]*.7152+linear[2]*.0722;
}
if(args.negative) {
  for(const [id,color] of [['review-negative','#f7f5ee'],['review-yellow','#f2c200']]) {
    const node=document.createElement('p');node.id=id;node.textContent=window.HUB_COPY.Gr07;
    node.style.color=color;node.style.backgroundColor='#f7f5ee';document.body.appendChild(node);
  }
}
const failures=[],yellow=[],pairs=new Map();
let checked=0;
function measure(node,style,kind,opacity) {
  const foreground=rgba(style.color), bg=background(node);
  if(!foreground) {failures.push({kind,color:style.color,reason:'unparsed color'});return;}
  foreground[3]*=opacity;
  const text=blend(foreground,bg);
  const l1=luminance(text),l2=luminance(bg);
  const ratio=(Math.max(l1,l2)+.05)/(Math.min(l1,l2)+.05);
  const size=parseFloat(style.fontSize),weight=parseInt(style.fontWeight,10);
  const threshold=size>=24 || (size>=18.66 && weight>=700) ? 3 : 4.5;
  const item={color:text.slice(0,3),background:bg.slice(0,3),ratio,size,weight,threshold};
  const key=JSON.stringify([item.color,item.background]);
  if(!pairs.has(key)||pairs.get(key).ratio>ratio) pairs.set(key,item);
  checked++;
  if(ratio+1e-6<threshold) failures.push({tag:node.tagName,id:node.id,kind,...item});
  if(foreground.slice(0,3).map(Math.round).join(',')==='242,194,0') yellow.push({tag:node.tagName,id:node.id});
}
for(const node of document.body.querySelectorAll('*')) {
  const rect=node.getBoundingClientRect(),style=getComputedStyle(node);
  if(!rect.width||!rect.height||style.visibility==='hidden'||style.display==='none') continue;
  if(node.closest('.hub-visually-hidden')||(node.classList.contains('hub-skip')&&node!==document.activeElement)) continue;
  const direct=Array.from(node.childNodes).some(n=>n.nodeType===Node.TEXT_NODE&&n.textContent.trim());
  if(direct) measure(node,style,'text',Number(style.opacity));
  if(node.matches('input[placeholder]')&&!node.value) {
    const placeholder=getComputedStyle(node,'::placeholder');
    measure(node,placeholder,'placeholder',Number(placeholder.opacity)*Number(style.opacity));
  }
}
return {checked,failures,yellow,pairs:Array.from(pairs.values())};
