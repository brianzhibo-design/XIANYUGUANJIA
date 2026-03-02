const express = require('express');
const router = express.Router();
const { auth } = require('../middleware/auth');
const User = require('../models/User');
const { PLAN_CONFIGS } = require('../services/codeReviewService');

router.get('/profile', auth, async (req, res) => {
  try {
    const user = await User.findByPk(req.user.id, {
      attributes: { exclude: ['password'] }
    });

    res.json({
      user: {
        id: user.id,
        email: user.email,
        username: user.username,
        avatar: user.avatar,
        plan: user.plan,
        planName: PLAN_CONFIGS[user.plan].name,
        reviewsLimit: user.reviewsLimit,
        reviewsUsed: user.reviewsUsed,
        reviewsRemaining: user.reviewsLimit - user.reviewsUsed,
        subscriptionStatus: user.subscriptionStatus,
        currentPeriodEnd: user.currentPeriodEnd,
        language: user.language
      }
    });
  } catch (error) {
    console.error('Get profile error:', error);
    res.status(500).json({ error: 'Failed to get profile' });
  }
});

router.put('/profile', auth, async (req, res) => {
  try {
    const { username, language } = req.body;
    const user = req.user;

    if (username) user.username = username;
    if (language) user.language = language;

    await user.save();

    res.json({
      message: 'Profile updated successfully',
      user: {
        id: user.id,
        email: user.email,
        username: user.username,
        language: user.language
      }
    });
  } catch (error) {
    console.error('Update profile error:', error);
    res.status(500).json({ error: 'Failed to update profile' });
  }
});

router.get('/usage', auth, async (req, res) => {
  try {
    const user = req.user;
    const usagePercentage = Math.round((user.reviewsUsed / user.reviewsLimit) * 100);

    res.json({
      plan: user.plan,
      reviewsLimit: user.reviewsLimit,
      reviewsUsed: user.reviewsUsed,
      reviewsRemaining: user.reviewsLimit - user.reviewsUsed,
      usagePercentage,
      resetDate: getNextMonthFirstDay()
    });
  } catch (error) {
    console.error('Get usage error:', error);
    res.status(500).json({ error: 'Failed to get usage' });
  }
});

function getNextMonthFirstDay() {
  const now = new Date();
  const nextMonth = new Date(now.getFullYear(), now.getMonth() + 1, 1);
  return nextMonth.toISOString();
}

module.exports = router;
