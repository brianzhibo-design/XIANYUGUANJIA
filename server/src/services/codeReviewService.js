const axios = require('axios');

const PLAN_CONFIGS = {
  free: { limit: 5, price: 0, name: 'Free' },
  basic: { limit: 50, price: 19, name: 'Basic' },
  pro: { limit: 200, price: 49, name: 'Pro' },
  team: { limit: 1000, price: 199, name: 'Team' }
};

async function reviewCode(codeContent, language, options = {}) {
  const startTime = Date.now();
  
  try {
    const systemPrompt = `You are an expert code reviewer. Analyze the code for:
1. Security vulnerabilities (SQL injection, XSS, auth issues, etc.)
2. Performance problems
3. Code quality and best practices
4. Potential bugs
5. Architecture suggestions

Language: ${language}
${options.language === 'zh' ? 'Please respond in Chinese.' : 'Please respond in English.'}

Provide a detailed analysis with specific line numbers and actionable suggestions.`;

    const response = await axios.post(
      process.env.GLM5_API_URL,
      {
        model: 'glm-4',
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: `Please review this code:\n\n\`\`\`${language}\n${codeContent}\n\`\`\`` }
        ],
        temperature: 0.7,
        max_tokens: 4000
      },
      {
        headers: {
          'Authorization': `Bearer ${process.env.GLM5_API_KEY}`,
          'Content-Type': 'application/json'
        },
        timeout: 60000
      }
    );

    const processingTime = (Date.now() - startTime) / 1000;
    const reviewText = response.data.choices[0].message.content;
    
    const result = parseReviewResult(reviewText);
    
    return {
      ...result,
      processingTime,
      rawResponse: reviewText
    };
  } catch (error) {
    console.error('GLM-5 API Error:', error.response?.data || error.message);
    throw new Error(`Code review failed: ${error.message}`);
  }
}

function parseReviewResult(reviewText) {
  const issues = [];
  let securityIssues = 0;
  let performanceIssues = 0;
  let bestPracticeIssues = 0;

  const securityPatterns = [
    /sql injection|injection|authentication|authorization|xss|csrf/gi
  ];
  
  const performancePatterns = [
    /performance|slow|optimization|efficient|n\+1|memory leak/gi
  ];
  
  const bestPracticePatterns = [
    /best practice|clean code|refactor|maintainable|solid|dry|kiss/gi
  ];

  const sections = reviewText.split(/\n(?=\d+\.|[-•*]|Security|Performance|Best Practice|Issue|Problem)/gi);
  
  sections.forEach(section => {
    if (!section.trim()) return;
    
    let type = 'general';
    if (securityPatterns.some(p => p.test(section))) {
      type = 'security';
      securityIssues++;
    } else if (performancePatterns.some(p => p.test(section))) {
      type = 'performance';
      performanceIssues++;
    } else if (bestPracticePatterns.some(p => p.test(section))) {
      type = 'best_practice';
      bestPracticeIssues++;
    }
    
    const lineNumber = extractLineNumber(section);
    
    issues.push({
      type,
      description: section.trim(),
      line: lineNumber,
      severity: determineSeverity(section)
    });
  });

  const summary = extractSummary(reviewText);

  return {
    issues,
    summary,
    securityIssues,
    performanceIssues,
    bestPracticeIssues,
    issuesFound: issues.length
  };
}

function extractLineNumber(text) {
  const match = text.match(/line\s*(\d+)/i);
  return match ? parseInt(match[1]) : null;
}

function determineSeverity(text) {
  const highKeywords = /critical|severe|vulnerability|security risk|dangerous/gi;
  const mediumKeywords = /warning|important|should|recommend/gi;
  
  if (highKeywords.test(text)) return 'high';
  if (mediumKeywords.test(text)) return 'medium';
  return 'low';
}

function extractSummary(text) {
  const summaryMatch = text.match(/(?:summary|conclusion|overall)[\s\S]*?(?=\n\n|\n\d+\.|$)/i);
  return summaryMatch ? summaryMatch[0].trim() : 'Code review completed.';
}

module.exports = {
  reviewCode,
  PLAN_CONFIGS
};
