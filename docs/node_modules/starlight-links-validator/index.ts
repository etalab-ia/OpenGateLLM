import type { StarlightPlugin } from '@astrojs/starlight/types'
import type { IntegrationResolvedRoute } from 'astro'
import { AstroError } from 'astro/errors'

import { clearContentLayerCache } from './libs/astro'
import { StarlightLinksValidatorOptionsSchema, type StarlightLinksValidatorUserOptions } from './libs/config'
import { pathnameToSlug, stripTrailingSlash } from './libs/path'
import { remarkStarlightLinksValidator, type RemarkStarlightLinksValidatorConfig } from './libs/remark'
import { logErrors, validateLinks } from './libs/validation'

export type { StarlightLinksValidatorOptions } from './libs/config'

export default function starlightLinksValidatorPlugin(
  userOptions?: StarlightLinksValidatorUserOptions,
): StarlightPlugin {
  const options = StarlightLinksValidatorOptionsSchema.safeParse(userOptions)

  if (!options.success) {
    throwPluginError('Invalid options passed to the starlight-links-validator plugin.')
  }

  return {
    name: 'starlight-links-validator-plugin',
    hooks: {
      'config:setup'({ addIntegration, astroConfig, config: starlightConfig, logger }) {
        let routes: IntegrationResolvedRoute[] = []
        const site = astroConfig.site ? stripTrailingSlash(astroConfig.site) : undefined

        addIntegration({
          name: 'starlight-links-validator-integration',
          hooks: {
            'astro:config:setup': async ({ command, updateConfig }) => {
              if (command !== 'build') {
                return
              }

              await clearContentLayerCache(astroConfig, logger)

              updateConfig({
                markdown: {
                  remarkPlugins: [
                    [
                      remarkStarlightLinksValidator,
                      {
                        base: astroConfig.base,
                        options: options.data,
                        site,
                        srcDir: astroConfig.srcDir,
                      } satisfies RemarkStarlightLinksValidatorConfig,
                    ],
                  ],
                },
              })
            },
            'astro:routes:resolved': (params) => {
              routes = params.routes
            },
            'astro:build:done': ({ dir, pages, assets }) => {
              const customPages = new Set<string>()

              for (const [pattern, urls] of assets) {
                const route = routes.find((route) => route.pattern === pattern)
                if (!route || route.origin !== 'project') continue

                for (const url of urls) {
                  customPages.add(pathnameToSlug(url.pathname.replace(astroConfig.outDir.pathname, '')))
                }
              }

              const errors = validateLinks(pages, customPages, dir, astroConfig, starlightConfig, options.data)

              const hasInvalidLinkToCustomPage = logErrors(logger, errors, site)

              if (errors.size > 0) {
                throwPluginError(
                  'Links validation failed.',
                  hasInvalidLinkToCustomPage
                    ? 'Some invalid links point to custom pages which cannot be validated, see the `exclude` option for more informations at https://starlight-links-validator.vercel.app/configuration#exclude'
                    : undefined,
                )
              }
            },
          },
        })
      },
    },
  }
}

function throwPluginError(message: string, additionalHint?: string): never {
  let hint = 'See the error report above for more informations.\n\n'
  if (additionalHint) hint += `${additionalHint}\n\n`
  hint +=
    'If you believe this is a bug, please file an issue at https://github.com/HiDeoo/starlight-links-validator/issues/new/choose'

  throw new AstroError(message, hint)
}
