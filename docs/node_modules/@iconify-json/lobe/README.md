<a name="readme-top"></a>

<div>
  <img width="64" height="64" src="https://raw.githubusercontent.com/proj-airi/iconify-lobe-icons/refs/heads/main/docs/examples/lobehub-color.svg" />
  <img width="64" height="64" src="https://raw.githubusercontent.com/proj-airi/iconify-lobe-icons/refs/heads/main/docs/examples/openai.svg" />
  <img width="64" height="64" src="https://raw.githubusercontent.com/proj-airi/iconify-lobe-icons/refs/heads/main/docs/examples/gemini-color.svg" />
  <img width="64" height="64" src="https://raw.githubusercontent.com/proj-airi/iconify-lobe-icons/refs/heads/main/docs/examples/deepseek-color.svg" />
</div>

# [Lobe Icons](https://lobehub.com/icons) ported into [Iconfiy](https://iconify.design/)

[![npm version][npm-version-src]][npm-version-href]
[![npm downloads][npm-downloads-src]][npm-downloads-href]
[![bundle][bundle-src]][bundle-href]
[![JSDocs][jsdocs-src]][jsdocs-href]
[![License][license-src]][license-href]

Popular AI / LLM Model Brand SVG Logo and Icon Collection. See them all on one page at [lobehub.com/icons](https://lobehub.com/icons).<br/>
Contributions, corrections & requests can be made on their [GitHub repository](https://github.com/lobehub/lobe-icons).

This enables you to use Lobe Icons in UnoCSS or any Iconify compatible scenario.

> [!NOTE]
>
> This project is part of (and also associate to) the [Project AIRI](https://github.com/moeru-ai/airi), we aim to build a LLM-driven VTuber like [Neuro-sama](https://www.youtube.com/@Neurosama) (subscribe if you didn't!) if you are interested in, please do give it a try on [live demo](https://airi.moeru.ai).

## Installation

Pick the package manager of your choice:

```shell
ni @proj-airi/lobe-icons -D # from @antfu/ni, can be installed via `npm i -g @antfu/ni`
pnpm i @proj-airi/lobe-icons @iconify/utils -D
yarn i @proj-airi/lobe-icons @iconify/utils -D
npm i @proj-airi/lobe-icons @iconify/utils -D
```

### UnoCSS usage

```typescript
import { createExternalPackageIconLoader } from '@iconify/utils/lib/loader/external-pkg'
import { presetIcons } from 'unocss'

export default defineConfig({
  presets: [
    // Other presets
    presetIcons({
      scale: 1.2,
      collections: {
        ...createExternalPackageIconLoader('@proj-airi/lobe-icons'),
      },
    }),
  ],
})
```

Now you can use it with UnoCSS's `i-` syntax:

```html
<div class i-lobe-icons:chatgpt></div>
```

## Other side projects born from Project AIRI

- [Awesome AI VTuber](https://github.com/proj-airi/awesome-ai-vtuber): A curated list of AI VTubers and related projects
- [`unspeech`](https://github.com/moeru-ai/unspeech): Universal endpoint proxy server for `/audio/transcriptions` and `/audio/speech`, like LiteLLM but for any ASR and TTS
- [`hfup`](https://github.com/moeru-ai/hfup): tools to help on deploying, bundling to HuggingFace Spaces
- [`xsai-transformers`](https://github.com/moeru-ai/xsai-transformers): Experimental [🤗 Transformers.js](https://github.com/huggingface/transformers.js) provider for [xsAI](https://github.com/moeru-ai/xsai).
- [WebAI: Realtime Voice Chat](https://github.com/proj-airi/webai-realtime-voice-chat): Full example of implementing ChatGPT's realtime voice from scratch with VAD + STT + LLM + TTS.
- [`@proj-airi/drizzle-duckdb-wasm`](https://github.com/moeru-ai/airi/tree/main/packages/drizzle-duckdb-wasm/README.md): Drizzle ORM driver for DuckDB WASM
- [`@proj-airi/duckdb-wasm`](https://github.com/moeru-ai/airi/tree/main/packages/duckdb-wasm/README.md): Easy to use wrapper for `@duckdb/duckdb-wasm`
- [Airi Factorio](https://github.com/moeru-ai/airi-factorio): Allow Airi to play Factorio
- [Factorio RCON API](https://github.com/nekomeowww/factorio-rcon-api): RESTful API wrapper for Factorio headless server console
- [`autorio`](https://github.com/moeru-ai/airi-factorio/tree/main/packages/autorio): Factorio automation library
- [`tstl-plugin-reload-factorio-mod`](https://github.com/moeru-ai/airi-factorio/tree/main/packages/tstl-plugin-reload-factorio-mod): Reload Factorio mod when developing
- [Velin](https://github.com/luoling8192/velin): Use Vue SFC and Markdown to write easy to manage stateful prompts for LLM
- [`demodel`](https://github.com/moeru-ai/demodel): Easily boost the speed of pulling your models and datasets from various of inference runtimes.
- [`inventory`](https://github.com/moeru-ai/inventory): Centralized model catalog and default provider configurations backend service
- [MCP Launcher](https://github.com/moeru-ai/mcp-launcher): Easy to use MCP builder & launcher for all possible MCP servers, just like Ollama for models!
- [🥺 SAD](https://github.com/moeru-ai/sad): Documentation and notes for self-host and browser running LLMs.

[npm-version-src]: https://img.shields.io/npm/v/@proj-airi/lobe-icons?style=flat&colorA=080f12&colorB=2a64be
[npm-version-href]: https://npmjs.com/package/@proj-airi/lobe-icons
[npm-downloads-src]: https://img.shields.io/npm/dm/@proj-airi/lobe-icons?style=flat&colorA=080f12&colorB=2a64be
[npm-downloads-href]: https://npmjs.com/package/@proj-airi/lobe-icons
[bundle-src]: https://img.shields.io/bundlephobia/minzip/@proj-airi/lobe-icons?style=flat&colorA=080f12&colorB=2a64be&label=minzip
[bundle-href]: https://bundlephobia.com/result?p=@proj-airi/lobe-icons
[license-src]: https://img.shields.io/github/license/proj-airi/iconify-lobe-icons.svg?style=flat&colorA=080f12&colorB=2a64be
[license-href]: https://github.com/proj-airi/iconify-lobe-icons/blob/main/LICENSE
[jsdocs-src]: https://img.shields.io/badge/jsdocs-reference-080f12?style=flat&colorA=080f12&colorB=2a64be
[jsdocs-href]: https://www.jsdocs.io/package/@proj-airi/lobe-icons
