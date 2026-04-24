import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  UserCog, Plus, Pencil, Trash2, Key,
  Users, Stethoscope, FlaskConical, Receipt, FileBarChart, LayoutDashboard, ShieldCheck
} from 'lucide-react';

import toast from 'react-hot-toast';
import { userAPI } from '../services/api';
import { useAuthStore } from '../store/authStore';
import { Pagination, Modal, EmptyState, LoadingSpinner, StatusBadge } from '../components/UI';

// All modules the admin can toggle per staff member
const ALL_MODULES = [
  { id: 'patients',  label: 'Patients',       icon: Users },
  { id: 'doctors',   label: 'Doctors',        icon: Stethoscope },
  { id: 'tests',     label: 'Tests & Services', icon: FlaskConical },
  { id: 'billing',   label: 'Billing',        icon: Receipt },
  { id: 'reports',   label: 'Reports',        icon: FileBarChart },
];

// Default: all modules enabled
const defaultModules = () =>
  Object.fromEntries(ALL_MODULES.map((m) => [m.id, true]));

export default function StaffPage() {
  const [users, setUsers] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({
    email: '', full_name: '', phone: '', password: '', role: 'staff',
    modules: defaultModules(),
  });
  const currentUser = useAuthStore((s) => s.user);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await userAPI.list({ page, page_size: 20 });
      setUsers(data.items);
      setTotal(data.total);
      setTotalPages(data.total_pages);
    } catch (err) {
      toast.error('Failed to load staff');
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => { loadUsers(); }, [loadUsers]);

  const openCreate = () => {
    setEditing(null);
    setForm({ email: '', full_name: '', phone: '', password: '', role: 'staff', modules: defaultModules() });
    setModalOpen(true);
  };

  const openEdit = (user) => {
    setEditing(user);
    setForm({
      full_name: user.full_name,
      phone: user.phone || '',
      role: user.role,
      password: '',
      // If user already has modules set, use them; otherwise default all on
      modules: user.modules ?? defaultModules(),
    });

    setModalOpen(true);
  };

  const toggleModule = (id) => {
    setForm((f) => ({
      ...f,
      modules: { ...f.modules, [id]: !f.modules[id] },
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editing) {
        await userAPI.update(editing.id, {
          full_name: form.full_name,
          phone: form.phone,
          role: form.role,
          modules: form.modules,
          password: form.password || undefined,
        });
        toast.success('User updated');

      } else {
        await userAPI.create({
          email: form.email,
          full_name: form.full_name,
          phone: form.phone,
          password: form.password,
          role: form.role,
        });
        toast.success('Staff user created');
      }
      setModalOpen(false);
      loadUsers();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Operation failed');
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Remove this staff member?')) return;
    try {
      await userAPI.delete(id);
      toast.success('User removed');
      loadUsers();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete');
    }
  };

  // Modules are only relevant for staff/doctor — admins always get full access
  const showModules = form.role !== 'admin';

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-surface-800">Staff Management</h1>
          <p className="text-surface-400 mt-1">{total} team members</p>
        </div>
        <button onClick={openCreate} className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" /> Add Staff
        </button>
      </div>

      {loading ? (
        <LoadingSpinner />
      ) : users.length === 0 ? (
        <EmptyState icon={UserCog} title="No staff members" description="Add staff members to manage your clinic." action={<button onClick={openCreate} className="btn-primary">Add Staff</button>} />
      ) : (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="glass-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-surface-50">
                  {['Name', 'Email', 'Role', 'Module Access', 'Status', 'Actions'].map((h) => (
                    <th key={h} className="px-6 py-3 text-left text-xs font-semibold text-surface-500 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-100">
                {users.map((user) => (
                  <tr key={user.id} className="hover:bg-surface-50/50">
                    <td className="px-6 py-4">
                      <p className="text-sm font-medium text-surface-800">{user.full_name}</p>
                      {user.phone && <p className="text-xs text-surface-400">{user.phone}</p>}
                    </td>
                    <td className="px-6 py-4 text-sm text-surface-600">{user.email}</td>
                    <td className="px-6 py-4"><StatusBadge status={user.role} /></td>
                    <td className="px-6 py-4">
                      {user.role === 'admin' ? (
                        <span className="inline-flex items-center gap-1 text-xs font-medium text-primary-600">
                          <ShieldCheck className="w-3.5 h-3.5" /> Full Access
                        </span>
                      ) : user.modules ? (
                        <div className="flex flex-wrap gap-1">
                          {ALL_MODULES.filter(m => user.modules[m.id] !== false).map(m => (
                            <span key={m.id} className="text-[10px] px-1.5 py-0.5 rounded bg-primary-50 text-primary-700 font-medium capitalize">
                              {m.label}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-xs text-surface-400">All (default)</span>
                      )}
                    </td>
                    <td className="px-6 py-4"><StatusBadge status={user.is_active ? 'active' : 'inactive'} /></td>
                    <td className="px-6 py-4">
                      {user.id !== currentUser?.id && (
                        <div className="flex gap-1">
                          <button onClick={() => openEdit(user)} className="btn-ghost p-2"><Pencil className="w-4 h-4 text-surface-500" /></button>
                          <button onClick={() => handleDelete(user.id)} className="btn-ghost p-2"><Trash2 className="w-4 h-4 text-red-400" /></button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="px-6 py-3 border-t border-surface-100 flex justify-end">
            <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
          </div>
        </motion.div>
      )}

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title={editing ? 'Edit Staff' : 'Add Staff'}>
        <form onSubmit={handleSubmit} className="space-y-4">
          {!editing && (
            <div>
              <label className="label-text">Email *</label>
              <input type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="input-field" />
            </div>
          )}
          <div>
            <label className="label-text">Full Name *</label>
            <input required value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} className="input-field" />
          </div>
          <div>
            <label className="label-text">Phone</label>
            <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} className="input-field" />
          </div>
          {!editing && (
            <div>
              <label className="label-text">Password *</label>
              <input type="password" required minLength={8} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} className="input-field" />
            </div>
          )}
          <div>
            <label className="label-text">Role</label>
            <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} className="input-field">
              <option value="staff">Staff / Receptionist</option>
              <option value="admin">Admin</option>
              <option value="doctor">Consulting Doctor</option>
            </select>
          </div>

          {editing && (
            <div className="pt-2 border-t border-surface-100">
              <label className="label-text flex items-center gap-2">
                <Key className="w-3.5 h-3.5 text-surface-400" /> Reset Password
              </label>
              <input 
                type="password" 
                placeholder="Leave blank to keep current" 
                value={form.password} 
                onChange={(e) => setForm({ ...form, password: e.target.value })} 
                className="input-field" 
              />
              <p className="text-[10px] text-surface-400 mt-1">
                Enter a new password if the staff member forgot theirs.
              </p>
            </div>
          )}

          {/* Module Access Control — only shown when editing non-admin staff */}
          {editing && showModules && (
            <div className="pt-2 border-t border-surface-100">
              <div className="flex items-center gap-2 mb-3">
                <ShieldCheck className="w-4 h-4 text-primary-500" />
                <label className="label-text mb-0">Module Access Permissions</label>
              </div>
              <p className="text-xs text-surface-400 mb-3">
                Control which sections this staff member can access in the sidebar.
              </p>
              <div className="grid grid-cols-2 gap-2">
                {ALL_MODULES.map((mod) => {
                  const Icon = mod.icon;
                  const enabled = form.modules[mod.id] !== false;
                  return (
                    <button
                      key={mod.id}
                      type="button"
                      onClick={() => toggleModule(mod.id)}
                      className={`flex items-center gap-2.5 px-3 py-2.5 rounded-lg border-2 text-sm font-medium transition-all duration-150 ${
                        enabled
                          ? 'border-primary-500 bg-primary-50 text-primary-700'
                          : 'border-surface-200 bg-surface-50 text-surface-400'
                      }`}
                    >
                      <div className={`w-4 h-4 rounded flex-shrink-0 border-2 flex items-center justify-center ${
                        enabled ? 'border-primary-500 bg-primary-500' : 'border-surface-300 bg-white'
                      }`}>
                        {enabled && (
                          <svg className="w-2.5 h-2.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                          </svg>
                        )}
                      </div>
                      <Icon className="w-4 h-4 flex-shrink-0" />
                      {mod.label}
                    </button>
                  );
                })}
              </div>
            </div>
          )}


          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={() => setModalOpen(false)} className="btn-secondary">Cancel</button>
            <button type="submit" className="btn-primary">{editing ? 'Update' : 'Create'}</button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
