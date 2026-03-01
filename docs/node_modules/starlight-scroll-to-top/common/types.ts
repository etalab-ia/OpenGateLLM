// Define configuration options type
export default interface ScrollToTopOptions {
  /**
   * Position of the scroll to top button
   * @default 'right'
   */
  position?: 'left' | 'right'| 'center';
  
  /**
   * Text to show in the tooltip. Can be a string for single language support
   * or an object with language codes as keys for internationalization (I18N).
   * @example 'Scroll to top'
   * @example { 'en': 'Scroll to top', 'es': 'Ir arriba', 'fr': 'Retour en haut' }
   * @default 'Scroll to top'
   */
  tooltipText?: string | Record<string, string>;

  /**
   * Whether to show the tooltip on hover.
   * @default false    
   */
  showTooltip?: boolean;

  /**
   * Whether to use smooth scrolling.
   * @default true
   */
  smoothScroll?: boolean;

  /**
   * Height after page scroll to be visible (percentage).
   * @default 30
   */
  threshold?: number;

  /**
   * The SVG icon path d attribute.
   * @default "M18 15l-6-6-6 6"
   */
  svgPath?: string;

  
  /**
   * The SVG icon stroke width.
   * @default "2" 
   */
  svgStrokeWidth?: number;
  
  /**
   * The radius of the button corners. 50% for circle, 0% for square.
   * @default "15"
   */
  borderRadius?: string;

  /**
   * Whether to show a circular progress ring around the button.
   * @default false
   */
  showProgressRing?: boolean;

  /**
   * Color of the scroll progress ring (CSS color value).
   * @default "yellow"
   */
  progressRingColor?: string;

  /**
   * Whether to show the scroll-to-top button on the homepage/landing page.
   * When false, the button will be hidden on pages with hero/landing elements.
   * @default false
   */
  showOnHomepage?: boolean;
}