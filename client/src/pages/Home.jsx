import React from 'react'
import { Link } from 'react-router-dom'
import { Shield, Zap, Code, CheckCircle, ArrowRight } from 'lucide-react'

const Home = () => {
  const features = [
    {
      icon: Shield,
      title: 'Security Analysis',
      description: 'Detect vulnerabilities, SQL injection, XSS, and authentication issues'
    },
    {
      icon: Zap,
      title: 'Performance Review',
      description: 'Identify performance bottlenecks and optimization opportunities'
    },
    {
      icon: Code,
      title: 'Best Practices',
      description: 'Get suggestions for cleaner, more maintainable code'
    }
  ]

  const benefits = [
    'AI-powered code analysis using GLM-5',
    'Support for 50+ programming languages',
    'Detailed security vulnerability reports',
    'Actionable performance improvement suggestions',
    'GitHub integration for seamless workflow',
    'Chinese and English support'
  ]

  return (
    <div>
      <section className="bg-gradient-to-br from-blue-600 to-blue-800 text-white py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <h1 className="text-4xl md:text-6xl font-bold mb-6">
              AI-Powered Code Review
            </h1>
            <p className="text-xl md:text-2xl mb-8 text-blue-100">
              Improve code quality, security, and performance with intelligent analysis
            </p>
            <div className="flex justify-center gap-4">
              <Link
                to="/register"
                className="bg-white text-blue-600 px-8 py-3 rounded-lg font-semibold hover:bg-gray-100 transition flex items-center gap-2"
              >
                Get Started Free <ArrowRight className="w-5 h-5" />
              </Link>
              <Link
                to="/pricing"
                className="border-2 border-white text-white px-8 py-3 rounded-lg font-semibold hover:bg-white hover:text-blue-600 transition"
              >
                View Pricing
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section className="py-20 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
              Why Choose CodeReview?
            </h2>
            <p className="text-xl text-gray-600">
              Powered by GLM-5 with 80.2% accuracy on SWE-Bench
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <div
                key={index}
                className="bg-gray-50 rounded-lg p-8 hover:shadow-lg transition"
              >
                <feature.icon className="w-12 h-12 text-blue-600 mb-4" />
                <h3 className="text-xl font-semibold mb-2">{feature.title}</h3>
                <p className="text-gray-600">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-6">
                Built for Developers
              </h2>
              <div className="space-y-4">
                {benefits.map((benefit, index) => (
                  <div key={index} className="flex items-start gap-3">
                    <CheckCircle className="w-6 h-6 text-green-500 flex-shrink-0 mt-0.5" />
                    <span className="text-gray-700">{benefit}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="bg-white rounded-lg shadow-lg p-8">
              <div className="font-mono text-sm bg-gray-900 text-green-400 p-4 rounded mb-4">
                <pre>{`// Example: Upload your code
const response = await fetch('/api/review/analyze', {
  method: 'POST',
  body: JSON.stringify({
    code: yourCode,
    language: 'javascript'
  })
});`}</pre>
              </div>
              <p className="text-gray-600 text-sm">
                Simple API integration or use our web interface
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="py-20 bg-blue-600 text-white">
        <div className="max-w-4xl mx-auto px-4 text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Ready to Improve Your Code?
          </h2>
          <p className="text-xl mb-8 text-blue-100">
            Start with 5 free reviews. No credit card required.
          </p>
          <Link
            to="/register"
            className="inline-block bg-white text-blue-600 px-8 py-3 rounded-lg font-semibold hover:bg-gray-100 transition"
          >
            Get Started Now
          </Link>
        </div>
      </section>

      <footer className="bg-gray-900 text-gray-400 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <p className="mb-4">
              &copy; {new Date().getFullYear()} CodeReview. All rights reserved.
            </p>
            <p className="text-sm">
              Powered by GLM-5 | Support: support@codereview.ai
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default Home
