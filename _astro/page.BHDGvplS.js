const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["_astro/mermaid.core.BVzgZ4Kp.js","_astro/preload-helper.CVfkMyKi.js","_astro/transform.B7IGp_JE.js","_astro/mermaid-layout-elk.core.6JLyTxwK.js"])))=>i.map(i=>d[i]);
import{_ as V}from"./preload-helper.CVfkMyKi.js";const oe={},W=new Set,x=new WeakSet;let H=!0,U,F=!1;function re(e){F||(F=!0,H??=!1,U??="hover",ne(),se(),ae(),le())}function ne(){for(const e of["touchstart","mousedown"])document.addEventListener(e,r=>{const n=r.target.closest("a");k(n,"tap")&&L(n.href,{ignoreSlowConnection:!0})},{passive:!0})}function se(){let e;document.body.addEventListener("focusin",t=>{const s=t.target.closest("a");k(s,"hover")&&r(s.href)},{passive:!0}),document.body.addEventListener("focusout",n,{passive:!0}),O(()=>{for(const t of document.getElementsByTagName("a"))x.has(t)||k(t,"hover")&&(x.add(t),t.addEventListener("mouseenter",s=>r(s.currentTarget.href),{passive:!0}),t.addEventListener("mouseleave",n,{passive:!0}))});function r(t){e&&clearTimeout(e),e=setTimeout(()=>{L(t)},80)}function n(){e&&(clearTimeout(e),e=0)}}function ae(){let e;O(()=>{for(const r of document.getElementsByTagName("a"))x.has(r)||k(r,"viewport")&&(x.add(r),e??=ie(),e.observe(r))})}function ie(){const e=new WeakMap;return new IntersectionObserver((r,n)=>{for(const t of r){const s=t.target,i=e.get(s);t.isIntersecting?(i&&clearTimeout(i),e.set(s,setTimeout(()=>{n.unobserve(s),e.delete(s),L(s.href)},300))):i&&(clearTimeout(i),e.delete(s))}})}function le(){O(()=>{for(const e of document.getElementsByTagName("a"))k(e,"load")&&L(e.href)})}function L(e,r){e=e.replace(/#.*/,"");const n=r?.ignoreSlowConnection??!1;if(ce(e,n))if(W.add(e),document.createElement("link").relList?.supports?.("prefetch")){const t=document.createElement("link");t.rel="prefetch",t.setAttribute("href",e),document.head.append(t)}else{const t=new Headers;for(const[s,i]of Object.entries(oe))t.set(s,i);fetch(e,{priority:"low",headers:t})}}function ce(e,r){if(!navigator.onLine||!r&&G())return!1;try{const n=new URL(e,location.href);return location.origin===n.origin&&(location.pathname!==n.pathname||location.search!==n.search)&&!W.has(e)}catch{}return!1}function k(e,r){if(e?.tagName!=="A")return!1;const n=e.dataset.astroPrefetch;return n==="false"?!1:r==="tap"&&(n!=null||H)&&G()?!0:n==null&&H||n===""?r===U:n===r}function G(){if("connection"in navigator){const e=navigator.connection;return e.saveData||/2g/.test(e.effectiveType)}return!1}function O(e){e();let r=!1;document.addEventListener("astro:page-load",()=>{if(!r){r=!0;return}e()})}const d=(...e)=>console.log("[astro-mermaid]",...e),X=(...e)=>console.error("[astro-mermaid]",...e),K=()=>document.querySelectorAll("pre.mermaid").length>0;let w=null;async function de(){return w||(d("Loading mermaid.js..."),w=V(()=>import("./mermaid.core.BVzgZ4Kp.js").then(e=>e.ba),__vite__mapDeps([0,1,2])).then(async({default:e})=>{const r=[{name:"logos",url:"https://unpkg.com/@iconify-json/logos@1/icons.json"},{name:"lobe",url:"https://unpkg.com/@proj-airi/lobe-icons@latest/icons.json"}];if(r&&r.length>0){d("Registering",r.length,"icon packs");const t=r.map(s=>({name:s.name,loader:()=>fetch(s.url).then(i=>i.json())}));await e.registerIconPacks(t)}const n=await V(()=>import("./mermaid-layout-elk.core.6JLyTxwK.js").then(t=>t.m),__vite__mapDeps([3,1])).catch(()=>null);return n?.default&&(d("Registering elk layouts"),e.registerLayoutLoaders(n.default)),e}).catch(e=>{throw X("Failed to load mermaid:",e),w=null,e}),w)}const D={startOnLoad:!1,theme:"forest"},ue={light:"default",dark:"dark"};async function z(){d("Initializing mermaid diagrams...");const e=document.querySelectorAll("pre.mermaid");if(d("Found",e.length,"mermaid diagrams"),e.length===0)return;const r=await de();let n=D.theme;{const t=document.documentElement.getAttribute("data-theme"),s=document.body.getAttribute("data-theme");n=ue[t||s]||D.theme,d("Using theme:",n,"from",t?"html":"body")}r.initialize({...D,theme:n,gitGraph:{mainBranchName:"main",showCommitLabel:!0,showBranches:!0,rotateCommitLabel:!0}});for(const t of e){if(t.hasAttribute("data-processed"))continue;t.hasAttribute("data-diagram")||t.setAttribute("data-diagram",t.textContent||"");const s=t.getAttribute("data-diagram")||"",i="mermaid-"+Math.random().toString(36).slice(2,11);d("Rendering diagram:",i);try{const p=document.getElementById(i);p&&p.remove();const{svg:u}=await r.render(i,s);t.innerHTML=u,t.setAttribute("data-processed","true"),d("Successfully rendered diagram:",i)}catch(p){X("Mermaid rendering error for diagram:",i,p);const u=document.createElement("div");u.style.cssText="color: red; padding: 1rem; border: 1px solid red; border-radius: 0.5rem;";const g=document.createElement("strong");g.textContent="Error rendering diagram:";const b=document.createElement("span");b.textContent=" "+(p.message||"Unknown error"),u.appendChild(g),u.appendChild(b),t.textContent="",t.appendChild(u),t.setAttribute("data-processed","true")}}}K()?(d("Mermaid diagrams detected on initial load"),z()):d("No mermaid diagrams found on initial load");{const e=new MutationObserver(r=>{for(const n of r)n.type==="attributes"&&n.attributeName==="data-theme"&&(document.querySelectorAll("pre.mermaid[data-processed]").forEach(t=>{t.removeAttribute("data-processed")}),z())});e.observe(document.documentElement,{attributes:!0,attributeFilter:["data-theme"]}),e.observe(document.body,{attributes:!0,attributeFilter:["data-theme"]})}document.addEventListener("astro:after-swap",()=>{d("View transition detected"),K()&&z()});const Y=document.createElement("style");Y.textContent=`
            /* Prevent layout shifts by setting minimum height */
            pre.mermaid {
              display: flex;
              justify-content: center;
              align-items: center;
              margin: 2rem 0;
              padding: 1rem;
              background-color: transparent;
              border: none;
              overflow: auto;
              min-height: 200px; /* Prevent layout shift */
              position: relative;
            }
            
            /* Loading state with skeleton loader */
            pre.mermaid:not([data-processed]) {
              background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
              background-size: 200% 100%;
              animation: shimmer 1.5s infinite;
            }
            
            /* Dark mode skeleton loader */
            [data-theme="dark"] pre.mermaid:not([data-processed]) {
              background: linear-gradient(90deg, #2a2a2a 25%, #3a3a3a 50%, #2a2a2a 75%);
              background-size: 200% 100%;
            }
            
            @keyframes shimmer {
              0% {
                background-position: -200% 0;
              }
              100% {
                background-position: 200% 0;
              }
            }
            
            /* Show processed diagrams with smooth transition */
            pre.mermaid[data-processed] {
              animation: none;
              background: transparent;
              min-height: auto; /* Allow natural height after render */
            }
            
            /* Ensure responsive sizing for mermaid SVGs */
            pre.mermaid svg {
              max-width: 100%;
              height: auto;
            }
            
            /* Optional: Add subtle background for better visibility */
            @media (prefers-color-scheme: dark) {
              pre.mermaid[data-processed] {
                background-color: rgba(255, 255, 255, 0.02);
                border-radius: 0.5rem;
              }
            }
            
            @media (prefers-color-scheme: light) {
              pre.mermaid[data-processed] {
                background-color: rgba(0, 0, 0, 0.02);
                border-radius: 0.5rem;
              }
            }
            
            /* Respect user's color scheme preference */
            [data-theme="dark"] pre.mermaid[data-processed] {
              background-color: rgba(255, 255, 255, 0.02);
              border-radius: 0.5rem;
            }
            
            [data-theme="light"] pre.mermaid[data-processed] {
              background-color: rgba(0, 0, 0, 0.02);
              border-radius: 0.5rem;
            }
          `;document.head.appendChild(Y);function me(e={}){const{position:r="right",smoothScroll:n=!0,threshold:t=300,svgPath:s="M18 15l-6-6-6 6",svgStrokeWidth:i="2",borderRadius:p="15",showTooltip:u=!1,showProgressRing:g=!1,progressRingColor:b="yellow",showOnHomepage:Z=!1}=e,q=((o,f)=>{if(typeof o=="string")return o;if(typeof o!="object"||o===null)return"Scroll to top";const l=f&&typeof f=="string"?f.toLowerCase().trim():"";if(!l){const m=o.en;return typeof m=="string"?m:"Scroll to top"}let c=o[l];if(typeof c=="string")return c;if(l.includes("-")){const m=l.split("-")[0];if(c=o[m],typeof c=="string")return c}return c=o.en,typeof c=="string"?c:"Scroll to top"})(e.tooltipText,document.documentElement.lang);let h=null;const J=()=>document.querySelector(".hero")||document.querySelector(".sl-hero")||document.querySelector('[data-page="index"]')||document.querySelector(".landing-page")||document.querySelector(".homepage")||document.querySelector("[data-starlight-homepage]")||document.querySelector(".site-hero")||document.body.classList.contains("homepage")||document.body.classList.contains("homepage")||document.body.classList.contains("landing")||document.querySelector("main.sl-main")&&document.querySelector("main.sl-main .hero, main.sl-main .sl-hero"),Q=()=>{if(h&&h(),J()&&!Z)return;const o=document.createElement("button");o.id="scroll-to-top-button",o.ariaLabel=q,o.setAttribute("aria-describedby",u?"scroll-to-top-tooltip":""),o.setAttribute("role","button"),o.setAttribute("tabindex","0");let f=!1;o.innerHTML=`
      ${g?`
      <svg class="scroll-progress-ring" 
           width="47"   
           height="47" 
           viewBox="0 0 47 47"
           style="position: absolute; top: 0; left: 0;">
        <!-- Background circle -->
        <circle cx="23.5" cy="23.5" r="22" 
                fill="none" 
                stroke="${b}" 
                stroke-width="3" 
                opacity="0.2" />
        <!-- Progress circle -->
        <circle cx="23.5" cy="23.5" r="22" 
                fill="none" 
                stroke="${b}" 
                stroke-width="3" 
                stroke-linecap="round"
                class="scroll-progress-circle"
                style="transform: rotate(-90deg); transform-origin: center;" />
      </svg>
      `:""}
      <svg xmlns="http://www.w3.org/2000/svg" 
           width="35" 
           height="35" 
           viewBox="0 0 24 24"            
           fill="none" 
           stroke="currentColor" 
           stroke-width="${i}" 
           stroke-linecap="round" 
           stroke-linejoin="round"
           style="position: relative; z-index: 1;">
        <path d="${s}"/>
      </svg>
    `;const l=document.createElement("div");l.id="scroll-to-top-tooltip",l.textContent=q;const c=document.createElement("div");c.style.cssText=`
    position: absolute;
    top: 100%; /* Position below the tooltip */
    left: 50%;
    transform: translateX(-50%);
    width: 0;
    height: 0;
    border-left: 6px solid transparent;
    border-right: 6px solid transparent;
    border-top: 6px solid var(--sl-color-gray-7);
  `;const m=document.createElement("style");m.id="scroll-to-top-styles",m.textContent=`
    .scroll-to-top-button {
      position: fixed;
      bottom: 40px;
      width: 47px;
      height: 47px;
      ${r==="left"?"left: 40px;":r==="right"?"right: 35px;":"left: 50%;"}
      border-radius: ${p}%;     
      background-color: var(--sl-color-accent);       
      color: white;
      cursor: pointer;
      display: flex;
      align-items: center;      
      justify-content: center;
      opacity: 0;
      visibility: hidden;
      transform: ${r==="center"?"translateX(-50%) scale(0)":"scale(0)"};
      transition: opacity 0.3s ease, visibility 0.3s ease, background-color 0.3s ease, transform 0.3s ease;      
      z-index: 100;            
      border: 1px solid var(--sl-color-accent);
      transform-origin: center;
      -webkit-tap-highlight-color: transparent; /* Disable mobile tap highlight */
      touch-action: manipulation; /* Prevent double-tap zoom */
      box-shadow: 0 0 0 1px rgba(0,0,0,0.04),0 4px 8px 0 rgba(0,0,0,0.2);
    }
      .scroll-to-top-button:active {
        background-color: var(--sl-color-accent-dark); 
        color: var(--sl-text-white);        
        transition: background-color 0.1s ease, transform 0.1s ease; 
     }
      .scroll-to-top-button.visible {
        opacity: 1;
        visibility: visible;
        transform: ${r==="center"?"translateX(-50%) scale(1)":"scale(1)"};        
      }

      .scroll-to-top-button:hover {
        background-color: var(--sl-color-accent-low); 
        box-shadow: 0 0 0 1px rgba(0,0,0,0.04),0 4px 8px 0 rgba(0,0,0,0.2);
        color: var(--sl-color-accent);
        border-color: var(--sl-color-accent);     
      }
      
      .scroll-to-top-button.keyboard-focus {
        outline: 2px solid var(--sl-color-text);
        outline-offset: 2px;
      }

      .scroll-to-top-btn-tooltip {
        position: absolute;
        ${r==="left"?"left: -25px;":"right: -22px;"}
        top: -47px;
        background-color: var(--sl-color-gray-7);
        color: var(--sl-color-text);
        padding: 5px 10px;
        border-radius: 4px;
        font-weight: 400;
        font-size: 14px;
        white-space: nowrap;
        opacity: 0;
        visibility: hidden;
        transition: opacity 0.2s, visibility 0.3s;
        pointer-events: none;
     }
      .scroll-to-top-btn-tooltip.visible {
        opacity: 1;
        visibility: visible;        
      }

      /* Progress ring styles */
      .scroll-progress-ring {
        pointer-events: none;
      }
      
      .scroll-progress-circle {
        stroke-dasharray: 138.23; /* 2 * π * r = 2 * π * 22 ≈ 138.23 */
        stroke-dashoffset: 138.23;
        transition: stroke-dashoffset 0.1s ease;
      }
    `,document.head.appendChild(m),o.classList.add("scroll-to-top-button"),document.body.appendChild(o),u&&(l.classList.add("scroll-to-top-btn-tooltip"),l.appendChild(c),o.appendChild(l));const T=()=>{l.classList.remove("visible")},B=()=>{u&&l.classList.add("visible")};o.addEventListener("mouseenter",()=>{B()}),o.addEventListener("mouseleave",()=>{T()});const S=()=>{T(),window.scrollTo({top:0,behavior:n?"smooth":"auto"}),o.classList.remove("active")};document.addEventListener("keydown",a=>{a.key==="Tab"&&(f=!0)}),o.addEventListener("mousedown",()=>{f=!1}),o.addEventListener("keydown",a=>{a.key==="Enter"&&(S(),o.classList.remove("keyboard-focus"))}),o.addEventListener("focus",()=>{f&&(B(),o.classList.add("keyboard-focus"))}),o.addEventListener("blur",()=>{T(),o.classList.remove("keyboard-focus")}),o.addEventListener("touchstart",a=>{a.preventDefault(),o.classList.add("active")}),o.addEventListener("touchend",a=>{a.preventDefault(),S(),o.classList.remove("active")}),o.addEventListener("click",a=>{a.preventDefault(),S()});function ee(a,A){let v;return function(){const P=arguments,M=this;v||(a.apply(M,P),v=!0,setTimeout(()=>v=!1,A))}}const R=()=>{const a=window.scrollY,A=window.innerHeight,v=document.documentElement.scrollHeight,P=a/(v-A);if(g){const $=o.querySelector(".scroll-progress-circle");if($){let y=P*100;y>=99.5&&(y=100),y<0&&(y=0);const N=138.23,te=N-y/100*N;$.style.strokeDashoffset=te.toString()}}const M=t>0?t:300;a>M?o.classList.add("visible"):o.classList.remove("visible")},_=ee(R,16);window.addEventListener("scroll",_),R();const j=()=>{document.documentElement.classList.contains("theme-dark")?(l.style.backgroundColor="var(--sl-color-gray-7)",l.style.color="var(--sl-color-text)",c.style.borderTopColor="var(--sl-color-gray-7)"):(l.style.backgroundColor="black",l.style.color="white",c.style.borderTopColor="black")};j();const I=new MutationObserver(j);I.observe(document.documentElement,{attributes:!0,attributeFilter:["class"]});function C(){Math.round(window.outerWidth/window.innerWidth*100)/100>3?o.style.display="none":o.style.display="flex"}return window.addEventListener("resize",C),C(),h=()=>{window.removeEventListener("scroll",_),window.removeEventListener("resize",C),I.disconnect(),o&&o.parentNode&&o.parentNode.removeChild(o);const a=document.getElementById("scroll-to-top-styles");a&&a.remove()},h},E=()=>{setTimeout(Q,10)};document.readyState==="loading"?document.addEventListener("DOMContentLoaded",E):E(),document.addEventListener("astro:page-load",E),document.addEventListener("astro:before-preparation",()=>{h&&h()})}me({position:"right",tooltipText:"Scroll to top",smoothScroll:!0,threshold:300,svgPath:"M18 15l-6-6-6 6",svgStrokeWidth:"2",borderRadius:"15",showTooltip:!1,showProgressRing:!1,progressRingColor:"yellow",showOnHomepage:!1});re();export{me as default};
