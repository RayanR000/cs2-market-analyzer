'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { motion } from 'framer-motion';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Header, PriceSourceFilter } from '@/components';
import CountUpNumber from '@/components/CountUpNumber';
import {
  getItem,
  getItemPrediction,
  getItemTrends,
  getMultiSourcePrices,
  getPriceHistory,
  MultiSourcePrices,
  PricePoint,
} from '@/lib/api';

interface CatalogItem {
  id: number;
  item_id: string;
  name: string;
  type: string;
  release_date?: string;
}

interface TrendResponse {
  item_id: string;
  item_name: string;
  current_price: number | null;
  trend_direction: 'bullish' | 'neutral' | 'bearish' | 'insufficient_data';
  confidence: 'low' | 'medium' | 'high';
  trend_score?: number | null;
  indicators?: {
    sma_7?: number | null;
    sma_30?: number | null;
    volatility?: number | null;
    rsi?: number | null;
    bollinger_upper?: number | null;
    bollinger_middle?: number | null;
    bollinger_lower?: number | null;
    macd?: number | null;
    macd_signal?: number | null;
    support?: number | null;
    resistance?: number | null;
  };
  factors?: string[];
  methodology?: string;
  timestamp?: string;
  message?: string;
}

interface PredictionResponse {
  item_id: string;
  item_name: string;
  current_price: number | null;
  forecast?: { low: number; mid: number; high: number };
  period_days?: number;
  period_label?: string;
  trend_direction?: string;
  confidence?: string;
  volatility?: number | null;
  methodology?: string;
  timestamp?: string;
  message?: string;
}

interface PriceSeriesRow {
  timestamp: number;
  label: string;
  [source: string]: number | string;
}

const TIME_RANGES = ['24h', '7d', '30d', 'all'] as const;
type TimeRange = (typeof TIME_RANGES)[number];

const EASE: [number, number, number, number] = [0.16, 1, 0.3, 1];

function summarizeHistory(history: PricePoint[]) {
  if (!history.length) return { currentPrice: null, priceChange24h: null, volume24h: null };

  const points = [...history].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
  const latest = points[points.length - 1];
  const latestTs = new Date(latest.timestamp).getTime();
  const cutoff = latestTs - 24 * 60 * 60 * 1000;
  const windowPoints = points.filter(point => new Date(point.timestamp).getTime() >= cutoff);
  const comparisonPoints = windowPoints.length > 1 ? windowPoints : points.slice(-2);
  const first = comparisonPoints[0];
  const last = comparisonPoints[comparisonPoints.length - 1];

  const priceChange24h = first && last && first.price > 0 ? ((last.price - first.price) / first.price) * 100 : null;
  const volumeWindow = windowPoints.length ? windowPoints : points.slice(-2);
  const volume24h = volumeWindow.reduce((sum, point) => sum + (point.volume ?? 0), 0) || null;

  return { currentPrice: latest.price, priceChange24h, volume24h };
}

function buildSourceChartData(sourceData: MultiSourcePrices | null, selectedSources: string[], range: TimeRange): PriceSeriesRow[] {
  if (!sourceData) return [];

  const activeSources = selectedSources.length ? selectedSources : sourceData.sources;
  const now = Date.now();
  const cutoff = range === '24h' ? now - 24 * 60 * 60 * 1000
    : range === '7d' ? now - 7 * 24 * 60 * 60 * 1000
    : range === '30d' ? now - 30 * 24 * 60 * 60 * 1000
    : Number.NEGATIVE_INFINITY;

  const buckets = new Map<string, PriceSeriesRow>();

  for (const source of activeSources) {
    const points = sourceData.data[source] ?? [];
    for (const point of points) {
      const timestamp = new Date(point.timestamp).getTime();
      if (timestamp < cutoff) continue;

      const bucketKey = range === '24h'
        ? new Date(timestamp).toISOString().slice(0, 13)
        : new Date(timestamp).toISOString().slice(0, 10);
      const label = range === '24h'
        ? new Date(timestamp).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
        : new Date(timestamp).toLocaleDateString([], { month: 'short', day: 'numeric' });

      const existing = buckets.get(bucketKey);
      if (!existing) {
        buckets.set(bucketKey, { timestamp, label, [source]: point.price });
      } else {
        existing[source] = point.price;
        existing.timestamp = Math.max(existing.timestamp as number, timestamp);
      }
    }
  }

  return [...buckets.values()].sort((a, b) => (a.timestamp as number) - (b.timestamp as number));
}

function formatCurrency(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) return '\u2014';
  return `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatPercent(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) return '\u2014';
  return `${value > 0 ? '+' : ''}${value.toFixed(2)}%`;
}

function formatVolume(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) return '\u2014';
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return `${value.toFixed(0)}`;
}

export default function ItemDetailPage() {
  const params = useParams();
  const itemId = params.id as string;
  const [item, setItem] = useState<CatalogItem | null>(null);
  const [history, setHistory] = useState<PricePoint[]>([]);
  const [trends, setTrends] = useState<TrendResponse | null>(null);
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null);
  const [multiSourceData, setMultiSourceData] = useState<MultiSourcePrices | null>(null);
  const [selectedSources, setSelectedSources] = useState<string[]>([]);
  const [timeRange, setTimeRange] = useState<TimeRange>('30d');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadItemData() {
      setIsLoading(true);
      setError(null);

      try {
        const [itemResponse, historyResponse, trendsResponse, predictionResponse, sourceResponse] = await Promise.all([
          getItem(itemId),
          getPriceHistory(itemId, 90, 0, 500),
          getItemTrends(itemId),
          getItemPrediction(itemId, '30_days'),
          getMultiSourcePrices(itemId, ['steam', 'csfloat'], 30),
        ]);

        if (cancelled) return;

        setItem(itemResponse as CatalogItem);
        setHistory(Array.isArray(historyResponse) ? historyResponse as PricePoint[] : []);
        setTrends({
          item_id: trendsResponse?.item_id ?? '',
          item_name: trendsResponse?.item_name ?? '',
          current_price: trendsResponse?.current_price ?? null,
          trend_direction: trendsResponse?.trend_direction ?? 'insufficient_data',
          confidence: trendsResponse?.confidence ?? 'low',
          indicators: {
            sma_7: trendsResponse?.sma_7 ?? null,
            sma_30: trendsResponse?.sma_30 ?? null,
            volatility: trendsResponse?.volatility ?? null,
          },
          explanation: trendsResponse?.explanation ?? '',
        } as TrendResponse);
        setPrediction({
          current_price: predictionResponse?.current_price ?? null,
          forecast: {
            low: predictionResponse?.forecast_low ?? 0,
            mid: predictionResponse?.forecast_mid ?? 0,
            high: predictionResponse?.forecast_high ?? 0,
          },
          period_label: predictionResponse?.forecast_period ?? '30_days',
          trend_direction: predictionResponse?.trend_direction,
          confidence: predictionResponse?.confidence,
        } as PredictionResponse);
        setMultiSourceData(sourceResponse);
        setSelectedSources(
          Array.isArray(sourceResponse?.sources) && sourceResponse.sources.length
            ? sourceResponse.sources
            : ['steam']
        );
      } catch (fetchError) {
        if (!cancelled) setError(fetchError instanceof Error ? fetchError.message : 'Failed to load item data');
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    loadItemData();
    return () => { cancelled = true; };
  }, [itemId]);

  const sourceChartData = useMemo(
    () => buildSourceChartData(multiSourceData, selectedSources, timeRange),
    [multiSourceData, selectedSources, timeRange]
  );

  const availableSources = multiSourceData?.sources ?? ['steam'];
  const visibleSources = selectedSources.length ? selectedSources : availableSources;
  const summary = summarizeHistory(history);
  const latestPrice = summary.currentPrice;
  const trendDirection = trends?.trend_direction ?? 'insufficient_data';
  const confidence = trends?.confidence ?? 'low';
  const trendFactors = trends?.factors ?? [];
  const forecast = prediction?.forecast;
  const hasPriceData = history.length > 0;

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background-primary">
        <Header />
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="widget-block p-6 text-sm text-secondary">
            Loading item data from the backend...
          </div>
        </div>
      </div>
    );
  }

  if (error || !item) {
    return (
      <div className="min-h-screen bg-background-primary">
        <Header />
        <div className="max-w-7xl mx-auto px-6 py-8">
          <Link href="/market" className="text-brand hover:underline text-xs font-medium mb-6 inline-block">
            &larr; MARKET
          </Link>
          <div className="widget-block p-6">
            <h1 className="text-2xl font-semibold text-primary mb-2">Item unavailable</h1>
            <p className="text-sm text-secondary">{error || 'No backend item data was returned for this id.'}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background-primary">
      <Header />

      <div className="max-w-7xl mx-auto px-6 py-8">
        <Link href="/market" className="text-brand hover:text-brand-hover text-xs font-bold uppercase tracking-[0.2em] mb-6 inline-block transition-colors">
          &larr; MARKET
        </Link>

        <div className="widget-block p-6 mb-8">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <h1 className="text-3xl font-bold text-primary mb-2">{item.name}</h1>
              <div className="flex flex-wrap items-center gap-3 text-xs font-data text-tertiary">
                <span className="uppercase tracking-wide">{item.type}</span>
                {item.release_date && <span>{new Date(item.release_date).toLocaleDateString()}</span>}
                <span className="tag-tech">{itemId}</span>
              </div>
            </div>

            <div className="text-right">
              <div className="text-4xl font-bold text-primary font-data mb-1">
                {hasPriceData ? (
                  <CountUpNumber from={latestPrice!} to={latestPrice!} decimals={2} formatFn={formatCurrency} />
                ) : (
                  <span className="text-tertiary">---</span>
                )}
              </div>
              <div
                className="font-data text-sm"
                style={{ color: (summary.priceChange24h ?? 0) >= 0 ? 'var(--data-up)' : 'var(--data-down)' }}
              >
                {hasPriceData ? `${formatPercent(summary.priceChange24h)} (24h)` : <span className="text-tertiary">No data</span>}
              </div>
            </div>
          </div>

          {!hasPriceData && (
            <div className="mt-4 rounded-sm border border-border bg-background-tertiary px-4 py-3 text-sm text-secondary">
              This item exists in the index but has no price history yet. Data will appear once the collection pipeline processes it.
            </div>
          )}

          <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard label="Trend" value={trendDirection.replace('_', ' ')} sub={`Confidence ${confidence}`} />
            <MetricCard label="7d SMA" value={hasPriceData ? formatCurrency(trends?.indicators?.sma_7 ?? null) : '\u2014'} mono />
            <MetricCard label="30d SMA" value={hasPriceData ? formatCurrency(trends?.indicators?.sma_30 ?? null) : '\u2014'} mono />
            <MetricCard label="Volume 24h" value={hasPriceData ? formatVolume(summary.volume24h) : '\u2014'} mono />
          </div>
        </div>

        <div className="grid grid-cols-1 gap-8 xl:grid-cols-4">
          <div className="xl:col-span-3">
            <div className="flex items-center justify-between gap-4 mb-4">
              <div className="flex gap-1 flex-wrap">
                {TIME_RANGES.map((range) => (
                  <button
                    key={range}
                    onClick={() => setTimeRange(range)}
                    className={`px-3 py-2 text-xs font-bold uppercase tracking-widest transition-colors ${
                      timeRange === range
                        ? 'text-primary border-b-2 border-brand'
                        : 'text-tertiary hover:text-primary'
                    }`}
                  >
                    {range}
                  </button>
                ))}
              </div>
              <span className="tag-tech">price history</span>
            </div>

            <div className="mb-4">
              <PriceSourceFilter
                selectedSources={visibleSources}
                onSourceChange={setSelectedSources}
                availableSources={availableSources}
              />
            </div>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.3 }}
              className="widget-block p-4"
            >
              {sourceChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={360}>
                  <LineChart data={sourceChartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" />
                    <XAxis dataKey="label" stroke="var(--text-tertiary)" style={{ fontSize: '12px' }} />
                    <YAxis
                      stroke="var(--text-tertiary)"
                      style={{ fontSize: '12px' }}
                      domain={['dataMin - 10', 'dataMax + 10']}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'var(--background-secondary)',
                        border: '1px solid var(--border)',
                        color: 'var(--text-primary)',
                        borderRadius: '4px',
                      }}
                      formatter={(value) => formatCurrency(Number(value))}
                    />
                    {visibleSources.includes('steam') && (
                      <Line type="monotone" dataKey="steam" stroke="var(--text-secondary)" strokeWidth={2} dot={false} isAnimationActive={false} name="Steam" />
                    )}
                    {visibleSources.includes('csfloat') && (
                      <Line type="monotone" dataKey="csfloat" stroke="var(--brand)" strokeWidth={2} dot={false} isAnimationActive={false} name="CSFloat" />
                    )}
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-[360px] text-sm text-tertiary">
                  {hasPriceData ? 'No price data available for the selected range' : 'No price history recorded for this item'}
                </div>
              )}
            </motion.div>
          </div>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1, ease: EASE }}
            className="space-y-4"
          >
            <div className="widget-block p-4">
              <div className="text-xs uppercase tracking-wide text-tertiary mb-2">Prediction</div>
              <div className="text-2xl font-bold text-primary font-data">
                {hasPriceData && forecast ? (
                  <CountUpNumber from={forecast.mid} to={forecast.mid} decimals={2} formatFn={formatCurrency} />
                ) : '\u2014'}
              </div>
              <div className="text-xs text-tertiary mt-1">
                {hasPriceData ? (prediction?.period_label || '30_days') + ' forecast' : 'Insufficient data'}
              </div>
            </div>

            <div className="widget-block p-4">
              <div className="text-xs uppercase tracking-wide text-tertiary mb-2">Forecast band</div>
              {hasPriceData ? (
                <div className="space-y-1 font-data text-sm text-primary">
                  <div>Low {formatCurrency(forecast?.low ?? null)}</div>
                  <div>Mid {formatCurrency(forecast?.mid ?? null)}</div>
                  <div>High {formatCurrency(forecast?.high ?? null)}</div>
                </div>
              ) : (
                <div className="text-sm text-tertiary">No price data to forecast from</div>
              )}
            </div>

            <div className="widget-block p-4">
              <div className="text-xs uppercase tracking-wide text-tertiary mb-2">Data sources</div>
              <div className="space-y-2">
                {availableSources.map((source) => (
                  <div key={source} className="flex items-center justify-between text-sm">
                    <span className="capitalize text-primary">{source}</span>
                    <span className="text-tertiary">
                      {(multiSourceData?.data[source]?.length ?? 0).toString()} points
                    </span>
                  </div>
                ))}
              </div>
              {!hasPriceData && (
                <div className="mt-2 text-xs text-tertiary">Awaiting collection...</div>
              )}
            </div>

            <div className="widget-block p-4">
              <div className="text-xs uppercase tracking-wide text-tertiary mb-2">Signals</div>
              <div className="space-y-2 text-sm text-primary">
                {hasPriceData && trendFactors.length ? (
                  trendFactors.map((factor) => (
                    <div key={factor} className="leading-snug">{factor}</div>
                  ))
                ) : (
                  <div className="text-tertiary">{hasPriceData ? 'No technical factors returned yet.' : 'No data to compute signals from'}</div>
                )}
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}

function MetricCard({ label, value, sub, mono }: { label: string; value: string; sub?: string; mono?: boolean }) {
  return (
    <div className="rounded-sm border border-border bg-background-tertiary p-4">
      <div className="text-xs uppercase tracking-wide text-tertiary mb-2">{label}</div>
      <div className={`text-lg font-semibold text-primary ${mono ? 'font-data' : ''} capitalize`}>{value}</div>
      {sub && <div className="text-xs text-tertiary mt-1">{sub}</div>}
    </div>
  );
}
