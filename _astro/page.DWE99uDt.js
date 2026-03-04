const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["_astro/mermaid.core.BZzq7Q2a.js","_astro/preload-helper.BlTxHScW.js","_astro/transform.CktKV0yf.js","_astro/mermaid-layout-elk.core.C8UwlYjx.js"])))=>i.map(i=>d[i]);
import{_ as N}from"./preload-helper.BlTxHScW.js";const ee={},F=new Set,w=new WeakSet;let C=!0,W,V=!1;function te(e){V||(V=!0,C??=!1,W??="hover",oe(),re(),ne(),ae())}function oe(){for(const e of["touchstart","mousedown"])document.addEventListener(e,r=>{v(r.target,"tap")&&k(r.target.href,{ignoreSlowConnection:!0})},{passive:!0})}function re(){let e;document.body.addEventListener("focusin",t=>{v(t.target,"hover")&&r(t)},{passive:!0}),document.body.addEventListener("focusout",n,{passive:!0}),M(()=>{for(const t of document.getElementsByTagName("a"))w.has(t)||v(t,"hover")&&(w.add(t),t.addEventListener("mouseenter",r,{passive:!0}),t.addEventListener("mouseleave",n,{passive:!0}))});function r(t){const s=t.target.href;e&&clearTimeout(e),e=setTimeout(()=>{k(s)},80)}function n(){e&&(clearTimeout(e),e=0)}}function ne(){let e;M(()=>{for(const r of document.getElementsByTagName("a"))w.has(r)||v(r,"viewport")&&(w.add(r),e??=se(),e.observe(r))})}function se(){const e=new WeakMap;return new IntersectionObserver((r,n)=>{for(const t of r){const s=t.target,l=e.get(s);t.isIntersecting?(l&&clearTimeout(l),e.set(s,setTimeout(()=>{n.unobserve(s),e.delete(s),k(s.href)},300))):l&&(clearTimeout(l),e.delete(s))}})}function ae(){M(()=>{for(const e of document.getElementsByTagName("a"))v(e,"load")&&k(e.href)})}function k(e,r){e=e.replace(/#.*/,"");const n=r?.ignoreSlowConnection??!1;if(ie(e,n))if(F.add(e),document.createElement("link").relList?.supports?.("prefetch")&&r?.with!=="fetch"){const t=document.createElement("link");t.rel="prefetch",t.setAttribute("href",e),document.head.append(t)}else{const t=new Headers;for(const[s,l]of Object.entries(ee))t.set(s,l);fetch(e,{priority:"low",headers:t})}}function ie(e,r){if(!navigator.onLine||!r&&U())return!1;try{const n=new URL(e,location.href);return location.origin===n.origin&&(location.pathname!==n.pathname||location.search!==n.search)&&!F.has(e)}catch{}return!1}function v(e,r){if(e?.tagName!=="A")return!1;const n=e.dataset.astroPrefetch;return n==="false"?!1:r==="tap"&&(n!=null||C)&&U()?!0:n==null&&C||n===""?r===W:n===r}function U(){if("connection"in navigator){const e=navigator.connection;return e.saveData||/2g/.test(e.effectiveType)}return!1}function M(e){e();let r=!1;document.addEventListener("astro:page-load",()=>{if(!r){r=!0;return}e()})}const G=()=>document.querySelectorAll("pre.mermaid").length>0;let b=null;async function le(){return b||(console.log("[astro-mermaid] Loading mermaid.js..."),b=N(()=>import("./mermaid.core.BZzq7Q2a.js").then(e=>e.bq),__vite__mapDeps([0,1,2])).then(async({default:e})=>{const r=[{name:"logos",loader:"() => fetch('https://unpkg.com/@iconify-json/logos@1/icons.json').then(res => res.json())"},{name:"lobe",loader:"() => fetch('https://unpkg.com/@proj-airi/lobe-icons@latest/icons.json').then((res) => res.json())"}];if(r&&r.length>0){console.log("[astro-mermaid] Registering",r.length,"icon packs");const t=r.map(s=>({name:s.name,loader:new Function("return "+s.loader)()}));await e.registerIconPacks(t)}const n=await N(()=>import("./mermaid-layout-elk.core.C8UwlYjx.js").then(t=>t.m),__vite__mapDeps([3,1])).catch(()=>null);return n?.default&&(console.log("[astro-mermaid] Registering elk layouts"),e.registerLayoutLoaders(n.default)),e}).catch(e=>{throw console.error("[astro-mermaid] Failed to load mermaid:",e),b=null,e}),b)}const P={startOnLoad:!1,theme:"forest"},ce={light:"default",dark:"dark"};async function H(){console.log("[astro-mermaid] Initializing mermaid diagrams...");const e=document.querySelectorAll("pre.mermaid");if(console.log("[astro-mermaid] Found",e.length,"mermaid diagrams"),e.length===0)return;const r=await le();let n=P.theme;{const t=document.documentElement.getAttribute("data-theme"),s=document.body.getAttribute("data-theme");n=ce[t||s]||P.theme,console.log("[astro-mermaid] Using theme:",n,"from",t?"html":"body")}r.initialize({...P,theme:n,gitGraph:{mainBranchName:"main",showCommitLabel:!0,showBranches:!0,rotateCommitLabel:!0}});for(const t of e){if(t.hasAttribute("data-processed"))continue;t.hasAttribute("data-diagram")||t.setAttribute("data-diagram",t.textContent||"");const s=t.getAttribute("data-diagram")||"",l="mermaid-"+Math.random().toString(36).slice(2,11);console.log("[astro-mermaid] Rendering diagram:",l);try{const m=document.getElementById(l);m&&m.remove();const{svg:f}=await r.render(l,s);t.innerHTML=f,t.setAttribute("data-processed","true"),console.log("[astro-mermaid] Successfully rendered diagram:",l)}catch(m){console.error("[astro-mermaid] Mermaid rendering error for diagram:",l,m),t.innerHTML=`<div style="color: red; padding: 1rem; border: 1px solid red; border-radius: 0.5rem;">
        <strong>Error rendering diagram:</strong><br/>
        ${m.message||"Unknown error"}
      </div>`,t.setAttribute("data-processed","true")}}}G()?(console.log("[astro-mermaid] Mermaid diagrams detected on initial load"),H()):console.log("[astro-mermaid] No mermaid diagrams found on initial load");{const e=new MutationObserver(r=>{for(const n of r)n.type==="attributes"&&n.attributeName==="data-theme"&&(document.querySelectorAll("pre.mermaid[data-processed]").forEach(t=>{t.removeAttribute("data-processed")}),H())});e.observe(document.documentElement,{attributes:!0,attributeFilter:["data-theme"]}),e.observe(document.body,{attributes:!0,attributeFilter:["data-theme"]})}document.addEventListener("astro:after-swap",()=>{console.log("[astro-mermaid] View transition detected"),G()&&H()});const X=document.createElement("style");X.textContent=`
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
          `;document.head.appendChild(X);function de(e={}){const{position:r="right",smoothScroll:n=!0,threshold:t=30,svgPath:s="M18 15l-6-6-6 6",svgStrokeWidth:l="2",borderRadius:m="15",showTooltip:f=!1,showProgressRing:O=!1,progressRingColor:q="yellow",showOnHomepage:K=!1}=e,z=((o,u)=>{if(typeof o=="string")return o;if(typeof o!="object"||o===null)return"Scroll to top";const i=u&&typeof u=="string"?u.toLowerCase().trim():"";if(!i){const d=o.en;return typeof d=="string"?d:"Scroll to top"}let c=o[i];if(typeof c=="string")return c;if(i.includes("-")){const d=i.split("-")[0];if(c=o[d],typeof c=="string")return c}return c=o.en,typeof c=="string"?c:"Scroll to top"})(e.tooltipText,document.documentElement.lang);let p=null;const Y=()=>document.querySelector(".hero")||document.querySelector(".sl-hero")||document.querySelector('[data-page="index"]')||document.querySelector(".landing-page")||document.querySelector(".homepage")||document.querySelector("[data-starlight-homepage]")||document.querySelector(".site-hero")||document.body.classList.contains("homepage")||document.body.classList.contains("homepage")||document.body.classList.contains("landing")||document.querySelector("main.sl-main")&&document.querySelector("main.sl-main .hero, main.sl-main .sl-hero"),Z=()=>{if(p&&p(),Y()&&!K)return;const o=document.createElement("button");o.id="scroll-to-top-button",o.ariaLabel=z,o.setAttribute("aria-describedby",f?"scroll-to-top-tooltip":""),o.setAttribute("role","button"),o.setAttribute("tabindex","0");let u=!1;o.innerHTML=`
      ${O?`
      <svg class="scroll-progress-ring" 
           width="47"   
           height="47" 
           viewBox="0 0 47 47"
           style="position: absolute; top: 0; left: 0;">
        <!-- Background circle -->
        <circle cx="23.5" cy="23.5" r="22" 
                fill="none" 
                stroke="${q}" 
                stroke-width="3" 
                opacity="0.2" />
        <!-- Progress circle -->
        <circle cx="23.5" cy="23.5" r="22" 
                fill="none" 
                stroke="${q}" 
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
           stroke-width="${l}" 
           stroke-linecap="round" 
           stroke-linejoin="round"
           style="position: relative; z-index: 1;">
        <path d="${s}"/>
      </svg>
    `;const i=document.createElement("div");i.id="scroll-to-top-tooltip",i.textContent=z;const c=document.createElement("div");c.style.cssText=`
    position: absolute;
    top: 100%; /* Position below the tooltip */
    left: 50%;
    transform: translateX(-50%);
    width: 0;
    height: 0;
    border-left: 6px solid transparent;
    border-right: 6px solid transparent;
    border-top: 6px solid var(--sl-color-gray-7);
  `;const d=document.createElement("style");d.id="scroll-to-top-styles",d.textContent=`
    .scroll-to-top-button {
      position: fixed;
      bottom: 40px;
      width: 47px;
      height: 47px;
      ${r==="left"?"left: 40px;":r==="right"?"right: 35px;":"left: 50%;"}
      border-radius: ${m}%;     
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
    `,document.head.appendChild(d),o.classList.add("scroll-to-top-button"),document.body.appendChild(o),f&&(i.classList.add("scroll-to-top-btn-tooltip"),i.appendChild(c),o.appendChild(i));const x=()=>{i.classList.remove("visible")},D=()=>{f&&i.classList.add("visible")};o.addEventListener("mouseenter",()=>{D()}),o.addEventListener("mouseleave",()=>{x()});const T=()=>{x(),window.scrollTo({top:0,behavior:n?"smooth":"auto"}),o.classList.remove("active")};document.addEventListener("keydown",a=>{a.key==="Tab"&&(u=!0)}),o.addEventListener("mousedown",()=>{u=!1}),o.addEventListener("keydown",a=>{a.key==="Enter"&&(T(),o.classList.remove("keyboard-focus"))}),o.addEventListener("focus",()=>{u&&(D(),o.classList.add("keyboard-focus"))}),o.addEventListener("blur",()=>{x(),o.classList.remove("keyboard-focus")}),o.addEventListener("touchstart",a=>{a.preventDefault(),o.classList.add("active")}),o.addEventListener("touchend",a=>{a.preventDefault(),T(),o.classList.remove("active")}),o.addEventListener("click",a=>{a.preventDefault(),T()});function J(a,S){let g;return function(){const y=arguments,A=this;g||(a.apply(A,y),g=!0,setTimeout(()=>g=!1,S))}}const j=()=>{const a=window.scrollY,S=window.innerHeight,g=document.documentElement.scrollHeight,y=a/(g-S);if(O){const $=o.querySelector(".scroll-progress-circle");if($){let h=y*100;h>=99.5&&(h=100),h<0&&(h=0);const I=138.23,Q=I-h/100*I;$.style.strokeDashoffset=Q.toString()}}const A=t>=10&&t<=99?t:30;y>A/100?o.classList.add("visible"):o.classList.remove("visible")},B=J(j,16);window.addEventListener("scroll",B),j();const R=()=>{document.documentElement.classList.contains("theme-dark")?(i.style.backgroundColor="var(--sl-color-gray-7)",i.style.color="var(--sl-color-text)",c.style.borderTopColor="var(--sl-color-gray-7)"):(i.style.backgroundColor="black",i.style.color="white",c.style.borderTopColor="black")};R();const _=new MutationObserver(R);_.observe(document.documentElement,{attributes:!0,attributeFilter:["class"]});function E(){Math.round(window.outerWidth/window.innerWidth*100)/100>3?o.style.display="none":o.style.display="flex"}return window.addEventListener("resize",E),E(),p=()=>{window.removeEventListener("scroll",B),window.removeEventListener("resize",E),_.disconnect(),o&&o.parentNode&&o.parentNode.removeChild(o);const a=document.getElementById("scroll-to-top-styles");a&&a.remove()},p},L=()=>{setTimeout(Z,10)};document.readyState==="loading"?document.addEventListener("DOMContentLoaded",L):L(),document.addEventListener("astro:page-load",L),document.addEventListener("astro:before-preparation",()=>{p&&p()})}de({position:"right",tooltipText:"Scroll to top",smoothScroll:!0,threshold:30,svgPath:"M18 15l-6-6-6 6",svgStrokeWidth:"2",borderRadius:"15",showTooltip:!1,showProgressRing:!1,progressRingColor:"yellow",showOnHomepage:!1});te();export{de as default};
