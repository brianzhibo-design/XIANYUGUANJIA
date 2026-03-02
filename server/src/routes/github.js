const express = require('express');
const router = express.Router();
const axios = require('axios');
const { auth } = require('../middleware/auth');

let githubTokens = new Map();

router.get('/repos', auth, async (req, res) => {
  try {
    const token = githubTokens.get(req.user.id);
    if (!token) {
      return res.status(401).json({ error: 'GitHub not connected' });
    }

    const response = await axios.get('https://api.github.com/user/repos', {
      headers: { Authorization: `Bearer ${token}` },
      params: {
        sort: 'updated',
        per_page: 100,
        visibility: 'all'
      }
    });

    const repos = response.data.map(repo => ({
      id: repo.id,
      name: repo.full_name,
      private: repo.private,
      description: repo.description,
      language: repo.language,
      stars: repo.stargazers_count,
      updatedAt: repo.updated_at
    }));

    res.json({ repos });
  } catch (error) {
    console.error('Get repos error:', error.response?.data || error.message);
    res.status(500).json({ error: 'Failed to fetch repositories' });
  }
});

router.get('/repos/:owner/:repo/contents', auth, async (req, res) => {
  try {
    const { owner, repo } = req.params;
    const { path = '' } = req.query;
    
    const token = githubTokens.get(req.user.id);
    if (!token) {
      return res.status(401).json({ error: 'GitHub not connected' });
    }

    const response = await axios.get(
      `https://api.github.com/repos/${owner}/${repo}/contents/${path}`,
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    );

    const contents = response.data.map(item => ({
      name: item.name,
      path: item.path,
      type: item.type,
      sha: item.sha
    }));

    res.json({ contents });
  } catch (error) {
    console.error('Get contents error:', error.response?.data || error.message);
    res.status(500).json({ error: 'Failed to fetch repository contents' });
  }
});

router.get('/repos/:owner/:repo/file', auth, async (req, res) => {
  try {
    const { owner, repo } = req.params;
    const { path } = req.query;
    
    if (!path) {
      return res.status(400).json({ error: 'File path required' });
    }

    const token = githubTokens.get(req.user.id);
    if (!token) {
      return res.status(401).json({ error: 'GitHub not connected' });
    }

    const response = await axios.get(
      `https://api.github.com/repos/${owner}/${repo}/contents/${path}`,
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    );

    if (response.data.type !== 'file') {
      return res.status(400).json({ error: 'Not a file' });
    }

    const content = Buffer.from(response.data.content, 'base64').toString('utf-8');

    res.json({
      name: response.data.name,
      path: response.data.path,
      content,
      size: response.data.size,
      sha: response.data.sha
    });
  } catch (error) {
    console.error('Get file error:', error.response?.data || error.message);
    res.status(500).json({ error: 'Failed to fetch file' });
  }
});

router.get('/repos/:owner/:repo/branches', auth, async (req, res) => {
  try {
    const { owner, repo } = req.params;
    
    const token = githubTokens.get(req.user.id);
    if (!token) {
      return res.status(401).json({ error: 'GitHub not connected' });
    }

    const response = await axios.get(
      `https://api.github.com/repos/${owner}/${repo}/branches`,
      {
        headers: { Authorization: `Bearer ${token}` }
      }
    );

    const branches = response.data.map(branch => ({
      name: branch.name,
      commit: branch.commit.sha
    }));

    res.json({ branches });
  } catch (error) {
    console.error('Get branches error:', error.response?.data || error.message);
    res.status(500).json({ error: 'Failed to fetch branches' });
  }
});

router.post('/connect', auth, async (req, res) => {
  try {
    const { accessToken } = req.body;
    
    if (!accessToken) {
      return res.status(400).json({ error: 'Access token required' });
    }

    const userResponse = await axios.get('https://api.github.com/user', {
      headers: { Authorization: `Bearer ${accessToken}` }
    });

    githubTokens.set(req.user.id, accessToken);

    res.json({ 
      message: 'GitHub connected successfully',
      username: userResponse.data.login
    });
  } catch (error) {
    console.error('Connect GitHub error:', error.response?.data || error.message);
    res.status(500).json({ error: 'Failed to connect GitHub' });
  }
});

module.exports = router;
