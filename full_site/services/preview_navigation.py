"""Trusted navigation shell around script-disabled, sanitized preview documents."""
import base64
import json
import html
from services.preview import preview_page


def navigable_preview(bundle,page,height=580, *, synchronized=False):
    pages={}; size=0
    for name in [page]+[p for p in bundle.pages if p!=page][:29]:
        html=preview_page(bundle,name,internal_navigation=True)
        raw=html.encode('utf-8')
        if pages and size+len(raw)>8_000_000:
            continue
        size+=len(raw); pages[name]=html
    payload=base64.b64encode(json.dumps({'start':page,'home':bundle.homepage,'pages':pages},ensure_ascii=False).encode()).decode()
    return '''<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>*{box-sizing:border-box}body{margin:0;font:13px system-ui;color:#24334a;background:white}.bar{display:flex;gap:8px;align-items:center;padding:8px;background:#f5f7fa;border:1px solid #dce3eb;border-radius:10px 10px 0 0}button{font:inherit;padding:6px 10px;border:1px solid #a8b5c7;border-radius:6px;background:white;color:#24334a;cursor:pointer}button:disabled{opacity:.45;cursor:default}button:focus-visible{outline:3px solid #315ccf;outline-offset:2px}#where{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}#notice{color:#82400a;padding:4px 8px}iframe{height:calc(100vh - 62px);width:100%;border:1px solid #dce3eb;background:white;display:block}</style></head><body>
<nav class="bar" aria-label="Preview navigation"><button id="back" type="button">← Back</button><button id="home" type="button">Home</button><span id="where"></span></nav><div id="notice" role="status"></div>
<iframe id="document" title="Website page" sandbox="allow-same-origin allow-popups allow-popups-to-escape-sandbox" height="HEIGHT"></iframe>
<script>
const data=JSON.parse(new TextDecoder().decode(Uint8Array.from(atob('PAYLOAD'),c=>c.charCodeAt(0))));
const frame=document.getElementById('document'),back=document.getElementById('back'),notice=document.getElementById('notice');
let current=data.start,history=[];
const synchronized=SYNC;
function navigate(path,fragment=''){
 if(synchronized)window.parent.postMessage({type:'afterlife-navigation',action:'open',path,fragment},'*');
 else show(path,fragment);
}
window.addEventListener('message',event=>{
 if(!synchronized || event.source!==window.parent || event.data?.type!=='afterlife-show')return;
 show(event.data.path,event.data.fragment||'',false);
 back.disabled=!event.data.canGoBack;
});
function show(path,fragment='',remember=true){
 if(!Object.prototype.hasOwnProperty.call(data.pages,path)){notice.textContent='Use the page selector above to open this page.';return;}
 if(remember)history.push(current);
 current=path; notice.textContent='';document.getElementById('where').textContent=path;back.disabled=!history.length;
 frame.onload=()=>{
  const doc=frame.contentDocument;
  doc.addEventListener('click',event=>{
   const a=event.target.closest('a[data-afterlife-page]');
   if(!a)return;
   event.preventDefault();navigate(a.dataset.afterlifePage,a.dataset.afterlifeFragment||'');
  });
  if(fragment){let id;try{id=decodeURIComponent(fragment)}catch(e){id=fragment};const target=doc.getElementById(id)||doc.getElementsByName(id)[0];if(target)target.scrollIntoView();}
 };
 frame.srcdoc=data.pages[path];
}
back.onclick=()=>{if(synchronized){window.parent.postMessage({type:'afterlife-navigation',action:'back'},'*');return;}const path=history.pop();if(path)show(path,'',false)};
document.getElementById('home').onclick=()=>navigate(data.home);
show(data.start,'',false);
</script></body></html>'''.replace('SYNC','true' if synchronized else 'false').replace('HEIGHT',str(height-52)).replace('PAYLOAD',payload)


def comparison_preview(original, revised, page):
    """One trusted parent owns navigation for both views; source scripts stay off."""
    left = html.escape(navigable_preview(original,page,620,synchronized=True),quote=True)
    right = html.escape(navigable_preview(revised,page,620,synchronized=True),quote=True)
    state = base64.b64encode(json.dumps({'page':page,'pages':original.pages}).encode()).decode()
    return r'''<!doctype html><html><head><meta charset="utf-8"><style>
    *{box-sizing:border-box}body{margin:0;font:14px system-ui;color:#24334a;background:white}
    .views{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:20px}
    h3{font-size:15px;margin:0 0 14px}iframe{width:100%;height:625px;border:0}
    @media(max-width:600px){.views{grid-template-columns:1fr;gap:12px}iframe{height:315px}h3{margin-bottom:6px}}
    </style></head><body><div class="views">
    <section><h3>BEFORE — original website</h3><iframe id="before" title="Original website" srcdoc="LEFT"></iframe></section>
    <section><h3>AFTER — updated original website</h3><iframe id="after" title="Redesigned website" srcdoc="RIGHT"></iframe></section>
    </div><script>
    const config=JSON.parse(atob('STATE'));
    const frames=[document.getElementById('before'),document.getElementById('after')];
    let current={path:config.page,fragment:''},history=[];
    function broadcast(){for(const frame of frames)frame.contentWindow.postMessage({type:'afterlife-show',...current,canGoBack:history.length>0},'*');}
    window.addEventListener('message',event=>{
      if(!frames.some(f=>f.contentWindow===event.source)||event.data?.type!=='afterlife-navigation')return;
      const message=event.data;
      if(message.action==='back'){if(!history.length)return;current=history.pop();}
      else if(message.action==='open'&&config.pages.includes(message.path)){
        history.push(current);current={path:message.path,fragment:typeof message.fragment==='string'?message.fragment:''};
      }else return;
      broadcast();
    });
    </script></body></html>'''.replace('LEFT',left).replace('RIGHT',right).replace('STATE',state)

