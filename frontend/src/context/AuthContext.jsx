import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react'

import {
  getCurrentUser,
  loginUser,
  registerUser,
} from '../services/auth'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const refreshUser = useCallback(async () => {
    const token = localStorage.getItem('resumeai_token')

    if (!token) {
      setUser(null)
      setLoading(false)
      return
    }

    try {
      const currentUser = await getCurrentUser()
      setUser(currentUser.user ?? currentUser)
    } catch {
      localStorage.removeItem('resumeai_token')
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refreshUser()
  }, [refreshUser])

  async function login(credentials) {
    const result = await loginUser(credentials)

    const token =
      result.access_token ??
      result.token ??
      result.data?.access_token

    if (!token) {
      throw new Error(
        'Login response did not contain an access token. Check the backend response schema.',
      )
    }

    localStorage.setItem('resumeai_token', token)

    const currentUser = await getCurrentUser()
    setUser(currentUser.user ?? currentUser)

    return currentUser
  }

  async function register(userData) {
    return registerUser(userData)
  }

  function logout() {
    localStorage.removeItem('resumeai_token')
    setUser(null)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)

  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider')
  }

  return context
}