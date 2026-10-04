// @ts-check
import { defineConfig } from 'astro/config';

import mdx from '@astrojs/mdx';
import cloudflare from '@astrojs/cloudflare';

// https://astro.build/config
export default defineConfig({
  // Public URL (custom domain, attached in wrangler.jsonc).
  site: 'https://datanotes.org',
  integrations: [mdx()],
  adapter: cloudflare(),
  vite: {
    // Pre-bundle Plot up front so the dev server never loses it from the deps cache.
    optimizeDeps: { include: ['@observablehq/plot'] },
  },
});
