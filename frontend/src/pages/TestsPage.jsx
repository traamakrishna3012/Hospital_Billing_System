import { useState, useEffect, useCallback, useRef } from 'react';
import { motion } from 'framer-motion';
import { FlaskConical, Plus, Pencil, Trash2, Tag, UploadCloud, Download } from 'lucide-react';
import { saveAs } from 'file-saver';
import toast from 'react-hot-toast';
import { testAPI } from '../services/api';
import { SearchInput, Pagination, Modal, EmptyState, LoadingSpinner } from '../components/UI';

export default function TestsPage() {
  const [tests, setTests] = useState([]);
  const [categories, setCategories] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [catModalOpen, setCatModalOpen] = useState(false);
  const [bulkModalOpen, setBulkModalOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState({ name: '', description: '', price: '', code: '', category_id: '' });
  const [catForm, setCatForm] = useState({ name: '', description: '' });
  
  const fileInputRef = useRef(null);

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    const toastId = toast.loading('Uploading and parsing file...');
    try {
      const res = await testAPI.bulkImport(formData);
      toast.success(res.data.message || 'File uploaded successfully', { id: toastId });
      loadTests();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to upload file', { id: toastId });
    } finally {
      // Clear value so the same file can be uploaded again if needed
      e.target.value = null;
    }
  };

  const loadTests = useCallback(async () => {
    setLoading(true);
    try {
      const [testsRes, catsRes] = await Promise.all([
        testAPI.list({ page, page_size: 15, search, category_id: categoryFilter || undefined, active_only: false }),
        testAPI.listCategories(),
      ]);
      setTests(testsRes.data.items);
      setTotal(testsRes.data.total);
      setTotalPages(testsRes.data.total_pages);
      setCategories(catsRes.data);
    } catch (err) {
      toast.error('Failed to load tests');
    } finally {
      setLoading(false);
    }
  }, [page, search, categoryFilter]);

  useEffect(() => { loadTests(); }, [loadTests]);
  useEffect(() => { setPage(1); }, [search, categoryFilter]);

  const openCreate = () => {
    setEditing(null);
    setForm({ name: '', description: '', price: '', code: '', category_id: '' });
    setModalOpen(true);
  };

  const openEdit = (test) => {
    setEditing(test);
    setForm({
      name: test.name, description: test.description || '',
      price: String(test.price), code: test.code || '',
      category_id: test.category_id || '',
    });
    setModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const payload = {
      ...form,
      price: parseFloat(form.price),
      category_id: form.category_id || null,
    };
    try {
      if (editing) {
        await testAPI.update(editing.id, payload);
        toast.success('Test updated');
      } else {
        await testAPI.create(payload);
        toast.success('Test added');
      }
      setModalOpen(false);
      loadTests();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Operation failed');
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this test?')) return;
    try {
      await testAPI.delete(id);
      toast.success('Test deleted');
      loadTests();
    } catch (err) {
      toast.error('Failed to delete');
    }
  };

  const handleCatSubmit = async (e) => {
    e.preventDefault();
    try {
      await testAPI.createCategory(catForm);
      toast.success('Category created');
      setCatModalOpen(false);
      setCatForm({ name: '', description: '' });
      loadTests();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create category');
    }
  };

  const handleExport = async () => {
    const toastId = toast.loading('Downloading Test Master...');
    try {
      const res = await testAPI.exportCSV();
      const blob = new Blob([res.data], { type: 'text/csv' });
      saveAs(blob, 'test_master.csv');
      toast.success('Download complete', { id: toastId });
    } catch (err) {
      toast.error('Failed to download Test Master', { id: toastId });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-surface-800">Tests & Services</h1>
          <p className="text-surface-400 text-sm mt-1">{total} tests registered</p>
        </div>
        <div className="flex flex-wrap gap-2 sm:gap-3">
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileUpload} 
            accept=".csv, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, application/vnd.ms-excel" 
            className="hidden" 
          />
          <button onClick={() => setBulkModalOpen(true)} className="btn-secondary flex items-center justify-center gap-2 flex-1 sm:flex-initial">
             <UploadCloud className="w-4 h-4" /> Bulk Upload
          </button>
          <button onClick={handleExport} className="btn-secondary flex items-center justify-center gap-2 flex-1 sm:flex-initial">
             <Download className="w-4 h-4" /> Download Test Master
          </button>
          <button onClick={() => setCatModalOpen(true)} className="btn-secondary flex items-center justify-center gap-2 flex-1 sm:flex-initial">
            <Tag className="w-4 h-4" /> Add Category
          </button>
          <button onClick={openCreate} className="btn-primary flex items-center justify-center gap-2 w-full sm:w-auto">
            <Plus className="w-4 h-4" /> Add Test
          </button>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
        <div className="flex-1">
          <SearchInput value={search} onChange={setSearch} placeholder="Search tests..." className="w-full" />
        </div>
        <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)} className="input-field sm:w-48">
          <option value="">All Categories</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <LoadingSpinner />
      ) : tests.length === 0 ? (
        <EmptyState
          icon={FlaskConical}
          title="No tests found"
          description="Add medical tests and services to include in billing."
          action={<button onClick={openCreate} className="btn-primary">Add Test</button>}
        />
      ) : (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="glass-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[800px] sm:min-w-0">
              <thead>
                <tr className="bg-surface-50">
                  {['Test Name', 'Code', 'Category', 'Price (MRP)', 'Status', 'Actions'].map((h) => (
                    <th key={h} className="px-4 sm:px-6 py-3 text-left text-xs font-semibold text-surface-500 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-100">
                {tests.map((t) => (
                  <tr key={t.id} className="hover:bg-surface-50/50 transition-colors">
                    <td className="px-4 sm:px-6 py-4">
                      <p className="text-sm font-medium text-surface-800">{t.name}</p>
                      {t.description && <p className="text-[10px] sm:text-xs text-surface-400 truncate max-w-[200px]">{t.description}</p>}
                    </td>
                    <td className="px-4 sm:px-6 py-4 text-sm text-surface-500 font-mono">{t.code || '—'}</td>
                    <td className="px-4 sm:px-6 py-4">
                      {t.category ? (
                        <span className="badge-info text-[10px] sm:text-xs">{t.category.name}</span>
                      ) : (
                        <span className="text-sm text-surface-400">—</span>
                      )}
                    </td>
                    <td className="px-4 sm:px-6 py-4 text-sm font-semibold text-surface-800 whitespace-nowrap">₹{Number(t.price).toLocaleString()}</td>
                    <td className="px-4 sm:px-6 py-4">
                      <span className={t.is_active ? 'badge-success' : 'badge-neutral'}>
                        {t.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-4 sm:px-6 py-4">
                      <div className="flex items-center gap-0.5">
                        <button onClick={() => openEdit(t)} className="p-2 text-surface-400 hover:text-primary-600"><Pencil className="w-4 h-4" /></button>
                        <button onClick={() => handleDelete(t.id)} className="p-2 text-surface-400 hover:text-red-500"><Trash2 className="w-4 h-4" /></button>
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

      {/* Test Modal */}
      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title={editing ? 'Edit Test' : 'Add Test'}>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="label-text">Test Name *</label>
            <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="input-field" placeholder="e.g., Complete Blood Count" />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="label-text">Price (MRP) *</label>
              <input type="number" required min="0" step="0.01" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} className="input-field" />
            </div>
            <div>
              <label className="label-text">Code *</label>
              <input required value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} className="input-field" placeholder="e.g., CBC001" />
            </div>
          </div>
          <div>
            <label className="label-text">Category</label>
            <select value={form.category_id} onChange={(e) => setForm({ ...form, category_id: e.target.value })} className="input-field">
              <option value="">None</option>
              {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
          <div>
            <label className="label-text">Description</label>
            <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="input-field resize-none text-sm" rows={2} />
          </div>
          <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 pt-2">
            <button type="button" onClick={() => setModalOpen(false)} className="btn-secondary w-full sm:w-auto">Cancel</button>
            <button type="submit" className="btn-primary w-full sm:w-auto">{editing ? 'Update' : 'Add'} Test</button>
          </div>
        </form>
      </Modal>

      {/* Category Modal */}
      <Modal isOpen={catModalOpen} onClose={() => setCatModalOpen(false)} title="Add Category" size="sm">
        <form onSubmit={handleCatSubmit} className="space-y-4">
          <div>
            <label className="label-text">Category Name *</label>
            <input required value={catForm.name} onChange={(e) => setCatForm({ ...catForm, name: e.target.value })} className="input-field" placeholder="e.g., Lab, Scan, Consultation" />
          </div>
          <div>
            <label className="label-text">Description</label>
            <textarea value={catForm.description} onChange={(e) => setCatForm({ ...catForm, description: e.target.value })} className="input-field resize-none" rows={2} />
          </div>
          <div className="flex justify-end gap-3">
            <button type="button" onClick={() => setCatModalOpen(false)} className="btn-secondary">Cancel</button>
            <button type="submit" className="btn-primary">Create Category</button>
          </div>
        </form>
      </Modal>

      {/* Bulk Upload Modal */}
      <Modal isOpen={bulkModalOpen} onClose={() => setBulkModalOpen(false)} title="Bulk Upload Tests & Services">
        <div className="space-y-4">
          <div className="bg-surface-50 p-4 rounded-xl border border-surface-100">
            <h4 className="text-sm font-semibold text-surface-800 mb-2">Instructions</h4>
            <ul className="text-xs text-surface-500 space-y-1 list-disc pl-4">
              <li>Supported format: .csv, .xlsx, .xls</li>
              <li>First row must be headers (column names)</li>
              <li>Columns are case-insensitive</li>
            </ul>
          </div>

          <table className="w-full text-xs">
            <thead>
              <tr className="text-left border-b border-surface-100">
                <th className="pb-2">Column Name</th>
                <th className="pb-2">Requirement</th>
                <th className="pb-2">Description</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-100">
              <tr>
                <td className="py-2 font-mono font-bold">code</td>
                <td className="py-2 text-red-500">Mandatory</td>
                <td className="py-2">Unique ID (e.g., LP01)</td>
              </tr>
              <tr>
                <td className="py-2 font-mono font-bold">name</td>
                <td className="py-2 text-red-500">Mandatory</td>
                <td className="py-2">Test Name</td>
              </tr>
              <tr>
                <td className="py-2 font-mono font-bold">price</td>
                <td className="py-2 text-red-500">Mandatory</td>
                <td className="py-2">Base Charge amount</td>
              </tr>
              <tr>
                <td className="py-2 font-mono font-bold">category</td>
                <td className="py-2 text-surface-400">Optional</td>
                <td className="py-2">Group name</td>
              </tr>
              <tr>
                <td className="py-2 font-mono font-bold">description</td>
                <td className="py-2 text-surface-400">Optional</td>
                <td className="py-2">Additional details</td>
              </tr>
            </tbody>
          </table>

          <div className="pt-4 flex flex-col items-center justify-center border-2 border-dashed border-surface-200 rounded-xl p-8 hover:bg-surface-50/50 transition-colors cursor-pointer" onClick={() => fileInputRef.current?.click()}>
            <UploadCloud className="w-8 h-8 text-primary-500 mb-2" />
            <p className="text-sm text-surface-600">Click to select file</p>
            <p className="text-xs text-surface-400 mt-1">Excel or CSV preferred</p>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <button onClick={() => setBulkModalOpen(false)} className="btn-secondary">Close</button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
