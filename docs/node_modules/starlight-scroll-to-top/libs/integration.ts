import type { AstroIntegration } from 'astro';
import { fileURLToPath } from 'node:url';
import { join, dirname } from 'node:path';
import { readFileSync } from 'node:fs';
import type ScrollToTopOptions from '../common/types.js';
// Get directory path of current file
const __dirname = dirname(fileURLToPath(import.meta.url));


export default function starlightScrollToTopIntegration(options: ScrollToTopOptions = {}): AstroIntegration {
  // Set default options.
  const config = {
    position: "right",
    tooltipText: "Scroll to top",
    smoothScroll: true,
    threshold: 30, // Default: show when scrolled 30% down.
    svgPath: "M18 15l-6-6-6 6",
    svgStrokeWidth: "2",
    borderRadius: "15",
    showTooltip: false,
    showProgressRing: false,
    progressRingColor: "yellow",
    showOnHomepage: false,    
    ...options
  };

  return {
    name: 'starlight-scroll-to-top',
    hooks: {
      'astro:config:setup': async ({ injectScript }) => {

        // Read the scroll-to-top JavaScript file
        const fileContent = readFileSync(join(__dirname, 'scroll-to-top.js'), 'utf-8');

        // Inject client-side script that will be processed and minified by Astro/Vite
        // Using 'page' mode so Vite will automatically minify and optimize the script
        injectScript('page', `
            ${fileContent};
            initScrollToTop(${JSON.stringify(config)});          
          `);
      },
      'astro:build:done': ({ logger }) => {
        logger.info(`Starlight Scroll To Top plugin has been installed successfully! Button position: ${config.position}`);
      }
    }
  };
}
