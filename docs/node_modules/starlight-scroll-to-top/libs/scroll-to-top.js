/**
 * Creates and manages the scroll-to-top button
 * @param {Object} config - Configuration options
 * @param {string} config.position - Button position relative to the bottom corner of the page ('left' or 'right')
 * @param {string|Object} config.tooltipText - Text to show in the tooltip. Can be a string for single language or an object with language codes as keys for I18N support
 * @param {boolean} config.smoothScroll - Whether to use smooth scrolling
 * @param {number} config.threshold - Height after page scroll to be visible (percentage)
 * @param {string} config.svgPath - The SVG icon path d attribute
 * @param {number} config.borderRadius - The radius of the button corners, 50 for circle.
 * @param {boolean} config.showTooltip - Whether to show the tooltip on hover
 * @param {boolean} config.svgStrokeWidth - The SVG icon stroke width
 * @param {boolean} config.showOnHomepage - Whether to show the button on homepage/landing pages
 */
function initScrollToTop(config = {}) {
  const {
    position = "right",
    smoothScroll = true,
    threshold = 30, // Default: show when scrolled 30% down
    svgPath = "M18 15l-6-6-6 6",
    svgStrokeWidth = "2",
    borderRadius = "15",
    showTooltip = false,
    showProgressRing = false,
    progressRingColor = "yellow",
    showOnHomepage = false,    
  } = config;

  // Enhanced tooltip text resolution with hierarchical language fallback.
  const resolveTooltipText = (tooltipConfig, documentLang) => {
    // If it's a string, use it directly.
    if (typeof tooltipConfig === 'string') {
      return tooltipConfig;
    }
    
    // If it's not an object, use default.
    if (typeof tooltipConfig !== 'object' || tooltipConfig === null) {
      return "Scroll to top";
    }
    
    // Normalize language code (lowercase, handle empty/null).
    const normalizedLang = documentLang && typeof documentLang === 'string' 
      ? documentLang.toLowerCase().trim() 
      : '';
    
    if (!normalizedLang) {
      // No valid language code, try 'en' or use default.
      const fallback = tooltipConfig['en'];
      return (typeof fallback === 'string') ? fallback : "Scroll to top";
    }
    
    // Try exact match first (e.g., "en-us").
    let match = tooltipConfig[normalizedLang];
    if (typeof match === 'string') {
      return match;
    }
    
    // Try base language if it's a variant (e.g., "en-us" → "en").
    if (normalizedLang.includes('-')) {
      const baseLang = normalizedLang.split('-')[0];
      match = tooltipConfig[baseLang];
      if (typeof match === 'string') {
        return match;
      }
    }
    
    // Try 'en' as common fallback.
    match = tooltipConfig['en'];
    if (typeof match === 'string') {
      return match;
    }
    
    // Use default fallback.
    return "Scroll to top";
  };

  const tooltipText = resolveTooltipText(config.tooltipText, document.documentElement.lang);

  // Store cleanup function globally to handle view transitions.
  let cleanup = null;

  // Check if current page is homepage using DOM content detection.
  const isHomepage = () => {
    // Check for common homepage/hero elements in Starlight.
    return document.querySelector('.hero') || 
           document.querySelector('.sl-hero') ||
           document.querySelector('[data-page="index"]') ||
           document.querySelector('.landing-page') ||
           document.querySelector('.homepage') ||
           document.querySelector('[data-starlight-homepage]') ||
           document.querySelector('.site-hero') ||
           // Check if body has homepage-related classes.
           document.body.classList.contains('homepage') ||
           document.body.classList.contains('homepage') ||
           document.body.classList.contains('landing') ||
           // Check for Starlight's main content wrapper with hero content.
           (document.querySelector('main.sl-main') && 
            document.querySelector('main.sl-main .hero, main.sl-main .sl-hero'));
  };

  const initButton = () => {
    // Clean up existing button if it exists. 
    if (cleanup) {
      cleanup();
    }

    // Skip button creation if this is the homepage and showOnHomepage is false.  
    if (isHomepage() && !showOnHomepage) {
      return;
    }
    // Create the button element.
    const scrollToTopButton = document.createElement("button");
    scrollToTopButton.id = "scroll-to-top-button";
    scrollToTopButton.ariaLabel = tooltipText;
    scrollToTopButton.setAttribute('aria-describedby', showTooltip ? 'scroll-to-top-tooltip' : '');
    scrollToTopButton.setAttribute('role', 'button');
    scrollToTopButton.setAttribute('tabindex', '0');
    let isKeyboard = false;

    // Add button with configurable SVG icon and optional progress ring.
    scrollToTopButton.innerHTML = `
      ${showProgressRing ? `
      <svg class="scroll-progress-ring" 
           width="47"   
           height="47" 
           viewBox="0 0 47 47"
           style="position: absolute; top: 0; left: 0;">
        <!-- Background circle -->
        <circle cx="23.5" cy="23.5" r="22" 
                fill="none" 
                stroke="${progressRingColor}" 
                stroke-width="3" 
                opacity="0.2" />
        <!-- Progress circle -->
        <circle cx="23.5" cy="23.5" r="22" 
                fill="none" 
                stroke="${progressRingColor}" 
                stroke-width="3" 
                stroke-linecap="round"
                class="scroll-progress-circle"
                style="transform: rotate(-90deg); transform-origin: center;" />
      </svg>
      ` : ''}
      <svg xmlns="http://www.w3.org/2000/svg" 
           width="35" 
           height="35" 
           viewBox="0 0 24 24"            
           fill="none" 
           stroke="currentColor" 
           stroke-width="${svgStrokeWidth}" 
           stroke-linecap="round" 
           stroke-linejoin="round"
           style="position: relative; z-index: 1;">
        <path d="${svgPath}"/>
      </svg>
    `;

    // Create tooltip element.
    const tooltip = document.createElement("div");
    tooltip.id = "scroll-to-top-tooltip";
    tooltip.textContent = tooltipText;

    // Create the arrow element.
    const arrow = document.createElement("div");
    arrow.style.cssText = `
    position: absolute;
    top: 100%; /* Position below the tooltip */
    left: 50%;
    transform: translateX(-50%);
    width: 0;
    height: 0;
    border-left: 6px solid transparent;
    border-right: 6px solid transparent;
    border-top: 6px solid var(--sl-color-gray-7);
  `;

    // Create the custom style element.
    const customStyle = document.createElement("style");
    customStyle.id = "scroll-to-top-styles";
    customStyle.textContent = `
    .scroll-to-top-button {
      position: fixed;
      bottom: 40px;
      width: 47px;
      height: 47px;
      ${
        position === "left"
          ? "left: 40px;"
          : position === "right"
            ? "right: 35px;"
            : "left: 50%;"
      }
      border-radius: ${borderRadius}%;     
      background-color: var(--sl-color-accent);       
      color: white;
      cursor: pointer;
      display: flex;
      align-items: center;      
      justify-content: center;
      opacity: 0;
      visibility: hidden;
      transform: ${position === "center" ? "translateX(-50%) scale(0)" : "scale(0)"};
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
        transform: ${position === "center" ? "translateX(-50%) scale(1)" : "scale(1)"};        
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
        ${position === "left" ? "left: -25px;" : "right: -22px;"}
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
    `;
    document.head.appendChild(customStyle);
    scrollToTopButton.classList.add("scroll-to-top-button");
    // Add the button to the body.
    document.body.appendChild(scrollToTopButton);

    // Add tooltip to the button's container.
    if (showTooltip) {
      tooltip.classList.add("scroll-to-top-btn-tooltip");
      tooltip.appendChild(arrow);
      scrollToTopButton.appendChild(tooltip);
    }
    
    const hideTooltip = () => {
      tooltip.classList.remove("visible");
    };
    const openTooltip = () => {
      if (showTooltip) {
        tooltip.classList.add("visible");
      }
    };

    // Add tooltip display on hover.
    scrollToTopButton.addEventListener("mouseenter", () => {
      openTooltip();
    });

    scrollToTopButton.addEventListener("mouseleave", () => {
      hideTooltip();
    });

    const doScrollToTop = () => {
      hideTooltip();
      window.scrollTo({
        top: 0,
        behavior: smoothScroll ? "smooth" : "auto",
      });
      // Explicitly reset styles after scroll.      
      scrollToTopButton.classList.remove("active");
    };

    // Detect keyboard input globally (e.g., Tab key).
    //This ensures that the isKeyboard flag is set as soon as the Tab key is pressed, before the focus event is triggered on the button.
    document.addEventListener("keydown", (event) => {
      if (event.key === "Tab") {
        isKeyboard = true;
      }
    });
    // Detect mouse input.
    scrollToTopButton.addEventListener("mousedown", () => {
      isKeyboard = false;
    });
    // Detect keyboard input (e.g., Tab key).
    scrollToTopButton.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        doScrollToTop();
        // Hide focus style.
        scrollToTopButton.classList.remove("keyboard-focus");
      }
    });

    // Handle focus event for buttons.
    scrollToTopButton.addEventListener("focus", () => {
      if (isKeyboard) {
        // We only need to outline the button when it focused using the keyboard.
        openTooltip();
        scrollToTopButton.classList.add("keyboard-focus");
      }
    });
    scrollToTopButton.addEventListener("blur", () => {
      hideTooltip();
      scrollToTopButton.classList.remove("keyboard-focus");
    });

    // Handle mobile taps.
    scrollToTopButton.addEventListener("touchstart", (e) => {
      e.preventDefault(); // Prevent default touch behavior.
      scrollToTopButton.classList.add("active");
    });

    scrollToTopButton.addEventListener("touchend", (e) => {
      e.preventDefault(); // Prevent default touch behavior.
      doScrollToTop();
      scrollToTopButton.classList.remove("active");      
    });

    // Add click event to scroll to top with smooth scrolling option.
    // Handle desktop clicks.
    scrollToTopButton.addEventListener("click", (e) => {
      e.preventDefault(); // Prevent default click behavior.
      doScrollToTop();
    });

    // Throttle function for performance optimization.
    function throttle(func, limit) {
      let inThrottle;
      return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
          func.apply(context, args);
          inThrottle = true;
          setTimeout(() => inThrottle = false, limit);
        }
      }
    }

    // Show/hide the button based on scroll position.
    const toggleScrollToTopButton = () => {
      const scrollPosition = window.scrollY;
      const viewportHeight = window.innerHeight;
      const pageHeight = document.documentElement.scrollHeight;

      // Calculate how far down the page the user has scrolled.
      const scrollPercentage = scrollPosition / (pageHeight - viewportHeight);

      // Update progress ring if enabled
      if (showProgressRing) {
        const progressCircle = scrollToTopButton.querySelector('.scroll-progress-circle');
        if (progressCircle) {
          // Calculate progress as percentage (0-100)
          let progress = scrollPercentage * 100;
          if (progress >= 99.5) progress = 100;
          if (progress < 0) progress = 0;
          
          // Calculate stroke-dashoffset (full circumference - progress)
          const circumference = 138.23; // 2 * π * 22
          const offset = circumference - (progress / 100) * circumference;
          progressCircle.style.strokeDashoffset = offset.toString();
        }
      }

      // Ensure threshold is between 10 and 99.
      const thresholdValue =
        threshold >= 10 && threshold <= 99 ? threshold : 30;

      if (scrollPercentage > thresholdValue / 100) {
        // Show when scrolled past configured threshold.
        scrollToTopButton.classList.add("visible");
      } else {
        scrollToTopButton.classList.remove("visible");
      }
    };

    // Add throttled scroll event listener (16ms ≈ 60fps).
    const throttledScrollHandler = throttle(toggleScrollToTopButton, 16);
    window.addEventListener("scroll", throttledScrollHandler);

    // Initial check on page load.
    toggleScrollToTopButton();

    // Handle theme changes by applying appropriate styles.
    const updateThemeStyles = () => {
      const isDarkTheme =
        document.documentElement.classList.contains("theme-dark");
      if (isDarkTheme) {
        tooltip.style.backgroundColor = "var(--sl-color-gray-7)";
        tooltip.style.color = "var(--sl-color-text)";
        arrow.style.borderTopColor = "var(--sl-color-gray-7)";
      } else {
        tooltip.style.backgroundColor = "black";
        tooltip.style.color = "white";
        arrow.style.borderTopColor = "black";
      }
    };

    // Initial theme check.
    updateThemeStyles();

    // Monitor theme changes.
    const observer = new MutationObserver(updateThemeStyles);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });

    // Function to check zoom level and hide the button accordingly.
    function checkZoomLevel() {
      // Calculate actual browser zoom level.
      const zoomLevel = Math.round((window.outerWidth / window.innerWidth) * 100) / 100;

      // If zoom level is above 300%, hide the button.
      if (zoomLevel > 3) {
        scrollToTopButton.style.display = "none";
      } else {
        scrollToTopButton.style.display = "flex";
      }
    }

    // Run the check whenever the window is resized or zoomed.
    window.addEventListener("resize", checkZoomLevel);

    // Also run it on initial load to account for the page's zoom state.
    checkZoomLevel();

    // Cleanup function to remove event listeners when navigating between pages.
    cleanup = () => {
      window.removeEventListener("scroll", throttledScrollHandler);
      window.removeEventListener("resize", checkZoomLevel);
      observer.disconnect();
      if (scrollToTopButton && scrollToTopButton.parentNode) {
        scrollToTopButton.parentNode.removeChild(scrollToTopButton);
      }
      // Remove the style element if it exists.
      const existingStyle = document.getElementById("scroll-to-top-styles");
      if (existingStyle) {
        existingStyle.remove();
      }
    };

    return cleanup;
  };

  // Initialize on page load (works for both initial load and view transitions).
  const handlePageLoad = () => {
    // Small delay to ensure DOM is ready.
    setTimeout(initButton, 10);
  };

  // Handle initial page load and Astro view transitions.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', handlePageLoad);
  } else {
    handlePageLoad();
  }

  // Handle Astro view transitions.
  document.addEventListener('astro:page-load', handlePageLoad);

  // Cleanup before navigation.
  document.addEventListener('astro:before-preparation', () => {
    if (cleanup) {
      cleanup();
    }
  });
}

export default initScrollToTop;
