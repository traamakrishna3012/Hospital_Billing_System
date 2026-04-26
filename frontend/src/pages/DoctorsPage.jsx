import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Stethoscope, Plus, Pencil, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { doctorAPI } from '../services/api';
import { SearchInput, Pagination, Modal, EmptyState, LoadingSpinner, StatusBadge } from '../components/UI';

export default function DoctorsPage() {
  const [doctors, setDoctors] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({
    name: '', specialization: '', qualification: '', phone: '',
    email: '', consultation_fee: '', availability: '',
  });

  const loadDoctors = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await doctorAPI.list({ page, page_size: 15, search, active_only: false });
      setDoctors(data.items);
      setTotal(data.total);
      setTotalPages(data.total_pages);
    } catch (err) {
      toast.error('Failed to load doctors');
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => { loadDoctors(); }, [loadDoctors]);
  useEffect(() => { setPage(1); }, [search]);

  const openCreate = () => {
    setEditing(null);
    setForm({ name: '', specialization: '', qualification: '', phone: '', email: '', consultation_fee: '', availability: '' });
    setModalOpen(true);
  };

  const openEdit = (doctor) => {
    setEditing(doctor);
    setForm({
      name: doctor.name, specialization: doctor.specialization,
      qualification: doctor.qualification || '', phone: doctor.phone || '',
      email: doctor.email || '', consultation_fee: String(doctor.consultation_fee),
      availability: doctor.availability || '',
    });
    setModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const payload = { ...form, consultation_fee: parseFloat(form.consultation_fee) };
    try {
      if (editing) {
        await doctorAPI.update(editing.id, payload);
        toast.success('Doctor updated');
      } else {
        await doctorAPI.create(payload);
        toast.success('Doctor added');
      }
      setModalOpen(false);
      loadDoctors();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Operation failed');
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Remove this doctor?')) return;
    try {
      await doctorAPI.delete(id);
      toast.success('Doctor removed');
      loadDoctors();
    } catch (err) {
      toast.error('Failed to delete');
    }
  };

  const toggleActive = async (doctor) => {
    try {
      await doctorAPI.update(doctor.id, { is_active: !doctor.is_active });
      toast.success(`Doctor ${doctor.is_active ? 'deactivated' : 'activated'}`);
      loadDoctors();
    } catch (err) {
      toast.error('Failed to update');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-surface-800">Doctors</h1>
          <p className="text-surface-400 text-sm mt-1">{total} registered doctors</p>
        </div>
        <button onClick={openCreate} className="btn-primary flex items-center justify-center gap-2 w-full sm:w-auto">
          <Plus className="w-4 h-4" /> Add Doctor
        </button>
      </div>

      <div className="w-full sm:w-80">
        <SearchInput value={search} onChange={setSearch} placeholder="Search by name..." className="w-full" />
      </div>

      {loading ? (
        <LoadingSpinner />
      ) : doctors.length === 0 ? (
        <EmptyState
          icon={Stethoscope}
          title="No doctors found"
          description="Add doctors to start creating bills with consultation fees."
          action={<button onClick={openCreate} className="btn-primary">Add Doctor</button>}
        />
      ) : (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-5">
          {doctors.map((doc) => (
            <div key={doc.id} className="glass-card-hover p-4 sm:p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-xl bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-lg">
                  <Stethoscope className="w-5 h-5 sm:w-6 sm:h-6 text-white" />
                </div>
                <StatusBadge status={doc.is_active ? 'active' : 'inactive'} />
              </div>
              <h3 className="text-base sm:text-lg font-semibold text-surface-800">Dr. {doc.name}</h3>
              <p className="text-xs sm:text-sm text-primary-600 font-medium mb-1.5">{doc.specialization}</p>
              {doc.qualification && <p className="text-[10px] sm:text-xs text-surface-400 mb-3">{doc.qualification}</p>}
              <div className="flex items-center justify-between pt-3 border-t border-surface-100">
                <p className="text-base sm:text-lg font-bold text-surface-800">₹{Number(doc.consultation_fee).toLocaleString()}</p>
                <div className="flex gap-0.5">
                  <button onClick={() => openEdit(doc)} className="p-2 text-surface-400 hover:text-primary-600" title="Edit">
                    <Pencil className="w-4 h-4" />
                  </button>
                  <button onClick={() => handleDelete(doc.id)} className="p-2 text-surface-400 hover:text-red-500" title="Delete">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </motion.div>
      )}

      <div className="flex justify-center sm:justify-end">
        <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
      </div>

      {/* Modal */}
      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title={editing ? 'Edit Doctor' : 'Add Doctor'}>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="label-text">Full Name *</label>
            <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="input-field" />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="label-text">Specialization *</label>
              <input required value={form.specialization} onChange={(e) => setForm({ ...form, specialization: e.target.value })} className="input-field" />
            </div>
            <div>
              <label className="label-text">Consultation Fee (₹) *</label>
              <input type="number" required min="0" step="0.01" value={form.consultation_fee} onChange={(e) => setForm({ ...form, consultation_fee: e.target.value })} className="input-field" />
            </div>
          </div>
          <div>
            <label className="label-text">Qualification</label>
            <input value={form.qualification} onChange={(e) => setForm({ ...form, qualification: e.target.value })} className="input-field" placeholder="e.g., MBBS, MD" />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="label-text">Phone</label>
              <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} className="input-field" />
            </div>
            <div>
              <label className="label-text">Email</label>
              <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="input-field" />
            </div>
          </div>
          <div>
            <label className="label-text">Availability</label>
            <input value={form.availability} onChange={(e) => setForm({ ...form, availability: e.target.value })} className="input-field" placeholder="e.g., Mon-Fri 9AM-5PM" />
          </div>
          <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 pt-2">
            <button type="button" onClick={() => setModalOpen(false)} className="btn-secondary w-full sm:w-auto">Cancel</button>
            <button type="submit" className="btn-primary w-full sm:w-auto">{editing ? 'Update' : 'Add'} Doctor</button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
