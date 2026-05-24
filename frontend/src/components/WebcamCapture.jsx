import React, { useState, useRef, useEffect } from 'react';
import { Camera, Circle, Play, Square } from 'lucide-react';
import { predictFrames } from '../services/api';
import ModelSelector from './ModelSelector';
import PredictionResults from './PredictionResults';

const WebcamCapture = () => {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  const [stream, setStream] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [frameBuffer, setFrameBuffer] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [model, setModel] = useState(() => localStorage.getItem('arsl_selected_model') || 'karsl_mediapipe');

  const [webcamError, setWebcamError] = useState(null);
  const [isVideoReady, setIsVideoReady] = useState(false);

  const [bufferSize, setBufferSize] = useState(60);
  const captureIntervalRef = useRef(null);
  const frameBufferRef = useRef([]);
  const isPredictingRef = useRef(false);

  const startWebcam = async () => {
    try {
      setWebcamError(null);
      setError(null);
      setIsVideoReady(false);

      // Stop previous stream if any (avoids “busy device” edge cases)
      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
      }

      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 },
        audio: false,
      });

      setStream(mediaStream);
    } catch (err) {
      setWebcamError(`Failed to access webcam: ${err.message}`);
      console.error('Webcam error:', err);
    }
  };

  const stopWebcam = () => {
    if (captureIntervalRef.current) {
      clearInterval(captureIntervalRef.current);
      captureIntervalRef.current = null;
    }
    setIsRecording(false);
    setFrameBuffer([]);
    frameBufferRef.current = [];
    setIsVideoReady(false);

    if (videoRef.current) {
      videoRef.current.pause?.();
      videoRef.current.srcObject = null;
    }

    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      setStream(null);
    }
  };

  // ✅ Key fix: when stream changes AND video element exists, attach srcObject
  useEffect(() => {
    const videoEl = videoRef.current;
    if (!stream || !videoEl) return;

    setIsVideoReady(false);
    videoEl.srcObject = stream;

    const onReady = () => {
      // Sometimes loadedmetadata fires but videoWidth is still 0,
      // so we also rely on canplay/playing.
      setIsVideoReady(true);
    };

    const onLoadedMetadata = () => {
      videoEl.play().catch(() => {
        // If autoplay is blocked for some reason, user can click Start Recording later
      });
    };

    videoEl.addEventListener('loadedmetadata', onLoadedMetadata);
    videoEl.addEventListener('canplay', onReady);
    videoEl.addEventListener('playing', onReady);

    return () => {
      videoEl.removeEventListener('loadedmetadata', onLoadedMetadata);
      videoEl.removeEventListener('canplay', onReady);
      videoEl.removeEventListener('playing', onReady);
    };
  }, [stream]);

  const captureFrame = () => {
    if (!videoRef.current || !canvasRef.current) return null;

    const video = videoRef.current;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');

    if (video.videoWidth === 0 || video.videoHeight === 0) return null;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0);

    return canvas.toDataURL('image/jpeg', 0.8);
  };

  const stopRecording = () => {
    setIsRecording(false);
    if (captureIntervalRef.current) {
      clearInterval(captureIntervalRef.current);
      captureIntervalRef.current = null;
    }
  };

  const handlePredict = async (frames) => {
    const toPredict = frames || frameBufferRef.current;
    if (!toPredict.length) {
      setError('No frames captured');
      return;
    }

    if (isPredictingRef.current) return;
    isPredictingRef.current = true;

    setLoading(true);
    setError(null);

    try {
      const prediction = await predictFrames(toPredict, 5, model);
      setResult(prediction);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Prediction failed');
    } finally {
      setLoading(false);
      isPredictingRef.current = false;
    }
  };

  const handleModelChange = (nextModel) => {
    setModel(nextModel);
    localStorage.setItem('arsl_selected_model', nextModel);
    setResult(null);
    setError(null);
  };

  const startRecording = () => {
    if (!stream) {
      setError('Start the webcam first.');
      return;
    }
    if (!isVideoReady) {
      setError('Video is not ready yet. Please wait a second.');
      return;
    }

    setIsRecording(true);
    setFrameBuffer([]);
    frameBufferRef.current = [];
    isPredictingRef.current = false;
    setResult(null);
    setError(null);

    captureIntervalRef.current = setInterval(() => {
      if (isPredictingRef.current) return;

      const frame = captureFrame();
      if (!frame) return;

      frameBufferRef.current.push(frame);
      setFrameBuffer([...frameBufferRef.current]);

      if (frameBufferRef.current.length >= bufferSize) {
        stopRecording();
        handlePredict(frameBufferRef.current);
      }
    }, 33);
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => stopWebcam();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="mx-auto grid max-w-7xl gap-6 xl:grid-cols-[minmax(0,1fr)_420px]">
      <div className="panel overflow-hidden">
        <div className="border-b border-gray-200 bg-white px-6 py-5">
          <p className="section-title">Live recognition</p>
          <h2 className="mt-2 text-2xl font-bold tracking-tight text-gray-950">Webcam capture</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-500">
            Record a short isolated sign directly from the browser and send sampled frames to the API.
          </p>
        </div>

        <div className="space-y-5 p-6">
        <ModelSelector
          value={model}
          onChange={handleModelChange}
          disabled={isRecording || loading}
        />

        <div className="relative mb-4 overflow-hidden rounded-lg bg-gray-950">
          {!stream ? (
            <div className="aspect-video flex items-center justify-center">
                <button onClick={startWebcam} className="btn-primary">
                <Camera className="w-5 h-5 inline mr-2" />
                Start Webcam
              </button>
            </div>
          ) : (
            <>
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="mx-auto max-h-[560px] w-full"
                style={{ display: 'block' }}
              />

              {!isVideoReady && (
                <div className="absolute left-4 top-4 rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-white">
                  Loading video...
                </div>
              )}

              {isRecording && (
                <div className="absolute left-4 top-4 flex items-center gap-2 rounded-lg bg-red-500/90 px-4 py-2 text-sm font-semibold text-white">
                  <Circle className="w-3 h-3 animate-pulse fill-current" />
                  Recording {frameBuffer.length}/{bufferSize}
                </div>
              )}

              <div className="absolute right-4 top-4 rounded-lg bg-black/70 px-4 py-2 text-sm font-semibold text-white">
                {frameBuffer.length} frames
              </div>
            </>
          )}
        </div>

        <canvas ref={canvasRef} className="hidden" />

        {webcamError && (
          <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-medium text-amber-800">
            {webcamError}
          </div>
        )}

        {stream && (
          <div className="mb-4 rounded-lg border border-gray-200 bg-gray-50 px-4 py-3">
            <label className="mb-2 block text-sm font-semibold text-gray-700">
              Buffer: {bufferSize} frames (~{(bufferSize / 30).toFixed(1)}s)
            </label>
            <input
              type="range"
              min="30"
              max="120"
              step="10"
              value={bufferSize}
              onChange={(e) => setBufferSize(Number(e.target.value))}
              disabled={isRecording}
              className="h-2 w-full rounded-full accent-gray-950"
            />
          </div>
        )}

        {stream && (
          <div className="flex gap-3">
            {!isRecording ? (
              <>
                <button
                  onClick={startRecording}
                  disabled={!isVideoReady}
                  className="btn-primary flex-1"
                >
                  <Play className="w-5 h-5 inline mr-2" />
                  {isVideoReady ? 'Start Recording' : 'Loading...'}
                </button>
                <button onClick={stopWebcam} className="btn-secondary">
                  Stop Webcam
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => {
                    stopRecording();
                    handlePredict(frameBufferRef.current);
                  }}
                  className="btn-primary flex-1"
                >
                  <Square className="w-5 h-5 inline mr-2" />
                  Stop & Predict
                </button>
                <button onClick={stopRecording} className="btn-danger">
                  Cancel
                </button>
              </>
            )}
          </div>
        )}

        {error && (
          <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
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

export default WebcamCapture;
