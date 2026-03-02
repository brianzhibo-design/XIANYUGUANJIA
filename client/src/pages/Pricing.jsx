import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { Check } from 'lucide-react'

const Pricing = () => {
  const { user } = useAuth()
  const navigate = useNavigate()

  const plans = [
    {
      name: 'Free',
      price: 0,
      limit: 5,
      features: [
        '5 code reviews per month',
        'Basic security checks',
        'Email support',
        'Community access'
      ],
      cta: 'Get Started',
      popular: false
    },
    {
      name: 'Basic',
      price: 19,
      limit: 50,
      features: [
        '50 code reviews per month',
        'Advanced security analysis',
        'Performance optimization',
        'Best practices review',
        'Priority email support'
      ],
      cta: 'Start Basic',
      popular: false
    },
    {
      name: 'Pro',
      price: 49,
      limit: 200,
      features: [
        '200 code reviews per month',
        'All Basic features',
        'Deep code analysis',
        'API access',
        'Custom rules',
        'Priority support'
      ],
      cta: 'Start Pro',
      popular: true
    },
    {
      name: 'Team',
      price: 199,
      limit: 1000,
      features: [
        '1000 code reviews per month',
        'All Pro features',
        'Team collaboration',
        'Admin dashboard',
        'SSO support',
        'Dedicated account manager'
      ],
      cta: 'Contact Sales',
      popular: false
    }
  ]

  const handleSelectPlan = (planName) => {
    if (!user) {
      navigate('/register')
      return
    }

    if (planName === 'free') {
      navigate('/dashboard')
      return
    }

    if (planName === 'team') {
      window.location.href = 'mailto:sales@codereview.ai'
      return
    }

    navigate('/settings/billing')
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-extrabold text-gray-900 sm:text-4xl">
            Simple, transparent pricing
          </h2>
          <p className="mt-4 text-xl text-gray-600">
            Choose the plan that fits your needs
          </p>
        </div>

        <div className="grid md:grid-cols-4 gap-8">
          {plans.map((plan) => (
            <div
              key={plan.name}
              className={`bg-white rounded-lg shadow-lg overflow-hidden ${
                plan.popular ? 'ring-2 ring-blue-600 relative' : ''
              }`}
            >
              {plan.popular && (
                <div className="absolute top-0 right-0 bg-blue-600 text-white px-3 py-1 text-sm font-medium">
                  Popular
                </div>
              )}
              <div className="p-6">
                <h3 className="text-2xl font-bold text-gray-900 mb-2">
                  {plan.name}
                </h3>
                <div className="mb-4">
                  <span className="text-4xl font-extrabold text-gray-900">
                    ${plan.price}
                  </span>
                  {plan.price > 0 && (
                    <span className="text-gray-600">/month</span>
                  )}
                </div>
                <p className="text-gray-600 mb-6">
                  {plan.limit} reviews per month
                </p>

                <ul className="space-y-3 mb-6">
                  {plan.features.map((feature, index) => (
                    <li key={index} className="flex items-start">
                      <Check className="h-5 w-5 text-green-500 mr-2 flex-shrink-0 mt-0.5" />
                      <span className="text-gray-700 text-sm">{feature}</span>
                    </li>
                  ))}
                </ul>

                <button
                  onClick={() => handleSelectPlan(plan.name.toLowerCase())}
                  className={`w-full py-3 px-4 rounded-lg font-medium transition ${
                    plan.popular
                      ? 'bg-blue-600 text-white hover:bg-blue-700'
                      : 'bg-gray-100 text-gray-900 hover:bg-gray-200'
                  }`}
                >
                  {plan.cta}
                </button>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-12 text-center">
          <p className="text-gray-600">
            All plans include 14-day free trial. No credit card required.
          </p>
        </div>

        <div className="mt-16 bg-white rounded-lg shadow p-8">
          <h3 className="text-2xl font-bold text-gray-900 mb-4">
            Frequently Asked Questions
          </h3>
          <div className="grid md:grid-cols-2 gap-8">
            <div>
              <h4 className="font-semibold text-gray-900 mb-2">
                Can I change plans later?
              </h4>
              <p className="text-gray-600 text-sm">
                Yes, you can upgrade or downgrade your plan at any time. Changes
                take effect immediately.
              </p>
            </div>
            <div>
              <h4 className="font-semibold text-gray-900 mb-2">
                What payment methods do you accept?
              </h4>
              <p className="text-gray-600 text-sm">
                We accept all major credit cards via Stripe. PayPal is also
                available for annual plans.
              </p>
            </div>
            <div>
              <h4 className="font-semibold text-gray-900 mb-2">
                Do unused reviews roll over?
              </h4>
              <p className="text-gray-600 text-sm">
                No, review counts reset monthly. This helps us maintain high
                service quality for all users.
              </p>
            </div>
            <div>
              <h4 className="font-semibold text-gray-900 mb-2">
                Is there a refund policy?
              </h4>
              <p className="text-gray-600 text-sm">
                Yes, we offer a 14-day money-back guarantee. No questions asked.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Pricing
