import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  IndianRupee, Users, Receipt, Stethoscope,
  TrendingUp, Calendar, ArrowUpRight,
} from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart, Bar,
} from 'recharts';
import { format } from 'date-fns';
import { dashboardAPI } from '../services/api';
import { useAuthStore } from '../store/authStore';
import { StatCard, LoadingSpinner, StatusBadge } from '../components/UI';


export default function DashboardPage() {
  const { isAuthenticated } = useAuthStore();
  const [stats, setStats] = useState(null);
  const [chartData, setChartData] = useState([]);
  const [recent, setRecent] = useState([]);
  const [chartPeriod, setChartPeriod] = useState('daily');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isAuthenticated) {
      loadData();
    }
  }, [chartPeriod, isAuthenticated]);

  const loadData = async () => {
    try {
      const [statsRes, chartRes, recentRes] = await Promise.all([
        dashboardAPI.getStats(),
        dashboardAPI.getChartData({ period: chartPeriod, days: 30 }),
        dashboardAPI.getRecent({ limit: 8 }),
      ]);
      setStats(statsRes.data);
      setChartData(chartRes.data);
      setRecent(recentRes.data);
    } catch (err) {
      // Only log if it's not an authentication error (which is handled by interceptor)
      if (err.response?.status !== 401) {
        console.error('Failed to load dashboard:', err);
      }
    } finally {
      setLoading(false);
    }
  };


  if (loading) return <LoadingSpinner />;

  const formatCurrency = (val) => `₹${Number(val).toLocaleString('en-IN')}`;

  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-surface-800">Dashboard</h1>
        <p className="text-surface-400 text-sm sm:text-base mt-1">Welcome back! Here's your clinic overview.</p>
      </div>

      {/* Stat Cards */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-5"
      >
        <StatCard
          icon={IndianRupee}
          label="Today's Revenue"
          value={formatCurrency(stats?.today_revenue || 0)}
          color="primary"
        />
        <StatCard
          icon={Receipt}
          label="Today's Bills"
          value={stats?.today_bills || 0}
          color="emerald"
        />
        <StatCard
          icon={Users}
          label="Total Patients"
          value={stats?.total_patients || 0}
          color="violet"
        />
        <StatCard
          icon={Stethoscope}
          label="Active Doctors"
          value={stats?.total_doctors || 0}
          color="amber"
        />
      </motion.div>

      {/* Revenue Overview + Monthly Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Revenue Chart */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="lg:col-span-2 glass-card p-4 sm:p-6"
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
            <div>
              <h2 className="text-base sm:text-lg font-semibold text-surface-800">Revenue Overview</h2>
              <p className="text-xs sm:text-sm text-surface-400">Track your earnings over time</p>
            </div>
            <div className="flex gap-1 bg-surface-100 rounded-xl p-1 self-start sm:self-center">
              {['daily', 'weekly', 'monthly'].map((period) => (
                <button
                  key={period}
                  onClick={() => setChartPeriod(period)}
                  className={`px-2.5 py-1.5 rounded-lg text-[10px] sm:text-xs font-medium transition-all ${
                    chartPeriod === period
                      ? 'bg-white text-primary-600 shadow-sm'
                      : 'text-surface-500 hover:text-surface-700'
                  }`}
                >
                  {period.charAt(0).toUpperCase() + period.slice(1)}
                </button>
              ))}
            </div>
          </div>

          <div className="h-[250px] sm:h-[300px]">
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#4f46e5" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="#4f46e5" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                  <XAxis
                    dataKey="label"
                    tick={{ fontSize: 10, fill: '#94a3b8' }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 10, fill: '#94a3b8' }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(v) => `₹${v >= 1000 ? `${(v/1000).toFixed(0)}k` : v}`}
                  />
                  <Tooltip
                    contentStyle={{
                      borderRadius: '12px',
                      border: '1px solid #e2e8f0',
                      boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
                      fontSize: '12px'
                    }}
                    formatter={(value) => [`₹${Number(value).toLocaleString()}`, 'Revenue']}
                  />
                  <Area
                    type="monotone"
                    dataKey="revenue"
                    stroke="#4f46e5"
                    strokeWidth={2}
                    fill="url(#revenueGradient)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-surface-400 text-sm">
                <p>No revenue data available yet.</p>
              </div>
            )}
          </div>
        </motion.div>

        {/* Monthly Summary */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="glass-card p-4 sm:p-6"
        >
          <h2 className="text-base sm:text-lg font-semibold text-surface-800 mb-4">Monthly Summary</h2>
          <div className="grid grid-cols-2 lg:grid-cols-1 gap-3 sm:gap-4">
            <div className="p-3 sm:p-4 rounded-xl bg-gradient-to-br from-primary-50 to-primary-100/50 border border-primary-100">
              <p className="text-[10px] text-primary-500 font-medium mb-0.5">This Month</p>
              <p className="text-sm sm:text-lg font-bold text-primary-700 truncate">{formatCurrency(stats?.month_revenue || 0)}</p>
            </div>
            <div className="p-3 sm:p-4 rounded-xl bg-gradient-to-br from-emerald-50 to-emerald-100/50 border border-emerald-100">
              <p className="text-[10px] text-emerald-500 font-medium mb-0.5">Bills Month</p>
              <p className="text-sm sm:text-lg font-bold text-emerald-700">{stats?.month_bills || 0}</p>
            </div>
            <div className="p-3 sm:p-4 rounded-xl bg-gradient-to-br from-violet-50 to-violet-100/50 border border-violet-100">
              <p className="text-[10px] text-violet-500 font-medium mb-0.5">Total Rev</p>
              <p className="text-sm sm:text-lg font-bold text-violet-700 truncate">{formatCurrency(stats?.total_revenue || 0)}</p>
            </div>
            <div className="p-3 sm:p-4 rounded-xl bg-gradient-to-br from-amber-50 to-amber-100/50 border border-amber-100">
              <p className="text-[10px] text-amber-500 font-medium mb-0.5">Total Bills</p>
              <p className="text-sm sm:text-lg font-bold text-amber-700">{stats?.total_bills || 0}</p>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Recent Transactions */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="glass-card overflow-hidden"
      >
        <div className="px-4 sm:px-6 py-4 border-b border-surface-100 flex items-center justify-between">
          <h2 className="text-base sm:text-lg font-semibold text-surface-800">Recent Transactions</h2>
          <a href="/billing" className="text-xs sm:text-sm text-primary-600 font-medium hover:text-primary-700 flex items-center gap-1">
            View All <ArrowUpRight className="w-3.5 h-3.5" />
          </a>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[600px] sm:min-w-0">
            <thead>
              <tr className="bg-surface-50">
                <th className="px-4 sm:px-6 py-3 text-left text-[10px] sm:text-xs font-semibold text-surface-500 uppercase tracking-wider">Bill No.</th>
                <th className="px-4 sm:px-6 py-3 text-left text-[10px] sm:text-xs font-semibold text-surface-500 uppercase tracking-wider">Patient</th>
                <th className="px-4 sm:px-6 py-3 text-left text-[10px] sm:text-xs font-semibold text-surface-500 uppercase tracking-wider">Amount</th>
                <th className="px-4 sm:px-6 py-3 text-left text-[10px] sm:text-xs font-semibold text-surface-500 uppercase tracking-wider">Status</th>
                <th className="px-4 sm:px-6 py-3 text-left text-[10px] sm:text-xs font-semibold text-surface-500 uppercase tracking-wider text-right">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-100">
              {recent.length > 0 ? (
                recent.map((txn) => {
                  let formattedDate = '-';
                  try {
                    if (txn.created_at) {
                      formattedDate = format(new Date(txn.created_at), 'dd MMM');
                    }
                  } catch (e) {}

                  return (
                    <tr key={txn.id} className="hover:bg-surface-50/50 transition-colors">
                      <td className="px-4 sm:px-6 py-4 text-xs sm:text-sm font-medium text-primary-600">{txn.bill_number || 'N/A'}</td>
                      <td className="px-4 sm:px-6 py-4 text-xs sm:text-sm text-surface-700 truncate max-w-[120px]">{txn.patient_name || 'Guest'}</td>
                      <td className="px-4 sm:px-6 py-4 text-xs sm:text-sm font-semibold text-surface-800">
                        {formatCurrency(txn.total || 0)}
                      </td>
                      <td className="px-4 sm:px-6 py-4"><StatusBadge status={txn.status || 'unpaid'} /></td>
                      <td className="px-4 sm:px-6 py-4 text-xs text-surface-400 text-right">{formattedDate}</td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={5} className="px-4 sm:px-6 py-12 text-center text-surface-400 text-sm">
                    No transactions yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </motion.div>
    </div>
  );
}
