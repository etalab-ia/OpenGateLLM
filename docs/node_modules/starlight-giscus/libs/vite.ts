import type { ViteUserConfig } from 'astro';
import type { StarlightGiscusConfig } from '..';

export function vitePluginStarlightGiscusConfig(
  starlightGiscusConfig: StarlightGiscusConfig
): VitePlugin {
  const modules = {
    'virtual:starlight-giscus-config': `export default ${JSON.stringify(
      starlightGiscusConfig
    )}`,
  };

  const moduleResolutionMap = Object.fromEntries(
    (Object.keys(modules) as (keyof typeof modules)[]).map((key) => [
      resolveVirtualModuleId(key),
      key,
    ])
  );

  return {
    name: 'vite-plugin-starlight-giscus',
    load(id) {
      const moduleId = moduleResolutionMap[id];
      return moduleId ? modules[moduleId] : undefined;
    },
    resolveId(id) {
      return id in modules ? resolveVirtualModuleId(id) : undefined;
    },
  };
}

function resolveVirtualModuleId<TModuleId extends string>(
  id: TModuleId
): `\0${TModuleId}` {
  return `\0${id}`;
}

type VitePlugin = NonNullable<ViteUserConfig['plugins']>[number];
