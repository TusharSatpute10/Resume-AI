import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'

import Login from './pages/Login'
import Register from './pages/Register'
import StudentDashboard from './pages/StudentDashboard'
import HRDashboard from './pages/HRDashboard'

function DashboardRouter() {
  const { user } = useAuth()

  const role = String(user?.role || '').toUpperCase()

  // Student dashboard
  if (role === 'STUDENT') {
    return <StudentDashboard />
  }

  // HR dashboard
  if (role === 'HR') {
    return <HRDashboard />
  }

  // Fallback for unknown roles
  return (
    <div className="dashboard-placeholder">
      <h1>Welcome to ResumeAI</h1>
      <p>Your dashboard will be available here next.</p>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      {/* Redirect home to dashboard */}
      <Route
        path="/"
        element={<Navigate to="/dashboard" replace />}
      />

      {/* Authentication pages */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* Protected dashboard */}
      <Route element={<ProtectedRoute />}>
        <Route
          path="/dashboard"
          element={<DashboardRouter />}
        />
      </Route>

      {/* Redirect unknown routes */}
      <Route
        path="*"
        element={<Navigate to="/" replace />}
      />
    </Routes>
  )
}