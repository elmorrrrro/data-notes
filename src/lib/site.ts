// Site-wide author info, used by the About page, header and footer.
export const AUTHOR = {
  name: 'Illia Hrebenko',
  socials: [
    { label: 'LinkedIn', handle: 'Illia Hrebenko', href: 'https://www.linkedin.com/in/illia-hrebenko-3595ab215/', icon: 'linkedin' },
    { label: 'Instagram', handle: '@elmorrrrro', href: 'https://www.instagram.com/elmorrrrro/', icon: 'instagram' },
  ],
} as const;

// Cloudflare Web Analytics (cookieless). Paste the token from the dashboard's JS snippet
// ("data-cf-beacon" token) to enable it; empty = no analytics script on the site.
export const CF_ANALYTICS_TOKEN: string = 'e2a868eb8df648219506b91240c1c918';
