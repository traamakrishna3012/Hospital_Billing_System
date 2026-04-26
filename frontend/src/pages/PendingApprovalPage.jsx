import { motion } from 'framer-motion';
import { Clock, ShieldCheck, Mail, ArrowLeft, LogOut } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

export default function PendingApprovalPage() {
  const navigate = useNavigate();
  const { logout, user } = useAuthStore();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-surface-50 flex items-center justify-center p-4 sm:p-6">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="max-w-xl w-full glass-card p-6 sm:p-10 text-center"
      >
        <div className="w-16 h-16 sm:w-20 sm:h-20 bg-amber-50 rounded-full flex items-center justify-center mx-auto mb-6 sm:mb-8 animate-pulse">
          <Clock className="w-8 h-8 sm:w-10 sm:h-10 text-amber-500" />
        </div>

        <h1 className="text-2xl sm:text-3xl font-bold text-surface-800 mb-4">Registration Pending</h1>
        <p className="text-surface-600 text-base sm:text-lg leading-relaxed mb-8">
          Welcome to the platform, <span className="font-semibold text-primary-600">{user?.full_name}</span>! 
          Your clinic profile is currently being reviewed by our Super Admin team for verification.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-10">
          <div className="p-4 bg-white rounded-2xl border border-surface-100 flex flex-col items-center shadow-sm">
            <ShieldCheck className="w-6 h-6 text-emerald-500 mb-2" />
            <p className="text-sm font-medium text-surface-700">Verification</p>
            <p className="text-[10px] sm:text-xs text-surface-400">Security check in progress</p>
          </div>
          <div className="p-4 bg-white rounded-2xl border border-surface-100 flex flex-col items-center shadow-sm">
            <Mail className="w-6 h-6 text-indigo-500 mb-2" />
            <p className="text-sm font-medium text-surface-700">Email Notification</p>
            <p className="text-[10px] sm:text-xs text-surface-400">You'll be notified via email</p>
          </div>
        </div>

        <div className="space-y-4">
          <p className="text-xs sm:text-sm text-surface-400">
            Usually, approvals are processed within 2-4 hours. 
            Once approved, you'll gain full access to Patient Management, Dashboard, and Billing features.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-3 justify-center pt-4">
            <button 
              onClick={() => navigate('/login')}
              className="btn-secondary flex items-center justify-center gap-2 px-6 w-full sm:w-auto"
            >
              <ArrowLeft className="w-4 h-4" /> Back to Login
            </button>
            <button 
              onClick={handleLogout}
              className="btn-ghost text-red-500 hover:bg-red-50 flex items-center justify-center gap-2 px-6 w-full sm:w-auto"
            >
              <LogOut className="w-4 h-4" /> Sign Out
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
