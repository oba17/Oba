/* Compact three-panel industry news carousel; sourced from generated publisher data. */
(() => {
  "use strict";
  const root=document.getElementById("industry-news");
  if (!root) return;
  const filterBar=root.querySelector("[data-news-filters]");
  const deck=root.querySelector("[data-news-cards]");
  const status=root.querySelector("[data-news-status]");
  const updated=root.querySelector("[data-news-updated]");
  const count=root.querySelector("[data-news-count]");
  const more=root.querySelector("[data-news-more]");
  if (more) more.hidden=true;
  const categories=["All","Salesforce","Microsoft","AI","Zoom","Tech","Business Analysis"];
  const groups=[
    {title:"Enterprise Platforms",description:"Salesforce & Microsoft",categories:["Salesforce","Microsoft"],mark:"◈"},
    {title:"AI & Emerging Tech",description:"AI & technology",categories:["AI","Tech"],mark:"✳"},
    {title:"Workplace & Analysis",description:"Zoom & business analysis",categories:["Zoom","Business Analysis"],mark:"◎"}
  ];
  const sources={
    Salesforce:"https://developer.salesforce.com/blogs/",
    Microsoft:"https://techcommunity.microsoft.com/",
    AI:"https://openai.com/news/",
    Zoom:"https://www.zoom.com/en/blog/",
    Tech:"https://arstechnica.com/",
    "Business Analysis":"https://www.iiba.org/"
  };
  const reduced=window.matchMedia("(prefers-reduced-motion: reduce)");
  let current="All",articles=[],controllers=[];
  const el=(tag,cls="",label)=>{
    const n=document.createElement(tag);
    if(cls)n.className=cls;
    if(label!==undefined)n.textContent=label;
    return n;
  };
  const safe=(value)=>{
    if(typeof value!=="string")return "";
    try{const url=new URL(value);return url.protocol==="https:" && !url.username && !url.password?url.href:"";}catch{return "";}
  };
  const external=(url,label,cls="")=>{
    const a=el("a",cls,label);a.href=safe(url)||"#";a.target="_blank";a.rel="noopener noreferrer";return a;
  };
  const date=(value)=>{
    const d=new Date(value);
    return Number.isNaN(+d)?"":new Intl.DateTimeFormat("en-CA",{month:"short",day:"numeric",timeZone:"UTC"}).format(d);
  };
  function card(item){
    const slide=el("article","news-rotator-slide");
    const thumb=external(item.url,"","news-rotator-media");
    thumb.setAttribute("aria-label","Open "+item.title);
    const imgUrl=safe(item.image_url);
    if(imgUrl){
      const img=el("img","news-rotator-image");
      img.src=imgUrl;img.alt="";img.loading="lazy";img.decoding="async";img.referrerPolicy="no-referrer";
      img.addEventListener("error",()=>{
        img.remove();thumb.classList.add("news-rotator-fallback");
        thumb.prepend(el("span","news-rotator-symbol",item.category==="AI"?"✳":"◈"));
      },{once:true});
      thumb.append(img);
    }else{
      thumb.classList.add("news-rotator-fallback");
      thumb.append(el("span","news-rotator-symbol",item.category==="Zoom"?"◎":item.category==="AI"?"✳":"◈"));
    }
    thumb.append(el("span","news-rotator-category",item.category));
    if(safe(item.video_url)||/(?:youtube\.com|youtu\.be|vimeo\.com)/i.test(item.url)){
      thumb.append(el("span","news-rotator-play","▶"));
    }
    const body=el("div","news-rotator-copy");
    const meta=el("p","news-rotator-meta",item.source+" · "+date(item.published_at));
    const heading=el("h4","news-rotator-title");
    heading.append(external(item.url,item.title));
    body.append(meta,heading);
    slide.append(thumb,body);
    return slide;
  }
  function reset(){controllers.forEach(c=>c.stop());controllers=[];}
  function panel(group,matching){
    const shell=el("section","news-rotator");
    shell.setAttribute("aria-label",group.title);
    const header=el("div","news-rotator-header");
    const left=el("div","");
    left.append(el("h3","news-rotator-heading",group.title),el("p","news-rotator-description",group.description));
    header.append(left,el("span","news-rotator-mark",group.mark));
    const viewport=el("div","news-rotator-viewport");
    const foot=el("div","news-rotator-controls");
    const indexLabel=el("span","news-rotator-count","");
    const navigation=el("div","news-rotator-buttons");
    const prev=el("button","news-rotator-arrow","‹");
    const next=el("button","news-rotator-arrow","›");
    prev.type=next.type="button";
    prev.setAttribute("aria-label","Previous "+group.title+" article");
    next.setAttribute("aria-label","Next "+group.title+" article");
    navigation.append(prev,next);
    foot.append(indexLabel,navigation);
    shell.append(header,viewport,foot);
    if(!matching.length){
      viewport.append(el("p","news-rotator-empty","No recent headlines available."));
      for(const cat of group.categories){
        if(current==="All"||current===cat)
          viewport.append(external(sources[cat],"Browse "+cat+" updates ↗","news-rotator-source"));
      }
      indexLabel.textContent="0 articles";navigation.hidden=true;
      return shell;
    }
    let index=0;
    let timer=null;
    let paused=false;
    const show=()=>{
      viewport.replaceChildren(card(matching[index]));
      indexLabel.textContent=(index+1)+" / "+matching.length;
    };
    const move=(step)=>{index=(index+step+matching.length)%matching.length;show();};
    const stop=()=>{if(timer!==null){clearInterval(timer);timer=null;}};
    const start=()=>{
      stop();
      if(matching.length>1&&!paused&&!reduced.matches&&!document.hidden){
        timer=setInterval(()=>move(1),5000);
      }
    };
    prev.addEventListener("click",()=>{move(-1);start();});
    next.addEventListener("click",()=>{move(1);start();});
    shell.addEventListener("mouseenter",()=>{paused=true;stop();});
    shell.addEventListener("mouseleave",()=>{paused=false;start();});
    shell.addEventListener("focusin",()=>{paused=true;stop();});
    shell.addEventListener("focusout",event=>{
      if(!shell.contains(event.relatedTarget)){paused=false;start();}
    });
    const onVisibility=()=>start();
    document.addEventListener("visibilitychange",onVisibility);
    const onMotion=()=>start();
    reduced.addEventListener?.("change",onMotion);
    shell.addEventListener("keydown",event=>{
      if(event.target.matches("button")&&(event.key==="ArrowRight"||event.key==="ArrowLeft")){
        event.preventDefault();move(event.key==="ArrowRight"?1:-1);start();
      }
    });
    show();start();
    controllers.push({stop:()=>{stop();document.removeEventListener("visibilitychange",onVisibility);
      reduced.removeEventListener?.("change",onMotion);}});
    return shell;
  }
  function render(){
    reset();deck.replaceChildren();
    filterBar.querySelectorAll("button").forEach(b=>{
      const active=b.dataset.topic===current;
      b.classList.toggle("is-active",active);
      b.setAttribute("aria-pressed",String(active));
    });
    const matching=articles.filter(a=>current==="All"||a.category===current);
    if(count)count.textContent=matching.length+" available articles";
    // Always keep exactly three equal-width boxes, even while a topic filter is selected.
    for(const group of groups){
      const source=matching.filter(a=>group.categories.includes(a.category));
      deck.append(panel(group,source));
    }
  }
  for(const category of categories){
    const b=el("button","news-filter",category);
    b.type="button";b.dataset.topic=category;
    b.addEventListener("click",()=>{current=category;render();});
    filterBar.append(b);
  }
  render();
  status.textContent="Loading news…";
  fetch("/Oba/previews/canadian/data/news.json?v="+Math.floor(Date.now()/300000),{cache:"no-store"})
    .then(r=>{if(!r.ok)throw new Error("Feed unavailable");return r.json();})
    .then(data=>{
      articles=(Array.isArray(data.articles)?data.articles:[])
        .filter(a=>a && categories.includes(a.category) && safe(a.url) && typeof a.title==="string" && a.published_at)
        .sort((a,b)=>new Date(b.published_at)-new Date(a.published_at));
      if(data.updated_at && updated){
        const d=new Date(data.updated_at);
        if(!Number.isNaN(+d))updated.textContent="Updated "+new Intl.DateTimeFormat("en-CA",
          {month:"short",day:"numeric",year:"numeric",hour:"numeric",minute:"2-digit"}).format(d);
      }
      status.textContent="News rotates automatically every 5 seconds. Hover or focus to pause.";
      render();
    })
    .catch(()=>{status.textContent="News is temporarily unavailable. Publisher links remain accessible.";render();});
})();
