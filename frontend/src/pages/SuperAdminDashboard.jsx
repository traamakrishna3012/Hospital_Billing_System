import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Building2, Users, Receipt, Activity,
  TrendingUp, Globe, ShieldCheck, ArrowUpRight
} from 'lucide-react';
import { superadminAPI } from '../services/api';
import { StatCard, LoadingSpinner } from '../components/UI';

export default function SuperAdminDashboard() {
  const { isAuthenticated } = useAuthStore();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isAuthenticated) {
      loadData();
    }
  }, [isAuthenticated]);

  const loadData = async () => {
    try {
      const res = await superadminAPI.getStats();
      setStats(res.data);
    } catch (err) {
      if (err.response?.status !== 401) {
        console.error('Failed to load platform stats:', err);
      }
    } finally {
      setLoading(false);
    }
  };


  if (loading) return <LoadingSpinner />;

  const formatCurrency = (val) => `₹${Number(val).toLocaleString('en-IN')}`;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-surface-800">Platform Overview</h1>
        <p className="text-surface-400 mt-1">Global statistics across all registered hospitals and clinics.</p>
      </div>

      {/* Global Stat Cards */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5"
      >
        <StatCard
          icon={Building2}
          label="Total Clinics"
          value={stats?.total_tenants || 0}
          color="primary"
        />
        <StatCard
          icon={Activity}
          label="Active Clinics"
          value={stats?.active_tenants || 0}
          color="emerald"
        />
        <StatCard
          icon={TrendingUp}
          label="Global Revenue"
          value={formatCurrency(stats?.total_revenue || 0)}
          color="violet"
        />
        <StatCard
          icon={Users}
          label="Total Users"
          value={stats?.total_users || 0}
          color="amber"
        />
      </motion.div>

      {/* Detailed Platform Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="lg:col-span-2 glass-card p-6"
        >
          <h2 className="text-lg font-semibold text-surface-800 mb-6 font-primary">Platform Health</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
             <div className="p-5 rounded-2xl bg-surface-50 border border-surface-100">
               <div className="w-10 h-10 rounded-xl bg-primary-100 text-primary-600 flex items-center justify-center mb-4">
                 <Users className="w-5 h-5" />
               </div>
               <p className="text-2xl font-bold text-surface-800">{stats?.total_patients || 0}</p>
               <p className="text-xs text-surface-400 font-medium uppercase tracking-wider">Total Patients</p>
             </div>
             <div className="p-5 rounded-2xl bg-surface-50 border border-surface-100">
               <div className="w-10 h-10 rounded-xl bg-violet-100 text-violet-600 flex items-center justify-center mb-4">
                 <Receipt className="w-5 h-5" />
               </div>
               <p className="text-2xl font-bold text-surface-800">{stats?.total_bills || 0}</p>
               <p className="text-xs text-surface-400 font-medium uppercase tracking-wider">Total Bills</p>
             </div>
             <div className="p-5 rounded-2xl bg-surface-50 border border-surface-100">
               <div className="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-600 flex items-center justify-center mb-4">
                 <ShieldCheck className="w-5 h-5" />
               </div>
               <p className="text-2xl font-bold text-surface-800">99.8%</p>
               <p className="text-xs text-surface-400 font-medium uppercase tracking-wider">System Uptime</p>
             </div>
          </div>
          
          <div className="mt-8 p-6 rounded-2xl bg-gradient-to-br from-primary-600 to-violet-600 text-white relative overflow-hidden">
             <div className="relative z-10">
               <p className="text-primary-100 font-medium text-sm mb-1 uppercase tracking-widest">Growth Factor</p>
               <h3 className="text-3xl font-bold mb-2">Steady Platform Expansion</h3>
               <p className="text-primary-100/80 max-w-md">Your SaaS platform is currently managing {stats?.total_tenants} healthcare institutions efficiently.</p>
             </div>
             <Globe className="absolute -bottom-12 -right-12 w-48 h-48 text-white/10" />
          </div>
        </motion.div>

         <motion.div
           initial={{ opacity: 0, y: 10 }}
           animate={{ opacity: 1, y: 0 }}
           transition={{ delay: 0.2 }}
           className="glass-card p-6"
        >
           <div className="flex items-center justify-between mb-6">
             <h2 className="text-lg font-semibold text-surface-800">Quick Actions</h2>
           </div>
           
           <div className="space-y-3">
             <button onClick={() => window.location.href = '/super/tenants'} className="flex items-center justify-between w-full p-4 rounded-xl border border-surface-200 hover:border-primary-300 hover:bg-primary-50 transition-all group">
               <div className="flex items-center gap-3">
                 <div className="w-8 h-8 rounded-lg bg-surface-100 group-hover:bg-white flex items-center justify-center">
                   <Building2 className="w-4 h-4 text-surface-600 group-hover:text-primary-600" />
                 </div>
                 <span className="text-sm font-medium text-surface-700">Manage All Clinics</span>
               </div>
               <ArrowUpRight className="w-4 h-4 text-surface-400 group-hover:text-primary-600" />
             </button>
             
             <button onClick={() => window.location.href = '/super/tenants'} className="flex items-center justify-between w-full p-4 rounded-xl border border-surface-200 hover:border-violet-300 hover:bg-violet-50 transition-all group">
               <div className="flex items-center gap-3">
                 <div className="w-8 h-8 rounded-lg bg-surface-100 group-hover:bg-white flex items-center justify-center">
                   <Users className="w-4 h-4 text-surface-600 group-hover:text-violet-600" />
                 </div>
                 <span className="text-sm font-medium text-surface-700">Audit Platform Users</span>
               </div>
               <ArrowUpRight className="w-4 h-4 text-surface-400 group-hover:text-violet-600" />
             </button>
             
             <button onClick={() => window.location.href = '/super/revenue'} className="flex items-center justify-between w-full p-4 rounded-xl border border-surface-200 hover:border-emerald-300 hover:bg-emerald-50 transition-all group">
               <div className="flex items-center gap-3">
                 <div className="w-8 h-8 rounded-lg bg-surface-100 group-hover:bg-white flex items-center justify-center">
                   <TrendingUp className="w-4 h-4 text-surface-600 group-hover:text-emerald-600" />
                 </div>
                 <span className="text-sm font-medium text-surface-700">Revenue Analytics</span>
               </div>
               <ArrowUpRight className="w-4 h-4 text-surface-400 group-hover:text-emerald-600" />
             </button>
           </div>
        </motion.div>
      </div>
    </div>
  );
}
