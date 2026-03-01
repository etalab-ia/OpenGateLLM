import type { StarlightPlugin } from '@astrojs/starlight/types'
import type ScrollToTopOptions from "./common/types.js";
import starlightScrollToTopIntegration from "./libs/integration.js";


export default function starlightScrollToTop(userConfig: ScrollToTopOptions = {}): StarlightPlugin {
  return {
    name: 'starlight-scroll-to-top-plugin',
    hooks: {
      'config:setup'({ addIntegration, logger }) {
        /**
         * This is the entry point of your Starlight plugin.
         * The `setup` hook is called when Starlight is initialized (during the Astro `astro:config:setup` integration
         * hook).
         * To learn more about the Starlight plugin API and all available options in this hook, check the Starlight
         * plugins reference.
         *
         * @see https://starlight.astro.build/reference/plugins/
         */
        //logger.info('Hello from the starlight-scroll-to-top plugin!')
        addIntegration(starlightScrollToTopIntegration(userConfig));
      },
    },
  }
}
