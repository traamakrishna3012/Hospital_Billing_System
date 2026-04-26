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


export default function Sidebar({ isOpen, onClose }) {
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
      onClick={() => {
        // On mobile, close sidebar when a link is clicked
        if (window.innerWidth < 1024) onClose();
      }}
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

  const effectiveModules = user?.modules ?? user?.tenant_modules;

  const filteredNavItems = navItems.filter(item => {
    if (item.id === 'dashboard') return true;
    if (isAdmin()) return true;
    if (effectiveModules == null) return true;
    return effectiveModules[item.id] !== false;
  });

  const filteredAdminItems = adminItems.filter(item => true);

  return (
    <>
      {/* Mobile Backdrop */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-surface-900/50 backdrop-blur-sm z-40 lg:hidden"
          />
        )}
      </AnimatePresence>

      <motion.aside
        initial={false}
        animate={{ 
          width: collapsed ? 80 : 272,
          x: isOpen ? 0 : (window.innerWidth < 1024 ? -272 : 0)
        }}
        transition={{ duration: 0.3, ease: 'easeInOut' }}
        className="fixed left-0 top-0 h-screen bg-white border-r border-surface-200 z-50 flex flex-col overflow-hidden lg:translate-x-0"
      >
        {/* Logo Section */}
        <div className="flex items-center justify-between px-5 py-5 border-b border-surface-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl gradient-primary flex items-center justify-center flex-shrink-0">
              <Building2 className="w-5 h-5 text-white" />
            </div>
            {!collapsed && (
              <div className="overflow-hidden">
                <h1 className="text-base font-bold text-surface-800 whitespace-nowrap">
                  {isSuperAdmin() ? 'SaaS Platform' : 'Hospital Billing'}
                </h1>
                <p className="text-xs text-surface-400 whitespace-nowrap">
                  {isSuperAdmin() ? 'Super Admin Console' : 'Management System'}
                </p>
              </div>
            )}
          </div>
          {/* Mobile Close Button */}
          <button onClick={onClose} className="lg:hidden p-2 text-surface-400 hover:text-surface-600">
            <ChevronLeft className="w-5 h-5" />
          </button>
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

        {/* Footer / Logout */}
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
          >
            <LogOut className="w-5 h-5 flex-shrink-0" />
            {!collapsed && <span>Logout</span>}
          </button>
          
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="hidden lg:flex items-center justify-center w-full py-2 rounded-xl text-surface-400 hover:bg-surface-100 transition-all"
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>
      </motion.aside>
    </>
  );
}
