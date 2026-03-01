import type { StarlightUserConfig } from '@astrojs/starlight/types';
import type { AstroIntegrationLogger } from 'astro';

export function overrideStarlightComponent(
  components: StarlightUserConfig['components'],
  logger: AstroIntegrationLogger,
  override: keyof NonNullable<StarlightUserConfig['components']>,
  component: string
) {
  if (components?.[override]) {
    logger.warn(
      `It looks like you already have a \`${override}\` component override in your Starlight configuration.`
    );
    logger.warn(
      `To use \`starlight-giscus\`, either remove your override or update it to render the content from \`starlight-giscus/components/${component}.astro\`.`
    );

    return {};
  }

  return {
    [override]: `starlight-giscus/overrides/${override}.astro`,
  };
}
