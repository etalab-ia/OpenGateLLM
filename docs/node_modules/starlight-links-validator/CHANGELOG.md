# starlight-links-validator

## 0.19.2

### Patch Changes

- [#131](https://github.com/HiDeoo/starlight-links-validator/pull/131) [`14f4d8d`](https://github.com/HiDeoo/starlight-links-validator/commit/14f4d8db5a6df3d95d3c4859b8a41468a99b3d63) Thanks [@DaniFoldi](https://github.com/DaniFoldi)! - Adds `astro` as a peer dependency to prevent potential build errors in monorepos with hoisting disabled.

## 0.19.1

### Patch Changes

- [#127](https://github.com/HiDeoo/starlight-links-validator/pull/127) [`2c0e83d`](https://github.com/HiDeoo/starlight-links-validator/commit/2c0e83d8abdbe9fca9eedfefc7a054a31c75979e) Thanks [@HiDeoo](https://github.com/HiDeoo)! - Fixes validation issues with links containing query strings when using the Astro `trailingSlash` option.

## 0.19.0

### Minor Changes

- [#123](https://github.com/HiDeoo/starlight-links-validator/pull/123) [`e9cc59d`](https://github.com/HiDeoo/starlight-links-validator/commit/e9cc59de376c7602f70e9310e320fdd6d44a17d3) Thanks [@HiDeoo](https://github.com/HiDeoo)! - Adds validation of [hero action links](https://starlight.astro.build/reference/frontmatter/#hero) in frontmatter.

- [#123](https://github.com/HiDeoo/starlight-links-validator/pull/123) [`e9cc59d`](https://github.com/HiDeoo/starlight-links-validator/commit/e9cc59de376c7602f70e9310e320fdd6d44a17d3) Thanks [@HiDeoo](https://github.com/HiDeoo)! - Adds validation of [previous](https://starlight.astro.build/reference/frontmatter/#prev) and [next](https://starlight.astro.build/reference/frontmatter/#next) page links in frontmatter.

## 0.18.1

### Patch Changes

- [#121](https://github.com/HiDeoo/starlight-links-validator/pull/121) [`242bc28`](https://github.com/HiDeoo/starlight-links-validator/commit/242bc2862aa7d911d5de0301e5caa29342e92ffd) Thanks [@HiDeoo](https://github.com/HiDeoo)! - Setups trusted publishing using OpenID Connect (OIDC) authentication — no code changes.

## 0.18.0

### Minor Changes

- [#118](https://github.com/HiDeoo/starlight-links-validator/pull/118) [`efef54a`](https://github.com/HiDeoo/starlight-links-validator/commit/efef54a647f65072d33b70ad92a2ea90b52ddb57) Thanks [@HiDeoo](https://github.com/HiDeoo)! - Adds [hyperlinks (OSC 8)](https://gist.github.com/egmontkob/eb114294efbcd5adb1944c9f3cb5feda) support to validation terminal output.

  In [supported terminals](https://github.com/Alhadis/OSC8-Adoption/), error slugs can be conveniently used (e.g. with `Ctrl+Click`, `Opt+Click`, `Cmd+Click`, or a context menu) to open the corresponding file using the default associated application.

## 0.17.2

### Patch Changes

- [#115](https://github.com/HiDeoo/starlight-links-validator/pull/115) [`b042c61`](https://github.com/HiDeoo/starlight-links-validator/commit/b042c61d479ad6584a4065bf84dadb6f3078145a) Thanks [@trueberryless](https://github.com/trueberryless)! - Fixes validation issue for links to Starlight page's title anchor, e.g. `/getting-started/#_top`.

## 0.17.1

### Patch Changes

- [#113](https://github.com/HiDeoo/starlight-links-validator/pull/113) [`3e0a88c`](https://github.com/HiDeoo/starlight-links-validator/commit/3e0a88cd2f7f6f84c57248ae72a8e8df32c22dbe) Thanks [@HiDeoo](https://github.com/HiDeoo)! - Prevents plugin remark plugin from running on Markdown and MDX content when using the Astro [`renderMarkdown()`](https://docs.astro.build/en/reference/content-loader-reference/#rendermarkdown) content loader API.

## 0.17.0

### Minor Changes

- [#108](https://github.com/HiDeoo/starlight-links-validator/pull/108) [`82f8ec5`](https://github.com/HiDeoo/starlight-links-validator/commit/82f8ec5cff97d5b9e343440666a3bb67de216b00) Thanks [@HiDeoo](https://github.com/HiDeoo)! - Adds support for [excluding](https://starlight-links-validator.vercel.app/configuration#exclude) links from validation using a function.

  When using the function syntax, the function should return `true` for any link that should be excluded from validation or `false` otherwise. The function will be called for each link to validate and will receive an object containing various properties to help determine whether to exclude the link or not.

  Check out the [`exclude` configuration option](https://starlight-links-validator.vercel.app/configuration#exclude) documentation for more details and examples.

## 0.16.0

### Minor Changes

- [#104](https://github.com/HiDeoo/starlight-links-validator/pull/104) [`cbeaa0f`](https://github.com/HiDeoo/starlight-links-validator/commit/cbeaa0f10d757947940af77e5e9de308f97993a8) Thanks [@HiDeoo](https://github.com/HiDeoo)! - Ignores query strings when checking for [excluded links](https://starlight-links-validator.vercel.app/configuration#exclude).

  Previously, to exclude links with query strings, you may have needed to rely on fairly loose glob patterns, e.g. `/playground/**` to exclude `/playground/`, `/playground/?id=foo` and `/playground/?id=bar`. With this change, excluding `/playground/` will ignore all query strings, so `/playground/`, `/playground/?id=foo` and `/playground/?id=bar` will all be excluded.

## 0.15.1

### Patch Changes

- [#102](https://github.com/HiDeoo/starlight-links-validator/pull/102) [`88e66a8`](https://github.com/HiDeoo/starlight-links-validator/commit/88e66a8236eeb419ae50e4aac046500600951cc9) Thanks [@HiDeoo](https://github.com/HiDeoo)! - Fixes a regression with version `0.15.0` where the `errorOnLocalLinks` option was not being applied correctly.

## 0.15.0

### Minor Changes

- [#93](https://github.com/HiDeoo/starlight-links-validator/pull/93) [`6d7174b`](https://github.com/HiDeoo/starlight-links-validator/commit/6d7174bcc6a2bb39f287a50bbdda29a6af4c16c8) Thanks [@HiDeoo](https://github.com/HiDeoo)! - ⚠️ **BREAKING CHANGE:** The minimum supported version of Starlight is now version `0.32.0`.

  Please use the `@astrojs/upgrade` command to upgrade your project:

  ```sh
  npx @astrojs/upgrade
  ```

- [#100](https://github.com/HiDeoo/starlight-links-validator/pull/100) [`b238cb7`](https://github.com/HiDeoo/starlight-links-validator/commit/b238cb7bd3db5f8fe848c317ba52d5ab44eb853e) Thanks [@HiDeoo](https://github.com/HiDeoo)! - Adds a new [`sameSitePolicy` option](https://starlight-links-validator.vercel.app/configuration#samesitepolicy) to configure how external links pointing to the same origin as the one configured in the [Astro `site` option](https://docs.astro.build/en/reference/configuration-reference/#site) should be handled.

  The current default behavior to ignore all external links remains unchanged. This new option allows to error on such links so they can be rewritten without the origin or to validate them as if they were internal links.

- [#100](https://github.com/HiDeoo/starlight-links-validator/pull/100) [`b238cb7`](https://github.com/HiDeoo/starlight-links-validator/commit/b238cb7bd3db5f8fe848c317ba52d5ab44eb853e) Thanks [@HiDeoo](https://github.com/HiDeoo)! - Adds a new [`components`](https://starlight-links-validator.vercel.app/configuration#components) option to define additional components and their props to validate as links on top of the built-in `<LinkButton>` and `<LinkCard>` Starlight components.

### Patch Changes

- [#99](https://github.com/HiDeoo/starlight-links-validator/pull/99) [`56ea78c`](https://github.com/HiDeoo/starlight-links-validator/commit/56ea78cefa40f554f88a32181daae1a82ec2fa9a) Thanks [@HiDeoo](https://github.com/HiDeoo)! - Fixes validation issue with the [Astro `base` option](https://docs.astro.build/en/reference/configuration-reference/#base) and the [`errorOnFallbackPages` plugin option](https://starlight-links-validator.vercel.app/configuration#erroronfallbackpages) set to `false` in a multilingual project.

## 0.14.3

### Patch Changes

- [#91](https://github.com/HiDeoo/starlight-links-validator/pull/91) [`1ef31b8`](https://github.com/HiDeoo/starlight-links-validator/commit/1ef31b81e7c5321a7481df6111d9161c4608fd4e) Thanks [@DaniFoldi](https://github.com/DaniFoldi)! - Moves `mdast-util-mdx-jsx` package to non-dev dependencies to prevent issues in monorepos with hoisting disabled.

## 0.14.2

### Patch Changes

- [#85](https://github.com/HiDeoo/starlight-links-validator/pull/85) [`57fdb1b`](https://github.com/HiDeoo/starlight-links-validator/commit/57fdb1b2f85f023e4b053480fd9ea5adb69a9e2a) Thanks [@HiDeoo](https://github.com/HiDeoo)! - Improves error message for invalid links to custom pages.

## 0.14.1

### Patch Changes

- [#82](https://github.com/HiDeoo/starlight-links-validator/pull/82) [`b3cbee8`](https://github.com/HiDeoo/starlight-links-validator/commit/b3cbee83fb54f5bd6dd06b01bb8397758c081752) Thanks [@HiDeoo](https://github.com/HiDeoo)! - Fixes regresion introduced in version [`0.14.0`](https://github.com/HiDeoo/starlight-links-validator/releases/tag/starlight-links-validator%400.14.0) of the plugin regarding validation of links to pages with [custom IDs/slugs](https://docs.astro.build/en/guides/content-collections/#defining-custom-ids).

  Note that you must use at least Astro version [`5.1.1`](https://github.com/withastro/astro/releases/tag/astro%405.1.1) to benefit from this fix.

- [#80](https://github.com/HiDeoo/starlight-links-validator/pull/80) [`876cb50`](https://github.com/HiDeoo/starlight-links-validator/commit/876cb5094d10a56a1be04b7cdc27e4f89fb1b681) Thanks [@lukekarrys](https://github.com/lukekarrys)! - Fixes validation issues for pages ending in `index`, e.g. `module_index`.

## 0.14.0

### Minor Changes

- [#77](https://github.com/HiDeoo/starlight-links-validator/pull/77) [`486a379`](https://github.com/HiDeoo/starlight-links-validator/commit/486a379c5bda40584126c376e14a3c82c23bd449) Thanks [@HiDeoo](https://github.com/HiDeoo)! - Adds support for Astro v5, drops support for Astro v4.

  ⚠️ **BREAKING CHANGE:** The minimum supported version of Starlight is now `0.30.0`.

  Please follow the [upgrade guide](https://github.com/withastro/starlight/releases/tag/%40astrojs/starlight%400.30.0) to update your project.

  When using the plugin with the [Content Layer API](https://docs.astro.build/en/guides/content-collections), the plugin will now automatically invalidate the content layer cache so that all links can be properly validated. To avoid unnecessary cache invalidation, it is recommended to conditionally use the plugin only when necessary. Check out the new [“Conditional Validation”](https://starlight-links-validator.vercel.app/guides/conditional-validation/) guide for more information.

  ⚠️ **BREAKING CHANGE:** Due to a [regression](https://github.com/withastro/astro/issues/12778) in Astro v5, links to pages with [custom IDs/slugs](https://docs.astro.build/en/guides/content-collections/#defining-custom-ids) can no longer be validated and will be flagged as invalid. If you rely on this feature, please stay on a previous version of Starlight and Astro in the meantime.
