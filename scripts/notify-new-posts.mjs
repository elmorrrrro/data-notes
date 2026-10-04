// Creates a Buttondown email for each newly added post (run by .github/workflows/newsletter.yml).
//
// Env:
//   BUTTONDOWN_API_KEY  required
//   NEWSLETTER_MODE     "draft" (default: email waits in Buttondown for a manual Send) or "send"
//   POSTS               space-separated post folders to announce, e.g. "intel-vs-amd-2026-10"
//   TEST                "1" = draft only, subject prefixed with [TEST], whatever NEWSLETTER_MODE says
//   SITE_URL            public site URL

import { readFileSync } from 'node:fs';

const API = 'https://api.buttondown.com/v1/emails';
const { BUTTONDOWN_API_KEY: KEY, NEWSLETTER_MODE = 'draft', POSTS = '', TEST, SITE_URL = 'https://datanotes.org' } = process.env;
const test = TEST === '1';
const send = NEWSLETTER_MODE === 'send' && !test;

if (!KEY) throw new Error('BUTTONDOWN_API_KEY is not set (add it with: gh secret set BUTTONDOWN_API_KEY)');

/** Minimal frontmatter reader for the fields we need (title, description). */
function frontmatter(slug) {
  const src = readFileSync(`src/content/posts/${slug}/index.mdx`, 'utf8');
  const block = src.match(/^---\r?\n([\s\S]*?)\r?\n---/)?.[1] ?? '';
  const field = (name) => block.match(new RegExp(`^${name}:\\s*"?(.*?)"?\\s*$`, 'm'))?.[1]?.replace(/\\"/g, '"');
  return { title: field('title'), description: field('description') };
}

/** Wait until the deploy has published the post, so the email never links to a 404. */
async function waitForPage(url, minutes = 10) {
  for (let i = 0; i < minutes * 4; i++) {
    const res = await fetch(url, { method: 'HEAD' }).catch(() => null);
    if (res?.ok) return;
    await new Promise((r) => setTimeout(r, 15_000));
  }
  throw new Error(`${url} is still not live after ${minutes} minutes`);
}

for (const slug of POSTS.split(/\s+/).filter(Boolean)) {
  const { title, description } = frontmatter(slug);
  if (!title) throw new Error(`No title in ${slug}`);
  const url = `${SITE_URL}/posts/${slug}/`;
  if (send) await waitForPage(url);

  const body = [
    `**New on Data Notes.**`,
    ``,
    description,
    ``,
    `**[Read the full study →](${url})**`,
    ``,
    `Got an idea for the next study? Just hit reply.`,
    ``,
    `Illia`,
  ].join('\n');

  const res = await fetch(API, {
    method: 'POST',
    headers: {
      Authorization: `Token ${KEY}`,
      'Content-Type': 'application/json',
      // Buttondown requires this header for API calls that send email immediately.
      ...(send ? { 'X-Buttondown-Live-Dangerously': 'true' } : {}),
    },
    body: JSON.stringify({
      subject: `${test ? '[TEST] ' : ''}${title}`,
      body,
      status: send ? 'about_to_send' : 'draft',
    }),
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`Buttondown ${res.status}: ${text}`);
  console.log(`${send ? 'Sending' : 'Draft created'}: "${title}" -> ${url}`);
}
