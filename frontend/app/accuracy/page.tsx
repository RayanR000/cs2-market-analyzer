'use client';

import { useEffect, useState } from 'react';
import { Header } from '@/components';
import {
  getAccuracySummary,
  type AccuracyRecord,
} from '@/lib/api';

type MetricValue = string | number | boolean | null | Record<string, unknown>;

interface GroupedAccuracy {
  prediction_type: string;
  horizon_days: number | null;
  evaluation_window_days: number | null;
  records: AccuracyRecord[];
}

function getLatest(records: AccuracyRecord[]): AccuracyRecord | null {
  if (!records.length) return null;
  return records.reduce((a, b) =>
    a.evaluation_date > b.evaluation_date ? a : b
  );
}

function MetricCard({
  label,
  value,
  unit,
  good,
}: {
  label: string;
  value: string | number;
  unit?: string;
  good?: boolean;
}) {
  const color = good === true ? 'text-[oklch(62%_0.14_155)]' :
    good === false ? 'text-[oklch(62%_0.12_25)]' :
    'text-primary';
  return (
    <div className="widget-block p-4">
      <div className="text-[10px] font-semibold uppercase tracking-[0.15em] text-muted mb-1">
        {label}
      </div>
      <div className={`font-data text-xl font-medium tabular-nums ${color}`}>
        {typeof value === 'number' ? value.toLocaleString(undefined, { maximumFractionDigits: 2 }) : value}
        {unit && <span className="text-sm text-secondary ml-1">{unit}</span>}
      </div>
    </div>
  );
}

function ForecastSection({ records }: { records: AccuracyRecord[] }) {
  const latest = getLatest(records);
  if (!latest) return null;
  const m = latest.metrics as Record<string, MetricValue>;

  return (
    <div className="mb-10">
      <div className="flex items-baseline justify-between mb-4">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-semibold text-primary">
            {latest.horizon_days}-Day Forecast
          </h3>
          <SourceBadge record={latest} />
        </div>
        <span className="text-[10px] font-data text-muted">
          {latest.sample_count.toLocaleString()} samples &middot; {latest.evaluation_date}
        </span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <MetricCard label="MAE" value={m.mae as number} unit="$" good={Number(m.mae) < 10} />
        <MetricCard label="RMSE" value={m.rmse as number} unit="$" />
        <MetricCard label="MAPE" value={m.mape as number} unit="%" good={Number(m.mape) < 15} />
        <MetricCard label="Directional Acc" value={m.directional_accuracy as number} unit="%" good={Number(m.directional_accuracy) > 50} />
        <MetricCard label="Interval Coverage" value={m.interval_coverage as number} unit="%" good={Number(m.interval_coverage) > 70} />
        <MetricCard label="Samples" value={latest.sample_count} />
      </div>
      {/* Confidence calibration */}
      <div className="mt-3 grid grid-cols-3 gap-3">
        <MetricCard label="Low Conf Acc" value={m.confidence_accuracy_low as number} unit="%" />
        <MetricCard label="Med Conf Acc" value={m.confidence_accuracy_medium as number} unit="%" />
        <MetricCard label="High Conf Acc" value={m.confidence_accuracy_high as number} unit="%" />
      </div>
    </div>
  );
}

function SourceBadge({ record }: { record: AccuracyRecord }) {
  return (
    <span className="text-[9px] font-bold uppercase tracking-[0.15em] px-2 py-0.5 rounded-sm bg-background-tertiary text-tertiary">
      LIVE
    </span>
  );
}



export default function AccuracyPage() {
  const [data, setData] = useState<GroupedAccuracy[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetch() {
      try {
        const summary = await getAccuracySummary();
        setData(summary as GroupedAccuracy[]);
      } catch {
        // empty
      } finally {
        setLoading(false);
      }
    }
    fetch();
  }, []);

  return (
    <div className="min-h-screen bg-background-primary">
      <Header />
      <main className="max-w-6xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="mb-10">
          <h1 className="text-2xl font-semibold tracking-tight text-primary">Prediction Accuracy</h1>
          <p className="text-sm text-secondary mt-1 max-w-lg">
            How well each signal type performs against actual market outcomes.
              <span className="block text-tertiary text-[11px] mt-1">
                <span className="text-tertiary">LIVE</span> = predictions made by the live ML forecast system.
              </span>
          </p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
          </div>
        ) : data.length === 0 ? (
          <div className="widget-block p-10 text-center">
            <p className="text-sm text-secondary">No accuracy data yet.</p>
            <p className="text-[11px] text-tertiary mt-2">
              Run <code className="font-data text-accent">python scripts/backtest_accuracy.py --type forecast</code> to generate metrics.
            </p>
          </div>
        ) : (
          data.map((group) => {
            const type = group.prediction_type;
            const label =
              type === 'forecast' ? `ML Forecast — ${group.horizon_days}d` :
              type;

            return (
              <div key={`${type}-${group.horizon_days ?? ''}-${group.evaluation_window_days ?? ''}`} className="mb-8">
                <div className="flex items-center gap-3 mb-4 border-b border-border pb-3">
                  <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-secondary">{label}</span>
                </div>
                {type === 'forecast' && <ForecastSection records={group.records} />}
              </div>
            );
          })
        )}

        {/* Footer */}
          {data.length > 0 && (
          <div className="mt-12 border-t border-border pt-8">
            <p className="text-[10px] font-data text-muted">
              Metrics compare stored ML forecasts against actual close prices. Updated daily via the backtesting pipeline.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
