'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
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
  forecast?: {
    low: number;
    mid: number;
    high: number;
  };
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

function summarizeHistory(history: PricePoint[]) {
  if (!history.length) {
    return {
      currentPrice: null,
      priceChange24h: null,
      volume24h: null,
    };
  }

  const points = [...history].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );
  const latest = points[points.length - 1];
  const latestTs = new Date(latest.timestamp).getTime();
  const cutoff = latestTs - 24 * 60 * 60 * 1000;
  const windowPoints = points.filter(point => new Date(point.timestamp).getTime() >= cutoff);
  const comparisonPoints = windowPoints.length > 1 ? windowPoints : points.slice(-2);
  const first = comparisonPoints[0];
  const last = comparisonPoints[comparisonPoints.length - 1];

  const priceChange24h =
    first && last && first.price > 0
      ? ((last.price - first.price) / first.price) * 100
      : null;

  const volumeWindow = windowPoints.length ? windowPoints : points.slice(-2);
  const volume24h = volumeWindow.reduce((sum, point) => sum + (point.volume ?? 0), 0) || null;

  return {
    currentPrice: latest.price,
    priceChange24h,
    volume24h,
  };
}

function buildSourceChartData(
  sourceData: MultiSourcePrices | null,
  selectedSources: string[],
  range: TimeRange
): PriceSeriesRow[] {
  if (!sourceData) {
    return [];
  }

  const activeSources = selectedSources.length ? selectedSources : sourceData.sources;
  const now = Date.now();
  const cutoff =
    range === '24h'
      ? now - 24 * 60 * 60 * 1000
      : range === '7d'
      ? now - 7 * 24 * 60 * 60 * 1000
      : range === '30d'
      ? now - 30 * 24 * 60 * 60 * 1000
      : Number.NEGATIVE_INFINITY;

  const buckets = new Map<string, PriceSeriesRow>();

  for (const source of activeSources) {
    const points = sourceData.data[source] ?? [];
    for (const point of points) {
      const timestamp = new Date(point.timestamp).getTime();
      if (timestamp < cutoff) {
        continue;
      }

      const bucketKey =
        range === '24h'
          ? new Date(timestamp).toISOString().slice(0, 13)
          : new Date(timestamp).toISOString().slice(0, 10);
      const label =
        range === '24h'
          ? new Date(timestamp).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
          : new Date(timestamp).toLocaleDateString([], { month: 'short', day: 'numeric' });

      const existing = buckets.get(bucketKey);
      if (!existing) {
        buckets.set(bucketKey, {
          timestamp,
          label,
          [source]: point.price,
        });
      } else {
        existing[source] = point.price;
        existing.timestamp = Math.max(existing.timestamp as number, timestamp);
      }
    }
  }

  return [...buckets.values()].sort((a, b) => (a.timestamp as number) - (b.timestamp as number));
}

function formatCurrency(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) {
    return '—';
  }

  return `$${value.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

function formatPercent(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) {
    return '—';
  }

  return `${value > 0 ? '+' : ''}${value.toFixed(2)}%`;
}

function formatVolume(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) {
    return '—';
  }

  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`;
  }

  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`;
  }

  return `${value.toFixed(0)}`;
}

export default function ItemDetailPage({ params }: { params: { id: string } }) {
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
          getItem(params.id),
          getPriceHistory(params.id, 90, 0, 1000),
          getItemTrends(params.id),
          getItemPrediction(params.id, '30_days'),
          getMultiSourcePrices(params.id, ['steam', 'csfloat'], 30),
        ]);

        if (cancelled) {
          return;
        }

        setItem(itemResponse as CatalogItem);
        setHistory(Array.isArray(historyResponse?.history) ? historyResponse.history : []);
        setTrends(trendsResponse as TrendResponse);
        setPrediction(predictionResponse as PredictionResponse);
        setMultiSourceData(sourceResponse);
        setSelectedSources(
          Array.isArray(sourceResponse?.sources) && sourceResponse.sources.length
            ? sourceResponse.sources
            : ['steam']
        );
      } catch (fetchError) {
        if (!cancelled) {
          setError(fetchError instanceof Error ? fetchError.message : 'Failed to load item data');
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    loadItemData();

    return () => {
      cancelled = true;
    };
  }, [params.id]);

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

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#0f1419]">
        <Header />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="rounded border border-[#2d3748] bg-[#1a1f2e] p-6 text-sm text-[#6b7280]">
            Loading item data from the backend...
          </div>
        </div>
      </div>
    );
  }

  if (error || !item) {
    return (
      <div className="min-h-screen bg-[#0f1419]">
        <Header />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Link href="/market" className="text-[#3b82f6] hover:underline text-xs font-medium mb-6 inline-block">
            ← MARKET
          </Link>
          <div className="rounded border border-[#2d3748] bg-[#1a1f2e] p-6">
            <h1 className="text-2xl font-semibold text-[#d1d5db] mb-2">Item unavailable</h1>
            <p className="text-sm text-[#6b7280]">{error || 'No backend item data was returned for this id.'}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0f1419]">
      <Header />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Link href="/market" className="text-[#3b82f6] hover:underline text-xs font-medium mb-6 inline-block">
          ← MARKET
        </Link>

        <div className="bg-[#1a1f2e] border border-[#2d3748] rounded p-6 mb-8">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <h1 className="text-3xl font-bold text-[#d1d5db] mb-2">{item.name}</h1>
              <div className="flex flex-wrap items-center gap-3 text-xs font-mono text-[#6b7280]">
                <span className="uppercase tracking-wide">{item.type}</span>
                {item.release_date && <span>{new Date(item.release_date).toLocaleDateString()}</span>}
                <span>{params.id}</span>
              </div>
            </div>

            <div className="text-right">
              <div className="text-4xl font-bold text-[#d1d5db] font-mono mb-1">
                <CountUpNumber from={latestPrice ?? 0} to={latestPrice ?? 0} decimals={2} formatFn={formatCurrency} />
              </div>
              <div
                className={`font-mono text-sm ${
                  (summary.priceChange24h ?? 0) >= 0 ? 'text-[#10b981]' : 'text-[#ef4444]'
                }`}
              >
                {formatPercent(summary.priceChange24h)} (24h)
              </div>
            </div>
          </div>

          <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded border border-[#2d3748] bg-[#131820] p-4">
              <div className="text-xs uppercase tracking-wide text-[#6b7280] mb-2">Trend</div>
              <div className="text-lg font-semibold text-[#d1d5db] capitalize">{trendDirection}</div>
              <div className="text-xs text-[#6b7280] mt-1">Confidence {confidence}</div>
            </div>
            <div className="rounded border border-[#2d3748] bg-[#131820] p-4">
              <div className="text-xs uppercase tracking-wide text-[#6b7280] mb-2">7d SMA</div>
              <div className="text-lg font-semibold text-[#d1d5db] font-mono">
                {formatCurrency(trends?.indicators?.sma_7 ?? null)}
              </div>
            </div>
            <div className="rounded border border-[#2d3748] bg-[#131820] p-4">
              <div className="text-xs uppercase tracking-wide text-[#6b7280] mb-2">30d SMA</div>
              <div className="text-lg font-semibold text-[#d1d5db] font-mono">
                {formatCurrency(trends?.indicators?.sma_30 ?? null)}
              </div>
            </div>
            <div className="rounded border border-[#2d3748] bg-[#131820] p-4">
              <div className="text-xs uppercase tracking-wide text-[#6b7280] mb-2">Volume 24h</div>
              <div className="text-lg font-semibold text-[#d1d5db] font-mono">
                {formatVolume(summary.volume24h)}
              </div>
            </div>
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
                    className={`px-3 py-2 text-xs font-medium transition-colors ${
                      timeRange === range
                        ? 'text-[#d1d5db] border-b-2 border-[#3b82f6]'
                        : 'text-[#6b7280] hover:text-[#d1d5db]'
                    }`}
                  >
                    {range.toUpperCase()}
                  </button>
                ))}
              </div>

              <div className="text-xs font-mono uppercase tracking-wide text-[#6b7280]">
                Backend history and source rows
              </div>
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
              className="bg-[#1a1f2e] border border-[#2d3748] p-4 rounded"
            >
              <ResponsiveContainer width="100%" height={360}>
                <LineChart data={sourceChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" />
                  <XAxis
                    dataKey="label"
                    stroke="#6b7280"
                    style={{ fontSize: '12px' }}
                  />
                  <YAxis
                    stroke="#6b7280"
                    style={{ fontSize: '12px' }}
                    domain={['dataMin - 10', 'dataMax + 10']}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1a1f2e',
                      border: '1px solid #2d3748',
                      color: '#d1d5db',
                      borderRadius: '4px',
                    }}
                    formatter={(value) => formatCurrency(Number(value))}
                  />
                  {visibleSources.includes('steam') && (
                    <Line
                      type="monotone"
                      dataKey="steam"
                      stroke="#cbd5e1"
                      strokeWidth={2}
                      dot={false}
                      isAnimationActive={false}
                      name="Steam"
                    />
                  )}
                  {visibleSources.includes('csfloat') && (
                    <Line
                      type="monotone"
                      dataKey="csfloat"
                      stroke="#ff6b35"
                      strokeWidth={2}
                      dot={false}
                      isAnimationActive={false}
                      name="CSFloat"
                    />
                  )}
                </LineChart>
              </ResponsiveContainer>
            </motion.div>
          </div>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className="bg-[#1a1f2e] border border-[#2d3748] rounded p-4 space-y-4 h-fit"
          >
            <div>
              <div className="text-xs uppercase tracking-wide text-[#6b7280] mb-2">Prediction</div>
              <div className="text-2xl font-bold text-[#d1d5db] font-mono">
                {forecast ? (
                  <CountUpNumber
                    from={forecast.mid}
                    to={forecast.mid}
                    decimals={2}
                    formatFn={formatCurrency}
                  />
                ) : (
                  '—'
                )}
              </div>
              <div className="text-xs text-[#6b7280] mt-1">
                {prediction?.period_label || '30_days'} forecast
              </div>
            </div>

            <div className="rounded border border-[#2d3748] bg-[#131820] p-4">
              <div className="text-xs uppercase tracking-wide text-[#6b7280] mb-2">Forecast band</div>
              <div className="space-y-1 font-mono text-sm text-[#d1d5db]">
                <div>Low {formatCurrency(forecast?.low ?? null)}</div>
                <div>Mid {formatCurrency(forecast?.mid ?? null)}</div>
                <div>High {formatCurrency(forecast?.high ?? null)}</div>
              </div>
            </div>

            <div className="rounded border border-[#2d3748] bg-[#131820] p-4">
              <div className="text-xs uppercase tracking-wide text-[#6b7280] mb-2">Data sources</div>
              <div className="space-y-2">
                {availableSources.map((source) => (
                  <div key={source} className="flex items-center justify-between text-sm">
                    <span className="capitalize text-[#d1d5db]">{source}</span>
                    <span className="text-[#6b7280]">
                      {(multiSourceData?.data[source]?.length ?? 0).toString()} points
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded border border-[#2d3748] bg-[#131820] p-4">
              <div className="text-xs uppercase tracking-wide text-[#6b7280] mb-2">Signals</div>
              <div className="space-y-2 text-sm text-[#d1d5db]">
                {trendFactors.length ? (
                  trendFactors.map((factor) => (
                    <div key={factor} className="leading-snug">
                      {factor}
                    </div>
                  ))
                ) : (
                  <div className="text-[#6b7280]">No technical factors returned yet.</div>
                )}
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
