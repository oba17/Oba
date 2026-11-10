/* Canadian Editorial — 3 compact rotating news previews, no visible categories. */
(() => {
  "use strict";
  const section = document.getElementById("industry-news");
  if (!section) return;
  const deck = section.querySelector("[data-news-cards]");
  const status = section.querySelector("[data-news-status]");
  const updated = section.querySelector("[data-news-updated]");
  const count = section.querySelector("[data-news-count]");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const topics = new Set(["Salesforce","Microsoft","AI","Zoom","Tech","Business Analysis"]);
  const sources = [
    "https://developer.salesforce.com/blogs/",
    "https://techcommunity.microsoft.com/",
    "https://openai.com/news/"
  ];
  let timers = [], articles = [];

  const el = (tag, className, value) => {
    const n = document.createElement(tag);
    if (className) n.className = className;
    if (value !== undefined) n.textContent = value;
    return n;
  };
  const safeLink = value => {
    if (typeof value !== "string") return "";
    try {
      const u = new URL(value, document.baseURI);
      if (u.protocol !== "https:" || u.username || u.password) return "";
      return u.href;
    } catch { return ""; }
  };
  const imageSrc = item => {
    const local = item.local_image_url;
    if (typeof local === "string" && /^\/Oba\/previews\/canadian\/assets\/news-images\/[a-f0-9]{16}\.(?:jpg|png|webp)$/.test(local)) {
      return local;
    }
    return safeLink(item.image_url);
  };
  const articleAnchor = (url, label, className) => {
    const a = el("a",className,label);
    a.href = url;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    return a;
  };
  const formatDate = iso => {
    const d = new Date(iso);
    return Number.isNaN(d.getTime()) ? "" :
      new Intl.DateTimeFormat("en-CA",{month:"short",day:"numeric",year:"numeric",timeZone:"UTC"}).format(d);
  };

  function articleCard(item) {
    const card = el("article","news-rotator-slide");
    const media = articleAnchor(item.url,"","news-rotator-media");
    media.setAttribute("aria-label","Open article: "+item.title);
    const photo = imageSrc(item);
    const fallback = () => {
      const existing = media.querySelector("img");
      if (existing) existing.remove();
      media.classList.add("news-rotator-fallback");
      if (!media.querySelector(".news-rotator-symbol")) {
        media.prepend(el("span","news-rotator-symbol","◈"));
      }
    };
    if (photo) {
      const img = el("img","news-rotator-image");
      img.src = photo;
      img.alt = "";
      img.loading = "eager";
      img.decoding = "async";
      img.addEventListener("error",fallback,{once:true});
      media.append(img);
    } else fallback();

    if (safeLink(item.video_url) ||
        /(?:youtube\.com|youtu\.be|vimeo\.com)/i.test(item.url)) {
      media.append(el("span","news-rotator-play","▶"));
    }
    const text = el("div","news-rotator-copy");
    text.append(el("p","news-rotator-meta",item.source+"  ·  "+formatDate(item.published_at)));
    const title = el("h4","news-rotator-title");
    title.append(articleAnchor(item.url,item.title,""));
    text.append(title);
    card.append(media,text);
    return card;
  }

  function cleanup() {
    timers.forEach(stop => stop());
    timers = [];
  }
  function makePanel(items, panelIndex) {
    const container = el("section","news-rotator");
    container.setAttribute("aria-label","News preview "+(panelIndex+1));
    const viewport = el("div","news-rotator-viewport");
    const control = el("div","news-rotator-controls");
    const progress = el("span","news-rotator-count");
    const buttons = el("div","news-rotator-buttons");
    const previous = el("button","news-rotator-arrow","‹");
    const next = el("button","news-rotator-arrow","›");
    previous.type = next.type = "button";
    previous.setAttribute("aria-label","Previous article in news preview "+(panelIndex+1));
    next.setAttribute("aria-label","Next article in news preview "+(panelIndex+1));
    buttons.append(previous,next);
    control.append(progress,buttons);
    container.append(viewport,control);
    if (!items.length) {
      viewport.append(el("p","news-rotator-empty","News articles are being refreshed."));
      viewport.append(articleAnchor(sources[panelIndex],"Visit publisher ↗","news-rotator-source"));
      progress.textContent = "0 articles";
      buttons.hidden = true;
      return container;
    }

    let active = 0, interval = null, paused = false;
    const show = () => {
      viewport.replaceChildren(articleCard(items[active]));
      progress.textContent = (active+1)+" / "+items.length;
    };
    const step = direction => {
      active = (active+direction+items.length)%items.length;
      show();
    };
    const stop = () => {
      if (interval !== null) clearInterval(interval);
      interval = null;
    };
    const start = () => {
      stop();
      if (!paused && !document.hidden && !reduceMotion.matches && items.length > 1) {
        interval = setInterval(() => step(1), 5000);
      }
    };
    previous.addEventListener("click",()=>{step(-1);start();});
    next.addEventListener("click",()=>{step(1);start();});
    container.addEventListener("mouseenter",()=>{paused=true;stop();});
    container.addEventListener("mouseleave",()=>{paused=false;start();});
    container.addEventListener("focusin",()=>{paused=true;stop();});
    container.addEventListener("focusout",event=>{
      if (!container.contains(event.relatedTarget)) {paused=false;start();}
    });
    const changed = () => start();
    document.addEventListener("visibilitychange",changed);
    reduceMotion.addEventListener?.("change",changed);
    timers.push(()=>{
      stop();
      document.removeEventListener("visibilitychange",changed);
      reduceMotion.removeEventListener?.("change",changed);
    });
    show();
    start();
    return container;
  }
  const display = () => {
    cleanup();
    deck.replaceChildren();
    // Distribute all topics among three equally sized rotating boxes.
    // Prefer genuine media first, then newer links without a preview.
    const ranked = [...articles].sort((a,b)=>{
      const quality = item => item.local_image_url && item.image_kind !== "publisher_logo" ? 3 :
        item.image_url && item.image_kind !== "publisher_logo" ? 2 :
        item.local_image_url ? 1 : 0;
      return quality(b)-quality(a) || new Date(b.published_at)-new Date(a.published_at);
    });
    const columns = [[],[],[]];
    ranked.forEach((a,i)=>columns[i%3].push(a));
    columns.forEach((items,i)=>deck.append(makePanel(items,i)));
    if (count) count.textContent=articles.length+" available articles";
  };
  display();
  if (status) status.textContent="Collecting the latest stories";
  fetch("/Oba/previews/canadian/data/news.json?v="+Math.floor(Date.now()/300000),{cache:"no-store"})
    .then(response=>{if(!response.ok)throw Error("News unavailable");return response.json();})
    .then(data=>{
      articles=(Array.isArray(data.articles)?data.articles:[])
        .filter(item=>item && topics.has(item.category) && safeLink(item.url) &&
          typeof item.title==="string" && item.published_at)
        .sort((a,b)=>new Date(b.published_at)-new Date(a.published_at));
      const d = new Date(data.updated_at);
      if (updated && !Number.isNaN(d.getTime())) {
        updated.textContent="Updated "+new Intl.DateTimeFormat("en-CA",{
          month:"short",day:"numeric",year:"numeric",hour:"numeric",minute:"2-digit"
        }).format(d);
      }
      if (status) status.textContent="Three automatic news previews";
      display();
    })
    .catch(()=>{
      if (status) status.textContent="News temporarily unavailable";
      display();
    });
})();
