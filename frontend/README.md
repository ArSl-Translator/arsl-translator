# ArSL Translator Frontend

This is the React/Vite web application for the ArSL Translator platform. It provides the browser interface for sign recognition, authentication, prediction history, dashboard views, and the Android Offline Chat download page.

## Tech Stack

- React 18
- Vite
- Tailwind CSS
- React Router
- Axios
- Lucide React icons

## Main Features

| Area | Description |
|---|---|
| Video upload | Upload a sign video and send it to the selected backend model |
| Webcam capture | Capture browser frames and send them as a sequence |
| Model selection | Uses `/api/health` to enable available engines |
| Prediction results | Shows top prediction, confidence, label ID, and top-k alternatives |
| Auth | Register, login, JWT-protected routes |
| History | Shows previous authenticated predictions |
| Dashboard | Displays platform usage summaries |
| Offline chat page | Publishes the signed Android APK and two-phone demo link |

## Recognition Engines

The frontend supports these backend model keys:

```text
karsl_mediapipe
arsl_rag
arabsign
karsl
```

Availability comes from:

```text
GET /api/health
```

If a model checkpoint is not mounted on the API container, that engine is shown as unavailable instead of breaking the UI.

`arsl_rag` is the Arabic Alphabet RAG route. It becomes selectable when the backend finds the Chroma index from `sign_index.zip` under:

```text
models/rag_sign_index/
```

## Android APK Download

The Offline Chat page links to:

```text
/downloads/accessible-chat.apk
```

Source file in the repo:

```text
frontend/public/downloads/accessible-chat.apk
```

Current checked APK matches the latest local release build:

```text
Release APK: offline-chat-android/app/build/outputs/apk/release/app-release.apk
SHA-256:     499EE72EEC0AB061B8E4CA06E9DEF3477988C06C5E1E6165D02317EC2A3AE0F5
Size:        13,124,454 bytes
```

When a new Android release is built, copy it into the frontend public folder:

```powershell
Copy-Item `
  ..\offline-chat-android\app\build\outputs\apk\release\app-release.apk `
  public\downloads\accessible-chat.apk `
  -Force
```

## Development

Install dependencies:

```bash
npm install
```

Create `.env`:

```env
VITE_API_URL=http://localhost:8000
```

Run locally:

```bash
npm run dev
```

Run on a VM or remote desktop session:

```bash
VITE_API_URL=http://localhost:8000 npm run dev -- --host 0.0.0.0 --port 3000
```

Build:

```bash
npm run build
```

Preview:

```bash
npm run preview
```

## Production

Production uses Docker. The frontend image builds the Vite app and serves the static files through Nginx. Caddy routes public traffic:

```text
https://arsl.hadighazi.com/       -> frontend
https://arsl.hadighazi.com/api/*  -> FastAPI backend
https://arsl.hadighazi.com/mlflow -> MLflow
```

Production API base URL is passed at build/runtime through:

```env
VITE_API_URL=/api
```

## Browser Notes

- Webcam access requires HTTPS or localhost.
- Chrome/Edge generally provide the best camera support.
- VM remote desktop sessions often do not expose the local laptop webcam; use video upload or open the production site directly from the laptop.
