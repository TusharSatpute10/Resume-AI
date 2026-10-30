import { useEffect, useState } from 'react'
import {
  LayoutDashboard,
  FileText,
  BriefcaseBusiness,
  ClipboardList,
  BrainCircuit,
  UserRound,
  LogOut,
  Bell,
  Search,
  ArrowUpRight,
  Upload,
  Sparkles,
  ChevronRight,
  Menu,
  X,
  CalendarDays,
} from 'lucide-react'

import { useAuth } from '../context/AuthContext'
import api from '../services/api'
import InterviewCenter from '../components/InterviewCenter'

const navigation = [
  { label: 'Overview', icon: LayoutDashboard },
  { label: 'My Resumes', icon: FileText },
  { label: 'Find Jobs', icon: BriefcaseBusiness },
  { label: 'Applications', icon: ClipboardList },
  { label: 'AI Matching', icon: BrainCircuit },
  { label: 'Interviews', icon: CalendarDays },
  { label: 'My Profile', icon: UserRound },
]

function getArray(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.items)) return data.items
  if (Array.isArray(data?.data)) return data.data
  if (Array.isArray(data?.results)) return data.results
  if (Array.isArray(data?.jobs)) return data.jobs
  if (Array.isArray(data?.resumes)) return data.resumes
  if (Array.isArray(data?.applications)) return data.applications
  return []
}

export default function StudentDashboard() {
  const { user, logout } = useAuth()

  const [activePage, setActivePage] = useState('Overview')
  const [resumes, setResumes] = useState([])
  const [jobs, setJobs] = useState([])
  const [applications, setApplications] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)
  const [mobileMenu, setMobileMenu] = useState(false)
  const [resumeActionLoading, setResumeActionLoading] = useState(false)
  const [selectedJob, setSelectedJob] = useState(null)
  const [applyingJobId, setApplyingJobId] = useState(null)
  const [notice, setNotice] = useState('')
  const [jobSearch, setJobSearch] = useState('')
  const [selectedMatchingResumeId, setSelectedMatchingResumeId] = useState('')
  const [selectedApplyResumeId, setSelectedApplyResumeId] = useState('')
  const [matchingLoading, setMatchingLoading] = useState(false)
  const [matchingResults, setMatchingResults] = useState([])
  const [matchingError, setMatchingError] = useState('')

  async function loadDashboard() {
    setLoading(true)
    setError('')

    const results = await Promise.allSettled([
      api.get('/resumes/me'),
      api.get('/jobs'),
      api.get('/applications/me'),
    ])

    if (results[0].status === 'fulfilled') {
      setResumes(getArray(results[0].value.data))
    }

    if (results[1].status === 'fulfilled') {
      setJobs(getArray(results[1].value.data))
    }

    if (results[2].status === 'fulfilled') {
      setApplications(getArray(results[2].value.data))
    }

    const failures = results.filter((result) => result.status === 'rejected')

    if (failures.length === results.length) {
      setError('Unable to load dashboard data. Check that your backend is running.')
    }

    setLoading(false)
  }

  useEffect(() => {
    loadDashboard()
  }, [])

  useEffect(() => {
    if (!resumes.length) {
      setSelectedApplyResumeId('')
      setSelectedMatchingResumeId('')
      setMatchingResults([])
      return
    }

    const applyResumeStillExists = resumes.some(
      (resume) => String(resume.id) === String(selectedApplyResumeId),
    )
    if (!applyResumeStillExists) {
      const preferredResume = resumes.find((resume) => resume.is_primary) || resumes[0]
      setSelectedApplyResumeId(String(preferredResume.id))
    }
    const selectedStillExists = resumes.some(
      (resume) => String(resume.id) === String(selectedMatchingResumeId),
    )
    if (!selectedStillExists) {
      const preferredResume = resumes.find((resume) => resume.is_primary) || resumes[0]
      setSelectedMatchingResumeId(String(preferredResume.id))
      setMatchingResults([])
    }
  }, [resumes, selectedMatchingResumeId])

  async function runStudentMatching() {
    if (!selectedMatchingResumeId) {
      setMatchingError('Upload a resume before requesting AI recommendations.')
      return
    }
    setMatchingLoading(true)
    setMatchingError('')
    setMatchingResults([])
    try {
      const response = await api.get('/matching/recommendations', {
        params: { resume_id: Number(selectedMatchingResumeId) },
      })
      const results = getArray(response.data)
      results.sort((a, b) => Number(b.final_score || 0) - Number(a.final_score || 0))
      setMatchingResults(results)
    } catch (err) {
      const detail = err.response?.data?.detail
      setMatchingError(
        typeof detail === 'string'
          ? detail
          : 'Could not generate recommendations. Check your connection and try again.',
      )
    } finally {
      setMatchingLoading(false)
    }
  }

  async function uploadResume(event) {
    const file = event.target.files?.[0]
    if (!file) return

    const allowedExtensions = /\.(pdf|docx)$/i

    if (!allowedExtensions.test(file.name)) {
      setError('Please select a PDF or DOCX resume.')
      event.target.value = ''
      return
    }

    const formData = new FormData()
    formData.append('file', file)

    setUploading(true)
    setError('')

    try {
      await api.post('/resumes/upload', formData)
      await loadDashboard()
      setActivePage('My Resumes')
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          'Resume upload failed. Check the backend upload requirements.',
      )
    } finally {
      setUploading(false)
      event.target.value = ''
    }
  }

  async function setPrimaryResume(resumeId) {
  setResumeActionLoading(true)
  setError('')

  try {
    await api.patch(`/resumes/${resumeId}/primary`)
    await loadDashboard()
  } catch (err) {
    setError(
      err.response?.data?.detail ||
        'Could not set the primary resume.',
    )
  } finally {
    setResumeActionLoading(false)
  }
}

async function deleteResume(resumeId) {
  const confirmed = window.confirm(
    'Are you sure you want to delete this resume?',
  )

  if (!confirmed) return

  setResumeActionLoading(true)
  setError('')

  try {
    await api.delete(`/resumes/${resumeId}`)
    await loadDashboard()
  } catch (err) {
    setError(
      err.response?.data?.detail ||
        'Could not delete this resume.',
    )
  } finally {
    setResumeActionLoading(false)
  }
}

  async function applyForJob(job) {
    if (!job?.id || applyingJobId !== null) return

    if (!resumes.length) {
      setError('Upload a resume before applying for jobs.')
      setActivePage('My Resumes')
      return
    }

    if (applications.some((application) => String(application.job_id ?? application.job?.id) === String(job.id))) {
      window.alert('You have already applied for this job. You cannot apply twice for the same job.')
      return
    }

    // AI Matching uses the resume that generated the recommendation.
    // Find Jobs uses the resume currently selected by the candidate.
    const resumeToUse =
      resumes.find((resume) => String(resume.id) === String(job.resume_id)) ||
      resumes.find((resume) => String(resume.id) === String(selectedApplyResumeId)) ||
      resumes.find((resume) => resume.is_primary) ||
      resumes[0]

    if (!resumeToUse?.id) {
      setError('Could not find a valid resume. Please upload or select a resume and try again.')
      setActivePage('My Resumes')
      return
    }

    setApplyingJobId(job.id)
    setError('')
    setNotice('')

    try {
      // The backend ApplicationCreate schema requires resume_id.
      await api.post(`/applications/jobs/${job.id}`, {
        resume_id: Number(resumeToUse.id),
      })
      const response = await api.get('/applications/me')
      setApplications(getArray(response.data))
      setNotice(`Application submitted successfully for ${job.title || job.job_title || 'this job'}!`)
      setSelectedJob(null)
      setActivePage('Applications')
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Unable to submit application. Please try again.')
    } finally {
      setApplyingJobId(null)
    }
  }

  function hasApplied(jobId) {
    return applications.some((application) => String(application.job_id ?? application.job?.id) === String(jobId))
  }

  const firstName =
    user?.full_name?.split(' ')[0] ||
    user?.name?.split(' ')[0] ||
    user?.email?.split('@')[0] ||
    'Student'

  const pageDescriptions = {
    Overview: 'Here is what is happening with your career journey.',
    'My Resumes': 'Manage your resumes and keep your career profile updated.',
    'Find Jobs': 'Discover opportunities that match your skills.',
    Applications: 'Keep track of your job applications.',
    'AI Matching': 'Explore AI-powered resume and job matching.',
    'My Profile': 'Review your account information.',
    Interviews: 'View your scheduled interviews and meeting details.',
  }

  function renderContent() {
    if (activePage === 'My Resumes') {
      return (
        <section className="student-panel">
          <div className="student-panel-heading">
            <div>
              <h2>My Resumes</h2>
              <p>Manage your uploaded resumes.</p>
            </div>

            <label className="student-primary-button">
              <Upload size={17} />
              {uploading ? 'Uploading...' : 'Upload Resume'}
              <input
                type="file"
                accept=".pdf,.docx"
                hidden
                disabled={uploading}
                onChange={uploadResume}
              />
            </label>
          </div>

          {resumes.length === 0 ? (
            <div className="student-empty-state">
              <FileText size={38} />
              <h3>No resumes found</h3>
              <p>Upload a PDF or DOCX resume to get started.</p>
            </div>
          ) : (
            <div className="student-data-list">
              {resumes.map((resume, index) => (
                <div className="student-data-row" key={resume.id ?? index}>
                  <div className="student-file-icon">
                    <FileText size={21} />
                  </div>

                  <div className="student-data-info">
                    <strong>
                      {resume.filename ||
                        resume.file_name ||
                        resume.title ||
                        `Resume ${index + 1}`}
                    </strong>
                    <span>
                      {resume.is_primary ? 'Primary resume' : 'Uploaded resume'}
                    </span>
                  </div>

                  <div className="student-resume-actions">
                    {resume.is_primary ? (
                      <span className="student-status">Primary</span>
                    ) : (
                      <button
                        className="student-resume-action"
                        disabled={resumeActionLoading}
                        onClick={() => setPrimaryResume(resume.id)}
                      >
                        Set Primary
                      </button>
                    )}

                    <button
                      className="student-resume-delete"
                      disabled={resumeActionLoading}
                      onClick={() => deleteResume(resume.id)}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )
    }

    if (activePage === 'Find Jobs') {
      const visibleJobs = jobs.filter((job) =>
        [job.title, job.job_title, job.company_name, job.company?.name, job.location, job.description]
          .filter(Boolean)
          .join(' ')
          .toLowerCase()
          .includes(jobSearch.toLowerCase().trim()),
      )
      return (
        <section className="student-panel">
          <div className="student-panel-heading">
            <div>
              <h2>Find Jobs</h2>
              <p>Explore available opportunities and apply with your resume.</p>
            </div>
            <Search size={21} />
          </div>
          <input
            type="search"
            aria-label="Search jobs"
            placeholder="Search job title, company, location..."
            value={jobSearch}
            onChange={(event) => setJobSearch(event.target.value)}
            style={{ width: '100%', padding: '12px 14px', borderRadius: 10, border: '1px solid #394158', background: '#171d2c', color: '#fff', marginBottom: 14 }}
          />
          {resumes.length > 0 && (
            <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap', padding: 14, marginBottom: 18, borderRadius: 10, border: '1px solid #394158', background: '#171d2c' }}>
              <label htmlFor="apply-resume-select" style={{ fontWeight: 600 }}>Apply using resume</label>
              <select
                id="apply-resume-select"
                value={selectedApplyResumeId}
                onChange={(event) => setSelectedApplyResumeId(event.target.value)}
                style={{ flex: '1 1 260px', minWidth: 220, padding: '11px 12px', borderRadius: 8, border: '1px solid #394158', background: '#222a3d', color: '#fff' }}
              >
                {resumes.map((resume, index) => (
                  <option key={resume.id ?? index} value={String(resume.id)}>
                    {resume.file_name || resume.filename || resume.title || `Resume ${index + 1}`}{resume.is_primary ? ' (Primary)' : ''}
                  </option>
                ))}
              </select>
              <span style={{ flexBasis: '100%', fontSize: 13, opacity: 0.8 }}>Choose the resume you want to use before clicking Apply Now. You can change it for your next application.</span>
            </div>
          )}
          {selectedJob && (
            <div style={{ border: '1px solid #4b5571', borderRadius: 12, padding: 20, marginBottom: 20, background: '#1a2235' }}>
              <div className="student-panel-heading">
                <div>
                  <h2>{selectedJob.title || selectedJob.job_title || 'Job details'}</h2>
                  <p>{selectedJob.company_name || selectedJob.company?.name || 'Company'}{selectedJob.location ? ` · ${selectedJob.location}` : ''}</p>
                </div>
                <button className="student-text-button" onClick={() => setSelectedJob(null)}>Close <X size={16} /></button>
              </div>
              {selectedJob.description && <p style={{ whiteSpace: 'pre-wrap', margin: '12px 0', lineHeight: 1.7 }}>{selectedJob.description}</p>}
              {selectedJob.requirements && <p style={{ whiteSpace: 'pre-wrap', margin: '12px 0' }}><strong>Requirements:</strong> {selectedJob.requirements}</p>}
              {selectedJob.experience_required != null && <p>Experience: {selectedJob.experience_required}</p>}
              {selectedJob.employment_type && <p>Type: {selectedJob.employment_type}</p>}
              <button
                className="student-primary-button"
                disabled={applyingJobId !== null}
                onClick={() => applyForJob(selectedJob)}
                style={{ marginTop: 16, opacity: hasApplied(selectedJob.id) ? 0.6 : 1 }}
              >
                {hasApplied(selectedJob.id) ? 'Already Applied' : applyingJobId === selectedJob.id ? 'Applying...' : 'Apply Now'}
              </button>
            </div>
          )}
          {visibleJobs.length === 0 ? (
            <div className="student-empty-state">
              <BriefcaseBusiness size={38} />
              <h3>{jobs.length ? 'No matching jobs' : 'No jobs available yet'}</h3>
              <p>{jobs.length ? 'Try a different search.' : 'Published job opportunities will appear here.'}</p>
            </div>
          ) : (
            <div className="student-data-list">
              {visibleJobs.map((job, index) => (
                <div className="student-data-row" key={job.id ?? index}>
                  <div className="student-file-icon"><BriefcaseBusiness size={21} /></div>
                  <div className="student-data-info">
                    <strong>{job.title || job.job_title || 'Untitled job'}</strong>
                    <span>{job.company_name || job.company?.name || 'Company'}{job.location ? ` · ${job.location}` : ''}</span>
                    {job.description && <p>{job.description.length > 160 ? `${job.description.slice(0, 160)}...` : job.description}</p>}
                    <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 12 }}>
                      <button className="student-resume-action" onClick={() => setSelectedJob(job)}>View Details</button>
                      <button
                        className="student-primary-button"
                        disabled={applyingJobId !== null}
                        onClick={() => applyForJob(job)}
                        style={{ opacity: hasApplied(job.id) ? 0.6 : 1 }}
                      >
                        {hasApplied(job.id) ? 'Already Applied' : applyingJobId === job.id ? 'Applying...' : 'Apply Now'}
                      </button>
                    </div>
                  </div>
                  <span className="student-status">{job.status || 'Available'}</span>
                </div>
              ))}
            </div>
          )}
        </section>
      )
    }

    if (activePage === 'Interviews') {
      return <InterviewCenter mode="student" />
    }

    if (activePage === 'Applications') {
      return (
        <section className="student-panel">
          <div className="student-panel-heading">
            <div>
              <h2>My Applications</h2>
              <p>Monitor your application progress.</p>
            </div>
          </div>

          {applications.length === 0 ? (
            <div className="student-empty-state">
              <ClipboardList size={38} />
              <h3>No applications yet</h3>
              <p>Your submitted job applications will appear here.</p>
            </div>
          ) : (
            <div className="student-data-list">
              {applications.map((application, index) => {
                // /applications/me returns job_id; /jobs provides the
                // corresponding title and company details. Join them here.
                const relatedJob = jobs.find(
                  (job) =>
                    String(job.id ?? job.job_id) ===
                    String(application.job_id ?? application.job?.id),
                )
                const title =
                  application.job_title ||
                  application.job?.title ||
                  relatedJob?.title ||
                  relatedJob?.job_title ||
                  'Job title unavailable'
                const company =
                  application.company_name ||
                  application.job?.company_name ||
                  application.job?.company?.name ||
                  relatedJob?.company_name ||
                  relatedJob?.company?.name ||
                  'Company details unavailable'
                // Applications API returns resume_id; resolve it against the
                // student's uploaded resumes so they can see which file was sent.
                const appliedResume = resumes.find(
                  (resume) => String(resume.id) === String(application.resume_id),
                )
                const resumeName = appliedResume
                  ? appliedResume.file_name || appliedResume.filename || appliedResume.title || `Resume #${appliedResume.id}`
                  : application.resume_id != null
                    ? `Resume #${application.resume_id}`
                    : 'Resume details unavailable'
                const appliedDate =
                  application.applied_at || application.created_at || application.application_date
                const formattedDate = appliedDate
                  ? new Date(appliedDate).toLocaleDateString()
                  : null
                const statusLabel = String(application.status || 'APPLIED')
                  .replaceAll('_', ' ')
                  .toLowerCase()
                  .replace(/\b\w/g, (letter) => letter.toUpperCase())

                return (
                  <div
                    className="student-data-row"
                    key={application.id ?? index}
                  >
                    <div className="student-file-icon">
                      <ClipboardList size={21} />
                    </div>
                    <div className="student-data-info">
                      <strong>{title}</strong>
                      <span>{company}</span>
                      <span><strong>Resume used:</strong> {resumeName}</span>
                      {relatedJob?.location && (
                        <span>{relatedJob.location}</span>
                      )}
                      {formattedDate && (
                        <span>Applied on {formattedDate}</span>
                      )}
                    </div>
                    <span className="student-status">{statusLabel}</span>
                  </div>
                )
              })}
            </div>
          )}
        </section>
      )
    }

    if (activePage === 'AI Matching') {
      const selectedResume = resumes.find(
        (resume) => String(resume.id) === String(selectedMatchingResumeId),
      )
      const formatScore = (value) => `${Math.round(Number(value) || 0)}%`
      const formatSalary = (min, max) => {
        if (min == null && max == null) return 'Salary not specified'
        const format = (amount) => `₹${Number(amount).toLocaleString('en-IN')}`
        if (min != null && max != null) return `${format(min)} – ${format(max)}`
        return min != null ? `From ${format(min)}` : `Up to ${format(max)}`
      }

      return (
        <section className="student-panel">
          <div className="student-panel-heading">
            <div>
              <h2><BrainCircuit size={24} style={{ verticalAlign: 'middle', marginRight: 8 }} />AI Resume Matching</h2>
              <p>Choose any uploaded resume to find published jobs ranked by match score.</p>
            </div>
          </div>

          <div className="student-ai-note" style={{ marginBottom: 18 }}>
            <Sparkles size={19} />
            <span>Scores compare extracted resume details with job requirements. They are not a probability of getting hired; review each job yourself.</span>
          </div>

          {resumes.length === 0 ? (
            <div className="student-empty-state">
              <FileText size={38} />
              <h3>Upload a resume to get started</h3>
              <p>AI matching needs one of your uploaded PDF or DOCX resumes.</p>
              <button className="student-primary-button" onClick={() => setActivePage('My Resumes')}>Go to My Resumes <ChevronRight size={17} /></button>
            </div>
          ) : (
            <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap', marginBottom: 22 }}>
              <label htmlFor="matching-resume-select" style={{ fontWeight: 600 }}>Resume to analyze</label>
              <select
                id="matching-resume-select"
                value={selectedMatchingResumeId}
                onChange={(event) => {
                  setSelectedMatchingResumeId(event.target.value)
                  setMatchingResults([])
                  setMatchingError('')
                }}
                style={{ flex: '1 1 260px', minWidth: 220, padding: '12px 14px', borderRadius: 10, border: '1px solid #394158', background: '#171d2c', color: '#fff' }}
              >
                {resumes.map((resume, index) => (
                  <option key={resume.id ?? index} value={String(resume.id)}>
                    {resume.file_name || resume.filename || resume.title || `Resume ${index + 1}`}{resume.is_primary ? ' (Primary)' : ''}
                  </option>
                ))}
              </select>
              <button className="student-primary-button" onClick={runStudentMatching} disabled={matchingLoading || !selectedMatchingResumeId}>
                {matchingLoading ? 'Analyzing...' : 'Find Matching Jobs'} <Sparkles size={17} />
              </button>
            </div>
          )}

          {matchingError && <div className="student-error" role="alert" style={{ marginBottom: 18 }}>{matchingError}</div>}
          {matchingLoading && <p className="student-muted" role="status">Comparing your resume with published jobs...</p>}

          {!matchingLoading && matchingResults.length === 0 && resumes.length > 0 && !matchingError && (
            <div className="student-empty-state">
              <BrainCircuit size={34} />
              <h3>Ready to find your best matches?</h3>
              <p>{selectedResume ? `Selected: ${selectedResume.file_name || selectedResume.filename || 'your resume'}.` : 'Select a resume'} Click “Find Matching Jobs” to calculate recommendations.</p>
            </div>
          )}

          {!matchingLoading && matchingResults.length > 0 && (
            <>
              <div className="student-section-title" style={{ marginTop: 24, marginBottom: 14 }}>
                <div><h2>Recommended jobs ({matchingResults.length})</h2><p>Ranked from highest to lowest match score.</p></div>
              </div>
              <div className="student-data-list">
                {matchingResults.map((match) => {
                  const jobId = match.job_id
                  const applied = hasApplied(jobId)
                  return (
                    <article className="student-data-row" key={`${match.resume_id}-${jobId}`} style={{ alignItems: 'flex-start', gap: 16 }}>
                      <div className="student-file-icon"><BriefcaseBusiness size={22} /></div>
                      <div className="student-data-info" style={{ minWidth: 0, flex: 1 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
                          <strong style={{ fontSize: 17 }}>{match.title || 'Untitled job'}</strong>
                          <span className="student-status" title="Match score, not hiring probability">Match: {formatScore(match.final_score)}</span>
                        </div>
                        <span>{match.company_name || 'Company'}{match.location ? ` · ${match.location}` : ''}</span>
                        <p style={{ margin: '10px 0', lineHeight: 1.6 }}>{match.description || 'No job description provided.'}</p>
                        <p style={{ margin: '6px 0' }}><strong>Salary:</strong> {formatSalary(match.salary_min, match.salary_max)} · <strong>Type:</strong> {match.employment_type || 'Not specified'} · <strong>Work mode:</strong> {match.remote_policy || 'Not specified'}</p>
                        <p style={{ margin: '6px 0' }}><strong>Experience:</strong> {match.required_experience_years ?? 0}+ years{match.experience_level ? ` (${match.experience_level})` : ''}{match.required_education ? ` · Education: ${match.required_education}` : ''}</p>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, margin: '14px 0' }}>
                          {[['Skills', match.skill_score], ['Text similarity', match.semantic_score], ['Experience', match.experience_score], ['Education', match.education_score], ['Projects', match.project_score]].map(([label, score]) => (
                            <span key={label} className="student-status">{label}: {formatScore(score)}</span>
                          ))}
                        </div>
                        {match.matched_skills?.length > 0 && <p style={{ margin: '8px 0' }}><strong>Matched skills:</strong> {match.matched_skills.join(', ')}</p>}
                        {match.missing_skills?.length > 0 && <p style={{ margin: '8px 0' }}><strong>Skills to develop:</strong> {match.missing_skills.join(', ')}</p>}
                        {match.explanation && <details style={{ margin: '10px 0' }}><summary style={{ cursor: 'pointer', fontWeight: 600 }}>Why this score?</summary><p style={{ lineHeight: 1.6 }}>{match.explanation}</p></details>}
                        <button
                          className="student-primary-button"
                          disabled={applyingJobId !== null}
                          onClick={() => applyForJob({ ...match, id: jobId })}
                          style={{ marginTop: 8, opacity: applied ? 0.6 : 1 }}
                        >
                          {applied ? 'Already Applied' : applyingJobId === jobId ? 'Applying...' : 'Apply Now'}
                        </button>
                      </div>
                    </article>
                  )
                })}
              </div>
            </>
          )}
        </section>
      )
    }

    if (activePage === 'My Profile') {
      return (
        <section className="student-panel">
          <h2>My Profile</h2>
          <p className="student-section-description">
            Your current account information.
          </p>

          <div className="student-profile-details">
            <div>
              <span>Full name</span>
              <strong>{user?.full_name || user?.name || firstName}</strong>
            </div>
            <div>
              <span>Email address</span>
              <strong>{user?.email || 'Not available'}</strong>
            </div>
            <div>
              <span>Account role</span>
              <strong>{user?.role || 'STUDENT'}</strong>
            </div>
          </div>
        </section>
      )
    }

    return (
      <>
        <section className="student-welcome-banner">
          <div className="student-welcome-copy">
            <span className="student-eyebrow">
              <Sparkles size={14} /> YOUR CAREER WORKSPACE
            </span>
            <h2>Your next opportunity starts here.</h2>
            <p>
              Build a stronger resume, discover relevant jobs, and track your
              progress in one place.
            </p>
            <button
              className="student-banner-button"
              onClick={() => setActivePage('Find Jobs')}
            >
              Explore Jobs <ArrowUpRight size={17} />
            </button>
          </div>

          <div className="student-banner-art">
            <div className="student-art-orbit">
              <BrainCircuit size={65} strokeWidth={1.2} />
            </div>
            <Sparkles className="student-art-sparkle" size={25} />
          </div>
        </section>

        <div className="student-section-title">
          <div>
            <h2>Your Overview</h2>
            <p>A snapshot of your job search activity.</p>
          </div>
        </div>

        <section className="student-stat-grid">
          <div className="student-stat-card">
            <div className="student-stat-top">
              <span>My Resumes</span>
              <div className="student-stat-icon purple">
                <FileText size={20} />
              </div>
            </div>
            <strong>{loading ? '—' : resumes.length}</strong>
            <span className="student-stat-caption">Uploaded resumes</span>
          </div>

          <div className="student-stat-card">
            <div className="student-stat-top">
              <span>Available Jobs</span>
              <div className="student-stat-icon blue">
                <BriefcaseBusiness size={20} />
              </div>
            </div>
            <strong>{loading ? '—' : jobs.length}</strong>
            <span className="student-stat-caption">Opportunities to explore</span>
          </div>

          <div className="student-stat-card">
            <div className="student-stat-top">
              <span>Applications</span>
              <div className="student-stat-icon green">
                <ClipboardList size={20} />
              </div>
            </div>
            <strong>{loading ? '—' : applications.length}</strong>
            <span className="student-stat-caption">Submitted applications</span>
          </div>

          <div className="student-stat-card">
            <div className="student-stat-top">
              <span>AI Matching</span>
              <div className="student-stat-icon orange">
                <BrainCircuit size={20} />
              </div>
            </div>
            <strong>AI</strong>
            <span className="student-stat-caption">Career matching tools</span>
          </div>
        </section>

        <div className="student-content-grid">
          <section className="student-panel">
            <div className="student-panel-heading">
              <div>
                <h2>Recent Resumes</h2>
                <p>Your uploaded documents.</p>
              </div>
              <button
                className="student-text-button"
                onClick={() => setActivePage('My Resumes')}
              >
                View all <ChevronRight size={16} />
              </button>
            </div>

            {loading ? (
              <p className="student-muted">Loading resumes...</p>
            ) : resumes.length === 0 ? (
              <div className="student-mini-empty">
                <FileText size={24} />
                <span>No resumes uploaded yet.</span>
              </div>
            ) : (
              resumes.slice(0, 3).map((resume, index) => (
                <div className="student-data-row" key={resume.id ?? index}>
                  <div className="student-file-icon">
                    <FileText size={20} />
                  </div>
                  <div className="student-data-info">
                    <strong>
                      {resume.filename ||
                        resume.file_name ||
                        resume.title ||
                        `Resume ${index + 1}`}
                    </strong>
                    <span>
                      {resume.is_primary ? 'Primary resume' : 'Resume document'}
                    </span>
                  </div>
                </div>
              ))
            )}
          </section>

          <section className="student-panel student-quick-panel">
            <div className="student-panel-heading">
              <div>
                <h2>Quick Actions</h2>
                <p>Continue building your profile.</p>
              </div>
            </div>

            <button
              className="student-action-row"
              onClick={() => setActivePage('My Resumes')}
            >
              <div className="student-action-icon">
                <Upload size={19} />
              </div>
              <span>
                <strong>Manage resumes</strong>
                <small>Upload and organize your files</small>
              </span>
              <ChevronRight size={18} />
            </button>

            <button
              className="student-action-row"
              onClick={() => setActivePage('Find Jobs')}
            >
              <div className="student-action-icon">
                <Search size={19} />
              </div>
              <span>
                <strong>Explore jobs</strong>
                <small>Find your next opportunity</small>
              </span>
              <ChevronRight size={18} />
            </button>

            <button
              className="student-action-row"
              onClick={() => setActivePage('AI Matching')}
            >
              <div className="student-action-icon">
                <BrainCircuit size={19} />
              </div>
              <span>
                <strong>AI matching</strong>
                <small>Explore resume matching</small>
              </span>
              <ChevronRight size={18} />
            </button>
          </section>
        </div>
      </>
    )
  }

  return (
    <div className="student-app">
      {mobileMenu && (
        <button
          className="student-mobile-backdrop"
          aria-label="Close navigation"
          onClick={() => setMobileMenu(false)}
        />
      )}

      <aside className={`student-sidebar ${mobileMenu ? 'mobile-open' : ''}`}>
        <div className="student-brand">
          <div className="student-brand-mark">R</div>
          <div>
            <strong>ResumeAI</strong>
            <span>CAREER INTELLIGENCE</span>
          </div>
          <button
            className="student-close-menu"
            aria-label="Close menu"
            onClick={() => setMobileMenu(false)}
          >
            <X size={20} />
          </button>
        </div>

        <div className="student-nav-label">WORKSPACE</div>

        <nav className="student-nav">
          {navigation.map(({ label, icon: Icon }) => (
            <button
              key={label}
              className={`student-nav-item ${
                activePage === label ? 'active' : ''
              }`}
              onClick={() => {
                setActivePage(label)
                setNotice('')
                setMobileMenu(false)
              }}
            >
              <Icon size={19} />
              <span>{label}</span>
              {activePage === label && <span className="student-nav-indicator" />}
            </button>
          ))}
        </nav>

        <div className="student-sidebar-bottom">
          <div className="student-sidebar-tip">
            <div className="student-tip-icon">
              <Sparkles size={19} />
            </div>
            <strong>Make your next move.</strong>
            <p>Keep your resume updated to make the most of every opportunity.</p>
            <button onClick={() => setActivePage('My Resumes')}>
              Update resume <ArrowUpRight size={15} />
            </button>
          </div>

          <button className="student-logout-button" onClick={logout}>
            <LogOut size={18} />
            <span>Sign out</span>
          </button>
        </div>
      </aside>

      <main className="student-main">
        <header className="student-topbar">
          <button
            className="student-menu-button"
            aria-label="Open navigation"
            onClick={() => setMobileMenu(true)}
          >
            <Menu size={22} />
          </button>

          <div className="student-breadcrumb">
            <span>Workspace</span>
            <ChevronRight size={15} />
            <strong>{activePage}</strong>
          </div>

          <div className="student-topbar-right">
            <button
              className="student-icon-button"
              aria-label="Notifications"
              title="Notifications"
            >
              <Bell size={19} />
            </button>
            <div className="student-user-chip">
              <div className="student-avatar">
                {firstName.charAt(0).toUpperCase()}
              </div>
              <div className="student-user-meta">
                <strong>{firstName}</strong>
                <span>Student</span>
              </div>
            </div>
          </div>
        </header>

        <div className="student-page-content">
          <div className="student-page-heading">
            <div>
              <span className="student-page-kicker">STUDENT WORKSPACE</span>
              <h1>
                {activePage === 'Overview'
                  ? `Welcome back, ${firstName}`
                  : activePage}
              </h1>
              <p>{pageDescriptions[activePage]}</p>
            </div>

            {activePage === 'Overview' && (
              <button
                className="student-primary-button"
                onClick={() => setActivePage('My Resumes')}
              >
                <Upload size={17} /> Manage Resumes
              </button>
            )}
          </div>

          {notice && <div className="student-status" role="status" style={{ padding: 14, marginBottom: 18 }}>{notice} <button onClick={() => setNotice('')} aria-label="Dismiss notification" style={{ marginLeft: 12 }}>×</button></div>}

          {notice && (
            <div className="student-panel" role="status" style={{ marginBottom: 16, border: '1px solid #297b5c', padding: 14 }}>
              <span>{notice}</span>
              <button className="student-text-button" onClick={() => setNotice('')} style={{ marginLeft: 12 }}>Dismiss</button>
            </div>
          )}

          {error && (
            <div className="student-error" role="alert">
              <span>{error}</span>
              <button onClick={() => setError('')} aria-label="Dismiss error">
                <X size={17} />
              </button>
            </div>
          )}

          {renderContent()}

          <footer className="student-footer">
            <span>ResumeAI</span>
            <span>AI-powered career intelligence</span>
          </footer>
        </div>
      </main>
    </div>
  )
}