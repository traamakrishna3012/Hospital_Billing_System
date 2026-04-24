import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { useAuthStore } from './store/authStore';
import DashboardLayout from './layouts/DashboardLayout';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import PatientsPage from './pages/PatientsPage';
import DoctorsPage from './pages/DoctorsPage';
import TestsPage from './pages/TestsPage';
import BillingPage from './pages/BillingPage';
import SettingsPage from './pages/SettingsPage';
import StaffPage from './pages/StaffPage';
import ReportsPage from './pages/ReportsPage';
import SuperAdminDashboard from './pages/SuperAdminDashboard';
import SuperAdminTenantsPage from './pages/SuperAdminTenantsPage';
import SuperAdminRevenuePage from './pages/SuperAdminRevenuePage';
import SuperAdminSettingsPage from './pages/SuperAdminSettingsPage';


import PendingApprovalPage from './pages/PendingApprovalPage';

function ProtectedRoute({ children }) {
  const { isAuthenticated, user, isSuperAdmin } = useAuthStore();
  
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  
  // Super Admins bypass approval check
  if (isSuperAdmin()) return children;

  // Scoped check for clinic approval
  if (!user?.is_approved) {
    return <Navigate to="/pending-approval" replace />;
  }
  
  return children;
}

function SuperAdminRoute({ children }) {
  const { isAuthenticated, isSuperAdmin } = useAuthStore();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (!isSuperAdmin()) return <Navigate to="/dashboard" replace />;
  return children;
}

function PublicRoute({ children }) {
  const { isAuthenticated, isSuperAdmin, user } = useAuthStore();
  if (isAuthenticated) {
    if (isSuperAdmin()) return <Navigate to="/super/dashboard" replace />;
    if (user?.is_approved === false) return <Navigate to="/pending-approval" replace />;
    return <Navigate to="/dashboard" replace />;
  }
  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            borderRadius: '12px',
            background: '#1e293b',
            color: '#f8fafc',
            fontSize: '14px',
          },
          duration: 3000,
        }}
      />
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={<PublicRoute><LoginPage /></PublicRoute>} />
        <Route path="/register" element={<PublicRoute><RegisterPage /></PublicRoute>} />
        <Route path="/pending-approval" element={<PendingApprovalPage />} />

        {/* Protected Clinic Routes */}
        <Route path="/" element={<ProtectedRoute><DashboardLayout /></ProtectedRoute>}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="patients" element={<PatientsPage />} />
          <Route path="doctors" element={<DoctorsPage />} />
          <Route path="tests" element={<TestsPage />} />
          <Route path="billing" element={<BillingPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="staff" element={<StaffPage />} />
          <Route path="reports" element={<ReportsPage />} />
          
          {/* Super Admin Section (Inside same layout but with SuperAdminRoute wrapper) */}
          <Route path="super/dashboard" element={<SuperAdminRoute><SuperAdminDashboard /></SuperAdminRoute>} />
          <Route path="super/tenants" element={<SuperAdminRoute><SuperAdminTenantsPage /></SuperAdminRoute>} />
          <Route path="super/revenue" element={<SuperAdminRoute><SuperAdminRevenuePage /></SuperAdminRoute>} />
          <Route path="super/settings" element={<SuperAdminRoute><SuperAdminSettingsPage /></SuperAdminRoute>} />

        </Route>


        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
