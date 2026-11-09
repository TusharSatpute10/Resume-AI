import { useCallback, useEffect, useMemo, useState } from 'react'
import { LayoutDashboard, BriefcaseBusiness, Users, BrainCircuit, Building2, RefreshCw, Search, CheckCircle2, Clock3, AlertCircle, LogOut, Plus, Pencil, Tags, X, Trash2, FileText, Download } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import api from '../services/api'
import { CalendarDays } from 'lucide-react'
import InterviewCenter from '../components/InterviewCenter'

const NAV = [
  ['Overview', LayoutDashboard],
  ['My Jobs', BriefcaseBusiness],
  ['Applicants', Users],
  ['Interviews', CalendarDays],
  ['AI Matching', BrainCircuit],
  ['Company Profile', Building2]
]
const toList = (v) => Array.isArray(v) ? v : (v?.items || v?.results || v?.jobs || v?.applicants || [])
const jobId = (j) => j?.id ?? j?.job_id
const jobTitle = (j) => j?.title ?? j?.job_title ?? j?.role ?? 'Untitled job'
const jobStatus = (j) => String(j?.status ?? (j?.is_published ? 'published' : 'draft')).toLowerCase()
const formatDate = (v) => v ? (Number.isNaN(new Date(v).getTime()) ? String(v) : new Date(v).toLocaleDateString()) : '—'

function Badge({ value }) {
  const text = String(value || 'pending').toLowerCase().replaceAll('_', ' ')
  return <span className={`hr-badge ${text.replaceAll(' ', '-')}`}>{text}</span>
}
function Empty({ icon: Icon, heading, text }) {
  return <div className="hr-empty"><span><Icon size={25}/></span><h3>{heading}</h3><p>{text}</p></div>
}

export default function HRDashboard() {
  const { user, logout } = useAuth()
  const [page, setPage] = useState('Overview')
  const [jobs, setJobs] = useState([])
  const [profile, setProfile] = useState(null)
  const [company, setCompany] = useState(null)
  const [applications, setApplications] = useState([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [selectedJob, setSelectedJob] = useState('')
  const [matches, setMatches] = useState([])
  const [matchingCompleted, setMatchingCompleted] = useState(false)
  const [applicantsLoadError, setApplicantsLoadError] = useState('')
  const [updatingApplicationIds, setUpdatingApplicationIds] = useState([])
  const emptyJobForm = { title: '', description: '', location: '', remote_policy: 'ONSITE', employment_type: 'FULL_TIME', salary_min: '', salary_max: '', required_experience_years: '0', experience_level: 'ENTRY', required_education: '', openings: '1' }
  const [jobModalOpen, setJobModalOpen] = useState(false)
  const [editingJob, setEditingJob] = useState(null)
  const [jobForm, setJobForm] = useState(emptyJobForm)
  const [savingJob, setSavingJob] = useState(false)
  const [skillsJob, setSkillsJob] = useState(null)
  const [jobSkills, setJobSkills] = useState([])
  const [skillForm, setSkillForm] = useState({ name: '', category: '', requirement_type: 'REQUIRED', minimum_years: '', importance_weight: '1' })
  const [skillsLoading, setSkillsLoading] = useState(false)
  const [savingSkill, setSavingSkill] = useState(false)

  const refresh = useCallback(async (quiet = false) => {
    if (quiet) setBusy(true); else setLoading(true)
    setError('')
    try {
      const [jobsRes, hrRes, companyRes] = await Promise.allSettled([
        api.get('/jobs/my'), api.get('/hr/me'), api.get('/companies/me'),
      ])
      if (jobsRes.status === 'fulfilled') setJobs(toList(jobsRes.value.data))
      else { setJobs([]); setError(jobsRes.reason?.response?.data?.detail || 'Could not load jobs. Check that you are signed in with an HR account.') }
      if (hrRes.status === 'fulfilled') setProfile(hrRes.value.data)
      if (companyRes.status === 'fulfilled') setCompany(companyRes.value.data)
    } finally { setLoading(false); setBusy(false) }
  }, [])
  useEffect(() => { refresh() }, [refresh])

  useEffect(() => {
    let cancelled = false
    async function fetchApplicants() {
      const groups = await Promise.all(jobs.map(async (job) => {
        try {
          const items = toList((await api.get(`/applications/jobs/${jobId(job)}/applicants`)).data)
          // The applicants endpoint returns candidate details but not job_id/title.
          // Attach the job context here so the Applicants table can identify each posting.
          return { items: items.map(a => ({ ...a, job_id: jobId(job), job_title: jobTitle(job) })), failed: false }
        } catch {
          return { items: [], failed: true }
        }
      }))
      if (!cancelled) {
        const seen = new Set()
        const all = groups.flatMap(group => group.items)
        setApplications(all.filter((a, i) => {
          const key = a?.id ?? a?.application_id ?? `${a?.student_email ?? a?.email}-${a?.job_id}-${i}`
          if (seen.has(key)) return false
          seen.add(key); return true
        }))
        setApplicantsLoadError(groups.some(group => group.failed)
          ? 'Some applicant lists could not be loaded. Refresh or check the backend logs.'
          : '')
      }
    }
    if (jobs.length) fetchApplicants()
    else {
      setApplications([])
      setApplicantsLoadError('')
    }
    return () => { cancelled = true }
  }, [jobs])

  const companyName = company?.company_name ?? company?.name ?? profile?.company_name ?? user?.company_name ?? 'Your Company'
  // An explicit closed/draft status takes precedence over any stale is_published flag.
  const isPublishedJob = (job) => {
    const status = jobStatus(job)
    return ['published', 'open', 'active'].includes(status)
  }
  const publishedJobs = jobs.filter(isPublishedJob)
  const activeCount = publishedJobs.length
  const filteredJobs = useMemo(() => {
    const q = search.trim().toLowerCase()
    return !q ? jobs : jobs.filter(j => [jobTitle(j), j?.location, j?.employment_type, j?.description].filter(Boolean).join(' ').toLowerCase().includes(q))
  }, [jobs, search])

  async function changeJobStatus(job, action) {
    setError(''); setNotice('')
    try {
      await api.patch(`/jobs/${jobId(job)}/${action}`)
      setNotice(action === 'publish' ? 'Job published successfully.' : 'Job closed successfully.')
      await refresh(true)
    } catch (e) { setError(e.response?.data?.detail || `Could not ${action} this job.`) }
  }

  function openCreateJob() {
    setEditingJob(null); setJobForm({ ...emptyJobForm }); setError(''); setNotice(''); setJobModalOpen(true)
  }
  function openEditJob(job) {
    setEditingJob(job)
    setJobForm({
      title: job.title ?? '', description: job.description ?? '', location: job.location ?? '',
      remote_policy: job.remote_policy ?? 'ONSITE', employment_type: job.employment_type ?? 'FULL_TIME',
      salary_min: job.salary_min ?? '', salary_max: job.salary_max ?? '',
      required_experience_years: job.required_experience_years ?? 0,
      experience_level: job.experience_level ?? 'ENTRY', required_education: job.required_education ?? '',
      openings: job.openings ?? 1,
    })
    setError(''); setNotice(''); setJobModalOpen(true)
  }
  async function saveJob(event) {
    event.preventDefault(); setError(''); setNotice('')
    const title = jobForm.title.trim(), description = jobForm.description.trim()
    if (title.length < 3) { setError('Job title must contain at least 3 characters.'); return }
    if (description.length < 20) { setError('Job description must contain at least 20 characters.'); return }
    const min = jobForm.salary_min === '' ? null : Number(jobForm.salary_min)
    const max = jobForm.salary_max === '' ? null : Number(jobForm.salary_max)
    if (min !== null && min < 0 || max !== null && max < 0) { setError('Salary cannot be negative.'); return }
    if (min !== null && max !== null && min > max) { setError('Minimum salary cannot exceed maximum salary.'); return }
    const payload = {
      title, description, location: jobForm.location.trim() || null,
      remote_policy: jobForm.remote_policy || null, employment_type: jobForm.employment_type || null,
      salary_min: min, salary_max: max,
      required_experience_years: jobForm.required_experience_years === '' ? null : Number(jobForm.required_experience_years),
      experience_level: jobForm.experience_level || null, required_education: jobForm.required_education.trim() || null,
      openings: Number(jobForm.openings || 1),
    }
    if (!Number.isInteger(payload.openings) || payload.openings < 1) { setError('Openings must be a whole number of at least 1.'); return }
    setSavingJob(true)
    try {
      if (editingJob) {
        await api.patch(`/jobs/${jobId(editingJob)}`, payload)
        setNotice('Job updated successfully.')
      } else {
        await api.post('/jobs', payload)
        setNotice('Job created as a draft. Publish it when you are ready.')
      }
      setJobModalOpen(false); await refresh(true)
    } catch (e) {
      const detail = e.response?.data?.detail
      setError(Array.isArray(detail) ? detail.map(x => x.msg).join(' · ') : (detail || `Could not ${editingJob ? 'update' : 'create'} the job.`))
    } finally { setSavingJob(false) }
  }
  async function openJobSkills(job) {
    setSkillsJob(job); setError(''); setNotice(''); setSkillsLoading(true); setJobSkills([])
    try {
      const jobSkillsRes = await api.get(`/jobs/${jobId(job)}/skills`)
      setJobSkills(toList(jobSkillsRes.data))
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not load skill requirements.')
    } finally { setSkillsLoading(false) }
  }
  async function addJobSkill(event) {
    event.preventDefault()
    if (!skillsJob || !skillForm.name.trim()) return
    setSavingSkill(true); setError(''); setNotice('')
    try {
      const skillName = skillForm.name.trim()
      let skillId
      try {
        const created = await api.post('/skills', { name: skillName, category: skillForm.category.trim() || null })
        skillId = created.data?.id ?? created.data?.skill_id
      } catch (createError) {
        // If this exact skill already exists globally, reuse it silently; HR still enters the skill manually.
        const status = createError.response?.status
        if (status !== 409 && status !== 400) throw createError
        const existingResponse = await api.get('/skills')
        const existing = toList(existingResponse.data).find(item => String(item.name ?? item.skill_name ?? '').trim().toLowerCase() === skillName.toLowerCase())
        if (!existing) throw createError
        skillId = existing.id ?? existing.skill_id
      }
      if (!skillId) throw new Error('The skill was created but the API did not return its ID. Check the skills API response.')
      const payload = { skill_id: Number(skillId), requirement_type: skillForm.requirement_type, minimum_years: skillForm.minimum_years === '' ? null : Number(skillForm.minimum_years), importance_weight: Number(skillForm.importance_weight) }
      await api.post(`/jobs/${jobId(skillsJob)}/skills`, payload)
      setJobSkills(toList((await api.get(`/jobs/${jobId(skillsJob)}/skills`)).data))
      setSkillForm({ name: '', category: '', requirement_type: 'REQUIRED', minimum_years: '', importance_weight: '1' })
      setNotice(`“${skillName}” added to this job.`)
    } catch (e) {
      const detail = e.response?.data?.detail
      setError(Array.isArray(detail) ? detail.map(x => x.msg).join(' · ') : (detail || e.message || 'Could not create and attach this skill.'))
    } finally { setSavingSkill(false) }
  }
  async function removeJobSkill(skill) {
    if (!skillsJob) return
    setError(''); setNotice('')
    try {
      await api.delete(`/jobs/${jobId(skillsJob)}/skills/${skill.skill_id}`)
      setJobSkills(current => current.filter(s => Number(s.skill_id) !== Number(skill.skill_id)))
      setNotice('Skill requirement removed.')
    } catch (e) { setError(e.response?.data?.detail || 'Could not remove this skill.') }
  }
  async function runMatching(jobOrId) {
    const job = typeof jobOrId === 'object'
      ? jobOrId
      : jobs.find(item => String(jobId(item)) === String(jobOrId))
    const id = job ? jobId(job) : jobOrId
    if (!id) return
    // Keep the UI guard as well as the backend guard: draft/closed jobs cannot be matched.
    if (job && !isPublishedJob(job)) {
      setPage('AI Matching')
      setSelectedJob('')
      setMatches([])
      setMatchingCompleted(false)
      setError('AI matching is available only for published jobs. Publish this job first.')
      return
    }
    setSelectedJob(String(id))
    setMatches([])
    setMatchingCompleted(false)
    setPage('AI Matching')
    setError('')
    setNotice('')
    setBusy(true)
    try {
      await api.post(`/matching/jobs/${id}/run`)
      const res = await api.get(`/matching/jobs/${id}/results`)
      setMatches(toList(res.data))
      setMatchingCompleted(true)
      setNotice('Matching completed.')
    } catch (e) {
      const detail = e.response?.data?.detail
      setError(Array.isArray(detail) ? detail.map(item => item.msg).join(' · ') : (detail || 'Matching failed. Confirm the job is published and belongs to your HR account.'))
    } finally {
      setBusy(false)
    }
  }

  async function updateApplicationStatus(application, nextStatus) {
    const applicationId = application?.id ?? application?.application_id
    const previousStatus = application?.status
    if (!applicationId || !nextStatus || nextStatus === previousStatus) return

    setError('')
    setNotice('')
    setUpdatingApplicationIds(current => [...current, String(applicationId)])
    try {
      const response = await api.patch(`/applications/${applicationId}/status`, {
        status: nextStatus,
      })
      const savedStatus = response.data?.status ?? nextStatus
      setApplications(current => current.map(item =>
        String(item?.id ?? item?.application_id) === String(applicationId)
          ? { ...item, status: savedStatus }
          : item
      ))
      setNotice(`Application status updated to ${String(savedStatus).replaceAll('_', ' ').toLowerCase()}.`)
    } catch (e) {
      const detail = e.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Could not update this application status. Please try again.')
    } finally {
      setUpdatingApplicationIds(current => current.filter(id => id !== String(applicationId)))
    }
  }

  async function viewResume(application) {
    const applicationId = application?.id ?? application?.application_id
    if (!applicationId) {
      setError('This application does not have a valid ID, so its resume cannot be opened.')
      return
    }

    setError('')
    setNotice('')
    // Open a tab synchronously to avoid browser popup blockers while the file loads.
    const previewTab = window.open('', '_blank')
    try {
      const response = await api.get(`/applications/${applicationId}/resume-file`, {
        responseType: 'blob',
      })
      const blob = new Blob([response.data], {
        type: response.headers?.['content-type'] || 'application/octet-stream',
      })
      const objectUrl = URL.createObjectURL(blob)
      const contentType = String(response.headers?.['content-type'] || '').toLowerCase()
      if (contentType.includes('application/pdf')) {
        if (previewTab) {
          previewTab.location.href = objectUrl
        } else {
          window.open(objectUrl, '_blank', 'noopener,noreferrer')
        }
        window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60000)
      } else {
        if (previewTab) previewTab.close()
        const link = document.createElement('a')
        link.href = objectUrl
        link.download = 'resume.docx'
        document.body.appendChild(link)
        link.click()
        link.remove()
        window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60000)
      }
    } catch (e) {
      if (previewTab) previewTab.close()
      const detail = e.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Could not open this resume. Confirm the backend is updated and the original file exists.')
    }
  }

  function JobTable({ items }) {
    if (!items.length) return <Empty icon={BriefcaseBusiness} heading="No jobs found" text="Jobs owned by your HR account will appear here." />
    return <div className="hr-table-wrap"><table className="hr-table"><thead><tr><th>Job title</th><th>Location / type</th><th>Posted</th><th>Status</th><th>Actions</th></tr></thead><tbody>
      {items.map((job, i) => {
        const isOpen = isPublishedJob(job)
        return <tr key={jobId(job) ?? i}><td><strong>{jobTitle(job)}</strong><small>{job?.company_name ?? companyName}</small></td><td>{[job?.location, job?.employment_type ?? job?.job_type].filter(Boolean).join(' · ') || 'Not specified'}</td><td>{formatDate(job?.created_at ?? job?.posted_at)}</td><td><Badge value={jobStatus(job)}/></td><td><div className="hr-actions"><button title={isOpen ? "Run AI matching" : "Publish this job before matching"} disabled={!isOpen || busy} onClick={() => runMatching(job)}><BrainCircuit size={16}/></button><button title="View applicants" onClick={() => setPage('Applicants')}><Users size={16}/></button><button title="Edit job" onClick={() => openEditJob(job)}><Pencil size={14}/> Edit</button><button title="Manage required skills" onClick={() => openJobSkills(job)}><Tags size={14}/> Skills</button><button onClick={() => changeJobStatus(job, isOpen ? 'close' : 'publish')}>{isOpen ? 'Close' : 'Publish'}</button></div></td></tr>
      })}
    </tbody></table></div>
  }

  return <div className="hr-app"><aside className="hr-sidebar">
    <div className="hr-brand"><span className="hr-brand-mark">R</span><div>Resume<span>AI</span><small>RECRUITMENT WORKSPACE</small></div></div>
    <p className="hr-sidebar-label">WORKSPACE</p>
    <nav>{NAV.map(([label, Icon]) => <button key={label} className={page === label ? 'active' : ''} onClick={() => setPage(label)}><Icon size={18}/>{label}{label === 'Applicants' && applications.length > 0 && <i>{applications.length}</i>}</button>)}</nav>
    <div className="hr-sidebar-bottom"><strong>{companyName}</strong><small>{user?.email}</small><button onClick={logout}><LogOut size={16}/> Sign out</button></div>
  </aside><main className="hr-main">
    <header className="hr-header"><div><small>RECRUITER WORKSPACE</small><h1>{page}</h1></div><div className="hr-header-right"><button className="hr-refresh" onClick={() => refresh(true)} disabled={busy} title="Refresh"><RefreshCw size={17}/></button><span className="hr-avatar">{String(user?.email || 'H').slice(0,1).toUpperCase()}</span></div></header>
    {error && <div className="hr-alert error"><AlertCircle size={17}/><span>{error}</span><button onClick={() => setError('')}>×</button></div>}
    {notice && <div className="hr-alert success"><CheckCircle2 size={17}/><span>{notice}</span><button onClick={() => setNotice('')}>×</button></div>}
    {loading ? <div className="hr-loading">Loading your recruitment workspace…</div> : <>
      {page === 'Overview' && <><section className="hr-hero"><div><span className="hr-tag">● RECRUITMENT OVERVIEW</span><h2>Find the right talent.<br/><em>Build your team.</em></h2><p>Manage your openings, review applicants, and discover candidates with AI-powered matching.</p><button className="hr-primary" onClick={() => setPage('My Jobs')}><BriefcaseBusiness size={16}/> Manage jobs</button></div><div className="hr-hero-art"><BrainCircuit size={70}/></div></section>
        <div className="hr-stats"><article><BriefcaseBusiness/><small>Total jobs</small><strong>{jobs.length}</strong><p>Jobs owned by your account</p></article><article><CheckCircle2/><small>Published / active</small><strong>{activeCount}</strong><p>Currently open opportunities</p></article><article><Users/><small>Applicants</small><strong>{applications.length}</strong><p>Applications across your jobs</p></article><article><Clock3/><small>Draft / closed</small><strong>{jobs.length-activeCount}</strong><p>Not currently open</p></article></div>
        <div className="hr-section-title"><div><h2>Recent job postings</h2><p>Your latest opportunities</p></div><button onClick={() => setPage('My Jobs')}>View all →</button></div><JobTable items={jobs.slice(0,5)}/></>}
      {page === 'My Jobs' && <><div className="hr-section-title"><div><h2>Job postings</h2><p>Create, edit, publish, and manage jobs associated with your HR account.</p></div><div className="hr-title-actions"><span className="hr-count">{jobs.length} jobs</span><button className="hr-primary" onClick={openCreateJob}><Plus size={15}/> Create Job</button></div></div><label className="hr-search"><Search size={17}/><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search jobs by title, location, or type…"/></label><JobTable items={filteredJobs}/></>}
      {page === 'Applicants' && <><div className="hr-section-title"><div><h2>Applicants</h2><p>People who applied to your job postings.</p></div><span className="hr-count">{applications.length} applications</span></div>{applicantsLoadError && <div className="hr-alert error"><AlertCircle size={17}/><span>{applicantsLoadError}</span><button onClick={() => setApplicantsLoadError('')}>×</button></div>}{applications.length ? <div className="hr-table-wrap"><table className="hr-table"><thead><tr><th>Candidate</th><th>Job</th><th>Applied</th><th>Status</th><th>Resume</th></tr></thead><tbody>{applications.map((a,i) => { const name = a?.student_name ?? a?.student?.full_name ?? a?.candidate_name ?? a?.full_name ?? a?.name ?? a?.student_email ?? a?.email ?? `Candidate ${i+1}`; const job = jobs.find(j => String(jobId(j)) === String(a?.job_id ?? a?.job?.id)); return <tr key={a?.id ?? a?.application_id ?? `${a?.job_id}-${i}`}><td><strong>{name}</strong><small>{a?.student_email ?? a?.email ?? a?.student?.email ?? ''}</small></td><td>{job ? jobTitle(job) : a?.job_title ?? a?.job?.title ?? 'Job posting'}</td><td>{formatDate(a?.applied_at ?? a?.created_at ?? a?.application_date)}</td><td><div className="hr-status-control"><Badge value={a?.status}/><select aria-label={`Update status for ${name}`} value={String(a?.status || 'APPLIED').toUpperCase()} disabled={updatingApplicationIds.includes(String(a?.id ?? a?.application_id))} onChange={e => updateApplicationStatus(a, e.target.value)}><option value="APPLIED">Applied</option><option value="UNDER_REVIEW">Under Review</option><option value="SHORTLISTED">Shortlisted</option><option value="INTERVIEW_SCHEDULED">Interview Scheduled</option><option value="HIRED">Hired</option><option value="REJECTED">Rejected</option></select></div></td><td><button className="hr-resume-button" onClick={() => viewResume(a)} title="Open the resume submitted with this application"><FileText size={14}/> View Resume</button></td></tr>})}</tbody></table></div> : <Empty icon={Users} heading={applicantsLoadError ? 'Applicants could not be fully loaded' : 'No applicants yet'} text={applicantsLoadError ? 'Some requests failed. Refresh the dashboard and check the backend if the problem continues.' : 'Applications to jobs owned by this HR account will appear here.'}/>}</>}

      {page === 'Interviews' && (
  <InterviewCenter
    mode="hr"
    applications={applications}
  />
)}

      {page === 'AI Matching' && <>
        <div className="hr-section-title">
          <div>
            <h2>AI candidate matching</h2>
            <p>Only published jobs are eligible. Results include applicants for the selected job only.</p>
          </div>
          <span className="hr-count">AI MATCHING</span>
        </div>

        <section className="hr-match-box">
          <BrainCircuit size={30}/>
          <div>
            <strong>Match applicants to a job</strong>
            <p>Select a published job to rank the students who applied to it.</p>
          </div>
          <select
            value={selectedJob}
            onChange={e => {
              setSelectedJob(e.target.value)
              setMatches([])
              setMatchingCompleted(false)
              setError('')
              setNotice('')
            }}
          >
            <option value="">
              {publishedJobs.length ? 'Choose a published job…' : 'No published jobs available'}
            </option>
            {publishedJobs.map(j => (
              <option key={jobId(j)} value={jobId(j)}>{jobTitle(j)}</option>
            ))}
          </select>
          <button
            className="hr-primary"
            disabled={!selectedJob || busy || !publishedJobs.some(j => String(jobId(j)) === String(selectedJob))}
            onClick={() => runMatching(selectedJob)}
          >
            {busy ? 'Matching…' : 'Run matching'}
          </button>
        </section>

        {!publishedJobs.length && (
          <p className="hr-help">Publish a job from My Jobs before running AI matching.</p>
        )}
        {busy && <p className="hr-help">Running the matching engine…</p>}

        {matches.length > 0 && (
          <>
            <div className="hr-match-summary">
              <span><strong>{matches.length}</strong> candidates ranked</span>
              <span>Sorted by final match score</span>
            </div>
            <div className="hr-table-wrap">
              <table className="hr-table hr-matching-table">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Candidate</th>
                    <th>Final score</th>
                    <th>Skills</th>
                    <th>Text similarity</th>
                    <th>Experience</th>
                    <th>Education</th>
                    <th>Projects</th>
                    <th>Match explanation</th>
                  </tr>
                </thead>
                <tbody>
                  {matches.map((m, i) => {
                    const explanation = m?.explanation ?? m?.reason ?? m?.summary ?? ''
                    const experienceNotEvaluated =
                      /job\s*does not specify.*experience requirement/i.test(explanation) ||
                      /experience information was not extracted/i.test(explanation)

                    const formatScore = value =>
                      value == null || Number.isNaN(Number(value))
                        ? 'N/A'
                        : `${Number(value).toFixed(1)}%`

                    const candidate =
                      m?.student_name ??
                      m?.candidate_name ??
                      m?.resume_name ??
                      m?.resume_file_name ??
                      m?.file_name ??
                      `Candidate ${i + 1}`

                    const matchedSkills = Array.isArray(m?.matched_skills) ? m.matched_skills : []
                    const missingSkills = Array.isArray(m?.missing_skills) ? m.missing_skills : []

                    return (
                      <tr key={m?.id ?? m?.resume_id ?? i}>
                        <td><span className="hr-rank-badge">#{m?.rank ?? i + 1}</span></td>
                        <td>
                          <strong>{candidate}</strong>
                          <small>{m?.student_email ?? m?.email ?? m?.resume_file_name ?? ''}</small>
                        </td>
                        <td>
                          <strong className="hr-score">{formatScore(m?.final_score ?? m?.match_score ?? m?.score ?? m?.overall_score)}</strong>
                        </td>
                        <td>{formatScore(m?.skill_score)}</td>
                        <td>{formatScore(m?.semantic_score)}</td>
                        <td>{experienceNotEvaluated ? 'N/A' : formatScore(m?.experience_score)}</td>
                        <td>{formatScore(m?.education_score)}</td>
                        <td>{formatScore(m?.project_score ?? m?.projects_score)}</td>
                        <td className="hr-match-explanation">
                          {explanation || 'No explanation was returned.'}
                          {matchedSkills.length > 0 && (
                            <div className="hr-skill-details">
                              <strong>Matched skills</strong>
                              <div className="hr-skill-chips">
                                {matchedSkills.map((skill, index) => (
                                  <span className="hr-skill-chip matched" key={`${skill}-${index}`}>{skill}</span>
                                ))}
                              </div>
                            </div>
                          )}
                          {missingSkills.length > 0 && (
                            <div className="hr-skill-details">
                              <strong>Missing skills</strong>
                              <div className="hr-skill-chips">
                                {missingSkills.map((skill, index) => (
                                  <span className="hr-skill-chip missing" key={`${skill}-${index}`}>{skill}</span>
                                ))}
                              </div>
                            </div>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <p className="hr-help">N/A means the score was not provided by the API. Component scores are not necessarily additive; the final score is the ranking score returned by the backend.</p>
          </>
        )}

        {!busy && !matches.length && (
          <Empty
            icon={BrainCircuit}
            heading={matchingCompleted ? 'No applicants to match yet' : 'Ready to match applicants?'}
            text={matchingCompleted
              ? 'This published job has no eligible applications with resumes yet. Results will appear after students apply and matching is run again.'
              : (publishedJobs.length
                ? 'Choose a published job above and run matching. Draft and closed jobs are not eligible.'
                : 'There are currently no published jobs. Open My Jobs and publish a complete job posting first.')}
          />
        )}
      </>}

      {page === 'Company Profile' && <><div className="hr-section-title"><div><h2>Company profile</h2><p>Company details associated with your recruiter account.</p></div></div><section className="hr-company-card"><Building2 size={30}/><div><h2>{companyName}</h2><p>{profile?.email ?? user?.email ?? '—'}</p></div><div className="hr-profile-fields">{Object.entries(company || profile || {}).filter(([k,v]) => !['id','user_id','created_at','updated_at','password'].includes(k) && ['string','number'].includes(typeof v)).slice(0,12).map(([k,v]) => <div key={k}><small>{k.replaceAll('_',' ')}</small><strong>{String(v) || '—'}</strong></div>)}</div></section><p className="hr-help">Profile editing can be connected after checking the fields accepted by your company API.</p></>}
    </>}
    {jobModalOpen && <div className="hr-modal-backdrop" role="presentation" onMouseDown={e => { if (e.target === e.currentTarget && !savingJob) setJobModalOpen(false) }}><section className="hr-modal" role="dialog" aria-modal="true" aria-labelledby="hr-job-modal-title"><div className="hr-modal-heading"><div><small>JOB MANAGEMENT</small><h2 id="hr-job-modal-title">{editingJob ? 'Edit job posting' : 'Create a job posting'}</h2><p>{editingJob ? 'Update the job details below.' : 'New jobs are saved as drafts until you publish them.'}</p></div><button className="hr-modal-close" disabled={savingJob} onClick={() => setJobModalOpen(false)} aria-label="Close"><X size={19}/></button></div><form onSubmit={saveJob} className="hr-job-form"><label className="wide">Job title *<input required minLength={3} maxLength={255} value={jobForm.title} onChange={e => setJobForm({...jobForm,title:e.target.value})} placeholder="e.g. Junior Python Developer"/></label><label className="wide">Job description *<textarea required minLength={20} rows={5} value={jobForm.description} onChange={e => setJobForm({...jobForm,description:e.target.value})} placeholder="Describe responsibilities, expectations, and the role…"/></label><label>Location<input maxLength={150} value={jobForm.location} onChange={e => setJobForm({...jobForm,location:e.target.value})} placeholder="e.g. Pune, Maharashtra"/></label><label>Remote policy<select value={jobForm.remote_policy} onChange={e => setJobForm({...jobForm,remote_policy:e.target.value})}><option value="ONSITE">On-site</option><option value="HYBRID">Hybrid</option><option value="REMOTE">Remote</option><option value="FLEXIBLE">Flexible</option></select></label><label>Employment type<select value={jobForm.employment_type} onChange={e => setJobForm({...jobForm,employment_type:e.target.value})}><option value="FULL_TIME">Full-time</option><option value="PART_TIME">Part-time</option><option value="CONTRACT">Contract</option><option value="INTERNSHIP">Internship</option><option value="TEMPORARY">Temporary</option></select></label><label>Experience level<select value={jobForm.experience_level} onChange={e => setJobForm({...jobForm,experience_level:e.target.value})}><option value="ENTRY">Entry level</option><option value="JUNIOR">Junior</option><option value="MID">Mid level</option><option value="SENIOR">Senior</option><option value="LEAD">Lead</option><option value="ANY">Any</option></select></label><label>Minimum salary (annual)<input type="number" min="0" step="1000" value={jobForm.salary_min} onChange={e => setJobForm({...jobForm,salary_min:e.target.value})} placeholder="e.g. 300000"/></label><label>Maximum salary (annual)<input type="number" min="0" step="1000" value={jobForm.salary_max} onChange={e => setJobForm({...jobForm,salary_max:e.target.value})} placeholder="e.g. 600000"/></label><label>Required experience (years)<input type="number" min="0" max="60" step="0.5" value={jobForm.required_experience_years} onChange={e => setJobForm({...jobForm,required_experience_years:e.target.value})}/></label><label>Required education<input maxLength={150} value={jobForm.required_education} onChange={e => setJobForm({...jobForm,required_education:e.target.value})} placeholder="e.g. Bachelor's degree"/></label><label>Number of openings<input required type="number" min="1" step="1" value={jobForm.openings} onChange={e => setJobForm({...jobForm,openings:e.target.value})}/></label><div className="hr-modal-actions"><button type="button" className="hr-secondary" disabled={savingJob} onClick={() => setJobModalOpen(false)}>Cancel</button><button type="submit" className="hr-primary" disabled={savingJob}>{savingJob ? 'Saving…' : editingJob ? 'Save changes' : 'Create draft job'}</button></div></form></section></div>}
    {skillsJob && <div className="hr-modal-backdrop" role="presentation" onMouseDown={e => { if (e.target === e.currentTarget && !savingSkill) setSkillsJob(null) }}><section className="hr-modal hr-skills-modal" role="dialog" aria-modal="true" aria-labelledby="hr-skills-modal-title"><div className="hr-modal-heading"><div><small>JOB REQUIREMENTS</small><h2 id="hr-skills-modal-title">Skills · {jobTitle(skillsJob)}</h2><p>Add required or preferred skills to this job posting.</p></div><button className="hr-modal-close" disabled={savingSkill} onClick={() => setSkillsJob(null)} aria-label="Close"><X size={19}/></button></div>{skillsLoading ? <div className="hr-loading">Loading skills…</div> : <><form className="hr-job-form hr-skill-form" onSubmit={addJobSkill}><label className="wide">Skill name *<input required maxLength={100} value={skillForm.name} onChange={e => setSkillForm({...skillForm,name:e.target.value})} placeholder="Enter any skill, e.g. Prompt Engineering" /></label><label className="wide">Category (optional)<input maxLength={100} value={skillForm.category} onChange={e => setSkillForm({...skillForm,category:e.target.value})} placeholder="e.g. AI/ML, Programming, Design, Communication" /></label><label>Requirement<select value={skillForm.requirement_type} onChange={e => setSkillForm({...skillForm,requirement_type:e.target.value})}><option value="REQUIRED">Required</option><option value="PREFERRED">Preferred</option></select></label><label>Minimum years<input type="number" min="0" max="50" step="0.5" value={skillForm.minimum_years} onChange={e => setSkillForm({...skillForm,minimum_years:e.target.value})} placeholder="Optional"/></label><label>Importance weight (0–1)<input required type="number" min="0" max="1" step="0.1" value={skillForm.importance_weight} onChange={e => setSkillForm({...skillForm,importance_weight:e.target.value})}/></label><div className="hr-modal-actions"><button type="submit" className="hr-primary" disabled={savingSkill || !skillForm.name.trim()}>{savingSkill ? 'Creating & adding…' : 'Create skill and add to job'}</button></div></form><div className="hr-current-skills"><h3>Current requirements <span>{jobSkills.length}</span></h3>{jobSkills.length ? <div className="hr-table-wrap"><table className="hr-table"><thead><tr><th>Skill</th><th>Requirement</th><th>Minimum years</th><th>Weight</th><th></th></tr></thead><tbody>{jobSkills.map(s => <tr key={s.skill_id}><td><strong>{s.skill_name ?? `Skill ${s.skill_id}`}</strong></td><td><Badge value={s.requirement_type}/></td><td>{s.minimum_years ?? '—'}</td><td>{s.importance_weight ?? '—'}</td><td><button className="hr-icon-danger" title="Remove skill" onClick={() => removeJobSkill(s)}><Trash2 size={15}/></button></td></tr>)}</tbody></table></div> : <p className="hr-help">No skill requirements added to this job yet.</p>}</div></>}</section></div>}
    </main><style>{CSS + EXTRA_CSS}</style></div>
}

const CSS = `
.hr-app{min-height:100vh;display:flex;background:#080b14;color:#e9edf8;font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif}.hr-app *{box-sizing:border-box}.hr-sidebar{width:245px;flex-shrink:0;background:#0b0f1b;border-right:1px solid #20283a;padding:25px 15px 18px;display:flex;flex-direction:column}.hr-brand{display:flex;align-items:center;gap:10px;padding:0 8px 32px;font-size:19px;font-weight:850;letter-spacing:-.6px}.hr-brand-mark{display:grid;place-items:center;width:38px;height:38px;border-radius:12px;background:linear-gradient(135deg,#8b5cf6,#5b5ce2);color:white;font-size:23px}.hr-brand>div>span{color:#a78bfa}.hr-brand small{display:block;color:#77839c;font-size:8px;letter-spacing:1.3px;margin-top:4px}.hr-sidebar-label{font-size:10px;color:#64708a;font-weight:800;letter-spacing:1.5px;padding-left:12px}.hr-sidebar nav{display:grid;gap:5px}.hr-sidebar nav button{display:flex;align-items:center;gap:11px;width:100%;border:0;border-radius:10px;padding:12px;background:transparent;color:#9aa5bd;text-align:left;font-size:12px;font-weight:650;cursor:pointer}.hr-sidebar nav button:hover,.hr-sidebar nav button.active{background:#211d39;color:#c4b5fd}.hr-sidebar nav button.active{box-shadow:inset 3px 0 #9b87f5}.hr-sidebar nav i{font-style:normal;margin-left:auto;background:#352b52;padding:3px 7px;border-radius:20px}.hr-sidebar-bottom{margin-top:auto;border-top:1px solid #20283a;padding:16px 8px 0}.hr-sidebar-bottom strong,.hr-sidebar-bottom small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.hr-sidebar-bottom strong{font-size:11px}.hr-sidebar-bottom small{color:#77839c;font-size:10px;margin-top:5px}.hr-sidebar-bottom button{display:flex;align-items:center;gap:8px;border:0;background:none;color:#8995ad;padding:18px 0 0;cursor:pointer;font-size:12px}.hr-main{flex:1;min-width:0;max-width:1600px;margin:auto;padding:0 34px 45px}.hr-header{height:98px;border-bottom:1px solid #20283a;display:flex;align-items:center;justify-content:space-between;margin-bottom:28px}.hr-header>div:first-child>small{font-size:9px;letter-spacing:1.7px;color:#a78bfa;font-weight:800}.hr-header h1{font-size:25px;margin:5px 0 0;letter-spacing:-.8px}.hr-header-right{display:flex;align-items:center;gap:13px}.hr-refresh{width:37px;height:37px;display:grid;place-items:center;border-radius:10px;border:1px solid #293249;background:#111827;color:#aab5cb;cursor:pointer}.hr-avatar{width:35px;height:35px;display:grid;place-items:center;border-radius:50%;background:#2a2349;color:#d6ccff;font-weight:800}.hr-hero{display:flex;justify-content:space-between;align-items:center;min-height:270px;padding:29px 34px;border:1px solid #30294e;border-radius:18px;background:radial-gradient(ellipse at 85% 45%,#282147,transparent 45%),linear-gradient(115deg,#151526,#101526);overflow:hidden}.hr-tag{font-size:9px;letter-spacing:1.2px;color:#c4b5fd;border:1px solid #514276;border-radius:30px;padding:7px 10px}.hr-hero h2{font-size:34px;line-height:1.18;letter-spacing:-1.4px;margin:20px 0 10px}.hr-hero h2 em{font-style:normal;color:#a99afa}.hr-hero p{font-size:12px;line-height:1.7;color:#9aa5bd;max-width:450px;margin:0 0 18px}.hr-hero-art{width:155px;height:155px;border:1px solid #6253a855;border-radius:36px;display:grid;place-items:center;background:#282044;color:#c4b5fd;box-shadow:0 0 65px #8b5cf633;margin-right:50px;transform:rotate(8deg)}.hr-primary{display:inline-flex;align-items:center;justify-content:center;gap:7px;border:0;border-radius:9px;padding:11px 15px;background:linear-gradient(135deg,#8b5cf6,#6961e8);color:white;font-size:11px;font-weight:750;cursor:pointer}.hr-primary:disabled{opacity:.5;cursor:not-allowed}.hr-stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:20px 0 30px}.hr-stats article{padding:18px;border:1px solid #20283a;border-radius:13px;background:#0e1320}.hr-stats article>svg{width:20px;height:20px;color:#b6a7ff;margin-bottom:12px}.hr-stats small{display:block;color:#97a3ba;font-size:11px}.hr-stats strong{display:block;font-size:29px;letter-spacing:-1px;margin:5px 0}.hr-stats p{font-size:10px;color:#75819a;margin:0}.hr-section-title{display:flex;justify-content:space-between;align-items:center;gap:14px;margin:23px 0 15px}.hr-section-title h2{font-size:16px;margin:0 0 5px}.hr-section-title p{font-size:11px;color:#8490a8;margin:0}.hr-section-title>button{border:0;background:none;color:#b6a7ff;cursor:pointer;font-size:11px}.hr-count{border:1px solid #30294e;background:#19172b;color:#c4b5fd;border-radius:30px;padding:7px 11px;font-size:10px}.hr-table-wrap{overflow-x:auto;border:1px solid #20283a;border-radius:12px;background:#0d121e}.hr-table{width:100%;border-collapse:collapse;text-align:left;white-space:nowrap}.hr-table th{padding:13px 15px;color:#74819b;font-size:9px;text-transform:uppercase;letter-spacing:1px;background:#101624;border-bottom:1px solid #20283a}.hr-table td{padding:14px 15px;border-bottom:1px solid #1b2232;color:#aab4c9;font-size:11px}.hr-table tbody tr:last-child td{border-bottom:0}.hr-table td strong{display:block;color:#e4e9f5;font-size:11px}.hr-table td small{display:block;color:#75819a;font-size:10px;margin-top:4px}.hr-badge{display:inline-block;text-transform:capitalize;border-radius:30px;padding:5px 8px;background:#202638;color:#aeb9d0;font-size:9px;font-weight:750}.hr-badge.published,.hr-badge.open,.hr-badge.active,.hr-badge.accepted,.hr-badge.hired{background:#15352e;color:#86efac}.hr-badge.draft,.hr-badge.pending,.hr-badge.under-review{background:#352b1e;color:#fcd34d}.hr-badge.closed,.hr-badge.rejected,.hr-badge.inactive{background:#38222a;color:#fda4af}.hr-actions{display:flex;align-items:center;gap:5px}.hr-actions button{height:29px;display:flex;align-items:center;justify-content:center;gap:4px;padding:0 8px;border:1px solid #293249;background:#131a29;border-radius:8px;color:#a9b5cf;cursor:pointer;font-size:10px}.hr-actions button:hover{border-color:#7967d8;color:#c4b5fd}.hr-search{display:flex;align-items:center;gap:10px;max-width:500px;margin-bottom:16px;padding:0 13px;height:43px;border:1px solid #283047;border-radius:10px;background:#0e1320;color:#7f8ba4}.hr-search input{width:100%;border:0;outline:0;background:transparent;color:#e9edf8;font-size:12px}.hr-help{font-size:10px;color:#74819b;margin-top:14px}.hr-empty{min-height:210px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;border:1px dashed #2a3348;border-radius:13px;background:#0d121e;padding:28px}.hr-empty>span{width:49px;height:49px;display:grid;place-items:center;border-radius:14px;background:#211d39;color:#b6a7ff}.hr-empty h3{font-size:14px;margin:14px 0 6px}.hr-empty p{font-size:11px;line-height:1.6;color:#8490a8;max-width:390px;margin:0}.hr-alert{display:flex;align-items:center;gap:9px;border-radius:9px;padding:12px 14px;font-size:12px;margin-bottom:14px}.hr-alert button{margin-left:auto;background:none;border:0;color:inherit;font-size:20px;cursor:pointer}.hr-alert.error{background:#351b25;border:1px solid #673044;color:#fda4af}.hr-alert.success{background:#15302b;border:1px solid #245848;color:#86efac}.hr-loading{min-height:250px;display:grid;place-items:center;color:#8e9ab2;font-size:12px}.hr-match-box{display:flex;align-items:center;gap:17px;padding:22px;border:1px solid #30294e;border-radius:14px;background:linear-gradient(110deg,#151526,#101526);margin-bottom:20px;color:#c4b5fd;flex-wrap:wrap}.hr-match-box>div{flex:1;min-width:190px}.hr-match-box strong{display:block;color:#e9edf8;font-size:13px}.hr-match-box p{font-size:11px;line-height:1.6;color:#8490a8;margin:6px 0 0}.hr-match-box select{min-width:170px;max-width:260px;flex:1;background:#0c1120;color:#e9edf8;border:1px solid #303950;border-radius:8px;padding:10px;font-size:11px}.hr-score{color:#86efac!important}.hr-company-card{display:grid;grid-template-columns:45px 1fr;align-items:center;gap:14px;border:1px solid #20283a;border-radius:14px;background:#0e1320;padding:24px}.hr-company-card>svg{color:#c4b5fd}.hr-company-card h2{font-size:16px;margin:0 0 5px}.hr-company-card p{font-size:11px;color:#8490a8;margin:0}.hr-profile-fields{grid-column:1/-1;border-top:1px solid #222a3b;padding-top:17px;margin-top:10px;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.hr-profile-fields small{display:block;color:#75819a;text-transform:capitalize;font-size:10px;margin-bottom:5px}.hr-profile-fields strong{overflow-wrap:anywhere;font-size:11px}.hr-app button:focus-visible{outline:2px solid #a78bfa;outline-offset:2px}.hr-status-control{display:flex;align-items:center;gap:8px}.hr-status-control select{max-width:155px;border:1px solid #303950;border-radius:8px;background:#090e19;color:#dbe2f2;padding:7px 8px;font:inherit;font-size:10px;cursor:pointer}.hr-status-control select:disabled{opacity:.55;cursor:wait}.hr-resume-button{display:inline-flex;align-items:center;gap:6px;padding:7px 10px;border:1px solid #514276;border-radius:8px;background:#211d39;color:#c4b5fd;font-size:10px;font-weight:700;cursor:pointer;white-space:nowrap}.hr-resume-button:hover{border-color:#9b87f5;background:#2b2450}
@media(max-width:1000px){.hr-sidebar{width:210px}.hr-main{padding:0 20px 35px}.hr-stats{grid-template-columns:repeat(2,minmax(0,1fr))}.hr-hero-art{margin-right:5px}}
@media(max-width:700px){.hr-app{display:block}.hr-sidebar{width:100%;padding:13px;border-right:0;border-bottom:1px solid #20283a}.hr-brand{padding:0 5px 13px}.hr-sidebar-label,.hr-sidebar-bottom{display:none}.hr-sidebar nav{display:flex;overflow-x:auto}.hr-sidebar nav button{white-space:nowrap;flex-shrink:0;width:auto;padding:10px;font-size:11px}.hr-main{padding:0 13px 30px}.hr-header{height:75px;margin-bottom:17px}.hr-header h1{font-size:21px}.hr-hero{padding:22px;min-height:0}.hr-hero h2{font-size:27px}.hr-hero-art{display:none}.hr-stats{gap:9px}.hr-stats article{padding:13px}.hr-stats article strong{font-size:25px}.hr-profile-fields{grid-template-columns:repeat(2,minmax(0,1fr))}.hr-match-box select,.hr-match-box .hr-primary{width:100%;max-width:none}.hr-section-title{align-items:flex-start}}
`


const EXTRA_CSS = `
.hr-title-actions{display:flex;align-items:center;gap:10px}.hr-modal-backdrop{position:fixed;inset:0;z-index:1000;display:flex;align-items:center;justify-content:center;padding:20px;background:rgba(2,5,12,.78);backdrop-filter:blur(7px);overflow-y:auto}.hr-modal{width:min(760px,100%);max-height:calc(100vh - 40px);overflow-y:auto;border:1px solid #343052;border-radius:17px;background:#0c1120;box-shadow:0 24px 90px #0009;padding:24px}.hr-modal-heading{display:flex;justify-content:space-between;gap:15px;align-items:flex-start;margin-bottom:22px}.hr-modal-heading small{font-size:9px;letter-spacing:1.5px;color:#b6a7ff;font-weight:800}.hr-modal-heading h2{font-size:21px;margin:7px 0}.hr-modal-heading p{font-size:11px;color:#8490a8;margin:0}.hr-modal-close{flex-shrink:0;width:34px;height:34px;display:grid;place-items:center;border:1px solid #303950;border-radius:9px;background:#131a29;color:#aab5cb;cursor:pointer}.hr-job-form{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px}.hr-job-form label{display:flex;flex-direction:column;gap:7px;font-size:11px;color:#aeb9d0}.hr-job-form label.wide{grid-column:1/-1}.hr-job-form input,.hr-job-form textarea,.hr-job-form select{width:100%;min-width:0;border:1px solid #303950;border-radius:8px;background:#090e19;color:#e9edf8;padding:11px 12px;font:inherit;font-size:12px;outline:none}.hr-job-form textarea{resize:vertical;line-height:1.6}.hr-job-form input:focus,.hr-job-form textarea:focus,.hr-job-form select:focus{border-color:#8b78ed;box-shadow:0 0 0 2px #8b78ed22}.hr-modal-actions{grid-column:1/-1;display:flex;justify-content:flex-end;gap:10px;padding-top:8px;border-top:1px solid #20283a;margin-top:3px}.hr-secondary{border:1px solid #303950;border-radius:9px;padding:10px 15px;background:#131a29;color:#c5cde0;font-size:11px;cursor:pointer}.hr-current-skills{margin-top:24px}.hr-current-skills h3{font-size:13px;margin:0 0 12px}.hr-current-skills h3 span{margin-left:7px;color:#b6a7ff}.hr-icon-danger{display:grid;place-items:center;border:1px solid #673044;border-radius:7px;background:#351b25;color:#fda4af;padding:7px;cursor:pointer}.hr-skills-modal{width:min(800px,100%)}.hr-skill-form{padding:16px;border:1px solid #20283a;border-radius:12px;background:#0e1320}.hr-skill-form .hr-modal-actions{border-top:0;margin-top:0}.hr-modal button:disabled{opacity:.55;cursor:not-allowed}@media(max-width:700px){.hr-modal-backdrop{padding:8px;align-items:flex-start}.hr-modal{max-height:calc(100vh - 16px);padding:17px}.hr-job-form{grid-template-columns:1fr}.hr-job-form label.wide,.hr-modal-actions{grid-column:1}.hr-title-actions{align-items:flex-end;flex-direction:column}.hr-title-actions .hr-primary{white-space:nowrap}}

.hr-match-summary{display:flex;justify-content:space-between;gap:12px;margin:18px 0 10px;color:#8490a8;font-size:11px}
.hr-match-summary strong{color:#c4b5fd;font-size:14px;margin-right:4px}
.hr-matching-table{min-width:1250px}
.hr-matching-table th{white-space:nowrap}
.hr-matching-table td{vertical-align:top}
.hr-matching-table td:nth-child(2){min-width:175px}
.hr-matching-table td:nth-child(3){font-size:13px}
.hr-match-explanation{min-width:330px;max-width:470px;white-space:normal!important;line-height:1.7}
.hr-rank-badge{display:inline-grid;place-items:center;min-width:30px;height:30px;border-radius:9px;background:#211d39;color:#c4b5fd;font-weight:800}
.hr-skill-details{margin-top:10px;padding:9px;border:1px solid #293249;border-radius:8px;background:#111827}
.hr-skill-details>strong{display:block;color:#a99afa;font-size:10px;margin-bottom:7px}
.hr-skill-chips{display:flex;flex-wrap:wrap;gap:5px}
.hr-skill-chip{display:inline-block;padding:4px 7px;border-radius:20px;font-size:9px;font-weight:700}
.hr-skill-chip.matched{background:#15352e;color:#86efac}
.hr-skill-chip.missing{background:#38222a;color:#fda4af}
@media(max-width:700px){.hr-match-summary{flex-direction:column;gap:5px}}

`
