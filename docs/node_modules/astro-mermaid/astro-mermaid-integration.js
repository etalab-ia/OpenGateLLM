import { resolve } from 'import-meta-resolve';

/**
 * Helper function to HTML-escape text content
 * This ensures HTML tags in mermaid diagrams are preserved as text
 */
function escapeHtml(text) {
  const htmlEntities = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  };
  return text.replace(/[&<>"']/g, char => htmlEntities[char]);
}

/**
 * Remark plugin to transform mermaid code blocks at the markdown level
 */
function remarkMermaidPlugin(options = {}) {
  return async function transformer(tree, file) {
    const { visit } = await import('unist-util-visit');

    let mermaidCount = 0;

    visit(tree, 'code', (node, index, parent) => {
      if (node.lang === 'mermaid') {
        mermaidCount++;

        // Transform to html node with pre.mermaid, escaping HTML content
        const htmlNode = {
          type: 'html',
          value: `<pre class="mermaid">${escapeHtml(node.value)}</pre>`
        };

        // Replace the code node with html node
        if (parent && typeof index === 'number') {
          parent.children[index] = htmlNode;
        }

        if (options.logger) {
          options.logger.info(`Remark transformed mermaid block #${mermaidCount} in ${file.path || 'unknown file'}`);
        }
      }
    });

    if (mermaidCount > 0 && options.logger) {
      options.logger.info(`Remark total mermaid blocks transformed: ${mermaidCount}`);
    }
  };
}

/**
 * Helper function to serialize HAST nodes back to HTML text
 * This preserves HTML tags within the mermaid content
 */
function serializeHastChildren(children) {
  let result = '';

  for (const child of children) {
    if (child.type === 'text') {
      result += child.value;
    } else if (child.type === 'element') {
      // Reconstruct the HTML tag
      const tagName = child.tagName;
      const selfClosing = ['br', 'hr', 'img', 'input', 'meta', 'link'].includes(tagName);

      result += `<${tagName}`;

      // Add attributes if any
      if (child.properties) {
        for (const [key, value] of Object.entries(child.properties)) {
          if (key !== 'className') {
            result += ` ${key}="${value}"`;
          } else if (Array.isArray(value)) {
            result += ` class="${value.join(' ')}"`;
          }
        }
      }

      if (selfClosing) {
        result += '/>';
      } else {
        result += '>';
        if (child.children && child.children.length > 0) {
          result += serializeHastChildren(child.children);
        }
        result += `</${tagName}>`;
      }
    }
  }

  return result;
}

/**
 * Rehype plugin to transform mermaid code blocks
 * Converts ```mermaid code blocks to <pre class="mermaid">
 */
function rehypeMermaidPlugin(options = {}) {
  return async function transformer(tree, file) {
    const { visit } = await import('unist-util-visit');

    let mermaidCount = 0;

    visit(tree, 'element', (node, index, parent) => {
      // Look for <pre><code class="language-mermaid">
      if (
        node.tagName === 'pre' &&
        node.children?.length === 1 &&
        node.children[0].tagName === 'code'
      ) {
        const codeNode = node.children[0];
        const className = codeNode.properties?.className;

        if (Array.isArray(className) && className.includes('language-mermaid')) {
          mermaidCount++;
          // Get the mermaid diagram content, preserving HTML tags
          const diagramContent = serializeHastChildren(codeNode.children || []);

          // Transform to <pre class="mermaid">
          node.properties = {
            ...node.properties,
            className: ['mermaid']
          };

          // Escape HTML to preserve it as text content
          node.children = [{
            type: 'text',
            value: escapeHtml(diagramContent)
          }];

          if (options.logger) {
            options.logger.info(`Rehype transformed mermaid block #${mermaidCount} in ${file.path || 'unknown file'}`);
          }
        }
      }
    });

    if (mermaidCount > 0 && options.logger) {
      options.logger.info(`Rehype total mermaid blocks transformed: ${mermaidCount}`);
    }
  };
}

/** Detect if optional peer dependency `@mermaid-js/layout-elk` is available. */
async function isElkInstalled(logger, consumerRoot) {
  try {
    resolve('@mermaid-js/layout-elk', `${consumerRoot.href}package.json`);
    logger.info('Enabling ELK support');
    return true;
  } catch {
    logger.info('Skipping ELK support');
    return false;
  }
}

/**
 * Astro integration for rendering Mermaid diagrams
 * Supports automatic theme switching and client-side rendering
 *
 * @param {Object} options - Configuration options
 * @param {string} [options.theme='default'] - Default theme ('default', 'dark', 'forest', 'neutral')
 * @param {boolean} [options.autoTheme=true] - Enable automatic theme switching based on data-theme attribute
 * @param {Object} [options.mermaidConfig={}] - Additional mermaid configuration options
 * @returns {import('astro').AstroIntegration}
 */
export default function astroMermaid(options = {}) {
  const {
    theme = 'default',
    autoTheme = true,
    mermaidConfig = {},
    iconPacks = []
  } = options;

  return {
    name: 'astro-mermaid',
    hooks: {
      'astro:config:setup': async ({ config, updateConfig, addWatchFile, injectScript, logger, command }) => {
        logger.info('Setting up Mermaid integration');

        // Log existing rehype plugins
        logger.info('Existing rehype plugins:', config.markdown?.rehypePlugins?.length || 0);

        // Always include mermaid.
        const viteOptimizeDepsInclude = ['mermaid'];
        
        // Conditionally include ELK
        const useElk = await isElkInstalled(logger, config.root);
        if (useElk) {
          viteOptimizeDepsInclude.push('@mermaid-js/layout-elk');
        }

        // Update markdown config to use both remark and rehype plugins
        updateConfig({
          markdown: {
            remarkPlugins: [
              ...(config.markdown?.remarkPlugins || []),
              [remarkMermaidPlugin, { logger }]
            ],
            rehypePlugins: [
              ...(config.markdown?.rehypePlugins || []),
              [rehypeMermaidPlugin, { logger }]
            ]
          },
          vite: {
            optimizeDeps: {
              include: viteOptimizeDepsInclude
            }
          }
        });

        // Serialize icon packs for client-side use
        const iconPacksConfig = iconPacks.map(pack => ({
          name: pack.name,
          loader: pack.loader.toString()
        }));

        // Inject client-side mermaid script with conditional loading
        const mermaidScriptContent = `
// Check if page has mermaid diagrams
const hasMermaidDiagrams = () => {
  return document.querySelectorAll('pre.mermaid').length > 0;
};

// Shared mermaid initialization function
let mermaidPromise = null;
let mermaidInstance = null;

async function loadMermaid() {
  if (mermaidPromise) return mermaidPromise;

  console.log('[astro-mermaid] Loading mermaid.js...');

  mermaidPromise = import('mermaid').then(async ({ default: mermaid }) => {
    // Register icon packs if provided
    const iconPacks = ${JSON.stringify(iconPacksConfig)};
    if (iconPacks && iconPacks.length > 0) {
      console.log('[astro-mermaid] Registering', iconPacks.length, 'icon packs');
      const packs = iconPacks.map(pack => ({
        name: pack.name,
        loader: new Function('return ' + pack.loader)()
      }));
      await mermaid.registerIconPacks(packs);
    }

    // Register ELK layouts if the optional peer is available at build-time
    ${useElk ? `
const elkModule = await import("@mermaid-js/layout-elk").catch(() => null);
if (elkModule?.default) {
  console.log("[astro-mermaid] Registering elk layouts");
  mermaid.registerLayoutLoaders(elkModule.default);
}
` : ``}

    mermaidInstance = mermaid;
    return mermaid;
  }).catch(error => {
    console.error('[astro-mermaid] Failed to load mermaid:', error);
    mermaidPromise = null;
    throw error;
  });

  return mermaidPromise;
}

// Mermaid configuration
const defaultConfig = ${JSON.stringify({
  startOnLoad: false,
  theme: theme,
  ...mermaidConfig
})};

// Theme mapping for auto-theme switching
const themeMap = {
  'light': 'default',
  'dark': 'dark'
};

// Initialize all mermaid diagrams
async function initMermaid() {
  console.log('[astro-mermaid] Initializing mermaid diagrams...');
  const diagrams = document.querySelectorAll('pre.mermaid');

  console.log('[astro-mermaid] Found', diagrams.length, 'mermaid diagrams');

  if (diagrams.length === 0) {
    return;
  }

  // Load mermaid if not already loaded
  const mermaid = await loadMermaid();

  // Get current theme from multiple sources
  let currentTheme = defaultConfig.theme;

  if (${autoTheme}) {
    // Check both html and body for data-theme attribute
    const htmlTheme = document.documentElement.getAttribute('data-theme');
    const bodyTheme = document.body.getAttribute('data-theme');
    const dataTheme = htmlTheme || bodyTheme;
    currentTheme = themeMap[dataTheme] || defaultConfig.theme;
    console.log('[astro-mermaid] Using theme:', currentTheme, 'from', htmlTheme ? 'html' : 'body');
  }

  // Configure mermaid with gitGraph support
  mermaid.initialize({
    ...defaultConfig,
    theme: currentTheme,
    gitGraph: {
      mainBranchName: 'main',
      showCommitLabel: true,
      showBranches: true,
      rotateCommitLabel: true
    }
  });

  // Render each diagram
  for (const diagram of diagrams) {
    // Skip if already processed
    if (diagram.hasAttribute('data-processed')) continue;

    // Store original content
    if (!diagram.hasAttribute('data-diagram')) {
      diagram.setAttribute('data-diagram', diagram.textContent || '');
    }

    const diagramDefinition = diagram.getAttribute('data-diagram') || '';
    const id = 'mermaid-' + Math.random().toString(36).slice(2, 11);

    console.log('[astro-mermaid] Rendering diagram:', id);

    try {
      // Clear any existing error state
      const existingGraph = document.getElementById(id);
      if (existingGraph) {
        existingGraph.remove();
      }

      const { svg } = await mermaid.render(id, diagramDefinition);
      diagram.innerHTML = svg;
      diagram.setAttribute('data-processed', 'true');
      console.log('[astro-mermaid] Successfully rendered diagram:', id);
    } catch (error) {
      console.error('[astro-mermaid] Mermaid rendering error for diagram:', id, error);
      diagram.innerHTML = \`<div style="color: red; padding: 1rem; border: 1px solid red; border-radius: 0.5rem;">
        <strong>Error rendering diagram:</strong><br/>
        \${error.message || 'Unknown error'}
      </div>\`;
      diagram.setAttribute('data-processed', 'true');
    }
  }
}

// Initialize on first load if there are diagrams
if (hasMermaidDiagrams()) {
  console.log('[astro-mermaid] Mermaid diagrams detected on initial load');
  initMermaid();
} else {
  console.log('[astro-mermaid] No mermaid diagrams found on initial load');
}

// Re-render on theme change if auto-theme is enabled
if (${autoTheme}) {
  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      if (mutation.type === 'attributes' && mutation.attributeName === 'data-theme') {
        // Reset processed state and re-render
        document.querySelectorAll('pre.mermaid[data-processed]').forEach(diagram => {
          diagram.removeAttribute('data-processed');
        });
        initMermaid();
      }
    }
  });

  // Observe both html and body for data-theme changes
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-theme']
  });
  observer.observe(document.body, {
    attributes: true,
    attributeFilter: ['data-theme']
  });
}

// Handle view transitions (for Astro View Transitions API)
// This is registered ALWAYS, not just when initial page has diagrams
document.addEventListener('astro:after-swap', () => {
  console.log('[astro-mermaid] View transition detected');
  // Check if new page has diagrams
  if (hasMermaidDiagrams()) {
    initMermaid();
  }
});
`;

        injectScript('page', mermaidScriptContent);

        // Add CSS to the page with layout shift prevention
        injectScript('page', `
          // Add CSS for mermaid diagrams
          const style = document.createElement('style');
          style.textContent = \`
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
          \`;
          document.head.appendChild(style);
        `);
      }
    }
  };
}
