const { DataTypes } = require('sequelize');
const sequelize = require('../config/database');

const User = sequelize.define('User', {
  id: {
    type: DataTypes.INTEGER,
    primaryKey: true,
    autoIncrement: true
  },
  email: {
    type: DataTypes.STRING,
    allowNull: false,
    unique: true,
    validate: {
      isEmail: true
    }
  },
  password: {
    type: DataTypes.STRING,
    allowNull: true
  },
  githubId: {
    type: DataTypes.STRING,
    allowNull: true,
    unique: true
  },
  username: {
    type: DataTypes.STRING,
    allowNull: false
  },
  avatar: {
    type: DataTypes.STRING,
    allowNull: true
  },
  plan: {
    type: DataTypes.ENUM('free', 'basic', 'pro', 'team'),
    defaultValue: 'free'
  },
  reviewsLimit: {
    type: DataTypes.INTEGER,
    defaultValue: 5
  },
  reviewsUsed: {
    type: DataTypes.INTEGER,
    defaultValue: 0
  },
  stripeCustomerId: {
    type: DataTypes.STRING,
    allowNull: true
  },
  subscriptionId: {
    type: DataTypes.STRING,
    allowNull: true
  },
  subscriptionStatus: {
    type: DataTypes.STRING,
    allowNull: true
  },
  currentPeriodEnd: {
    type: DataTypes.DATE,
    allowNull: true
  },
  language: {
    type: DataTypes.ENUM('zh', 'en'),
    defaultValue: 'en'
  },
  isActive: {
    type: DataTypes.BOOLEAN,
    default: true
  }
}, {
  timestamps: true,
  indexes: [
    { fields: ['email'] },
    { fields: ['githubId'] }
  ]
});

module.exports = User;
