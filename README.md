# TaxPilot Pro - Vercel Deployment

## Structure
```
vercel_backend/
├── api.py              # All API endpoints + admin panel routes
├── vercel.json         # Vercel configuration
├── requirements.txt   # Python dependencies
├── public/
│   ├── index.html      # Root landing page
│   └── admin/
│       ├── login.html  # Admin login
│       └── index.html  # Admin dashboard
└── .gitignore
```

## Deploy Steps

### 1. Push to GitHub
```bash
cd taxpilot-pro/vercel_backend
git init
git add .
git commit -m "Vercel ready"
git remote add origin https://github.com/YOUR_USERNAME/taxpilot-backend.git
git push -u origin main
```

### 2. Deploy on Vercel
1. Go to [vercel.com](https://vercel.com)
2. Add New Project → Import GitHub repo
3. Framework: **Python** (auto-detected)
4. Click Deploy

### 3. Add Environment Variables
In Vercel Dashboard → Settings → Environment Variables:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | Your Neon PostgreSQL connection string |
| `JWT_SECRET` | Any secure random string |
| `GROQ_API_KEY` | Your Groq API key from console.groq.com |

### 4. Get Your URL
After deployment, you'll get a URL like:
`https://taxpilot-backend.vercel.app`

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/auth/register` | User registration |
| POST | `/api/auth/login` | User login |
| GET | `/api/auth/profile` | Get user profile |
| GET | `/api/folders` | List folders |
| POST | `/api/folders` | Create folder |
| GET | `/api/folders/:id/documents` | Get folder documents |
| GET | `/api/documents` | List documents |
| POST | `/api/documents/upload` | Upload document |
| DELETE | `/api/documents/:id` | Delete document |
| GET | `/api/documents/types` | Get document types |
| POST | `/api/tax/calculate` | Calculate tax |
| GET | `/api/tax/slabs` | Get tax slabs |
| GET | `/api/tax/suggestions` | Tax saving tips |
| POST | `/api/chatbot/query` | Chat with AI |
| GET | `/api/chatbot/topics` | Chat topics |
| GET | `/api/chatbot/quick-actions` | Quick actions |

## Admin Panel
- **URL**: `https://your-app.vercel.app/admin`
- **Login**: `admin@taxpilot.com` / `admin123`

## Update Frontend API URL
After getting your Vercel URL, update:

**frontend/app.json:**
```json
{
  "extra": {
    "apiUrl": "https://your-app.vercel.app/api"
  }
}
```

**frontend/services/api.js:**
```javascript
const getApiBaseUrl = () => {
  if (__DEV__) {
    return 'http://localhost:5000/api';
  }
  return 'https://your-app.vercel.app/api';
};
```

## Database
Uses your existing **Neon PostgreSQL** connection string from `.env` file.
