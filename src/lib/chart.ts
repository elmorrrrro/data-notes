// Client-side helpers shared by every chart: theme tokens + responsive re-rendering.

export interface Tokens {
  surface: string;
  ink: string;
  ink2: string;
  muted: string;
  grid: string;
  axis: string;
  border: string;
  intel: string;
  amd: string;
  up: string;
  down: string;
}

export function tokens(): Tokens {
  const cs = getComputedStyle(document.documentElement);
  const v = (name: string) => cs.getPropertyValue(name).trim();
  return {
    surface: v('--surface'),
    ink: v('--ink'),
    ink2: v('--ink-2'),
    muted: v('--muted'),
    grid: v('--grid'),
    axis: v('--axis'),
    border: v('--border'),
    intel: v('--intel'),
    amd: v('--amd'),
    up: v('--up'),
    down: v('--down'),
  };
}

export const BRANDS = ['Intel', 'AMD'] as const;
export const brandScale = (t: Tokens) => ({ domain: [...BRANDS], range: [t.intel, t.amd] });

/** Shared Plot options: transparent background, recessive axes, inherited font. */
export function base(t: Tokens, width: number) {
  return {
    width,
    style: { background: 'transparent', color: t.muted, fontFamily: 'inherit', fontSize: '12px', overflow: 'visible' },
  };
}

/** Plot `tip` styling that follows the theme. */
export const tipStyle = (t: Tokens) => ({ fill: t.surface, stroke: t.axis, textPadding: 10, fontSize: 12.5 });

/** "Intel Core Ultra 7 270K Plus" -> "Core Ultra 7 270K Plus" */
export const productName = (cpu: string) => cpu.replace(/^(AMD|Intel) /, '');
/** "Intel Core Ultra 7 270K Plus" -> "270K Plus", "AMD Ryzen 5 9600X" -> "9600X" */
export const modelName = (cpu: string) => cpu.replace(/^.*? \d (?=\w)/, '');

export const usd =(n: number) => `$${n.toLocaleString('en-US', { maximumFractionDigits: 2 })}`;
export const thousands = (n: number) => (n === 0 ? '0' : `${Math.round(n / 1000)}k`);

/**
 * Renders `draw(width, tokens)` into `el` and re-renders when the container width
 * or the color theme changes. Returns a function that forces a re-render.
 */
export function mount(el: HTMLElement, draw: (width: number, t: Tokens) => Element): () => void {
  let lastWidth = 0;
  const render = () => {
    lastWidth = el.clientWidth;
    el.replaceChildren(draw(lastWidth, tokens()));
  };
  new ResizeObserver(() => {
    if (Math.abs(el.clientWidth - lastWidth) > 4) render();
  }).observe(el);
  new MutationObserver(render).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', render);
  render();
  return render;
}
