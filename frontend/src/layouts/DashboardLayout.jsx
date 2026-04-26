import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import { Toaster } from 'react-hot-toast';
import { Menu } from 'lucide-react';

export default function DashboardLayout() {
  const [isSidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-surface-50">
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
      
      <Sidebar isOpen={isSidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Mobile Top Header */}
      <header className="lg:hidden sticky top-0 bg-white border-b border-surface-200 z-30 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg gradient-primary flex items-center justify-center">
            <span className="text-white font-bold text-xs">HB</span>
          </div>
          <span className="font-bold text-surface-800 text-sm">Hospital Billing</span>
        </div>
        <button
          onClick={() => setSidebarOpen(true)}
          className="p-2 text-surface-500 hover:bg-surface-100 rounded-lg"
        >
          <Menu className="w-6 h-6" />
        </button>
      </header>

      <main className="lg:ml-[272px] transition-all duration-300 min-h-screen">
        <div className="p-4 sm:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
