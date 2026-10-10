import type { APIRoute } from 'astro';

// Server-rendered on every request (the rest of the site is static).
export const prerender = false;

const ALLOWED = new Set(['INTC', 'AMD', 'NVDA', 'TSM', 'SPY', 'QQQ', 'SOXX', 'UAL', 'LHA.DE', 'RYA.IR', 'SWMR', 'FRO', 'BNO', 'AVAV', 'RCAT', 'UMAC', 'LMT', '7203.T', '1211.HK', 'TSLA', 'VLO', 'ODFL', 'STNG']);
const MAX_HISTORY_DAYS = 400;
const CACHE_SECONDS = 300;

interface Quote {
  price: number;
  time: string;
  previousClose: number | null;
  history: { date: string; close: number }[];
}

async function fetchQuote(symbol: string, fromUnix: number): Promise<Quote> {
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${symbol}?period1=${fromUnix}&period2=${Math.floor(Date.now() / 1000)}&interval=1d`;
  const res = await fetch(url, { headers: { 'User-Agent': 'Mozilla/5.0 (data-notes quote proxy)' } });
  if (!res.ok) throw new Error(`Yahoo ${symbol}: HTTP ${res.status}`);
  const result = (await res.json())?.chart?.result?.[0];
  if (!result) throw new Error(`Yahoo ${symbol}: empty response`);

  const tz = result.meta.exchangeTimezoneName as string;
  const day = (t: number) => new Date(t * 1000).toLocaleDateString('en-CA', { timeZone: tz });
  const closes: (number | null)[] = result.indicators?.quote?.[0]?.close ?? [];
  const history = (result.timestamp ?? [])
    .map((t: number, i: number) => ({ date: day(t), close: closes[i] }))
    .filter((d: { close: number | null }) => d.close != null)
    .map((d: { date: string; close: number }) => ({ date: d.date, close: Math.round(d.close * 100) / 100 }));

  return {
    price: result.meta.regularMarketPrice,
    time: new Date(result.meta.regularMarketTime * 1000).toISOString(),
    previousClose: result.meta.chartPreviousClose ?? null,
    history,
  };
}

export const GET: APIRoute = async ({ url }) => {
  const symbols = (url.searchParams.get('symbols') ?? '')
    .split(',')
    .map((s) => s.trim().toUpperCase())
    .filter((s) => ALLOWED.has(s));
  if (!symbols.length) return Response.json({ error: `symbols must be one of ${[...ALLOWED].join(', ')}` }, { status: 400 });

  const fromParam = Date.parse(url.searchParams.get('from') ?? '');
  const earliest = Date.now() - MAX_HISTORY_DAYS * 86_400_000;
  const fromUnix = Math.floor(Math.max(Number.isNaN(fromParam) ? earliest : fromParam, earliest) / 1000);

  // Edge cache: Yahoo gets at most one request per symbol set and start day every CACHE_SECONDS.
  const cache = (globalThis as { caches?: { default?: Cache } }).caches?.default;
  const cacheKey = new Request(`${url.origin}/api/quote?symbols=${symbols.join(',')}&from=${fromUnix - (fromUnix % 86_400)}`);
  const cached = await cache?.match(cacheKey);
  if (cached) return cached;

  try {
    const entries = await Promise.all(symbols.map(async (s) => [s, await fetchQuote(s, fromUnix)] as const));
    const res = Response.json(
      { fetchedAt: new Date().toISOString(), source: 'Yahoo Finance', quotes: Object.fromEntries(entries) },
      { headers: { 'Cache-Control': `public, max-age=60, s-maxage=${CACHE_SECONDS}` } },
    );
    await cache?.put(cacheKey, res.clone());
    return res;
  } catch (err) {
    return Response.json({ error: (err as Error).message }, { status: 502 });
  }
};
