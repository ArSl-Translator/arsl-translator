import React, { useEffect, useState, useRef, useCallback } from 'react';
import { Trophy, TrendingUp, Volume2, VolumeX } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Current audio instance so we can stop previous playback
let currentAudio = null;

/**
 * Play the pre-recorded audio file for a given label ID.
 * Files are served from: GET {API_BASE}/audio/{label_id}.mp3
 */
const playAudio = (labelId) => {
  if (!labelId) return;

  if (currentAudio) {
    currentAudio.pause();
    currentAudio.currentTime = 0;
    currentAudio = null;
  }

  const audio = new Audio(`${API_BASE}/audio/${labelId}.wav`);
  currentAudio = audio;
  audio.play().catch(() => {
    // Audio file doesn't exist yet for this label – silently ignore
    currentAudio = null;
  });
};

const stopAudio = () => {
  if (currentAudio) {
    currentAudio.pause();
    currentAudio.currentTime = 0;
    currentAudio = null;
  }
};

const canPlayAudio = (prediction) => /^\d+$/.test(String(prediction?.label_id || ''));

const PredictionResults = ({ result, loading = false }) => {
  const [muted, setMuted] = useState(() => {
    try { return localStorage.getItem('arsl_speech_muted') === 'true'; } catch { return false; }
  });
  const prevResultRef = useRef(null);

  const toggleMute = useCallback(() => {
    setMuted((prev) => {
      const next = !prev;
      try { localStorage.setItem('arsl_speech_muted', String(next)); } catch {}
      if (next) stopAudio();
      return next;
    });
  }, []);

  // Auto-play audio for the top prediction whenever a new result arrives
  useEffect(() => {
    if (!result || result === prevResultRef.current) return;
    prevResultRef.current = result;

    if (!muted && canPlayAudio(result.top_prediction)) {
      playAudio(result.top_prediction.label_id);
    }
  }, [result, muted]);

  if (loading) {
    return (
      <div className="card">
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-10 w-10 border-2 border-primary-200 border-t-primary-500"></div>
          <span className="ml-4 text-gray-600">Processing...</span>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="card">
        <p className="section-title">Prediction output</p>
        <div className="mt-8 text-center">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-lg bg-gray-100">
            <Trophy className="h-5 w-5 text-gray-400" />
          </div>
          <h3 className="mt-4 text-lg font-bold text-gray-900">No prediction yet</h3>
          <p className="mt-2 text-sm leading-6 text-gray-500">
            Upload or record a sign to see top ranked labels, confidence scores, and pronunciation controls.
          </p>
        </div>
      </div>
    );
  }

  const { top_prediction, top_k_predictions } = result;

  return (
    <div className="space-y-4">
      {top_prediction && (
        <div className="card">
          <div className="flex items-start gap-4">
            <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-gray-950">
              <Trophy className="h-5 w-5 text-white" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="section-title mb-2">Top Prediction</h3>
              <p className="mb-3 text-3xl font-bold text-gray-950">{top_prediction.text}</p>
              <div className="flex flex-wrap items-center gap-3">
                <span className="rounded-full bg-emerald-50 px-3 py-1 text-sm font-bold text-emerald-700">
                  {(top_prediction.confidence * 100).toFixed(1)}% confident
                </span>
                <span className="rounded-full bg-gray-100 px-3 py-1 text-sm font-semibold text-gray-500">
                  Label ID: {top_prediction.label_id}
                </span>
              </div>
            </div>
            {canPlayAudio(top_prediction) && (
              <div className="flex items-center gap-1 flex-shrink-0">
                <button
                  onClick={() => playAudio(top_prediction.label_id)}
                  className="rounded-lg p-2 text-gray-700 transition-colors hover:bg-gray-100"
                  title="Play pronunciation"
                >
                  <Volume2 className="w-5 h-5" />
                </button>
                <button
                  onClick={toggleMute}
                  className={`rounded-lg p-2 transition-colors ${
                    muted ? 'text-red-400 hover:bg-red-50' : 'text-gray-400 hover:bg-gray-100'
                  }`}
                  title={muted ? 'Unmute auto-play' : 'Mute auto-play'}
                >
                  {muted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-4 h-4 opacity-50" />}
                </button>
              </div>
            )}
            {!canPlayAudio(top_prediction) && (
              <div className="flex-shrink-0 rounded-lg bg-gray-100 px-3 py-1.5 text-xs font-semibold text-gray-500">
                Text output
              </div>
            )}
          </div>
        </div>
      )}

      {top_k_predictions && top_k_predictions.length > 1 && (
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-5 h-5 text-gray-500" />
            <h3 className="text-lg font-bold text-gray-900">Other Predictions</h3>
          </div>
          <div className="space-y-2">
            {top_k_predictions.slice(1).map((pred, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between rounded-lg border border-gray-100 bg-gray-50/80 p-3 transition-colors hover:bg-gray-100/80"
              >
                <div className="flex items-center gap-3">
                  <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-white text-sm font-bold text-gray-700 shadow-sm">
                    {idx + 2}
                  </span>
                  <div>
                    <p className="font-semibold text-gray-900">{pred.text}</p>
                    <p className="text-xs text-gray-500">Label ID: {pred.label_id}</p>
                  </div>
                </div>
                <div className="text-right flex items-center gap-3">
                  {canPlayAudio(pred) && (
                    <button
                      onClick={() => playAudio(pred.label_id)}
                      className="p-1.5 rounded-lg text-gray-400 hover:text-primary-500 hover:bg-primary-50 transition-colors"
                      title="Play pronunciation"
                    >
                      <Volume2 className="w-4 h-4" />
                    </button>
                  )}
                  <div>
                    <p className="font-bold text-gray-950">
                      {(pred.confidence * 100).toFixed(1)}%
                    </p>
                    <div className="w-20 bg-gray-200 rounded-full h-1.5 mt-1">
                      <div
                        className="bg-primary-500 h-1.5 rounded-full transition-all duration-300"
                        style={{ width: `${pred.confidence * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default PredictionResults;
