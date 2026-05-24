import React, { useEffect, useMemo, useState } from 'react';
import { CheckCircle2, Layers, Loader2 } from 'lucide-react';
import { healthCheck } from '../services/api';

export const MODEL_OPTIONS = [
  {
    value: 'karsl_mediapipe',
    title: 'KArSL isolated-sign recognition',
    description: 'Best for single Arabic signs with the trained 502-class landmark model.',
  },
  {
    value: 'arabsign',
    title: 'ArabSign phrase translation',
    description: 'Best for continuous Arabic sign phrases using the ArabSign sequence model.',
  },
  {
    value: 'karsl',
    title: 'KArSL image-sequence recognition',
    description: 'Alternative visual recognition path when its model is installed.',
  },
];

const preferredOrder = ['karsl_mediapipe', 'arabsign', 'karsl'];

const ModelSelector = ({ value, onChange, disabled = false }) => {
  const [health, setHealth] = useState(null);
  const [loadingHealth, setLoadingHealth] = useState(true);

  useEffect(() => {
    let cancelled = false;

    healthCheck()
      .then((data) => {
        if (!cancelled) {
          setHealth(data);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setHealth(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingHealth(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const loadedModels = health?.models || null;

  const availableModel = useMemo(() => {
    if (!loadedModels) return null;
    return preferredOrder.find((modelName) => loadedModels[modelName]?.loaded) || null;
  }, [loadedModels]);

  useEffect(() => {
    if (!loadedModels || !availableModel) return;
    if (!loadedModels[value]?.loaded) {
      onChange(availableModel);
    }
  }, [availableModel, loadedModels, onChange, value]);

  const isModelReady = (modelName) => {
    if (!loadedModels) return true;
    return Boolean(loadedModels[modelName]?.loaded);
  };

  return (
    <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <label className="flex items-center gap-2 text-sm font-semibold text-gray-700">
          <Layers className="h-4 w-4 text-gray-400" />
          Recognition engine
        </label>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-gray-200 bg-white px-2.5 py-1 text-xs font-semibold text-gray-500">
          {loadingHealth ? (
            <>
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Checking
            </>
          ) : (
            <>
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
              Live options
            </>
          )}
        </span>
      </div>

      <div className="grid gap-2">
        {MODEL_OPTIONS.map((option) => {
          const ready = isModelReady(option.value);
          const selected = value === option.value;

          return (
            <button
              key={option.value}
              type="button"
              onClick={() => ready && onChange(option.value)}
              disabled={disabled || !ready}
              className={`rounded-lg border px-4 py-3 text-left transition ${
                selected
                  ? 'border-gray-950 bg-white shadow-sm'
                  : 'border-gray-200 bg-white hover:border-gray-400'
              } ${disabled || !ready ? 'cursor-not-allowed opacity-55' : ''}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-bold text-gray-950">{option.title}</p>
                  <p className="mt-1 text-xs leading-5 text-gray-500">{option.description}</p>
                </div>
                <span
                  className={`mt-0.5 rounded-full px-2 py-1 text-[11px] font-bold ${
                    ready
                      ? selected
                        ? 'bg-gray-950 text-white'
                        : 'bg-emerald-50 text-emerald-700'
                      : 'bg-gray-100 text-gray-500'
                  }`}
                >
                  {ready ? (selected ? 'Selected' : 'Ready') : 'Unavailable'}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default ModelSelector;
