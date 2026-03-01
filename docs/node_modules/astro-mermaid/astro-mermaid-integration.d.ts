import type { AstroIntegration } from 'astro';

export interface IconPack {
  /**
   * Name of the icon pack
   */
  name: string;
  
  /**
   * Function that returns a promise resolving to the icon pack data
   */
  loader: () => Promise<any>;
}

export interface AstroMermaidOptions {
  /**
   * Default mermaid theme
   * @default 'default'
   */
  theme?: 'default' | 'dark' | 'forest' | 'neutral' | 'base';
  
  /**
   * Enable automatic theme switching based on data-theme attribute
   * @default true
   */
  autoTheme?: boolean;
  
  /**
   * Additional mermaid configuration options
   * @see https://mermaid.js.org/config/setup/modules/mermaidAPI.html#mermaidapi-configuration-defaults
   */
  mermaidConfig?: Record<string, any>;
  
  /**
   * Icon packs to register with mermaid
   * @example
   * ```js
   * iconPacks: [
   *   {
   *     name: 'logos',
   *     loader: () => fetch('https://unpkg.com/@iconify-json/logos@1/icons.json').then(res => res.json())
   *   }
   * ]
   * ```
   */
  iconPacks?: IconPack[];
}

/**
 * Astro integration for rendering Mermaid diagrams
 * 
 * @example
 * ```js
 * import { defineConfig } from 'astro/config';
 * import mermaid from 'astro-mermaid';
 * 
 * export default defineConfig({
 *   integrations: [
 *     mermaid({
 *       theme: 'forest',
 *       autoTheme: true
 *     })
 *   ]
 * });
 * ```
 */
export default function astroMermaid(options?: AstroMermaidOptions): AstroIntegration;