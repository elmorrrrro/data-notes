import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

// Each study lives in its own folder: src/content/posts/<slug>/index.mdx
const posts = defineCollection({
  loader: glob({ pattern: '*/index.mdx', base: './src/content/posts', generateId: ({ entry }) => entry.split('/')[0] }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    date: z.coerce.date(),
    tags: z.array(z.string()).default([]),
    // Any CSS colors, e.g. ['var(--intel)', 'var(--amd)']; drives the page glow and highlights.
    accents: z.tuple([z.string(), z.string()]).optional(),
    // Tickers to compare "at publication vs now" on the post card; closes come from src/data/<slug>/stocks_snapshot.json.
    stocks: z.array(z.string()).default([]),
    // A company with no listed shares yet: the card shows an "IPO expected" badge instead of prices.
    ipo: z.string().optional(),
    draft: z.boolean().default(false),
  }),
});

export const collections = { posts };
