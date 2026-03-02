# Deployment Guide

## Prerequisites

- Node.js >= 18
- PostgreSQL >= 14
- Domain name (recommended)
- SSL certificate (for production)

## Environment Variables

### Backend (.env)

```bash
NODE_ENV=production
PORT=3001
DATABASE_URL=postgresql://user:password@host:5432/dbname
JWT_SECRET=your_super_secret_jwt_key
JWT_EXPIRE=7d
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
GITHUB_CALLBACK_URL=https://yourdomain.com/api/auth/github/callback
STRIPE_SECRET_KEY=sk_live_your_key
STRIPE_WEBHOOK_SECRET=whsec_your_secret
GLM5_API_KEY=your_glm5_api_key
FRONTEND_URL=https://yourdomain.com
```

### Frontend (.env)

```bash
REACT_APP_API_URL=https://yourdomain.com/api
```

---

## Option 1: Traditional Deployment (VPS)

### 1. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Install PM2
sudo npm install -g pm2

# Install Nginx
sudo apt install -y nginx
```

### 2. Database Setup

```bash
sudo -u postgres psql

CREATE DATABASE code_review_db;
CREATE USER your_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE code_review_db TO your_user;
\q
```

### 3. Application Deployment

```bash
# Clone repository
git clone https://github.com/yourrepo/code-review-service.git
cd code-review-service

# Backend setup
cd server
npm install --production
cp .env.example .env
# Edit .env with production values

# Frontend setup
cd ../client
npm install
npm run build

# Start backend with PM2
cd ../server
pm2 start src/app.js --name code-review-api

# Save PM2 config
pm2 save
pm2 startup
```

### 4. Nginx Configuration

```nginx
# /etc/nginx/sites-available/code-review

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Frontend
    location / {
        root /path/to/code-review-service/client/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:3001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Stripe webhook (requires raw body)
    location /api/payment/webhook {
        proxy_pass http://localhost:3001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/code-review /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 5. SSL Certificate (Let's Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

---

## Option 2: Docker Deployment

### Dockerfile (Backend)

```dockerfile
FROM node:18-alpine

WORKDIR /app

COPY server/package*.json ./
RUN npm install --production

COPY server/src ./src

EXPOSE 3001

CMD ["node", "src/app.js"]
```

### Dockerfile (Frontend)

```dockerfile
FROM node:18-alpine as builder

WORKDIR /app
COPY client/package*.json ./
RUN npm install
COPY client/ ./
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  db:
    image: postgres:14-alpine
    environment:
      POSTGRES_DB: code_review_db
      POSTGRES_USER: your_user
      POSTGRES_PASSWORD: your_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: always

  backend:
    build: ./server
    ports:
      - "3001:3001"
    environment:
      NODE_ENV: production
      DATABASE_URL: postgresql://your_user:your_password@db:5432/code_review_db
      JWT_SECRET: ${JWT_SECRET}
      GITHUB_CLIENT_ID: ${GITHUB_CLIENT_ID}
      GITHUB_CLIENT_SECRET: ${GITHUB_CLIENT_SECRET}
      STRIPE_SECRET_KEY: ${STRIPE_SECRET_KEY}
      GLM5_API_KEY: ${GLM5_API_KEY}
      FRONTEND_URL: ${FRONTEND_URL}
    depends_on:
      - db
    restart: always

  frontend:
    build: ./client
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: always

volumes:
  postgres_data:
```

```bash
docker-compose up -d
```

---

## Option 3: Cloud Platforms

### Heroku

```bash
# Install Heroku CLI
npm install -g heroku

# Create apps
heroku create code-review-api
heroku create code-review-client

# Add PostgreSQL
heroku addons:create heroku-postgresql:mini -a code-review-api

# Deploy backend
cd server
git subtree push --prefix server heroku main

# Deploy frontend
cd ../client
git subtree push --prefix client heroku main
```

### Vercel (Frontend) + Railway (Backend)

**Frontend (Vercel):**
```bash
npm install -g vercel
cd client
vercel --prod
```

**Backend (Railway):**
1. Connect GitHub repo to Railway
2. Add PostgreSQL addon
3. Set environment variables
4. Deploy

### AWS (ECS + RDS)

1. Create RDS PostgreSQL instance
2. Build Docker images and push to ECR
3. Create ECS task definitions
4. Set up Application Load Balancer
5. Configure Route53 for DNS

---

## Monitoring & Logging

### PM2 Monitoring

```bash
pm2 monit
pm2 logs code-review-api
```

### Log Rotation

```bash
pm2 install pm2-logrotate
pm2 set pm2-logrotate:max_size 10M
pm2 set pm2-logrotate:retain 7
```

### Health Check

```bash
# Add to crontab
*/5 * * * * curl -f http://localhost:3001/health || pm2 restart code-review-api
```

---

## Backup Strategy

### Database Backup

```bash
# Daily backup script
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d)
pg_dump -U your_user code_review_db > $BACKUP_DIR/db_$DATE.sql

# Keep only last 30 days
find $BACKUP_DIR -name "db_*.sql" -mtime +30 -delete
```

### Automated Backup (cron)

```bash
# Edit crontab
crontab -e

# Daily backup at 2 AM
0 2 * * * /path/to/backup_script.sh
```

---

## Scaling

### Horizontal Scaling

1. Use load balancer (Nginx/ALB)
2. Run multiple backend instances
3. Use Redis for session management
4. Consider read replicas for database

### Performance Optimization

1. Enable gzip compression in Nginx
2. Use CDN for static assets
3. Implement caching strategies
4. Monitor and optimize database queries

---

## Security Checklist

- [ ] HTTPS enabled
- [ ] Environment variables secured
- [ ] Database credentials rotated
- [ ] Rate limiting configured
- [ ] CORS properly configured
- [ ] Input validation enabled
- [ ] SQL injection protection
- [ ] XSS protection
- [ ] CSRF protection
- [ ] Regular security updates
- [ ] Firewall configured
- [ ] Backup strategy in place
