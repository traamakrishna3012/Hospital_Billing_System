import { useState } from 'react';
import { motion } from 'framer-motion';
import { Shield, Key, Save, Server, Mail, User } from 'lucide-react';
import toast from 'react-hot-toast';
import { authAPI } from '../services/api';
import { useAuthStore } from '../store/authStore';

export default function SuperAdminSettingsPage() {
  const { user } = useAuthStore();
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  });
  const [changing, setChanging] = useState(false);

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      return toast.error('New passwords do not match');
    }
    
    setChanging(true);
    try {
      await authAPI.changePassword({
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password,
      });
      toast.success('Password updated successfully');
      setPasswordForm({ current_password: '', new_password: '', confirm_password: '' });
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update password');
    } finally {
      setChanging(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold text-surface-800">Platform Settings</h1>
        <p className="text-surface-400 mt-1">Manage system-wide configurations and security</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Profile Card */}
        <motion.div 
          initial={{ opacity: 0, y: 10 }} 
          animate={{ opacity: 1, y: 0 }} 
          className="glass-card p-6 md:col-span-1"
        >
          <div className="flex flex-col items-center text-center">
            <div className="w-20 h-20 rounded-2xl gradient-primary flex items-center justify-center text-white mb-4 shadow-lg shadow-primary-500/20">
              <Shield className="w-10 h-10" />
            </div>
            <h2 className="text-lg font-bold text-surface-800">{user?.full_name}</h2>
            <p className="text-xs font-semibold uppercase tracking-wider text-primary-600 bg-primary-50 px-2 py-0.5 rounded-full mt-1">
              Super Admin
            </p>
            
            <div className="w-full mt-6 space-y-3 text-left">
              <div className="flex items-center gap-3 text-sm text-surface-600">
                <Mail className="w-4 h-4 text-surface-400" />
                <span className="truncate">{user?.email}</span>
              </div>
              <div className="flex items-center gap-3 text-sm text-surface-600">
                <Server className="w-4 h-4 text-surface-400" />
                <span>Production Mode</span>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Password Change Section */}
        <motion.div 
          initial={{ opacity: 0, y: 10 }} 
          animate={{ opacity: 1, y: 0 }} 
          transition={{ delay: 0.1 }}
          className="glass-card p-6 md:col-span-2"
        >
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-indigo-50 rounded-lg text-indigo-600">
              <Key className="w-5 h-5" />
            </div>
            <h2 className="text-lg font-semibold text-surface-800">Change Security Password</h2>
          </div>

          <form onSubmit={handlePasswordChange} className="space-y-4">
            <div>
              <label className="label-text">Current Password</label>
              <input 
                type="password" 
                required
                value={passwordForm.current_password}
                onChange={(e) => setPasswordForm({ ...passwordForm, current_password: e.target.value })}
                className="input-field" 
                placeholder="••••••••"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="label-text">New Password</label>
                <input 
                  type="password" 
                  required
                  minLength={8}
                  value={passwordForm.new_password}
                  onChange={(e) => setPasswordForm({ ...passwordForm, new_password: e.target.value })}
                  className="input-field" 
                  placeholder="••••••••"
                />
              </div>
              <div>
                <label className="label-text">Confirm New Password</label>
                <input 
                  type="password" 
                  required
                  value={passwordForm.confirm_password}
                  onChange={(e) => setPasswordForm({ ...passwordForm, confirm_password: e.target.value })}
                  className="input-field" 
                  placeholder="••••••••"
                />
              </div>
            </div>
            
            <p className="text-[10px] text-surface-400">
              Password must be at least 8 characters long and include an uppercase letter and a digit.
            </p>

            <div className="flex justify-end pt-4">
              <button 
                type="submit" 
                disabled={changing} 
                className="btn-primary flex items-center gap-2"
              >
                <Save className="w-4 h-4" /> 
                {changing ? 'Updating...' : 'Update Password'}
              </button>
            </div>
          </form>
        </motion.div>
      </div>

      {/* System Info Placeholder */}
      <motion.div 
        initial={{ opacity: 0, y: 10 }} 
        animate={{ opacity: 1, y: 0 }} 
        transition={{ delay: 0.2 }}
        className="glass-card p-6"
      >
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 bg-amber-50 rounded-lg text-amber-600">
            <Server className="w-5 h-5" />
          </div>
          <h2 className="text-lg font-semibold text-surface-800">System Information</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-4 bg-surface-50 rounded-xl border border-surface-100">
            <p className="text-xs text-surface-400 font-medium uppercase mb-1">Database Status</p>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-green-500"></div>
              <p className="text-sm font-semibold text-surface-700">Connected</p>
            </div>
          </div>
          <div className="p-4 bg-surface-50 rounded-xl border border-surface-100">
            <p className="text-xs text-surface-400 font-medium uppercase mb-1">Environment</p>
            <p className="text-sm font-semibold text-surface-700">Production (Render)</p>
          </div>
          <div className="p-4 bg-surface-50 rounded-xl border border-surface-100">
            <p className="text-xs text-surface-400 font-medium uppercase mb-1">Last Backup</p>
            <p className="text-sm font-semibold text-surface-700">Daily Automated</p>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
