import { useEffect, useState } from 'react'
import {
  CalendarDays, Clock, Video, MapPin, Link as LinkIcon,
  RefreshCw, XCircle, CheckCircle2, Users
} from 'lucide-react'
import api from '../services/api'

const list = (data) => Array.isArray(data) ? data : data?.items || []

const formatDate = (value) => {
  if (!value) return 'Not specified'
  return new Date(value).toLocaleString([], {
    dateStyle: 'medium',
    timeStyle: 'short'
  })
}

const label = (value) =>
  String(value || '').replaceAll('_', ' ').toLowerCase()
    .replace(/\b\w/g, c => c.toUpperCase())

export default function InterviewCenter({ mode, applications = [] }) {
  const isHR = mode === 'hr'

  const [interviews, setInterviews] = useState([])
  const [selected, setSelected] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const [form, setForm] = useState({
    scheduled_at: '',
    duration_minutes: 30,
    round_name: 'Technical Round',
    interview_type: 'ONLINE',
    meeting_link: '',
    venue: '',
    instructions: ''
  })

  async function loadInterviews() {
    setLoading(true)
    setError('')

    try {
      const response = await api.get(
        isHR ? '/interviews/hr' : '/interviews/me'
      )
      setInterviews(list(response.data))
    } catch (e) {
      setError(
        e.response?.data?.detail ||
        'Unable to load interviews.'
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadInterviews()
  }, [isHR])

  const shortlisted = applications.filter(
    a => String(a.status).toUpperCase() === 'SHORTLISTED'
  )

  function updateForm(key, value) {
    setForm(current => ({ ...current, [key]: value }))
  }

  function toggleCandidate(id) {
    setSelected(current =>
      current.includes(id)
        ? current.filter(item => item !== id)
        : [...current, id]
    )
  }

  async function scheduleInterviews(e) {
    e.preventDefault()
    setError('')
    setNotice('')

    if (!selected.length) {
      setError('Select at least one shortlisted candidate.')
      return
    }

    if (!form.scheduled_at) {
      setError('Select an interview date and time.')
      return
    }

    if (new Date(form.scheduled_at) <= new Date()) {
      setError('Interview must be scheduled in the future.')
      return
    }

    if (form.interview_type === 'OFFLINE' && !form.venue.trim()) {
      setError('Enter the offline interview venue.')
      return
    }

    if (form.interview_type === 'ONLINE' && form.venue.trim()) {
      setError('Online interviews cannot have a venue.')
      return
    }

    if (form.interview_type === 'OFFLINE' && form.meeting_link.trim()) {
      setError('Offline interviews cannot have a meeting link.')
      return
    }

    const payload = {
      interviews: selected.map(applicationId => ({
        application_id: applicationId,
        scheduled_at: form.scheduled_at,
        duration_minutes: Number(form.duration_minutes),
        round_name: form.round_name,
        interview_type: form.interview_type,
        meeting_link: form.meeting_link.trim() || null,
        venue: form.venue.trim() || null,
        instructions: form.instructions.trim() || null
      }))
    }

    setSaving(true)

    try {
      await api.post('/interviews/bulk', payload)

      setNotice(
        `${selected.length} interview(s) scheduled successfully.`
      )

      setSelected([])
      await loadInterviews()
    } catch (e) {
      const detail = e.response?.data?.detail
      setError(
        typeof detail === 'string'
          ? detail
          : 'Could not schedule interviews. Check the selected applications.'
      )
    } finally {
      setSaving(false)
    }
  }

  async function reschedule(interview) {
    const date = window.prompt(
      'Enter the new date and time (YYYY-MM-DDTHH:mm):'
    )

    if (!date) return

    if (new Date(date) <= new Date()) {
      setError('New interview time must be in the future.')
      return
    }

    try {
      await api.patch(`/interviews/${interview.id}`, {
        scheduled_at: date
      })

      setNotice('Interview rescheduled successfully.')
      await loadInterviews()
    } catch (e) {
      setError(e.response?.data?.detail || 'Rescheduling failed.')
    }
  }

  async function addMeetingLink(interview) {
    const link = window.prompt('Enter the online meeting link:')

    if (!link?.trim()) return

    try {
      await api.patch(
        `/interviews/${interview.id}/meeting-link`,
        { meeting_link: link.trim() }
      )

      setNotice('Meeting link updated and notification sent.')
      await loadInterviews()
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not update meeting link.')
    }
  }

  async function cancelInterview(interview) {
    if (!window.confirm('Are you sure you want to cancel this interview?')) {
      return
    }

    try {
      await api.patch(`/interviews/${interview.id}/cancel`)

      setNotice('Interview cancelled and notification sent.')
      await loadInterviews()
    } catch (e) {
      setError(e.response?.data?.detail || 'Cancellation failed.')
    }
  }

  return (
    <div className="ic-container">

      <div className="ic-heading">
        <div>
          <span className="ic-kicker">
            {isHR ? 'RECRUITMENT MANAGEMENT' : 'YOUR INTERVIEW SCHEDULE'}
          </span>

          <h2>
            {isHR ? 'Interview Management' : 'My Interviews'}
          </h2>

          <p>
            {isHR
              ? 'Schedule, manage and track candidate interviews.'
              : 'View your upcoming interviews and meeting details.'}
          </p>
        </div>

        <button className="ic-refresh" onClick={loadInterviews}>
          <RefreshCw size={16} /> Refresh
        </button>
      </div>

      {error && <div className="ic-message error">{error}</div>}
      {notice && <div className="ic-message success">{notice}</div>}

      {isHR && (
        <>
          <section className="ic-card">
            <div className="ic-section-heading">
              <div>
                <h3><Users size={19}/> Shortlisted Candidates</h3>
                <p>Select candidates for bulk interview scheduling.</p>
              </div>

              <span className="ic-count">
                {shortlisted.length} shortlisted
              </span>
            </div>

            {shortlisted.length === 0 ? (
              <p className="ic-empty">
                No shortlisted candidates available.
                Shortlist applicants from the Applicants section first.
              </p>
            ) : (
              <div className="ic-candidates">
                {shortlisted.map(a => {
                  const id = Number(a.id ?? a.application_id)

                  return (
                    <label className="ic-candidate" key={id}>
                      <input
                        type="checkbox"
                        checked={selected.includes(id)}
                        onChange={() => toggleCandidate(id)}
                      />

                      <span>
                        <strong>{a.student_name || 'Candidate'}</strong>
                        <small>
                          {a.student_email || a.email || ''}
                        </small>
                        <small>
                          {a.job_title || 'Job application'}
                        </small>
                      </span>
                    </label>
                  )
                })}
              </div>
            )}
          </section>

          <section className="ic-card">
            <h3><CalendarDays size={19}/> Schedule Interviews</h3>

            <form onSubmit={scheduleInterviews} className="ic-form">

              <label>
                Interview date and time *
                <input
                  type="datetime-local"
                  required
                  value={form.scheduled_at}
                  onChange={e => updateForm('scheduled_at', e.target.value)}
                />
              </label>

              <label>
                Duration (minutes) *
                <input
                  type="number"
                  min="5"
                  max="480"
                  required
                  value={form.duration_minutes}
                  onChange={e =>
                    updateForm('duration_minutes', e.target.value)
                  }
                />
              </label>

              <label>
                Interview round *
                <input
                  required
                  value={form.round_name}
                  onChange={e => updateForm('round_name', e.target.value)}
                />
              </label>

              <label>
                Interview mode *
                <select
                  value={form.interview_type}
                  onChange={e =>
                    setForm(current => ({
                      ...current,
                      interview_type: e.target.value,
                      venue: '',
                      meeting_link: ''
                    }))
                  }
                >
                  <option value="ONLINE">Online</option>
                  <option value="OFFLINE">Offline</option>
                </select>
              </label>

              {form.interview_type === 'ONLINE' ? (
                <label className="wide">
                  Meeting link (optional)
                  <input
                    type="url"
                    placeholder="https://meet.google.com/..."
                    value={form.meeting_link}
                    onChange={e =>
                      updateForm('meeting_link', e.target.value)
                    }
                  />
                </label>
              ) : (
                <label className="wide">
                  Interview venue *
                  <input
                    required
                    value={form.venue}
                    onChange={e => updateForm('venue', e.target.value)}
                    placeholder="Office address / meeting room"
                  />
                </label>
              )}

              <label className="wide">
                Instructions
                <textarea
                  rows="3"
                  value={form.instructions}
                  onChange={e =>
                    updateForm('instructions', e.target.value)
                  }
                  placeholder="Additional instructions for candidates..."
                />
              </label>

              <div className="ic-form-footer">
                <span>{selected.length} candidate(s) selected</span>

                <button
                  className="ic-primary"
                  disabled={saving || !selected.length}
                >
                  {saving ? 'Scheduling...' : 'Schedule Interviews'}
                </button>
              </div>

            </form>
          </section>
        </>
      )}

      <section className="ic-card">
        <div className="ic-section-heading">
          <div>
            <h3>
              <CalendarDays size={19}/>
              {isHR ? 'Scheduled Interviews' : 'Your Interview Schedule'}
            </h3>
            <p>
              {interviews.length} interview record(s)
            </p>
          </div>
        </div>

        {loading ? (
          <p className="ic-empty">Loading interviews...</p>
        ) : interviews.length === 0 ? (
          <p className="ic-empty">
            {isHR
              ? 'No interviews scheduled yet.'
              : 'You do not have any scheduled interviews.'}
          </p>
        ) : (
          <div className="ic-list">
            {interviews.map(interview => (
              <article className="ic-interview" key={interview.id}>

                <div className="ic-interview-top">
                  <div>
                    <span className="ic-round">
                      {interview.round_name || 'Interview'}
                    </span>

                    <h3>
                      {interview.job_title || 'Interview'}
                    </h3>

                    <p>
                      {isHR
                        ? `${interview.student_name || 'Candidate'} · ${interview.student_email || ''}`
                        : interview.company_name || 'Company'}
                    </p>
                  </div>

                  <span className={`ic-status ${String(interview.status).toLowerCase()}`}>
                    {label(interview.status)}
                  </span>
                </div>

                <div className="ic-details">
                  <span>
                    <CalendarDays size={16}/>
                    {formatDate(interview.scheduled_at)}
                  </span>

                  <span>
                    <Clock size={16}/>
                    {interview.duration_minutes} minutes
                  </span>

                  <span>
                    {interview.interview_type === 'ONLINE'
                      ? <Video size={16}/>
                      : <MapPin size={16}/>}
                    {label(interview.interview_type)}
                  </span>
                </div>

                {interview.interview_type === 'ONLINE' ? (
                  <div className="ic-location">
                    <LinkIcon size={16}/>

                    {interview.meeting_link_status === 'AVAILABLE' &&
                    interview.meeting_link ? (
                      <a
                        href={interview.meeting_link}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Join interview
                      </a>
                    ) : (
                      <span>Meeting link pending. Recruiter will share it.</span>
                    )}
                  </div>
                ) : (
                  <div className="ic-location">
                    <MapPin size={16}/>
                    {interview.venue || 'Venue pending'}
                  </div>
                )}

                {interview.instructions && (
                  <p className="ic-instructions">
                    {interview.instructions}
                  </p>
                )}

                {isHR && interview.status === 'SCHEDULED' && (
                  <div className="ic-actions">
                    <button onClick={() => reschedule(interview)}>
                      <RefreshCw size={14}/> Reschedule
                    </button>

                    {interview.interview_type === 'ONLINE' && (
                      <button onClick={() => addMeetingLink(interview)}>
                        <LinkIcon size={14}/> Add meeting link
                      </button>
                    )}

                    <button
                      className="danger"
                      onClick={() => cancelInterview(interview)}
                    >
                      <XCircle size={14}/> Cancel
                    </button>
                  </div>
                )}

              </article>
            ))}
          </div>
        )}
      </section>

      <style>{`
        .ic-container{display:flex;flex-direction:column;gap:18px;color:#e9edf8}
        .ic-heading,.ic-section-heading,.ic-interview-top{display:flex;justify-content:space-between;align-items:center;gap:14px}
        .ic-kicker{font-size:10px;letter-spacing:1.5px;color:#a99afa;font-weight:800}
        .ic-heading h2{font-size:24px;margin:7px 0}
        .ic-heading p,.ic-section-heading p{font-size:12px;color:#8490a8;margin:0}
        .ic-card{padding:20px;border:1px solid #283047;border-radius:14px;background:#0e1320}
        .ic-card h3{display:flex;align-items:center;gap:9px;font-size:15px;margin:0 0 7px}
        .ic-section-heading{margin-bottom:17px}
        .ic-count{padding:7px 11px;border-radius:20px;background:#211d39;color:#c4b5fd;font-size:11px}
        .ic-refresh,.ic-actions button{display:flex;align-items:center;gap:7px;padding:9px 12px;border:1px solid #303950;border-radius:8px;background:#131a29;color:#c4b5fd;cursor:pointer;font-size:11px}
        .ic-candidates{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}
        .ic-candidate{display:flex;gap:11px;padding:13px;border:1px solid #283047;border-radius:9px;background:#101624;cursor:pointer}
        .ic-candidate input{accent-color:#8b5cf6}
        .ic-candidate strong,.ic-candidate small{display:block}
        .ic-candidate strong{font-size:12px}
        .ic-candidate small{font-size:10px;color:#8490a8;margin-top:4px}
        .ic-form{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-top:18px}
        .ic-form label{display:flex;flex-direction:column;gap:7px;font-size:11px;color:#aeb9d0}
        .ic-form .wide{grid-column:1/-1}
        .ic-form input,.ic-form select,.ic-form textarea{width:100%;padding:11px;border:1px solid #303950;border-radius:8px;background:#090e19;color:#e9edf8;font:inherit;font-size:12px;min-width:0}
        .ic-form-footer{grid-column:1/-1;display:flex;align-items:center;justify-content:space-between;gap:12px;border-top:1px solid #283047;padding-top:15px}
        .ic-form-footer span{font-size:11px;color:#aeb9d0}
        .ic-primary{padding:11px 16px;border:0;border-radius:8px;background:#7959e8;color:white;font-weight:700;cursor:pointer}
        .ic-primary:disabled{opacity:.5;cursor:not-allowed}
        .ic-message{padding:12px 14px;border-radius:9px;font-size:12px}
        .ic-message.error{background:#351b25;color:#fda4af}
        .ic-message.success{background:#15302b;color:#86efac}
        .ic-empty{padding:25px;text-align:center;color:#8490a8;font-size:12px}
        .ic-list{display:flex;flex-direction:column;gap:12px}
        .ic-interview{padding:17px;border:1px solid #283047;border-radius:12px;background:#101624}
        .ic-round{font-size:10px;color:#c4b5fd}
        .ic-interview-top h3{margin:6px 0;font-size:15px}
        .ic-interview-top p{font-size:11px;color:#8490a8;margin:0}
        .ic-status{font-size:10px;padding:6px 10px;border-radius:20px;background:#263047;color:#cbd5e1}
        .ic-status.scheduled{background:#15352e;color:#86efac}
        .ic-status.cancelled{background:#38222a;color:#fda4af}
        .ic-status.completed{background:#202638;color:#aeb9d0}
        .ic-details{display:flex;flex-wrap:wrap;gap:18px;margin-top:17px}
        .ic-details span,.ic-location{display:flex;align-items:center;gap:7px;font-size:11px;color:#aeb9d0}
        .ic-location{margin-top:13px}
        .ic-location a{color:#a99afa}
        .ic-instructions{font-size:11px;color:#8490a8;white-space:pre-wrap;margin-top:13px}
        .ic-actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px;padding-top:13px;border-top:1px solid #283047}
        .ic-actions button.danger{color:#fda4af;border-color:#673044}
        @media(max-width:650px){.ic-candidates,.ic-form{grid-template-columns:1fr}.ic-form .wide,.ic-form-footer{grid-column:1}.ic-heading,.ic-section-heading{align-items:flex-start;flex-wrap:wrap}.ic-form-footer{flex-wrap:wrap}}
      `}</style>
    </div>
  )
}