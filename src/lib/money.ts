/** 12.5 -> "$12.50", or "€12.50" with currency 'EUR'. Snapshots without a currency are US dollars. */
export const money = (n: number, currency = 'USD') =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency, minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n);
