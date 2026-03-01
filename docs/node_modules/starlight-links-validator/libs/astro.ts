import fs from 'node:fs'

import type { AstroConfig, AstroIntegrationLogger } from 'astro'

const dataStoreFile = 'data-store.json'

export async function clearContentLayerCache(config: AstroConfig, logger: AstroIntegrationLogger) {
  const dataStore = getDataStoreFile(config)
  if (fs.existsSync(dataStore)) {
    logger.info('Invalidating content layer cache…')
    await fs.promises.rm(dataStore, { force: true })
  }
}

function getDataStoreFile(config: AstroConfig) {
  return new URL(dataStoreFile, config.cacheDir)
}
