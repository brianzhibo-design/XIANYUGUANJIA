import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'
import { FileText, Filter, Search, AlertCircle } from 'lucide-react'

const History = () => {
  const [reviews, setReviews] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [pagination, setPagination] = useState({})

  useEffect(() => {
    fetchReviews()
  }, [page, filter])

  const fetchReviews = async () => {
    try {
      const params = {
        page,
        limit: 20,
        ...(filter !== 'all' && { status: filter })
      }

      const response = await axios.get('/api/review/history', { params })
      setReviews(response.data.reviews)
      setPagination(response.data.pagination)
    } catch (error) {
      console.error('Failed to fetch reviews:', error)
    } finally {
      setLoading(false)
    }
  }

  const filteredReviews = reviews.filter((review) => {
    if (!search) return true
    return (
      review.fileName?.toLowerCase().includes(search.toLowerCase()) ||
      review.language?.toLowerCase().includes(search.toLowerCase())
    )
  })

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-700'
      case 'processing':
        return 'bg-yellow-100 text-yellow-700'
      case 'failed':
        return 'bg-red-100 text-red-700'
      default:
        return 'bg-gray-100 text-gray-700'
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Review History</h1>
        <p className="mt-2 text-gray-600">View all your past code reviews</p>
      </div>

      <div className="bg-white rounded-lg shadow mb-6">
        <div className="p-4 border-b border-gray-200">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search by file name or language..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Filter className="h-5 w-5 text-gray-400" />
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="all">All Status</option>
                <option value="completed">Completed</option>
                <option value="processing">Processing</option>
                <option value="failed">Failed</option>
              </select>
            </div>
          </div>
        </div>

        {filteredReviews.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600 mb-2">No reviews found</p>
            <p className="text-sm text-gray-500 mb-4">
              {search || filter !== 'all'
                ? 'Try adjusting your search or filter'
                : 'Start by creating your first review'}
            </p>
            {!search && filter === 'all' && (
              <Link
                to="/review"
                className="inline-block bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition"
              >
                Create Review
              </Link>
            )}
          </div>
        ) : (
          <>
            <div className="divide-y divide-gray-200">
              {filteredReviews.map((review) => (
                <Link
                  key={review.id}
                  to={`/history/${review.id}`}
                  className="block px-6 py-4 hover:bg-gray-50 transition"
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-1">
                        <h3 className="font-medium text-gray-900">
                          {review.fileName || 'Code Review'}
                        </h3>
                        <span
                          className={`px-2 py-0.5 text-xs font-medium rounded ${getStatusColor(
                            review.status
                          )}`}
                        >
                          {review.status}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 text-sm text-gray-600">
                        <span>{review.language}</span>
                        {review.status === 'completed' && (
                          <>
                            <span>•</span>
                            <span className="flex items-center gap-1">
                              <AlertCircle className="w-4 h-4" />
                              {review.issuesFound} issues
                            </span>
                          </>
                        )}
                        {review.processingTime && (
                          <>
                            <span>•</span>
                            <span>{review.processingTime.toFixed(1)}s</span>
                          </>
                        )}
                      </div>
                      {review.status === 'completed' && (
                        <div className="mt-2 flex gap-4 text-xs">
                          {review.securityIssues > 0 && (
                            <span className="text-red-600">
                              {review.securityIssues} security
                            </span>
                          )}
                          {review.performanceIssues > 0 && (
                            <span className="text-yellow-600">
                              {review.performanceIssues} performance
                            </span>
                          )}
                          {review.bestPracticeIssues > 0 && (
                            <span className="text-blue-600">
                              {review.bestPracticeIssues} best practices
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                    <div className="text-right text-sm text-gray-500">
                      <p>{new Date(review.createdAt).toLocaleDateString()}</p>
                      <p>{new Date(review.createdAt).toLocaleTimeString()}</p>
                    </div>
                  </div>
                </Link>
              ))}
            </div>

            {pagination.pages > 1 && (
              <div className="px-6 py-4 border-t border-gray-200 flex justify-between items-center">
                <button
                  onClick={() => setPage(page - 1)}
                  disabled={page === 1}
                  className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <span className="text-sm text-gray-600">
                  Page {page} of {pagination.pages}
                </span>
                <button
                  onClick={() => setPage(page + 1)}
                  disabled={page === pagination.pages}
                  className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

export default History
