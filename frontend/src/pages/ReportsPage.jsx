import { useState } from 'react';
import { motion } from 'framer-motion';
import { FileBarChart, Download, FileSpreadsheet, Calendar } from 'lucide-react';
import toast from 'react-hot-toast';
import { reportAPI } from '../services/api';

export default function ReportsPage() {
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [exporting, setExporting] = useState(false);

  const exportCSV = async () => {
    setExporting(true);
    try {
      const response = await reportAPI.exportCSV({
        date_from: dateFrom,
        date_to: dateTo,
        status: statusFilter,
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.download = `bills_report_${new Date().toISOString().split('T')[0]}.csv`;
      link.click();
      window.URL.revokeObjectURL(url);
      toast.success('CSV exported successfully');
    } catch (err) {
      toast.error('Failed to export report');
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-xl sm:text-2xl font-bold text-surface-800">Reports</h1>
        <p className="text-surface-400 text-sm mt-1">Export your billing data for analysis</p>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card p-4 sm:p-6 space-y-6"
      >
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 sm:w-14 sm:h-14 rounded-xl sm:rounded-2xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-lg">
            <FileSpreadsheet className="w-6 h-6 sm:w-7 sm:h-7 text-white" />
          </div>
          <div>
            <h2 className="text-base sm:text-lg font-semibold text-surface-800">Export Bills Report</h2>
            <p className="text-xs sm:text-sm text-surface-400">Download your billing data as a CSV file</p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="label-text flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5" /> Date From
            </label>
            <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="input-field" />
          </div>
          <div>
            <label className="label-text flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5" /> Date To
            </label>
            <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="input-field" />
          </div>
          <div>
            <label className="label-text">Status</label>
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="input-field">
              <option value="">All</option>
              <option value="paid">Paid</option>
              <option value="unpaid">Unpaid</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>
        </div>

        <button onClick={exportCSV} disabled={exporting} className="btn-primary flex items-center justify-center gap-2 w-full sm:w-auto">
          <Download className="w-4 h-4" /> {exporting ? 'Exporting...' : 'Download CSV Report'}
        </button>
      </motion.div>

      {/* Report Info Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-5">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="glass-card p-4 sm:p-5"
        >
          <h3 className="text-sm font-semibold text-surface-700 mb-2">What's included in the CSV?</h3>
          <ul className="text-xs sm:text-sm text-surface-500 space-y-1.5">
            <li>• Bill number and date</li>
            <li>• Patient name and phone</li>
            <li>• Doctor name</li>
            <li>• Subtotal, tax, discount, total</li>
            <li>• Payment mode and status</li>
          </ul>
        </motion.div>
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="glass-card p-4 sm:p-5"
        >
          <h3 className="text-sm font-semibold text-surface-700 mb-2">Tips</h3>
          <ul className="text-xs sm:text-sm text-surface-500 space-y-1.5">
            <li>• Leave dates empty to export all bills</li>
            <li>• Use the status filter to export only paid bills</li>
            <li>• Open CSV in Excel or Google Sheets</li>
            <li>• Individual bill PDFs available in Billing</li>
          </ul>
        </motion.div>
      </div>
    </div>
  );
}
