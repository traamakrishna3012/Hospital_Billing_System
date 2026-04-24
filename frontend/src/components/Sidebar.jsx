import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard, Users, Stethoscope, FlaskConical,
  Receipt, Settings, UserCog, FileBarChart, LogOut,
  ChevronLeft, ChevronRight, Building2, Menu, TrendingUp
} from 'lucide-react';
import { useAuthStore } from '../store/authStore';

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard', id: 'dashboard' },
  { to: '/patients', icon: Users, label: 'Patients', id: 'patients' },
  { to: '/doctors', icon: Stethoscope, label: 'Doctors', id: 'doctors' },
  { to: '/tests', icon: FlaskConical, label: 'Tests & Services', id: 'tests' },
  { to: '/billing', icon: Receipt, label: 'Billing', id: 'billing' },
  { to: '/reports', icon: FileBarChart, label: 'Reports', id: 'reports' },
];

const adminItems = [
  { to: '/staff', icon: UserCog, label: 'Staff Management', id: 'staff' },
  { to: '/settings', icon: Settings, label: 'Clinic Settings', id: 'settings' },
];

const superadminItems = [
  { to: '/super/dashboard', icon: LayoutDashboard, label: 'Platform Stats' },
  { to: '/super/tenants', icon: Building2, label: 'Manage Clinics' },
  { to: '/super/revenue', icon: TrendingUp, label: 'Revenue Analytics' },
  { to: '/super/settings', icon: Settings, label: 'Platform Settings' },
];


export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const { user, logout, isAdmin, isSuperAdmin } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const linkClasses = (isActive) =>
    `flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200 group ${
      isActive
        ? 'bg-primary-600 text-white shadow-md shadow-primary-600/25'
        : 'text-surface-500 hover:bg-surface-100 hover:text-surface-800'
    }`;

  const renderNavItems = (items) => items.map((item) => (
    <NavLink
      key={item.to}
      to={item.to}
      className={({ isActive }) => linkClasses(isActive)}
      title={collapsed ? item.label : undefined}
    >
      <item.icon className="w-5 h-5 flex-shrink-0" />
      <AnimatePresence>
        {!collapsed && (
          <motion.span
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="whitespace-nowrap"
          >
            {item.label}
          </motion.span>
        )}
      </AnimatePresence>
    </NavLink>
  ));

  // Effective module access:
  // 1. If user has their own modules set → use those
  // 2. Otherwise fall through to tenant-level modules
  const effectiveModules = user?.modules ?? user?.tenant_modules;

  const filteredNavItems = navItems.filter(item => {
    if (item.id === 'dashboard') return true;           // always visible
    if (isAdmin()) return true;                          // admins see all
    if (effectiveModules == null) return true;           // no restrictions set
    return effectiveModules[item.id] !== false;
  });

  const filteredAdminItems = adminItems.filter(item => {
    if (item.id === 'settings') return true;             // always visible to admin
    return true;                                         // admin nav already gated by isAdmin()
  });

  return (
    <motion.aside
      animate={{ width: collapsed ? 80 : 272 }}
      transition={{ duration: 0.3, ease: 'easeInOut' }}
      className="fixed left-0 top-0 h-screen bg-white border-r border-surface-200 z-40 flex flex-col overflow-hidden"
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-surface-100">
        <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center flex-shrink-0">
          <Building2 className="w-5 h-5 text-white" />
        </div>
        <AnimatePresence>
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              className="overflow-hidden"
            >
              <h1 className="text-base font-bold text-surface-800 whitespace-nowrap">
                {isSuperAdmin() ? 'SaaS Platform' : 'Hospital Billing'}
              </h1>
              <p className="text-xs text-surface-400 whitespace-nowrap">
                {isSuperAdmin() ? 'Super Admin Console' : 'Management System'}
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {isSuperAdmin() ? (
          <>
            {!collapsed && (
              <p className="px-4 text-[10px] font-semibold text-surface-400 uppercase tracking-widest mb-2">
                Platform Management
              </p>
            )}
            {renderNavItems(superadminItems)}
          </>
        ) : (
          <>
            {!collapsed && (
              <p className="px-4 text-[10px] font-semibold text-surface-400 uppercase tracking-widest mb-2">
                Main Menu
              </p>
            )}
            {renderNavItems(filteredNavItems)}

            {isAdmin() && (
              <>
                {!collapsed && (
                  <p className="px-4 pt-5 text-[10px] font-semibold text-surface-400 uppercase tracking-widest mb-2">
                    Administration
                  </p>
                )}
                {renderNavItems(filteredAdminItems)}
              </>
            )}
          </>
        )}
      </nav>

      {/* User & Collapse */}
      <div className="border-t border-surface-100 p-3 space-y-2">
        {!collapsed && user && (
          <div className="px-3 py-2">
            <p className="text-sm font-medium text-surface-800 truncate">{user.full_name}</p>
            <p className="text-xs text-surface-400 truncate">{user.email}</p>
            <span className="inline-block mt-1 badge-info text-[10px] uppercase font-bold tracking-wider">
              {user.role}
            </span>
          </div>
        )}
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 w-full px-4 py-2.5 rounded-xl text-sm font-medium text-red-500 hover:bg-red-50 transition-all duration-200"
          title="Logout"
        >
          <LogOut className="w-5 h-5 flex-shrink-0" />
          {!collapsed && <span>Logout</span>}
        </button>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex items-center justify-center w-full py-2 rounded-xl text-surface-400 hover:bg-surface-100 transition-all"
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>
    </motion.aside>
  );
}
