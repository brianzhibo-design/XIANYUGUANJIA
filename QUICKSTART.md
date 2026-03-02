# Quick Start Guide

## 5-Minute Setup

### 1. Prerequisites

Ensure you have installed:
- Node.js >= 18
- PostgreSQL >= 14
- npm or yarn

### 2. Installation

```bash
# Make setup script executable
chmod +x setup.sh

# Run setup
./setup.sh
```

Or manually:

```bash
# Install dependencies
cd server && npm install
cd ../client && npm install

# Create environment files
cp server/.env.example server/.env
cp client/.env.example client/.env
```

### 3. Configure API Keys

Edit `server/.env` and add your API keys:

```bash
# Required
JWT_SECRET=your_random_secret_key_here

# GitHub OAuth (https://github.com/settings/developers)
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret

# Stripe (https://dashboard.stripe.com/test/apikeys)
STRIPE_SECRET_KEY=sk_test_your_key

# GLM-5 API (https://open.bigmodel.cn)
GLM5_API_KEY=your_glm5_api_key
```

### 4. Database Setup

```bash
# Create database
createdb code_review_db

# Run schema
psql code_review_db < database/schema.sql
```

### 5. Start Services

```bash
# Terminal 1 - Backend
cd server
npm run dev

# Terminal 2 - Frontend
cd client
npm run dev
```

### 6. Access Application

Open http://localhost:5173

---

## Getting API Keys

### GitHub OAuth

1. Go to https://github.com/settings/developers
2. Click "New OAuth App"
3. Fill in:
   - Application name: CodeReview Local
   - Homepage URL: http://localhost:5173
   - Callback URL: http://localhost:3001/api/auth/github/callback
4. Copy Client ID and Client Secret

### Stripe

1. Go to https://dashboard.stripe.com/test/apikeys
2. Copy "Secret key" (starts with sk_test_)
3. For webhooks, use Stripe CLI:
   ```bash
   stripe listen --forward-to localhost:3001/api/payment/webhook
   ```

### GLM-5 API

1. Go to https://open.bigmodel.cn
2. Register/Login
3. Create API key in console
4. Copy API key

---

## First Steps

1. **Register Account**
   - Go to http://localhost:5173/register
   - Create account with email or GitHub

2. **Review Your First Code**
   - Click "New Review"
   - Paste code or upload file
   - Select language
   - Click "Start Review"

3. **View Results**
   - Check security issues
   - Review performance suggestions
   - See best practices

4. **Upgrade Plan**
   - Go to Pricing page
   - Select plan
   - Complete payment (test mode)

---

## Testing

### Test Credit Cards (Stripe)

- Success: 4242 4242 4242 4242
- Failed: 4000 0000 0000 0002
- Any future expiry date
- Any CVC

### API Testing

```bash
# Health check
curl http://localhost:3001/health

# Register user
curl -X POST http://localhost:3001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"test123","username":"testuser"}'
```

---

## Common Issues

### Port Already in Use

```bash
# Kill process on port 3001
lsof -ti:3001 | xargs kill -9

# Kill process on port 5173
lsof -ti:5173 | xargs kill -9
```

### Database Connection Failed

```bash
# Check PostgreSQL is running
pg_isready

# Start PostgreSQL (macOS)
brew services start postgresql@14

# Start PostgreSQL (Ubuntu)
sudo systemctl start postgresql
```

### npm install Fails

```bash
# Clear cache
npm cache clean --force

# Delete node_modules
rm -rf node_modules package-lock.json

# Reinstall
npm install
```

---

## Need Help?

- 📖 Full docs: [docs/API.md](docs/API.md)
- 🚀 Deployment: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- 🐛 Issues: https://github.com/yourrepo/code-review-service/issues
- 💬 Discord: https://discord.gg/yourserver
