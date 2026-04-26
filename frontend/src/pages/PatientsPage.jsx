import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Users, Plus, Pencil, Trash2, Phone, Mail } from 'lucide-react';
import toast from 'react-hot-toast';
import { patientAPI } from '../services/api';
import { SearchInput, Pagination, Modal, EmptyState, LoadingSpinner } from '../components/UI';

export default function PatientsPage() {
  const [patients, setPatients] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [search, setSearch] = useState('');
  const [gender, setGender] = useState('');
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({
    name: '', age: '', gender: 'male', phone: '', email: '',
    address: '', blood_group: '', medical_notes: '',
  });

  const loadPatients = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await patientAPI.list({ page, page_size: 15, search, gender });
      setPatients(data.items);
      setTotal(data.total);
      setTotalPages(data.total_pages);
    } catch (err) {
      toast.error('Failed to load patients');
    } finally {
      setLoading(false);
    }
  }, [page, search, gender]);

  useEffect(() => { loadPatients(); }, [loadPatients]);

  useEffect(() => { setPage(1); }, [search, gender]);

  const openCreate = () => {
    setEditing(null);
    setForm({ name: '', age: '', gender: 'male', phone: '', email: '', address: '', blood_group: '', medical_notes: '' });
    setModalOpen(true);
  };

  const openEdit = (patient) => {
    setEditing(patient);
    setForm({
      name: patient.name, age: String(patient.age), gender: patient.gender,
      phone: patient.phone, email: patient.email || '', address: patient.address || '',
      blood_group: patient.blood_group || '', medical_notes: patient.medical_notes || '',
    });
    setModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const payload = { ...form, age: parseInt(form.age) };
    try {
      if (editing) {
        await patientAPI.update(editing.id, payload);
        toast.success('Patient updated');
      } else {
        await patientAPI.create(payload);
        toast.success('Patient created');
      }
      setModalOpen(false);
      loadPatients();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Operation failed');
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this patient?')) return;
    try {
      await patientAPI.delete(id);
      toast.success('Patient deleted');
      loadPatients();
    } catch (err) {
      toast.error('Failed to delete');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-surface-800">Patients</h1>
          <p className="text-surface-400 text-sm mt-1">{total} total records</p>
        </div>
        <button onClick={openCreate} className="btn-primary flex items-center justify-center gap-2 w-full sm:w-auto">
          <Plus className="w-4 h-4" /> Add Patient
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
        <div className="flex-1">
          <SearchInput value={search} onChange={setSearch} placeholder="Search by name or phone..." className="w-full" />
        </div>
        <select value={gender} onChange={(e) => setGender(e.target.value)} className="input-field sm:w-40">
          <option value="">All Genders</option>
          <option value="male">Male</option>
          <option value="female">Female</option>
          <option value="other">Other</option>
        </select>
      </div>

      {/* Table */}
      {loading ? (
        <LoadingSpinner />
      ) : patients.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No patients found"
          description="Add your first patient to get started with billing."
          action={<button onClick={openCreate} className="btn-primary">Add Patient</button>}
        />
      ) : (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="glass-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[800px] sm:min-w-0">
              <thead>
                <tr className="bg-surface-50">
                  {['Name', 'Age', 'Gender', 'Phone', 'Blood Group', 'Actions'].map((h) => (
                    <th key={h} className="px-4 sm:px-6 py-3 text-left text-xs font-semibold text-surface-500 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-100">
                {patients.map((p) => (
                  <tr key={p.id} className="hover:bg-surface-50/50 transition-colors">
                    <td className="px-4 sm:px-6 py-4">
                      <p className="text-sm font-medium text-surface-800">{p.name}</p>
                      {p.email && <p className="text-[10px] sm:text-xs text-surface-400">{p.email}</p>}
                    </td>
                    <td className="px-4 sm:px-6 py-4 text-sm text-surface-600">{p.age}</td>
                    <td className="px-4 sm:px-6 py-4 text-sm text-surface-600 capitalize">{p.gender}</td>
                    <td className="px-4 sm:px-6 py-4 text-sm text-surface-600">
                      <div className="flex items-center gap-1.5">
                        <Phone className="w-3.5 h-3.5 text-surface-400" /> {p.phone}
                      </div>
                    </td>
                    <td className="px-4 sm:px-6 py-4 text-sm text-surface-600">{p.blood_group || '—'}</td>
                    <td className="px-4 sm:px-6 py-4">
                      <div className="flex items-center gap-1">
                        <button onClick={() => openEdit(p)} className="p-2 text-surface-400 hover:text-primary-600" title="Edit">
                          <Pencil className="w-4 h-4" />
                        </button>
                        <button onClick={() => handleDelete(p.id)} className="p-2 text-surface-400 hover:text-red-500" title="Delete">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="px-6 py-3 border-t border-surface-100 flex justify-center sm:justify-end">
            <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
          </div>
        </motion.div>
      )}

      {/* Modal */}
      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title={editing ? 'Edit Patient' : 'New Patient'} size="lg">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="label-text">Full Name *</label>
              <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="input-field" />
            </div>
            <div>
              <label className="label-text">Age *</label>
              <input type="number" required min="0" max="150" value={form.age} onChange={(e) => setForm({ ...form, age: e.target.value })} className="input-field" />
            </div>
            <div>
              <label className="label-text">Gender *</label>
              <select value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value })} className="input-field">
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div>
              <label className="label-text">Phone *</label>
              <input required value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} className="input-field" />
            </div>
            <div>
              <label className="label-text">Email</label>
              <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="input-field" />
            </div>
            <div>
              <label className="label-text">Blood Group</label>
              <input value={form.blood_group} onChange={(e) => setForm({ ...form, blood_group: e.target.value })} className="input-field" placeholder="e.g., O+" />
            </div>
          </div>
          <div>
            <label className="label-text">Address</label>
            <textarea value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} className="input-field resize-none" rows={2} />
          </div>
          <div>
            <label className="label-text">Medical Notes</label>
            <textarea value={form.medical_notes} onChange={(e) => setForm({ ...form, medical_notes: e.target.value })} className="input-field resize-none" rows={2} />
          </div>
          <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 pt-2">
            <button type="button" onClick={() => setModalOpen(false)} className="btn-secondary w-full sm:w-auto">Cancel</button>
            <button type="submit" className="btn-primary w-full sm:w-auto">{editing ? 'Update' : 'Create'} Patient</button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
