import { z } from 'astro/zod'

export const StarlightLinksValidatorOptionsSchema = z
  .object({
    /**
     * Defines a list of additional components and their props that should be validated as links.
     *
     * By default, the plugin will only validate links defined in the `href` prop of the `<LinkButton>` and `<LinkCard>`
     * built-in Starlight components.
     * Adding custom components to this list will allow the plugin to validate links in those components as well.
     *
     * @default []
     */
    components: z.tuple([z.string(), z.string()]).array().default([]),
    /**
     * Defines whether the plugin should error on fallback pages.
     *
     * If you do not expect to have all pages translated in all configured locales and want to use the fallback pages
     * feature built-in into Starlight, you should set this option to `false`.
     *
     * @default true
     * @see https://starlight.astro.build/guides/i18n/#fallback-content
     */
    errorOnFallbackPages: z.boolean().default(true),
    /**
     * Defines whether the plugin should error on inconsistent locale links.
     *
     * When set to `true`, the plugin will error on links that are pointing to a page in a different locale.
     *
     * @default false
     */
    errorOnInconsistentLocale: z.boolean().default(false),
    /**
     * Defines whether the plugin should error on internal relative links.
     *
     * When set to `false`, the plugin will ignore relative links (e.g. `./foo` or `../bar`).
     *
     * @default true
     */
    errorOnRelativeLinks: z.boolean().default(true),
    /**
     * Defines whether the plugin should error on invalid hashes.
     *
     * When set to `false`, the plugin will only validate link pages and ignore hashes.
     *
     * @default true
     */
    errorOnInvalidHashes: z.boolean().default(true),
    /**
     * Defines whether the plugin should error on local links, e.g. URLs with a hostname of `localhost` or `127.0.0.1`.
     *
     * @default true
     */
    errorOnLocalLinks: z.boolean().default(true),
    /**
     * Defines a list of links or glob patterns that should be excluded from validation or a function that will be
     * called for each link to determine if it should be excluded from validation or not.
     *
     * The links in this list or links where the function returns `true` will be ignored by the plugin and will not be
     * validated.
     *
     * @default []
     */
    exclude: z
      .union([
        z.array(z.string()),
        z
          .function()
          .args(
            z.object({
              /**
               * The absolute path to the file where the link is defined.
               */
              file: z.string(),
              /**
               * The link to validate as authored in the content.
               */
              link: z.string(),
              /**
               * The slug of the page where the link is defined.
               */
              slug: z.string(),
            }),
          )
          .returns(z.boolean()),
      ])
      .default([]),
    /**
     * Defines the policy for external links with an origin matching the Astro `site` option.
     *
     * By default, all external links are ignored and not validated by the plugin.
     * Setting this option to `error` will make the plugin error on external links with an origin matching the Astro
     * `site` option and hint that the link can be rewritten without the origin.
     * Setting this option to `validate` will make the plugin validate external links with an origin matching the Astro
     * `site` option as if they were internal links.
     *
     * @default 'ignore'
     * @see https://docs.astro.build/en/reference/configuration-reference/#site
     * @see https://developer.mozilla.org/en-US/docs/Web/API/URL/origin
     */
    sameSitePolicy: z.enum(['error', 'ignore', 'validate']).default('ignore'),
  })
  .default({})

export type StarlightLinksValidatorUserOptions = z.input<typeof StarlightLinksValidatorOptionsSchema>
export type StarlightLinksValidatorOptions = z.output<typeof StarlightLinksValidatorOptionsSchema>
