// @ts-check
import { defineConfig } from 'astro/config';

import mdx from '@astrojs/mdx';
import cloudflare from '@astrojs/cloudflare';

// https://astro.build/config
export default defineConfig({
  // Public URL; change when a custom domain is attached.
  site: 'https://data-notes.data-notes.workers.dev',
  integrations: [mdx()],
  adapter: cloudflare(),
  vite: {
    // Pre-bundle Plot up front so the dev server never loses it from the deps cache.
    optimizeDeps: { include: ['@observablehq/plot'] },
  },
});
