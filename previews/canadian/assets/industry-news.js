/* Canadian Editorial: three editorial news widgets with clickable publisher media. */
(() => {
  "use strict";
  const root = document.getElementById("industry-news");
  if (!root) return;
  const filters = root.querySelector("[data-news-filters]");
  const outlet = root.querySelector("[data-news-cards]");
  const status = root.querySelector("[data-news-status]");
  const updated = root.querySelector("[data-news-updated]");
  const count = root.querySelector("[data-news-count]");
  const more = root.querySelector("[data-news-more]");
  const categories = ["All", "Salesforce", "Microsoft", "AI", "Zoom", "Tech", "Business Analysis"];
  const groups = [
    {title:"Enterprise Platforms",subtitle:"Salesforce & Microsoft",categories:["Salesforce","Microsoft"],symbol:"◈"},
    {title:"AI & Emerging Tech",subtitle:"AI, innovation & technology",categories:["AI","Tech"],symbol:"✳"},
    {title:"Workplace & Analysis",subtitle:"Zoom & business analysis",categories:["Zoom","Business Analysis"],symbol:"◎"}
  ];
  const sources = {
    Salesforce:"https://developer.salesforce.com/blogs/",
    Microsoft:"https://techcommunity.microsoft.com/",
    AI:"https://openai.com/news/",
    Tech:"https://arstechnica.com/",
    Zoom:"https://www.zoom.com/en/blog/",
    "Business Analysis":"https://www.iiba.org/business-analysis-blogs/"
  };
  let articles = [];
  let current = "All";
  let expanded = false;

  const element = (tag, css, text) => {
    const n = document.createElement(tag);
    if (css) n.className = css;
    if (text !== undefined) n.textContent = text;
    return n;
  };
  const safeUrl = (s) => {
    if (typeof s !== "string") return "";
    try {
      const u = new URL(s);
      return u.protocol === "https:" && !u.username && !u.password ? u.href : "";
    } catch { return ""; }
  };
  const dateLabel = s => {
    const d = new Date(s);
    return Number.isNaN(+d) ? "" : new Intl.DateTimeFormat("en-CA",
      {month:"short",day:"numeric",timeZone:"UTC"}).format(d);
  };
  const external = (url, label, className="") => {
    const a = element("a",className,label);
    a.href = url;
    a.target="_blank";
    a.rel="noopener noreferrer";
    return a;
  };
  const openMedia = item => {
    const media = external(item.url,"","news-widget-media");
    const src = safeUrl(item.image_url);
    if (src) {
      const image = element("img","news-widget-image");
      image.src=src;
      image.alt="";
      image.loading="lazy";
      image.decoding="async";
      image.referrerPolicy="no-referrer";
      image.addEventListener("error",()=> {
        image.remove();
        media.classList.add("news-media-fallback");
        if (!media.querySelector(".news-media-symbol")) {
          media.prepend(element("span","news-media-symbol",item.category === "AI" ? "✳" : "◈"));
        }
      },{once:true});
      media.append(image);
    } else {
      media.classList.add("news-media-fallback");
      media.append(element("span","news-media-symbol",item.category === "Zoom" ? "◎" : item.category === "AI" ? "✳" : "◈"));
    }
    media.append(element("span","news-media-label",item.category));
    if (safeUrl(item.video_url) || /(?:youtube\.com|youtu\.be|vimeo\.com)/i.test(item.url)) {
      media.append(element("span","news-media-play","▶"));
      media.setAttribute("aria-label","Open video: "+item.title);
    } else {
      media.setAttribute("aria-label","Read article: "+item.title);
    }
    return media;
  };
  function leadCard(item) {
    const card = element("article","news-widget-lead");
    card.append(openMedia(item));
    const body = element("div","news-widget-lead-body");
    const meta = element("div","news-widget-article-meta");
    meta.append(element("span","",item.source),element("time","",dateLabel(item.published_at)));
    const h = element("h4","news-widget-title");
    h.append(external(item.url,item.title));
    const summary=element("p","news-widget-summary",item.summary || "Explore the latest update from the publisher.");
    body.append(meta,h,summary);
    card.append(body);
    return card;
  }
  function smallCard(item) {
    const article=element("article","news-widget-small");
    const thumb=external(item.url,"","news-widget-small-thumb");
    const imageUrl=safeUrl(item.image_url);
    if (imageUrl) {
      const img=element("img","");
      img.src=imageUrl;img.alt="";img.loading="lazy";img.referrerPolicy="no-referrer";
      img.addEventListener("error",()=>{img.remove();thumb.textContent="↗";},{once:true});
      thumb.append(img);
    } else thumb.textContent="↗";
    const content=element("div","news-widget-small-copy");
    content.append(element("span","news-widget-small-meta",item.category+" · "+dateLabel(item.published_at)));
    const h=element("h4","");
    h.append(external(item.url,item.title));
    content.append(h);
    article.append(thumb,content);
    return article;
  }
  function noStories(box, group) {
    const empty=element("div","news-widget-empty");
    empty.append(element("p","","No recent stories in this category yet."));
    const links=element("div","news-widget-source-links");
    for (const category of group.categories) {
      if (current === "All" || current === category) {
        links.append(external(sources[category],"Visit "+category+" updates ↗"));
      }
    }
    empty.append(links);
    box.append(empty);
  }
  function render() {
    filters.querySelectorAll("button").forEach(button=>{
      const selected=button.dataset.category===current;
      button.classList.toggle("is-active",selected);
      button.setAttribute("aria-pressed",String(selected));
    });
    const visible=articles.filter(item=> current==="All" || current===item.category);
    count.textContent=visible.length?visible.length+" available stories":"";
    outlet.replaceChildren();
    const relevant=groups.filter(group=>current==="All" || group.categories.includes(current));
    for (const group of relevant) {
      const panel=element("section","news-widget");
      panel.setAttribute("aria-label",group.title);
      const header=element("div","news-widget-header");
      const headerLeft=element("div","");
      headerLeft.append(element("span","news-widget-kicker","INDUSTRY / INSIGHTS"));
      headerLeft.append(element("h3","news-widget-heading",group.title));
      headerLeft.append(element("p","news-widget-subheading",group.subtitle));
      header.append(headerLeft,element("span","news-widget-mark",group.symbol));
      panel.append(header);
      const scroll=element("div","news-widget-scroll");
      const matched=visible.filter(item=>group.categories.includes(item.category));
      if (!matched.length) noStories(scroll,group);
      else {
        const limit=expanded?7:4;
        const selection=matched.slice(0,limit);
        // Give the lead position to a genuine publisher image/video when available.
        const mediaIndex=selection.findIndex(item=>safeUrl(item.image_url) || safeUrl(item.video_url));
        if (mediaIndex>0) selection.unshift(selection.splice(mediaIndex,1)[0]);
        selection.forEach((item,index)=>scroll.append(index===0?leadCard(item):smallCard(item)));
      }
      panel.append(scroll);
      const footer=element("div","news-widget-footer");
      footer.append(element("span","",matched.length+" stories"));
      if (matched.length) footer.append(element("span","","Scroll for more ↓"));
      panel.append(footer);
      outlet.append(panel);
    }
    if (more) {
      more.hidden = !relevant.some(group=>visible.filter(item=>group.categories.includes(item.category)).length>4);
      more.textContent=expanded?"Show fewer stories":"Show more stories per widget";
    }
  }
  filters.replaceChildren();
  for (const category of categories) {
    const b=element("button","news-filter",category);
    b.type="button";b.dataset.category=category;
    b.addEventListener("click",()=>{current=category;expanded=false;render();});
    filters.append(b);
  }
  more?.addEventListener("click",()=>{expanded=!expanded;render();});
  render();
  status.textContent="Loading the latest stories…";

  fetch("/Oba/previews/canadian/data/news.json?v="+Math.floor(Date.now()/300000),{cache:"no-store"})
    .then(response=>{if(!response.ok)throw Error("Feed unavailable");return response.json();})
    .then(data=>{
      articles=(Array.isArray(data.articles)?data.articles:[])
        .filter(item=>item && categories.includes(item.category) && item.category!=="All" &&
          typeof item.title==="string" && safeUrl(item.url) && item.published_at)
        .sort((a,b)=>new Date(b.published_at)-new Date(a.published_at));
      if (data.updated_at && updated) {
        const d=new Date(data.updated_at);
        if (!Number.isNaN(+d)) updated.textContent="Updated "+new Intl.DateTimeFormat("en-CA",
          {month:"short",day:"numeric",year:"numeric",hour:"numeric",minute:"2-digit"}).format(d);
      }
      status.textContent=articles.length?"Headlines and previews link directly to their publishers.":
        "Live headlines are being collected. You can browse the publishers below.";
      render();
    })
    .catch(()=>{
      status.textContent="Live news is temporarily unavailable. Publisher links remain accessible.";
      render();
    });
})();
