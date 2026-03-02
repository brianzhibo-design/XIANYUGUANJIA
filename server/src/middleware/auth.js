const jwt = require('jsonwebtoken');
const User = require('../models/User');

const auth = async (req, res, next) => {
  try {
    const token = req.header('Authorization')?.replace('Bearer ', '');
    
    if (!token) {
      return res.status(401).json({ error: 'No token provided' });
    }
    
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    const user = await User.findByPk(decoded.userId);
    
    if (!user || !user.isActive) {
      return res.status(401).json({ error: 'User not found or inactive' });
    }
    
    req.user = user;
    req.token = token;
    next();
  } catch (error) {
    res.status(401).json({ error: 'Invalid token' });
  }
};

const checkReviewLimit = async (req, res, next) => {
  try {
    const user = req.user;
    
    if (user.reviewsUsed >= user.reviewsLimit) {
      return res.status(403).json({
        error: 'Review limit exceeded',
        message: 'You have reached your monthly review limit. Please upgrade your plan.',
        limit: user.reviewsLimit,
        used: user.reviewsUsed
      });
    }
    
    next();
  } catch (error) {
    res.status(500).json({ error: 'Failed to check review limit' });
  }
};

const requirePlan = (plans) => {
  return (req, res, next) => {
    if (!plans.includes(req.user.plan)) {
      return res.status(403).json({
        error: 'Plan upgrade required',
        message: `This feature requires one of these plans: ${plans.join(', ')}`
      });
    }
    next();
  };
};

module.exports = { auth, checkReviewLimit, requirePlan };
