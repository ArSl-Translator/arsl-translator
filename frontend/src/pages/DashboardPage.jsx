import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { BarChart3, Activity, Video, Camera, TrendingUp } from 'lucide-react';
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
        if (!nextPage.items || nextPage.items.length === 0) {
          break;
        }
        items = items.concat(nextPage.items);
      }

      setHistory({
        ...firstPage,
        total,
        items,
      });
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const {
    totalCount,
    videoCount,
    webcamCount,
    avgConfidence,
    dailyCounts,
    topLabels,
  } = useMemo(() => {
    const items = history?.items || [];
    const total = history?.total ?? items.length;

    let video = 0;
    let webcam = 0;
    let confidenceSum = 0;
    let confidenceCount = 0;
    const labelCounts = {};

    items.forEach((item) => {
      if (item.prediction_type === 'video') video += 1;
      else if (item.prediction_type === 'frames') webcam += 1;

      if (typeof item.top_prediction_confidence === 'number') {
        confidenceSum += item.top_prediction_confidence;
        confidenceCount += 1;
      }

      const label =
        item.top_prediction_text || item.top_prediction_label || 'Unknown';
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
      acc[getDayKey(day)] = {
        key: getDayKey(day),
        label: formatDayLabel(day),
        count: 0,
      };
      return acc;
    }, {});

    items.forEach((item) => {
      const created = new Date(item.created_at);
      const key = getDayKey(created);
      if (dailyMap[key]) {
        dailyMap[key].count += 1;
      }
    });

    const daily = Object.values(dailyMap);

    const top = Object.entries(labelCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([name, count]) => ({
        name: name.length > 18 ? `${name.slice(0, 18)}…` : name,
        count,
      }));

    return {
      totalCount: total,
      videoCount: video,
      webcamCount: webcam,
      avgConfidence:
        confidenceCount > 0 ? confidenceSum / confidenceCount : null,
      dailyCounts: daily,
      topLabels: top,
    };
  }, [history]);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="card">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center text-white">
            <BarChart3 className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-900 tracking-tight">Dashboard</h2>
            <p className="text-sm text-gray-500">
              Insights from your predictions · all data
            </p>
          </div>
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary-200 border-t-primary-500"></div>
        </div>
      )}

      {error && (
        <div className="px-4 py-3 rounded-xl bg-red-50 text-sm text-red-700">
          {error}
        </div>
      )}

      {!loading && !error && (!history?.items || history.items.length === 0) && (
        <div className="card text-center py-14 text-gray-500">
          <Activity className="w-14 h-14 mx-auto mb-4 opacity-30" />
          <p className="font-medium text-gray-600">No predictions yet</p>
          <p className="text-sm mt-1">
            Make a prediction to start seeing dashboard insights
          </p>
        </div>
      )}

      {!loading && !error && history?.items?.length > 0 && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="rounded-2xl bg-white/70 px-5 py-4">
              <div className="text-sm text-gray-500">Total Predictions</div>
              <div className="text-2xl font-bold text-gray-900 mt-1">
                {totalCount}
              </div>
            </div>
            <div className="rounded-2xl bg-white/70 px-5 py-4">
              <div className="text-sm text-gray-500">Video Predictions</div>
              <div className="text-2xl font-bold text-gray-900 mt-1">
                {videoCount}
              </div>
            </div>
            <div className="rounded-2xl bg-white/70 px-5 py-4">
              <div className="text-sm text-gray-500">Webcam Predictions</div>
              <div className="text-2xl font-bold text-gray-900 mt-1">
                {webcamCount}
              </div>
            </div>
            <div className="rounded-2xl bg-white/70 px-5 py-4">
              <div className="text-sm text-gray-500">Avg Confidence</div>
              <div className="text-2xl font-bold text-gray-900 mt-1">
                {avgConfidence != null
                  ? `${(avgConfidence * 100).toFixed(1)}%`
                  : '—'}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="rounded-2xl bg-white/70 px-5 py-4">
              <div className="flex items-center gap-2 mb-4">
                <TrendingUp className="w-4 h-4 text-gray-500" />
                <h3 className="text-lg font-semibold text-gray-800">
                  Predictions in the Last 7 Days
                </h3>
              </div>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={dailyCounts}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="label" />
                    <YAxis allowDecimals={false} />
                    <Tooltip />
                    <Line
                      type="monotone"
                      dataKey="count"
                      stroke="#2563eb"
                      strokeWidth={2}
                      dot={{ r: 3 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="rounded-2xl bg-white/70 px-5 py-4">
              <div className="flex items-center gap-2 mb-4">
                <Activity className="w-4 h-4 text-gray-500" />
                <h3 className="text-lg font-semibold text-gray-800">
                  Prediction Types
                </h3>
              </div>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={[
                      { name: 'Video', count: videoCount },
                      { name: 'Webcam', count: webcamCount },
                    ]}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis allowDecimals={false} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#10b981" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          <div className="rounded-2xl bg-white/70 px-5 py-4">
            <div className="flex items-center gap-2 mb-4">
              <Video className="w-4 h-4 text-gray-500" />
              <Camera className="w-4 h-4 text-gray-500" />
              <h3 className="text-lg font-semibold text-gray-800">
                Top Predicted Labels
              </h3>
            </div>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={topLabels}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
