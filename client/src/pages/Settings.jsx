import React, { useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import axios from 'axios'
import toast from 'react-hot-toast'
import { User, Shield, CreditCard, Bell, Globe } from 'lucide-react'

const Settings = () => {
  const { user, fetchUser } = useAuth()
  const [activeTab, setActiveTab] = useState('profile')
  const [formData, setFormData] = useState({
    username: user?.username || '',
    language: user?.language || 'en'
  })
  const [loading, setLoading] = useState(false)

  const tabs = [
    { id: 'profile', name: 'Profile', icon: User },
    { id: 'security', name: 'Security', icon: Shield },
    { id: 'billing', name: 'Billing', icon: CreditCard },
    { id: 'notifications', name: 'Notifications', icon: Bell },
    { id: 'preferences', name: 'Preferences', icon: Globe }
  ]

  const handleUpdateProfile = async (e) => {
    e.preventDefault()
    setLoading(true)

    try {
      await axios.put('/api/user/profile', formData)
      await fetchUser()
      toast.success('Profile updated successfully')
    } catch (error) {
      toast.error(error.response?.data?.error || 'Failed to update profile')
    } finally {
      setLoading(false)
    }
  }

  const handleManageSubscription = async () => {
    try {
      const response = await axios.post('/api/payment/create-portal-session')
      window.location.href = response.data.url
    } catch (error) {
      toast.error('Failed to open billing portal')
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
        <p className="mt-2 text-gray-600">Manage your account settings</p>
      </div>

      <div className="flex flex-col md:flex-row gap-8">
        <div className="md:w-64 flex-shrink-0">
          <nav className="space-y-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 text-left rounded-lg transition ${
                  activeTab === tab.id
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-700 hover:bg-gray-50'
                }`}
              >
                <tab.icon className="w-5 h-5" />
                {tab.name}
              </button>
            ))}
          </nav>
        </div>

        <div className="flex-1">
          <div className="bg-white rounded-lg shadow">
            {activeTab === 'profile' && (
              <div className="p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-6">
                  Profile Information
                </h2>
                <form onSubmit={handleUpdateProfile} className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Username
                    </label>
                    <input
                      type="text"
                      value={formData.username}
                      onChange={(e) =>
                        setFormData({ ...formData, username: e.target.value })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Email
                    </label>
                    <input
                      type="email"
                      value={user?.email}
                      disabled
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Language
                    </label>
                    <select
                      value={formData.language}
                      onChange={(e) =>
                        setFormData({ ...formData, language: e.target.value })
                      }
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="en">English</option>
                      <option value="zh">中文</option>
                    </select>
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="bg-blue-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-blue-700 transition disabled:opacity-50"
                  >
                    {loading ? 'Saving...' : 'Save Changes'}
                  </button>
                </form>
              </div>
            )}

            {activeTab === 'security' && (
              <div className="p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-6">
                  Security Settings
                </h2>
                <div className="space-y-6">
                  <div>
                    <h3 className="font-medium text-gray-900 mb-2">
                      Password
                    </h3>
                    <p className="text-sm text-gray-600 mb-4">
                      Change your password to keep your account secure
                    </p>
                    <button
                      onClick={() => toast.info('Password change coming soon')}
                      className="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200 transition"
                    >
                      Change Password
                    </button>
                  </div>

                  <div className="border-t pt-6">
                    <h3 className="font-medium text-gray-900 mb-2">
                      Two-Factor Authentication
                    </h3>
                    <p className="text-sm text-gray-600 mb-4">
                      Add an extra layer of security to your account
                    </p>
                    <button
                      onClick={() => toast.info('2FA coming soon')}
                      className="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200 transition"
                    >
                      Enable 2FA
                    </button>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'billing' && (
              <div className="p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-6">
                  Billing & Subscription
                </h2>
                <div className="space-y-6">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="flex justify-between items-center">
                      <div>
                        <h3 className="font-medium text-gray-900">
                          Current Plan: {user?.planName || 'Free'}
                        </h3>
                        <p className="text-sm text-gray-600">
                          {user?.reviewsRemaining} reviews remaining
                        </p>
                      </div>
                      <span
                        className={`px-3 py-1 rounded-full text-sm font-medium ${
                          user?.subscriptionStatus === 'active'
                            ? 'bg-green-100 text-green-700'
                            : 'bg-gray-100 text-gray-700'
                        }`}
                      >
                        {user?.subscriptionStatus || 'Free'}
                      </span>
                    </div>
                  </div>

                  {user?.plan !== 'free' && (
                    <button
                      onClick={handleManageSubscription}
                      className="bg-blue-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-blue-700 transition"
                    >
                      Manage Subscription
                    </button>
                  )}

                  {user?.plan === 'free' && (
                    <div className="bg-blue-50 rounded-lg p-4">
                      <h3 className="font-medium text-blue-900 mb-2">
                        Upgrade to get more features
                      </h3>
                      <p className="text-sm text-blue-700 mb-4">
                        Get more code reviews and advanced features
                      </p>
                      <button
                        onClick={() => (window.location.href = '/pricing')}
                        className="bg-blue-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-blue-700 transition"
                      >
                        View Plans
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeTab === 'notifications' && (
              <div className="p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-6">
                  Notification Preferences
                </h2>
                <p className="text-gray-600">
                  Notification settings coming soon...
                </p>
              </div>
            )}

            {activeTab === 'preferences' && (
              <div className="p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-6">
                  Preferences
                </h2>
                <p className="text-gray-600">
                  Additional preferences coming soon...
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default Settings
