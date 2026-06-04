import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Layout from './components/Layout';

import Login from './pages/Login';
import Register from './pages/Register';

import AdminDashboard from './pages/admin/Dashboard';
import AdminPlans from './pages/admin/Plans';
import AdminTenants from './pages/admin/Tenants';
import AdminHealth from './pages/admin/Health';
import AdminAudit from './pages/admin/Audit';

import ClientDashboard from './pages/client/Dashboard';
import ClientCollector from './pages/client/Collector';
import ClientChannels from './pages/client/Channels';
import ClientUsage from './pages/client/Usage';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          {/* Admin routes */}
          <Route
            path="/tenants"
            element={
              <ProtectedRoute requireAdmin>
                <Layout><AdminTenants /></Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/plans"
            element={
              <ProtectedRoute requireAdmin>
                <Layout><AdminPlans /></Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/health"
            element={
              <ProtectedRoute requireAdmin>
                <Layout><AdminHealth /></Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/audit"
            element={
              <ProtectedRoute requireAdmin>
                <Layout><AdminAudit /></Layout>
              </ProtectedRoute>
            }
          />

          {/* Client routes */}
          <Route
            path="/collector"
            element={
              <ProtectedRoute>
                <Layout><ClientCollector /></Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/channels"
            element={
              <ProtectedRoute>
                <Layout><ClientChannels /></Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/usage"
            element={
              <ProtectedRoute>
                <Layout><ClientUsage /></Layout>
              </ProtectedRoute>
            }
          />

          {/* Root — redirect based on role */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout>
                  <AuthBasedRedirect />
                </Layout>
              </ProtectedRoute>
            }
          />

          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

function AuthBasedRedirect() {
  const { isAdmin } = useAuth();
  return isAdmin ? <AdminDashboard /> : <ClientDashboard />;
}
