-- Database Schema for Code Review Service

-- Users table
CREATE TABLE IF NOT EXISTS "Users" (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255) NOT NULL UNIQUE,
  password VARCHAR(255),
  "githubId" VARCHAR(255) UNIQUE,
  username VARCHAR(255) NOT NULL,
  avatar VARCHAR(255),
  plan VARCHAR(50) DEFAULT 'free' CHECK (plan IN ('free', 'basic', 'pro', 'team')),
  "reviewsLimit" INTEGER DEFAULT 5,
  "reviewsUsed" INTEGER DEFAULT 0,
  "stripeCustomerId" VARCHAR(255),
  "subscriptionId" VARCHAR(255),
  "subscriptionStatus" VARCHAR(50),
  "currentPeriodEnd" TIMESTAMP,
  language VARCHAR(10) DEFAULT 'en' CHECK (language IN ('zh', 'en')),
  "isActive" BOOLEAN DEFAULT true,
  "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON "Users"(email);
CREATE INDEX idx_users_github_id ON "Users"("githubId");

-- Reviews table
CREATE TABLE IF NOT EXISTS "Reviews" (
  id SERIAL PRIMARY KEY,
  "userId" INTEGER NOT NULL REFERENCES "Users"(id) ON DELETE CASCADE,
  repository VARCHAR(255),
  branch VARCHAR(255),
  "commitHash" VARCHAR(255),
  "fileName" VARCHAR(255),
  "codeContent" TEXT NOT NULL,
  language VARCHAR(50) NOT NULL,
  status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
  result JSONB,
  summary TEXT,
  "issuesFound" INTEGER DEFAULT 0,
  "securityIssues" INTEGER DEFAULT 0,
  "performanceIssues" INTEGER DEFAULT 0,
  "bestPracticeIssues" INTEGER DEFAULT 0,
  "processingTime" FLOAT,
  "errorMessage" TEXT,
  "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_reviews_user_id ON "Reviews"("userId");
CREATE INDEX idx_reviews_status ON "Reviews"(status);
CREATE INDEX idx_reviews_created_at ON "Reviews"("createdAt");

-- Teams table
CREATE TABLE IF NOT EXISTS "Teams" (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  "ownerId" INTEGER NOT NULL REFERENCES "Users"(id),
  "reviewsLimit" INTEGER DEFAULT 1000,
  "reviewsUsed" INTEGER DEFAULT 0,
  plan VARCHAR(50) DEFAULT 'team',
  "isActive" BOOLEAN DEFAULT true,
  "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- TeamMembers table
CREATE TABLE IF NOT EXISTS "TeamMembers" (
  id SERIAL PRIMARY KEY,
  "teamId" INTEGER NOT NULL REFERENCES "Teams"(id) ON DELETE CASCADE,
  "userId" INTEGER NOT NULL REFERENCES "Users"(id) ON DELETE CASCADE,
  role VARCHAR(50) DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member')),
  "createdAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  "updatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE("teamId", "userId")
);

-- Function to update timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW."updatedAt" = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for automatic timestamp update
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON "Users"
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_reviews_updated_at BEFORE UPDATE ON "Reviews"
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_teams_updated_at BEFORE UPDATE ON "Teams"
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_team_members_updated_at BEFORE UPDATE ON "TeamMembers"
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- View for review statistics
CREATE OR REPLACE VIEW review_stats AS
SELECT 
  "userId",
  COUNT(*) as total_reviews,
  SUM("issuesFound") as total_issues,
  SUM("securityIssues") as total_security_issues,
  SUM("performanceIssues") as total_performance_issues,
  SUM("bestPracticeIssues") as total_best_practice_issues,
  AVG("processingTime") as avg_processing_time
FROM "Reviews"
WHERE status = 'completed'
GROUP BY "userId";

-- Function to reset monthly usage
CREATE OR REPLACE FUNCTION reset_monthly_usage()
RETURNS void AS $$
BEGIN
  UPDATE "Users"
  SET "reviewsUsed" = 0
  WHERE "isActive" = true;
  
  UPDATE "Teams"
  SET "reviewsUsed" = 0
  WHERE "isActive" = true;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions (adjust as needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO your_user;
