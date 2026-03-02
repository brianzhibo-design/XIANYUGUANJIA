# API Documentation

## Base URL

```
Development: http://localhost:3001/api
Production: https://api.codereview.ai/api
```

## Authentication

All API requests require authentication via JWT token:

```http
Authorization: Bearer <token>
```

---

## Endpoints

### Authentication

#### Register User

```http
POST /auth/register
```

**Body:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "username": "johndoe"
}
```

**Response:**
```json
{
  "message": "User registered successfully",
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "johndoe",
    "plan": "free",
    "reviewsLimit": 5,
    "reviewsUsed": 0
  }
}
```

#### Login

```http
POST /auth/login
```

**Body:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

#### GitHub OAuth

```http
GET /auth/github
```

Redirects to GitHub for OAuth authorization.

---

### User

#### Get Profile

```http
GET /user/profile
```

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "johndoe",
    "plan": "pro",
    "reviewsLimit": 200,
    "reviewsUsed": 45,
    "reviewsRemaining": 155
  }
}
```

#### Update Profile

```http
PUT /user/profile
```

**Headers:** `Authorization: Bearer <token>`

**Body:**
```json
{
  "username": "newusername",
  "language": "zh"
}
```

#### Get Usage

```http
GET /user/usage
```

**Response:**
```json
{
  "plan": "pro",
  "reviewsLimit": 200,
  "reviewsUsed": 45,
  "reviewsRemaining": 155,
  "usagePercentage": 23,
  "resetDate": "2024-02-01T00:00:00.000Z"
}
```

---

### Code Review

#### Analyze Code

```http
POST /review/analyze
```

**Headers:** `Authorization: Bearer <token>`

**Body:**
```json
{
  "code": "function add(a, b) { return a + b; }",
  "language": "javascript",
  "fileName": "utils.js",
  "repository": "owner/repo",
  "branch": "main"
}
```

**Response:**
```json
{
  "message": "Review started",
  "reviewId": 123,
  "status": "processing"
}
```

#### Get Review Status

```http
GET /review/status/:id
```

**Response:**
```json
{
  "id": 123,
  "status": "completed",
  "result": [
    {
      "type": "security",
      "description": "Potential SQL injection vulnerability",
      "line": 42,
      "severity": "high"
    }
  ],
  "summary": "Found 3 security issues and 2 performance optimizations",
  "issuesFound": 5,
  "securityIssues": 3,
  "performanceIssues": 2,
  "processingTime": 2.5
}
```

#### Get Review History

```http
GET /review/history?page=1&limit=20&status=completed
```

**Response:**
```json
{
  "reviews": [
    {
      "id": 123,
      "fileName": "utils.js",
      "language": "javascript",
      "status": "completed",
      "issuesFound": 5,
      "createdAt": "2024-01-15T10:30:00.000Z"
    }
  ],
  "pagination": {
    "total": 45,
    "page": 1,
    "pages": 3,
    "limit": 20
  }
}
```

#### Get Review Details

```http
GET /review/:id
```

Returns full review details including code content and analysis results.

#### Delete Review

```http
DELETE /review/:id
```

---

### GitHub Integration

#### Get Repositories

```http
GET /github/repos
```

**Response:**
```json
{
  "repos": [
    {
      "id": 123456,
      "name": "owner/repo",
      "private": false,
      "language": "JavaScript",
      "stars": 150
    }
  ]
}
```

#### Get Repository Contents

```http
GET /github/repos/:owner/:repo/contents?path=src
```

#### Get File Content

```http
GET /github/repos/:owner/:repo/file?path=src/index.js
```

#### Connect GitHub

```http
POST /github/connect
```

**Body:**
```json
{
  "accessToken": "gho_xxxxx"
}
```

---

### Payment

#### Get Plans

```http
GET /payment/plans
```

**Response:**
```json
{
  "plans": [
    {
      "id": "basic",
      "name": "Basic",
      "price": 19,
      "limit": 50,
      "features": ["50 reviews/month", "Security analysis", "..."]
    }
  ]
}
```

#### Create Checkout Session

```http
POST /payment/create-checkout-session
```

**Body:**
```json
{
  "plan": "pro"
}
```

**Response:**
```json
{
  "sessionId": "cs_test_xxxxx",
  "url": "https://checkout.stripe.com/pay/xxxxx"
}
```

#### Create Portal Session

```http
POST /payment/create-portal-session
```

Returns URL to Stripe billing portal.

---

## Error Responses

All errors follow this format:

```json
{
  "error": "Error type",
  "message": "Detailed error message"
}
```

### Common Status Codes

- `200` - Success
- `201` - Created
- `202` - Accepted (processing)
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `500` - Internal Server Error

---

## Rate Limits

- Free plan: 5 requests/minute
- Basic plan: 20 requests/minute
- Pro plan: 60 requests/minute
- Team plan: 120 requests/minute

Rate limit headers:

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1642234567
```

---

## Webhooks

### Stripe Webhook

```http
POST /payment/webhook
```

Events handled:
- `checkout.session.completed`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.payment_failed`
