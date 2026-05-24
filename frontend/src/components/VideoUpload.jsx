import React, { useState, useRef } from 'react';
import { ArrowRight, FileVideo, Upload, Video, X } from 'lucide-react';
import { predictVideo } from '../services/api';
import ModelSelector from './ModelSelector';
import PredictionResults from './PredictionResults';

const VideoUpload = () => {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [model, setModel] = useState(() => localStorage.getItem('arsl_selected_model') || 'karsl_mediapipe');
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setPreview(URL.createObjectURL(selectedFile));
      setResult(null);
      setError(null);
    }
  };

  const handleClear = () => {
    setFile(null);
    setPreview(null);
    setResult(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleModelChange = (nextModel) => {
    setModel(nextModel);
    localStorage.setItem('arsl_selected_model', nextModel);
    setResult(null);
    setError(null);
  };

  const handlePredict = async () => {
    if (!file) return;

    setLoading(true);
    setError(null);

    try {
      const prediction = await predictVideo(file, 5, model);
      setResult(prediction);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Prediction failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto grid max-w-7xl gap-6 xl:grid-cols-[minmax(0,1fr)_420px]">
      <div className="panel overflow-hidden">
        <div className="border-b border-gray-200 bg-white px-6 py-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="section-title">Video intelligence</p>
              <h2 className="mt-2 text-2xl font-bold tracking-tight text-gray-950">Upload a sign video</h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-500">
                Upload an Arabic sign clip and receive ranked translation results with confidence scores.
              </p>
            </div>
            <div className="hidden rounded-lg border border-gray-200 bg-gray-50 p-3 text-gray-600 sm:block">
              <FileVideo className="h-5 w-5" />
            </div>
          </div>
        </div>

        <div className="space-y-5 p-6">
          <ModelSelector value={model} onChange={handleModelChange} disabled={loading} />

          <div
            className={`rounded-lg border-2 border-dashed p-10 text-center transition-all duration-200 ${
              file
                ? 'border-gray-950 bg-gray-50'
                : 'border-gray-200 hover:border-gray-400 hover:bg-gray-50'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="video/*"
              onChange={handleFileChange}
              className="hidden"
              id="video-upload"
            />
            <label
              htmlFor="video-upload"
              className="cursor-pointer flex flex-col items-center"
            >
              {file ? (
                <Video className="mb-3 h-12 w-12 text-gray-950" />
              ) : (
                <Upload className="mb-3 h-12 w-12 text-gray-400" />
              )}
              <span className="text-base font-bold text-gray-800">
                {file ? file.name : 'Click to upload video'}
              </span>
              <span className="mt-1 text-sm text-gray-500">
                MP4, AVI, MOV (max 100MB)
              </span>
            </label>
          </div>

          {preview && (
            <div className="relative overflow-hidden rounded-lg border border-gray-200 bg-black">
              <video
                src={preview}
                controls
                className="max-h-[520px] w-full"
              />
              <button
                onClick={handleClear}
                className="absolute right-3 top-3 rounded-lg bg-red-500/90 p-2 text-white transition-colors hover:bg-red-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          )}

          <div className="flex gap-3">
            <button
              onClick={handlePredict}
              disabled={!file || loading}
              className="btn-primary flex-1"
            >
              {loading ? 'Processing...' : (
                <>
                  Predict Sign
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
            {file && !loading && (
              <button onClick={handleClear} className="btn-secondary">
                Clear
              </button>
            )}
          </div>

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
              {error}
            </div>
          )}
        </div>
      </div>

      <div className="space-y-6">
        <PredictionResults result={result} loading={loading} />
      </div>
    </div>
  );
};

export default VideoUpload;
