import type { AstroConfig } from "astro";

type VitePlugin = Required<AstroConfig["vite"]>["plugins"][number];

/**
 * Builds a Vite plugin that creates a virtual module.
 *
 * @param moduleId - The ID of the virtual module.
 * @param name - The name of the plugin.
 * @param moduleContent - The content of the virtual module.
 * @returns A Vite plugin that resolves and loads the virtual module.
 */
export function viteVirtualModulePluginBuilder(
  moduleId: string,
  name: string,
  moduleContent: string
) {
  return function modulePlugin(): VitePlugin {
    const resolvedVirtualModuleId = `\0${moduleId}`; // Prefix with \0 to avoid conflicts

    return {
      name,
      resolveId(id) {
        if (id === moduleId) {
          return resolvedVirtualModuleId;
        }
        return;
      },
      load(id) {
        if (id === resolvedVirtualModuleId) {
          return moduleContent;
        }
        return;
      },
    };
  };
}
