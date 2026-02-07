# ArSL Translator Frontend

Modern React web application for Arabic Sign Language recognition.

## Tech Stack

- **React 18** - UI library
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **React Router** - Client-side routing
- **Axios** - HTTP client
- **Lucide React** - Icon library

## Features

### 🎥 Video Upload
- Drag & drop or click to upload
- Video preview before prediction
- Support for multiple video formats (MP4, AVI, MOV)
- Real-time prediction results

### 📹 Webcam Capture
- Live webcam feed
- Configurable frame buffer (30-120 frames)
- Visual recording indicator
- Auto-predict when buffer is full
- Manual prediction trigger

### 📊 Prediction Results
- Top prediction highlighted
- Top-K predictions with confidence scores
- Visual confidence bars
- Clean, modern UI

### 🔄 API Status
- Real-time API health monitoring
- Model loaded indicator
- Automatic status checks

## Installation

```bash
# Install dependencies
npm install

# Create environment file
cp .env.example .env

# Start development server
npm run dev
```

## Configuration

Create `.env` file:

```env
VITE_API_URL=http://localhost:8000
```

## Development

```bash
# Start dev server (with hot reload)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Lint code
npm run lint
```

## Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── VideoUpload.jsx       # Video upload interface
│   │   ├── WebcamCapture.jsx     # Webcam capture interface
│   │   └── PredictionResults.jsx # Prediction display
│   ├── services/
│   │   └── api.js                # API client
│   ├── App.jsx                   # Main application
│   ├── main.jsx                  # Entry point
│   └── index.css                 # Global styles + Tailwind
├── index.html                    # HTML template
├── vite.config.js                # Vite configuration
├── tailwind.config.js            # Tailwind configuration
├── postcss.config.js             # PostCSS configuration
└── package.json                  # Dependencies
```

## Components

### VideoUpload

Handles video file uploads and predictions.

**Features:**
- File input with drag & drop
- Video preview
- Upload progress
- Error handling
- Results display

### WebcamCapture

Handles real-time webcam capture and prediction.

**Features:**
- Webcam initialization
- Frame capture at 30fps
- Configurable buffer size
- Recording indicator
- Auto-prediction
- Manual stop & predict

### PredictionResults

Displays prediction results in a beautiful format.

**Features:**
- Top prediction highlighted
- Top-K predictions list
- Confidence percentages
- Visual progress bars
- Loading states

## API Integration

The app communicates with the FastAPI backend through `src/services/api.js`.

### API Client

```javascript
import { predictVideo, predictFrames, healthCheck } from './services/api';

// Upload video
const result = await predictVideo(file, topK);

// Send webcam frames
const result = await predictFrames(base64Frames, topK);

// Check API health
const health = await healthCheck();
```

## Styling

The app uses **Tailwind CSS** for styling with a custom color scheme:

### Primary Colors
- `primary-50` to `primary-900` - Purple gradient

### Custom Components
- `.btn-primary` - Primary button style
- `.btn-secondary` - Secondary button style
- `.btn-danger` - Danger button style
- `.card` - Card container style
- `.input` - Input field style

## Browser Support

- Chrome/Edge (recommended)
- Firefox
- Safari 14+

**Note:** Webcam features require HTTPS or localhost.

## Troubleshooting

### API Connection Failed

**Problem:** "Failed to fetch" error

**Solutions:**
1. Check API is running: `curl http://localhost:8000/health`
2. Verify VITE_API_URL in `.env`
3. Check CORS settings in backend

### Webcam Not Working

**Problem:** Webcam won't start

**Solutions:**
1. Grant camera permissions in browser
2. Use Chrome (best support)
3. Ensure HTTPS or localhost
4. Check if camera is used by another app

### Build Errors

**Problem:** Build fails with dependency errors

**Solutions:**
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install

# Use correct Node version
nvm use 18
```

## Production Deployment

### Build

```bash
npm run build
```

Output will be in `dist/` directory.

### Serve

```bash
# Preview locally
npm run preview

# Or use any static server
npx serve -s dist

# Or deploy to:
# - Vercel
# - Netlify
# - GitHub Pages
# - Any static hosting
```

### Environment Variables

For production, set:
```env
VITE_API_URL=https://your-api-domain.com
```

## Performance

### Optimizations

- Lazy loading of components
- Image optimization
- Code splitting
- Tree shaking
- Minification
- Gzip compression

### Bundle Size

- React + React DOM: ~130 KB
- Router + Axios: ~40 KB
- Tailwind CSS: ~5 KB (purged)
- Total: ~180 KB gzipped

## Contributing

1. Create feature branch
2. Make changes
3. Test thoroughly
4. Submit pull request

## License

MIT License - see LICENSE file for details
