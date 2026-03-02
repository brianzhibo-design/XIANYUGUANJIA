const { DataTypes } = require('sequelize');
const sequelize = require('../config/database');

const Review = sequelize.define('Review', {
  id: {
    type: DataTypes.INTEGER,
    primaryKey: true,
    autoIncrement: true
  },
  userId: {
    type: DataTypes.INTEGER,
    allowNull: false,
    references: {
      model: 'Users',
      key: 'id'
    }
  },
  repository: {
    type: DataTypes.STRING,
    allowNull: true
  },
  branch: {
    type: DataTypes.STRING,
    allowNull: true
  },
  commitHash: {
    type: DataTypes.STRING,
    allowNull: true
  },
  fileName: {
    type: DataTypes.STRING,
    allowNull: true
  },
  codeContent: {
    type: DataTypes.TEXT,
    allowNull: false
  },
  language: {
    type: DataTypes.STRING,
    allowNull: false
  },
  status: {
    type: DataTypes.ENUM('pending', 'processing', 'completed', 'failed'),
    defaultValue: 'pending'
  },
  result: {
    type: DataTypes.JSONB,
    allowNull: true
  },
  summary: {
    type: DataTypes.TEXT,
    allowNull: true
  },
  issuesFound: {
    type: DataTypes.INTEGER,
    defaultValue: 0
  },
  securityIssues: {
    type: DataTypes.INTEGER,
    defaultValue: 0
  },
  performanceIssues: {
    type: DataTypes.INTEGER,
    defaultValue: 0
  },
  bestPracticeIssues: {
    type: DataTypes.INTEGER,
    defaultValue: 0
  },
  processingTime: {
    type: DataTypes.FLOAT,
    allowNull: true
  },
  errorMessage: {
    type: DataTypes.TEXT,
    allowNull: true
  }
}, {
  timestamps: true,
  indexes: [
    { fields: ['userId'] },
    { fields: ['status'] },
    { fields: ['createdAt'] }
  ]
});

module.exports = Review;
