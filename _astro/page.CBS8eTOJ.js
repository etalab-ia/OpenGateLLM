const __vite__mapDeps=(i,m=__vite__mapDeps,d=(m.f||(m.f=["_astro/mermaid.core.YvTXrFxq.js","_astro/src.bJO6PwwU.js","_astro/preload-helper.CxFQXtKk.js","_astro/chunk-AGHRB4JF.CROZz2So.js","_astro/chunk-5ZQYHXKU.LMSgRgAK.js","_astro/dist.COb4Bndm.js","_astro/chunk-CSCIHK7Q.DUx9o0jO.js","_astro/chunk-O5CBEL6O.ChsxFULu.js","_astro/chunk-BSJP7CBP.BG17UDkX.js","_astro/chunk-L5ZTLDWV.B0F-uKM2.js","_astro/chunk-NZK2D7GU.BTmXUBBX.js","_astro/chunk-3OPIFGDE.DQgGdtE-.js","_astro/rough.esm.Dy-Kn_BL.js","_astro/chunk-KSCS5N6A.C2c1JGry.js","_astro/line.DnRNdJKN.js","_astro/path.fybaL0A-.js","_astro/array.BifhSqXX.js","_astro/mermaid-layout-elk.core.B6u4Rzwp.js"])))=>i.map(i=>d[i]);
import{t as e}from"./preload-helper.CxFQXtKk.js";var t={},n=new Set,r=new WeakSet,i=!0,a=void 0,o=!1;function s(e){o||(o=!0,i??=e?.prefetchAll??!1,a??=e?.defaultStrategy??`hover`,c(),l(),u(),f())}function c(){for(let e of[`touchstart`,`mousedown`])document.addEventListener(e,e=>{let t=e.target.closest(`a`);h(t,`tap`)&&p(t.href,{ignoreSlowConnection:!0})},{passive:!0})}function l(){let e;document.body.addEventListener(`focusin`,e=>{let n=e.target.closest(`a`);h(n,`hover`)&&t(n.href)},{passive:!0}),document.body.addEventListener(`focusout`,n,{passive:!0}),_(()=>{for(let e of document.getElementsByTagName(`a`))r.has(e)||h(e,`hover`)&&(r.add(e),e.addEventListener(`mouseenter`,e=>t(e.currentTarget.href),{passive:!0}),e.addEventListener(`mouseleave`,n,{passive:!0}))});function t(t){e&&clearTimeout(e),e=setTimeout(()=>{p(t)},80)}function n(){e&&=(clearTimeout(e),0)}}function u(){let e;_(()=>{for(let t of document.getElementsByTagName(`a`))r.has(t)||h(t,`viewport`)&&(r.add(t),e??=d(),e.observe(t))})}function d(){let e=new WeakMap;return new IntersectionObserver((t,n)=>{for(let r of t){let t=r.target,i=e.get(t);r.isIntersecting?(i&&clearTimeout(i),e.set(t,setTimeout(()=>{n.unobserve(t),e.delete(t),p(t.href)},300))):i&&(clearTimeout(i),e.delete(t))}})}function f(){_(()=>{for(let e of document.getElementsByTagName(`a`))h(e,`load`)&&p(e.href)})}function p(e,r){e=e.replace(/#.*/,``);let i=r?.ignoreSlowConnection??!1;if(m(e,i)){if(n.add(e),document.createElement(`link`).relList?.supports?.(`prefetch`)){let t=document.createElement(`link`);t.rel=`prefetch`,t.setAttribute(`href`,e),document.head.append(t)}else{let n=new Headers;for(let[e,r]of Object.entries(t))n.set(e,r);fetch(e,{priority:`low`,headers:n}).catch(()=>{})}}}function m(e,t){if(!navigator.onLine||!t&&g())return!1;try{let t=new URL(e,location.href);return location.origin===t.origin&&(location.pathname!==t.pathname||location.search!==t.search)&&!n.has(e)}catch{}return!1}function h(e,t){if(e?.tagName!==`A`)return!1;let n=e.dataset.astroPrefetch;return n===`false`?!1:t===`tap`&&(n!=null||i)&&g()?!0:n==null&&i||n===``?t===a:n===t}function g(){if(`connection`in navigator){let e=navigator.connection;return e.saveData||/2g/.test(e.effectiveType)}return!1}function _(e){e();let t=!1;document.addEventListener(`astro:page-load`,()=>{if(!t){t=!0;return}e()}),new MutationObserver(t=>{for(let n of t)for(let t of n.addedNodes)if(t instanceof Element&&(t.tagName===`A`||t.querySelector?.(`a`))){e();return}}).observe(document.body,{childList:!0,subtree:!0})}var v=(...e)=>console.log(`[astro-mermaid]`,...e),y=(...e)=>console.error(`[astro-mermaid]`,...e),b=()=>document.querySelectorAll(`pre.mermaid`).length>0,x=null;async function S(){return x||(v(`Loading mermaid.js...`),x=e(async()=>{let{default:e}=await import(`./mermaid.core.YvTXrFxq.js`);return{default:e}},__vite__mapDeps([0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16])).then(async({default:t})=>{let n=[{name:`logos`,url:`https://unpkg.com/@iconify-json/logos@1/icons.json`},{name:`lobe`,url:`https://unpkg.com/@proj-airi/lobe-icons@latest/icons.json`}];if(n&&n.length>0){v(`Registering`,n.length,`icon packs`);let e=n.map(e=>({name:e.name,loader:()=>fetch(e.url).then(e=>e.json())}));await t.registerIconPacks(e)}let r=await e(()=>import(`./mermaid-layout-elk.core.B6u4Rzwp.js`).then(e=>e.t),__vite__mapDeps([17,1,2])).catch(()=>null);return r?.default&&(v(`Registering elk layouts`),t.registerLayoutLoaders(r.default)),t}).catch(e=>{throw y(`Failed to load mermaid:`,e),x=null,e}),x)}var C={startOnLoad:!1,theme:`forest`},w={light:`default`,dark:`dark`};async function T(){v(`Initializing mermaid diagrams...`);let e=document.querySelectorAll(`pre.mermaid`);if(v(`Found`,e.length,`mermaid diagrams`),e.length===0)return;let t=await S(),n=C.theme;{let e=document.documentElement.getAttribute(`data-theme`),t=document.body.getAttribute(`data-theme`);n=w[e||t]||C.theme,v(`Using theme:`,n,`from`,e?`html`:`body`)}t.initialize({...C,theme:n,gitGraph:{mainBranchName:`main`,showCommitLabel:!0,showBranches:!0,rotateCommitLabel:!0}});for(let n of e){if(n.hasAttribute(`data-processed`))continue;n.hasAttribute(`data-diagram`)||n.setAttribute(`data-diagram`,n.textContent||``);let e=n.getAttribute(`data-diagram`)||``,r=`mermaid-`+Math.random().toString(36).slice(2,11);v(`Rendering diagram:`,r);try{let i=document.getElementById(r);i&&i.remove();let{svg:a}=await t.render(r,e);n.innerHTML=a,n.setAttribute(`data-processed`,`true`),v(`Successfully rendered diagram:`,r)}catch(e){y(`Mermaid rendering error for diagram:`,r,e);let t=document.createElement(`div`);t.style.cssText=`color: red; padding: 1rem; border: 1px solid red; border-radius: 0.5rem;`;let i=document.createElement(`strong`);i.textContent=`Error rendering diagram:`;let a=document.createElement(`span`);a.textContent=` `+(e.message||`Unknown error`),t.appendChild(i),t.appendChild(a),n.textContent=``,n.appendChild(t),n.setAttribute(`data-processed`,`true`)}}}b()?(v(`Mermaid diagrams detected on initial load`),T()):v(`No mermaid diagrams found on initial load`);{let e=new MutationObserver(e=>{for(let t of e)t.type===`attributes`&&t.attributeName===`data-theme`&&(document.querySelectorAll(`pre.mermaid[data-processed]`).forEach(e=>{e.removeAttribute(`data-processed`)}),T())});e.observe(document.documentElement,{attributes:!0,attributeFilter:[`data-theme`]}),e.observe(document.body,{attributes:!0,attributeFilter:[`data-theme`]})}document.addEventListener(`astro:after-swap`,()=>{v(`View transition detected`),b()&&T()});var E=document.createElement(`style`);E.textContent=`
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
          `,document.head.appendChild(E);function D(e={}){let{position:t=`right`,smoothScroll:n=!0,threshold:r=300,svgPath:i=`M18 15l-6-6-6 6`,svgStrokeWidth:a=`2`,borderRadius:o=`15`,showTooltip:s=!1,showProgressRing:c=!1,progressRingColor:l=`yellow`,showOnHomepage:u=!1}=e,d=((e,t)=>{if(typeof e==`string`)return e;if(typeof e!=`object`||!e)return`Scroll to top`;let n=t&&typeof t==`string`?t.toLowerCase().trim():``;if(!n){let t=e.en;return typeof t==`string`?t:`Scroll to top`}let r=e[n];return typeof r==`string`||n.includes(`-`)&&(r=e[n.split(`-`)[0]],typeof r==`string`)||(r=e.en,typeof r==`string`)?r:`Scroll to top`})(e.tooltipText,document.documentElement.lang),f=null,p=()=>document.querySelector(`.hero`)||document.querySelector(`.sl-hero`)||document.querySelector(`[data-page="index"]`)||document.querySelector(`.landing-page`)||document.querySelector(`.homepage`)||document.querySelector(`[data-starlight-homepage]`)||document.querySelector(`.site-hero`)||document.body.classList.contains(`homepage`)||document.body.classList.contains(`homepage`)||document.body.classList.contains(`landing`)||document.querySelector(`main.sl-main`)&&document.querySelector(`main.sl-main .hero, main.sl-main .sl-hero`),m=()=>{if(f&&f(),p()&&!u)return;let e=document.createElement(`button`);e.id=`scroll-to-top-button`,e.ariaLabel=d,e.setAttribute(`aria-describedby`,s?`scroll-to-top-tooltip`:``),e.setAttribute(`role`,`button`),e.setAttribute(`tabindex`,`0`);let m=!1;e.innerHTML=`
      ${c?`
      <svg class="scroll-progress-ring" 
           width="47"   
           height="47" 
           viewBox="0 0 47 47"
           style="position: absolute; top: 0; left: 0;">
        <!-- Background circle -->
        <circle cx="23.5" cy="23.5" r="22" 
                fill="none" 
                stroke="${l}" 
                stroke-width="3" 
                opacity="0.2" />
        <!-- Progress circle -->
        <circle cx="23.5" cy="23.5" r="22" 
                fill="none" 
                stroke="${l}" 
                stroke-width="3" 
                stroke-linecap="round"
                class="scroll-progress-circle"
                style="transform: rotate(-90deg); transform-origin: center;" />
      </svg>
      `:``}
      <svg xmlns="http://www.w3.org/2000/svg" 
           width="35" 
           height="35" 
           viewBox="0 0 24 24"            
           fill="none" 
           stroke="currentColor" 
           stroke-width="${a}" 
           stroke-linecap="round" 
           stroke-linejoin="round"
           style="position: relative; z-index: 1;">
        <path d="${i}"/>
      </svg>
    `;let h=document.createElement(`div`);h.id=`scroll-to-top-tooltip`,h.textContent=d;let g=document.createElement(`div`);g.style.cssText=`
    position: absolute;
    top: 100%; /* Position below the tooltip */
    left: 50%;
    transform: translateX(-50%);
    width: 0;
    height: 0;
    border-left: 6px solid transparent;
    border-right: 6px solid transparent;
    border-top: 6px solid var(--sl-color-gray-7);
  `;let _=document.createElement(`style`);_.id=`scroll-to-top-styles`,_.textContent=`
    .scroll-to-top-button {
      position: fixed;
      bottom: 40px;
      width: 47px;
      height: 47px;
      ${t===`left`?`left: 40px;`:t===`right`?`right: 35px;`:`left: 50%;`}
      border-radius: ${o}%;     
      background-color: var(--sl-color-accent);       
      color: white;
      cursor: pointer;
      display: flex;
      align-items: center;      
      justify-content: center;
      opacity: 0;
      visibility: hidden;
      transform: ${t===`center`?`translateX(-50%) scale(0)`:`scale(0)`};
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
        transform: ${t===`center`?`translateX(-50%) scale(1)`:`scale(1)`};        
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
        ${t===`left`?`left: -25px;`:`right: -22px;`}
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
    `,document.head.appendChild(_),e.classList.add(`scroll-to-top-button`),document.body.appendChild(e),s&&(h.classList.add(`scroll-to-top-btn-tooltip`),h.appendChild(g),e.appendChild(h));let v=()=>{h.classList.remove(`visible`)},y=()=>{s&&h.classList.add(`visible`)};e.addEventListener(`mouseenter`,()=>{y()}),e.addEventListener(`mouseleave`,()=>{v()});let b=()=>{v(),window.scrollTo({top:0,behavior:n?`smooth`:`auto`}),e.classList.remove(`active`)};document.addEventListener(`keydown`,e=>{e.key===`Tab`&&(m=!0)}),e.addEventListener(`mousedown`,()=>{m=!1}),e.addEventListener(`keydown`,t=>{t.key===`Enter`&&(b(),e.classList.remove(`keyboard-focus`))}),e.addEventListener(`focus`,()=>{m&&(y(),e.classList.add(`keyboard-focus`))}),e.addEventListener(`blur`,()=>{v(),e.classList.remove(`keyboard-focus`)}),e.addEventListener(`touchstart`,t=>{t.preventDefault(),e.classList.add(`active`)}),e.addEventListener(`touchend`,t=>{t.preventDefault(),b(),e.classList.remove(`active`)}),e.addEventListener(`click`,e=>{e.preventDefault(),b()});function x(e,t){let n;return function(){let r=arguments,i=this;n||(e.apply(i,r),n=!0,setTimeout(()=>n=!1,t))}}let S=()=>{let t=window.scrollY,n=window.innerHeight,i=t/(document.documentElement.scrollHeight-n);if(c){let t=e.querySelector(`.scroll-progress-circle`);if(t){let e=i*100;e>=99.5&&(e=100),e<0&&(e=0);let n=138.23,r=n-e/100*n;t.style.strokeDashoffset=r.toString()}}t>(r>0?r:300)?e.classList.add(`visible`):e.classList.remove(`visible`)},C=x(S,16);window.addEventListener(`scroll`,C),S();let w=()=>{document.documentElement.classList.contains(`theme-dark`)?(h.style.backgroundColor=`var(--sl-color-gray-7)`,h.style.color=`var(--sl-color-text)`,g.style.borderTopColor=`var(--sl-color-gray-7)`):(h.style.backgroundColor=`black`,h.style.color=`white`,g.style.borderTopColor=`black`)};w();let T=new MutationObserver(w);T.observe(document.documentElement,{attributes:!0,attributeFilter:[`class`]});function E(){Math.round(window.outerWidth/window.innerWidth*100)/100>3?e.style.display=`none`:e.style.display=`flex`}return window.addEventListener(`resize`,E),E(),f=()=>{window.removeEventListener(`scroll`,C),window.removeEventListener(`resize`,E),T.disconnect(),e&&e.parentNode&&e.parentNode.removeChild(e);let t=document.getElementById(`scroll-to-top-styles`);t&&t.remove()},f},h=()=>{setTimeout(m,10)};document.readyState===`loading`?document.addEventListener(`DOMContentLoaded`,h):h(),document.addEventListener(`astro:page-load`,h),document.addEventListener(`astro:before-preparation`,()=>{f&&f()})}D({position:`right`,tooltipText:`Scroll to top`,smoothScroll:!0,threshold:300,svgPath:`M18 15l-6-6-6 6`,svgStrokeWidth:`2`,borderRadius:`15`,showTooltip:!1,showProgressRing:!1,progressRingColor:`yellow`,showOnHomepage:!1}),s();export{D as default};