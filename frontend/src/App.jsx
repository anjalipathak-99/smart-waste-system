import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/Login'
import Register from './pages/Register'
import AdminDashboard from './pages/AdminDashboard'
import WorkerPortal from './pages/WorkerPortal'
import CitizenPortal from './pages/CitizenPortal'
import ClassifyWaste from './pages/ClassifyWaste'
import { useAuth } from './context/AuthContext'

const ROLE_HOME = { admin: '/admin', worker: '/worker', citizen: '/citizen' }

function Home() {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  return <Navigate to={ROLE_HOME[user.role]} replace />
}

export default function App() {
  const { user } = useAuth()
  return (
    <>
      {user && <Navbar />}
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/" element={<Home />} />

        <Route path="/admin" element={
          <ProtectedRoute roles={['admin']}><AdminDashboard /></ProtectedRoute>
        } />
        <Route path="/worker" element={
          <ProtectedRoute roles={['worker']}><WorkerPortal /></ProtectedRoute>
        } />
        <Route path="/citizen" element={
          <ProtectedRoute roles={['citizen']}><CitizenPortal /></ProtectedRoute>
        } />
        <Route path="/classify" element={
          <ProtectedRoute roles={['admin', 'worker', 'citizen']}><ClassifyWaste /></ProtectedRoute>
        } />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  )
}
