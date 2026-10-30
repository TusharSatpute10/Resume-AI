import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import {
  ArrowRight,
  BrainCircuit,
  BriefcaseBusiness,
  GraduationCap,
  LockKeyhole,
  Mail,
  UserRound,
  Building2,
} from 'lucide-react'

import { useAuth } from '../context/AuthContext'

export default function Register() {
  const { register, user } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState({
    full_name: '',
    email: '',
    password: '',
    role: 'STUDENT',
    company_name: '',
  })

  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [success, setSuccess] = useState(false)

  if (user) {
    return <Navigate to="/dashboard" replace />
  }

  function updateField(event) {
    const { name, value } = event.target

    setForm((previous) => ({
      ...previous,
      [name]: value,
    }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setSuccess(false)

    if (form.password.length < 8) {
      setError('Password must contain at least 8 characters.')
      return
    }

    if (form.role === 'HR' && form.company_name.trim().length < 2) {
      setError('Please enter your company name.')
      return
    }

    setSubmitting(true)

    try {
      const payload = {
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        password: form.password,
        role: form.role,
      }

      if (form.role === 'HR') {
        payload.company_name = form.company_name.trim()
      }

      await register(payload)

      setSuccess(true)

      setTimeout(() => {
        navigate('/login', {
          replace: true,
          state: {
            registeredEmail: form.email.trim(),
          },
        })
      }, 1200)
    } catch (err) {
      const detail = err.response?.data?.detail

      setError(
        typeof detail === 'string'
          ? detail
          : 'Registration failed. Please check your details and try again.',
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
            <BrainCircuit size={14} />
            INTELLIGENT RECRUITMENT
          </div>

          <h1>
            Build better
            <br />
            <span>career connections.</span>
          </h1>

          <p>
            Join ResumeAI to manage resumes, explore opportunities,
            and make recruitment decisions with intelligent matching.
          </p>

          <div className="auth-benefits">
            <div>
              <span>01</span>
              <p>Build and manage your professional profile</p>
            </div>

            <div>
              <span>02</span>
              <p>Connect opportunities with relevant skills</p>
            </div>

            <div>
              <span>03</span>
              <p>Manage applications and recruitment workflows</p>
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
            <div className="eyebrow">CREATE YOUR ACCOUNT</div>
            <h2>Join ResumeAI</h2>
            <p>Choose your account type and enter your details.</p>
          </div>

          <form className="auth-form" onSubmit={handleSubmit}>
            <label htmlFor="full_name">Full name</label>

            <div className="auth-input-wrap">
              <UserRound size={18} />

              <input
                id="full_name"
                name="full_name"
                value={form.full_name}
                onChange={updateField}
                placeholder="Enter your full name"
                autoComplete="name"
                minLength={2}
                maxLength={150}
                required
              />
            </div>

            <label htmlFor="email">Email address</label>

            <div className="auth-input-wrap">
              <Mail size={18} />

              <input
                id="email"
                name="email"
                type="email"
                value={form.email}
                onChange={updateField}
                placeholder="you@example.com"
                autoComplete="email"
                required
              />
            </div>

            <label htmlFor="password">Password</label>

            <div className="auth-input-wrap">
              <LockKeyhole size={18} />

              <input
                id="password"
                name="password"
                type="password"
                value={form.password}
                onChange={updateField}
                placeholder="At least 8 characters"
                autoComplete="new-password"
                minLength={8}
                maxLength={128}
                required
              />
            </div>

            <label>Account type</label>

            <div className="role-options">
              <button
                type="button"
                className={`role-option ${
                  form.role === 'STUDENT' ? 'role-selected' : ''
                }`}
                onClick={() =>
                  setForm((previous) => ({
                    ...previous,
                    role: 'STUDENT',
                  }))
                }
              >
                <GraduationCap size={21} />

                <span>
                  <strong>Student</strong>
                  <small>Find opportunities</small>
                </span>

                <span className="role-radio" />
              </button>

              <button
                type="button"
                className={`role-option ${
                  form.role === 'HR' ? 'role-selected' : ''
                }`}
                onClick={() =>
                  setForm((previous) => ({
                    ...previous,
                    role: 'HR',
                  }))
                }
              >
                <BriefcaseBusiness size={21} />

                <span>
                  <strong>HR / Recruiter</strong>
                  <small>Hire candidates</small>
                </span>

                <span className="role-radio" />
              </button>
            </div>

            {form.role === 'HR' && (
              <>
                <label htmlFor="company_name">Company name</label>

                <div className="auth-input-wrap">
                  <Building2 size={18} />

                  <input
                    id="company_name"
                    name="company_name"
                    value={form.company_name}
                    onChange={updateField}
                    placeholder="Enter your company name"
                    minLength={2}
                    maxLength={200}
                    required
                  />
                </div>
              </>
            )}

            {error && (
              <div className="auth-error" role="alert">
                {error}
              </div>
            )}

            {success && (
              <div className="auth-success" role="status">
                Account created successfully! Redirecting to login…
              </div>
            )}

            <button
              type="submit"
              className="primary-button auth-submit"
              disabled={submitting || success}
            >
              {submitting ? 'Creating account…' : 'Create account'}
              {!submitting && <ArrowRight size={17} />}
            </button>
          </form>

          <div className="auth-switch">
            Already have an account? <Link to="/login">Sign in</Link>
          </div>

          <div className="auth-security">
            <LockKeyhole size={14} />
            Your account is managed by the ResumeAI backend.
          </div>
        </div>
      </section>
    </main>
  )
}