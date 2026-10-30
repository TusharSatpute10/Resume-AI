import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import {
  ArrowRight,
  BrainCircuit,
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  Sparkles,
} from 'lucide-react'

import { useAuth } from '../context/AuthContext'

export default function Login() {
  const { login, user } = useAuth()
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (user) {
    return <Navigate to="/dashboard" replace />
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setSubmitting(true)

    try {
      await login({ email, password })
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(
        err.response?.data?.detail ??
          err.message ??
          'Unable to sign in. Please try again.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-brand-panel">
        <div className="auth-brand">
          <div className="brand-icon">
            <BrainCircuit size={23} />
          </div>
          <div className="brand-name">
            Resume<span>AI</span>
          </div>
        </div>

        <div className="auth-brand-content">
          <div className="eyebrow">
            <Sparkles size={14} /> INTELLIGENT RECRUITMENT
          </div>

          <h1>
            Talent meets
            <br />
            <span>intelligence.</span>
          </h1>

          <p>
            Bring resumes, opportunities, and intelligent candidate
            matching together in one recruitment platform.
          </p>

          <div className="auth-benefits">
            <div>
              <span>01</span>
              <p>Manage resumes and candidate profiles</p>
            </div>
            <div>
              <span>02</span>
              <p>Discover job opportunities and applications</p>
            </div>
            <div>
              <span>03</span>
              <p>Rank applicants against job requirements</p>
            </div>
          </div>
        </div>

        <div className="auth-brand-footer">
          ResumeAI · Recruitment intelligence platform
        </div>
      </section>

      <section className="auth-form-panel">
        <div className="auth-form-container">
          <div className="auth-mobile-brand">
            <div className="brand-icon">
              <BrainCircuit size={21} />
            </div>
            <div className="brand-name">
              Resume<span>AI</span>
            </div>
          </div>

          <div className="auth-heading">
            <div className="eyebrow">WELCOME BACK</div>
            <h2>Sign in to your account</h2>
            <p>Enter your credentials to continue to ResumeAI.</p>
          </div>

          <form onSubmit={handleSubmit} className="auth-form">
            <label htmlFor="email">Email address</label>

            <div className="auth-input-wrap">
              <Mail size={18} />
              <input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </div>

            <div className="auth-label-row">
              <label htmlFor="password">Password</label>
            </div>

            <div className="auth-input-wrap">
              <LockKeyhole size={18} />
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                placeholder="Enter your password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />

              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword((value) => !value)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
              </button>
            </div>

            {error && (
              <div className="auth-error" role="alert">
                {typeof error === 'string'
                  ? error
                  : JSON.stringify(error)}
              </div>
            )}

            <button
              type="submit"
              className="primary-button auth-submit"
              disabled={submitting}
            >
              {submitting ? 'Signing in...' : 'Sign in'}
              {!submitting && <ArrowRight size={17} />}
            </button>
          </form>

          <div className="auth-switch">
            Don't have an account?{' '}
            <Link to="/register">Create account</Link>
          </div>

          <div className="auth-security">
            <LockKeyhole size={14} />
            Secure authentication powered by your ResumeAI backend.
          </div>
        </div>
      </section>
    </main>
  )
}