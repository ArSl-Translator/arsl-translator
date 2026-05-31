import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, BarChart3, Camera, Gauge, Target, TrendingUp, Video } from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  BarChart,
  Bar,
} from 'recharts';
import { getHistory } from '../services/api';

const formatDayLabel = (date) =>
  date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

const getDayKey = (date) => date.toISOString().slice(0, 10);

export default function DashboardPage() {
  const [history, setHistory] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const pageSize = 100;

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const firstPage = await getHistory(1, pageSize);
      const total = firstPage.total ?? firstPage.items?.length ?? 0;
      const totalPages = Math.ceil(total / pageSize) || 1;
      let items = [...(firstPage.items || [])];

      for (let page = 2; page <= totalPages; page += 1) {
        const nextPage = await getHistory(page, pageSize);
        if (!nextPage.items || nextPage.items.length === 0) break;
        items = items.concat(nextPage.items);
      }

      setHistory({ ...firstPage, total, items });
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const { totalCount, videoCount, webcamCount, avgConfidence, dailyCounts, topLabels } = useMemo(() => {
    const items = history?.items || [];
    const total = history?.total ?? items.length;
    let video = 0;
    let webcam = 0;
    let confidenceSum = 0;
    let confidenceCount = 0;
    const labelCounts = {};

    items.forEach((item) => {
      if (item.prediction_type?.startsWith('video')) video += 1;
      else if (item.prediction_type?.startsWith('frames')) webcam += 1;

      if (typeof item.top_prediction_confidence === 'number') {
        confidenceSum += item.top_prediction_confidence;
        confidenceCount += 1;
      }

      const label = item.top_prediction_text || item.top_prediction_label || 'Unknown';
      labelCounts[label] = (labelCounts[label] || 0) + 1;
    });

    const today = new Date();
    const days = [];
    for (let i = 6; i >= 0; i -= 1) {
      const date = new Date(today);
      date.setDate(today.getDate() - i);
      days.push(date);
    }

    const dailyMap = days.reduce((acc, day) => {
      acc[getDayKey(day)] = { key: getDayKey(day), label: formatDayLabel(day), count: 0 };
      return acc;
    }, {});

    items.forEach((item) => {
      const key = getDayKey(new Date(item.created_at));
      if (dailyMap[key]) dailyMap[key].count += 1;
    });

    const top = Object.entries(labelCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([name, count]) => ({
        name: name.length > 18 ? `${name.slice(0, 18)}...` : name,
        count,
      }));

    return {
      totalCount: total,
      videoCount: video,
      webcamCount: webcam,
      avgConfidence: confidenceCount > 0 ? confidenceSum / confidenceCount : null,
      dailyCounts: Object.values(dailyMap),
      topLabels: top,
    };
  }, [history]);

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="panel overflow-hidden">
        <div className="border-b border-gray-200 bg-white px-6 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-gray-950 text-white">
              <BarChart3 className="h-5 w-5" />
            </div>
            <div>
              <p className="section-title">Model operations</p>
              <h2 className="mt-1 text-2xl font-bold tracking-tight text-gray-950">Prediction analytics</h2>
              <p className="mt-1 text-sm text-gray-500">
                Monitor usage, confidence, and the labels your recognition system is producing.
              </p>
            </div>
          </div>
        </div>

        <div className="p-6">
          {loading && (
            <div className="flex items-center justify-center py-12">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-gray-200 border-t-gray-950"></div>
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
              {error}
            </div>
          )}

          {!loading && !error && (!history?.items || history.items.length === 0) && (
            <div className="rounded-lg border border-dashed border-gray-200 bg-gray-50 py-14 text-center text-gray-500">
              <Activity className="mx-auto mb-4 h-12 w-12 opacity-30" />
              <p className="font-semibold text-gray-700">No predictions yet</p>
              <p className="mt-1 text-sm">Make a prediction to start collecting analytics.</p>
            </div>
          )}

          {!loading && !error && history?.items?.length > 0 && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
                {[
                  { label: 'Total predictions', value: totalCount, icon: Activity },
                  { label: 'Video predictions', value: videoCount, icon: Video },
                  { label: 'Webcam predictions', value: webcamCount, icon: Camera },
                  {
                    label: 'Average confidence',
                    value: avgConfidence != null ? `${(avgConfidence * 100).toFixed(1)}%` : '-',
                    icon: Gauge,
                  },
                ].map(({ label, value, icon: Icon }) => (
                  <div key={label} className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-semibold text-gray-500">{label}</p>
                      <Icon className="h-4 w-4 text-gray-400" />
                    </div>
                    <div className="mt-3 text-3xl font-bold tracking-tight text-gray-950">{value}</div>
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                <ChartPanel icon={TrendingUp} title="Last 7 days">
                  <LineChart data={dailyCounts}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="label" tick={{ fill: '#6b7280', fontSize: 12 }} />
                    <YAxis allowDecimals={false} tick={{ fill: '#6b7280', fontSize: 12 }} />
                    <Tooltip />
                    <Line type="monotone" dataKey="count" stroke="#111827" strokeWidth={2} dot={{ r: 3 }} />
                  </LineChart>
                </ChartPanel>

                <ChartPanel icon={Target} title="Prediction sources">
                  <BarChart data={[{ name: 'Video', count: videoCount }, { name: 'Webcam', count: webcamCount }]}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="name" tick={{ fill: '#6b7280', fontSize: 12 }} />
                    <YAxis allowDecimals={false} tick={{ fill: '#6b7280', fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#2563eb" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ChartPanel>
              </div>

              <ChartPanel icon={Video} title="Top predicted labels">
                <BarChart data={topLabels}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="name" tick={{ fill: '#6b7280', fontSize: 12 }} />
                  <YAxis allowDecimals={false} tick={{ fill: '#6b7280', fontSize: 12 }} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#2563eb" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ChartPanel>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ChartPanel({ icon: Icon, title, children }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5">
      <div className="mb-4 flex items-center gap-2">
        <Icon className="h-4 w-4 text-gray-500" />
        <h3 className="text-lg font-bold text-gray-900">{title}</h3>
      </div>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          {children}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
