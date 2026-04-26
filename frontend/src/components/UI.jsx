import { useState } from 'react';
import { Search, ChevronLeft, ChevronRight } from 'lucide-react';

export function SearchInput({ value, onChange, placeholder = 'Search...', className = '' }) {
  return (
    <div className={`relative ${className}`}>
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-400" />
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="input-field pl-10 w-full"
      />
    </div>
  );
}

export function Pagination({ page, totalPages, onPageChange }) {
  if (totalPages <= 1) return null;

  return (
    <div className="flex items-center gap-2 mt-4 select-none">
      <button
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
        className="p-2 text-surface-400 hover:text-primary-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
      >
        <ChevronLeft className="w-5 h-5" />
      </button>
      <span className="text-xs sm:text-sm font-medium text-surface-600">
        Page {page} of {totalPages}
      </span>
      <button
        onClick={() => onPageChange(page + 1)}
        disabled={page >= totalPages}
        className="p-2 text-surface-400 hover:text-primary-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
      >
        <ChevronRight className="w-5 h-5" />
      </button>
    </div>
  );
}

export function Modal({ isOpen, onClose, title, children, size = 'md' }) {
  if (!isOpen) return null;

  const sizes = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-0 sm:p-4">
      <div 
        className="absolute inset-0 bg-surface-900/60 backdrop-blur-sm animate-fade-in" 
        onClick={onClose} 
      />
      <div className={`relative bg-white sm:rounded-2xl shadow-2xl w-full h-full sm:h-auto ${sizes[size]} sm:max-h-[90vh] flex flex-col overflow-hidden animate-slide-up`}>
        <div className="sticky top-0 z-10 bg-white border-b border-surface-100 px-5 sm:px-6 py-4 flex items-center justify-between flex-shrink-0">
          <h2 className="text-base sm:text-lg font-bold text-surface-800 truncate pr-4">{title}</h2>
          <button 
            onClick={onClose} 
            className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-surface-50 text-surface-400 hover:text-surface-600 transition-colors"
          >
            ✕
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-5 sm:p-6 custom-scrollbar">
          {children}
        </div>
      </div>
    </div>
  );
}

export function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-16 h-16 rounded-2xl bg-surface-100 flex items-center justify-center mb-4">
        <Icon className="w-8 h-8 text-surface-400" />
      </div>
      <h3 className="text-lg font-semibold text-surface-700 mb-1">{title}</h3>
      <p className="text-sm text-surface-400 mb-6 max-w-sm">{description}</p>
      {action}
    </div>
  );
}

export function StatusBadge({ status }) {
  const styles = {
    paid: 'badge-success',
    unpaid: 'badge-warning',
    cancelled: 'badge-danger',
    active: 'badge-success',
    inactive: 'badge-neutral',
    admin: 'badge-info',
    staff: 'badge-neutral',
  };

  return (
    <span className={styles[status] || 'badge-neutral'}>
      {status?.charAt(0).toUpperCase() + status?.slice(1)}
    </span>
  );
}

export function LoadingSpinner({ fullPage = false }) {
  const content = (
    <div className="flex flex-col items-center justify-center gap-3">
      <div className="relative w-12 h-12">
        <div className="absolute inset-0 border-4 border-primary-100 rounded-full" />
        <div className="absolute inset-0 border-4 border-primary-500 border-t-transparent rounded-full animate-spin" />
      </div>
      <p className="text-xs font-medium text-surface-400 animate-pulse">Loading data...</p>
    </div>
  );

  if (fullPage) {
    return (
      <div className="fixed inset-0 z-[100] flex items-center justify-center bg-white/60 backdrop-blur-[2px]">
        {content}
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center py-20">
      {content}
    </div>
  );
}

export function StatCard({ icon: Icon, label, value, trend, color = 'primary' }) {
  const gradients = {
    primary: 'from-primary-500 to-primary-700',
    emerald: 'from-emerald-500 to-emerald-700',
    amber: 'from-amber-500 to-amber-700',
    rose: 'from-rose-500 to-rose-700',
    violet: 'from-violet-500 to-violet-700',
    blue: 'from-blue-500 to-blue-700',
  };

  return (
    <div className="glass-card-hover p-4 sm:p-6 relative overflow-hidden">
      <div className="flex items-start justify-between mb-3 sm:mb-4">
        <div className={`w-10 h-10 sm:w-12 sm:h-12 rounded-xl bg-gradient-to-br ${gradients[color]} flex items-center justify-center shadow-lg`}>
          <Icon className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
        </div>
        {trend && (
          <span className={`text-xs font-semibold ${trend > 0 ? 'text-emerald-600' : 'text-red-500'}`}>
            {trend > 0 ? '+' : ''}{trend}%
          </span>
        )}
      </div>
      <p className="text-xl sm:text-2xl font-bold text-surface-800 mb-0.5 sm:mb-1">{value}</p>
      <p className="text-xs sm:text-sm text-surface-400">{label}</p>
    </div>
  );
}
