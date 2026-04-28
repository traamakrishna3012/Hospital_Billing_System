import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Receipt, Plus, Eye, Download, Mail, Trash2, Filter,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { format } from 'date-fns';
import { saveAs } from 'file-saver';
import { billAPI, patientAPI, doctorAPI, testAPI, clinicAPI } from '../services/api';
import {
  SearchInput, Pagination, Modal, EmptyState,
  LoadingSpinner, StatusBadge,
} from '../components/UI';

export default function BillingPage() {
  const [bills, setBills] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [loading, setLoading] = useState(true);

  // Create Bill Modal State
  const [createModal, setCreateModal] = useState(false);
  const [detailModal, setDetailModal] = useState(false);
  const [payModal, setPayModal] = useState(false);
  const [selectedBill, setSelectedBill] = useState(null);

  // Form Data
  const [patients, setPatients] = useState([]);
  const [doctors, setDoctors] = useState([]);
  const [tests, setTests] = useState([]);
  const [billForm, setBillForm] = useState({
    patient_id: '',
    doctor_id: '',
    include_doctor_fee: false,
    items: [{ description: '', unit_price: '', quantity: 1, medical_test_id: '' }],
    tax_percent: '0',
    discount_type: 'percent', // 'percent' or 'flat'
    discount_value: '0',
    payment_mode: 'cash',
    transaction_id: '',
    status: 'paid',
    notes: '',
  });

  const [payForm, setPayForm] = useState({ payment_mode: 'cash', transaction_id: '' });

  const [clinicProfile, setClinicProfile] = useState(null);

  const loadBills = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await billAPI.list({ page, page_size: 15, search, status: statusFilter });
      setBills(data.items);
      setTotal(data.total);
      setTotalPages(data.total_pages);
    } catch (err) {
      toast.error('Failed to load bills');
    } finally {
      setLoading(false);
    }
  }, [page, search, statusFilter]);

  useEffect(() => { loadBills(); }, [loadBills]);
  useEffect(() => { setPage(1); }, [search, statusFilter]);

  useEffect(() => {
    clinicAPI.getProfile()
      .then(res => setClinicProfile(res.data))
      .catch(() => {});
  }, []);

  const openCreateModal = async () => {
    try {
      const [pRes, dRes, tRes] = await Promise.all([
        patientAPI.list({ page_size: 100 }),
        doctorAPI.list({ page_size: 100 }),
        testAPI.list({ page_size: 100 }),
      ]);
      setPatients(pRes.data.items);
      setDoctors(dRes.data.items);
      setTests(tRes.data.items);
      setBillForm({
        patient_id: '', doctor_id: '', include_doctor_fee: false,
        items: [{ description: '', unit_price: '', quantity: 1, medical_test_id: '', code: '' }],
        tax_percent: '0', discount_type: 'percent', discount_value: '0', payment_mode: 'cash', transaction_id: '', status: 'paid', notes: '',
      });
      setPatientSearch('');
      setDoctorSearch('');
      setCreateModal(true);
    } catch (err) {
      toast.error('Failed to load form data');
    }
  };

  const addItem = () => {
    setBillForm({
      ...billForm,
      items: [...billForm.items, { description: '', unit_price: '', quantity: 1, medical_test_id: '', code: '' }],
    });
  };

  const removeItem = (index) => {
    if (billForm.items.length <= 1) return;
    setBillForm({
      ...billForm,
      items: billForm.items.filter((_, i) => i !== index),
    });
  };

  const updateItem = (index, field, value) => {
    const newItems = [...billForm.items];

    // Ensure item not already in list
    if (field === 'medical_test_id' && value) {
        if (newItems.some((item, i) => i !== index && item.medical_test_id === value)) {
            toast.error('This test has already been added to the bill.');
            return;
        }
    }

    newItems[index] = { ...newItems[index], [field]: value };

    // Auto-fill from test selection
    if (field === 'medical_test_id' && value) {
      const test = tests.find((t) => t.id === value);
      if (test) {
        newItems[index].description = test.name;
        newItems[index].unit_price = String(test.price);
        newItems[index].code = test.code || '';  // carry the test code
      }
    }
    setBillForm({ ...billForm, items: newItems });
  };

  const calcSubtotal = () => {
    let sub = billForm.items.reduce((sum, item) => {
      return sum + (parseFloat(item.unit_price) || 0) * (parseInt(item.quantity) || 1);
    }, 0);
    if (billForm.include_doctor_fee && billForm.doctor_id) {
       const doc = doctors.find(d => d.id === billForm.doctor_id);
       if (doc) sub += parseFloat(doc.consultation_fee || 0);
    }
    return sub;
  };

  const handleCreateBill = async (e) => {
    e.preventDefault();
    if (['upi', 'card', 'online'].includes(billForm.payment_mode) && !billForm.transaction_id) {
        toast.error('Transaction ID is required for online payments');
        return;
    }

    let discountPct = 0;
    const sub = calcSubtotal();
    const rawValue = parseFloat(billForm.discount_value) || 0;
    if (billForm.discount_type === 'flat') {
        discountPct = sub > 0 ? (rawValue / sub) * 100 : 0;
    } else {
        discountPct = rawValue;
    }

    const payload = {
      patient_id: billForm.patient_id,
      doctor_id: billForm.doctor_id,
      items: billForm.items.map((item) => ({
        description: item.description,
        code: item.code || null,
        unit_price: parseFloat(item.unit_price),
        quantity: parseInt(item.quantity),
        medical_test_id: item.medical_test_id || null,
      })),
      tax_percent: billForm.tax_percent ? parseFloat(billForm.tax_percent) : 0,
      discount_percent: discountPct,
      payment_mode: billForm.payment_mode,
      transaction_id: billForm.transaction_id || undefined,
      status: billForm.status,
      notes: billForm.notes || null,
    };

    if (billForm.include_doctor_fee && billForm.doctor_id) {
       const doc = doctors.find(d => d.id === billForm.doctor_id);
       if (doc && doc.consultation_fee > 0) {
           payload.items.push({
               description: `Consultation Fee: Dr. ${doc.name}`,
               unit_price: parseFloat(doc.consultation_fee),
               quantity: 1,
               medical_test_id: null
           });
       }
    }

    try {
      const response = await billAPI.create(payload);
      toast.success('Bill created successfully!');
      setCreateModal(false);
      loadBills();
      
      // Auto Receipt Generation
      downloadPDF(response.data.id);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create bill');
    }
  };

  const viewBill = async (id) => {
    try {
      const { data } = await billAPI.get(id);
      setSelectedBill(data);
      setDetailModal(true);
    } catch (err) {
      toast.error('Failed to load bill');
    }
  };

  const openPayModal = () => {
    setPayForm({ payment_mode: 'cash', transaction_id: '' });
    setPayModal(true);
  };

  const handlePayNow = async (e) => {
    e.preventDefault();
    if (['upi', 'card', 'online'].includes(payForm.payment_mode) && !payForm.transaction_id) {
        toast.error('Transaction ID is required for online payments');
        return;
    }
    try {
      await billAPI.update(selectedBill.id, {
          status: 'paid',
          payment_mode: payForm.payment_mode,
          transaction_id: payForm.transaction_id || undefined
      });
      toast.success('Payment recorded successfully');
      setPayModal(false);
      setDetailModal(false);
      loadBills();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to record payment');
    }
  };

  const downloadPDF = async (id) => {
    try {
      // Use arraybuffer to guarantee binary-safe transfer (blob can mangle encoding on some browsers)
      const response = await billAPI.downloadPDF(id);
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const billNum = selectedBill?.bill_number || id;
      saveAs(blob, `receipt-${billNum}.pdf`);
      toast.success('PDF downloaded');
    } catch (err) {
      toast.error('Failed to download PDF');
    }
  };



  const sendEmail = async (id) => {
    try {
      await billAPI.sendEmail(id);
      toast.success('Receipt sent to patient');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to send email');
    }
  };

  const deleteBill = async (id) => {
    if (!confirm('Delete this bill?')) return;
    try {
      await billAPI.delete(id);
      toast.success('Bill deleted');
      loadBills();
    } catch (err) {
      toast.error('Failed to delete');
    }
  };

  const [patientSearch, setPatientSearch] = useState('');
  const [doctorSearch, setDoctorSearch] = useState('');
  const [showPatientDropdown, setShowPatientDropdown] = useState(false);
  const [showDoctorDropdown, setShowDoctorDropdown] = useState(false);

  const filteredPatientOptions = patients.filter(p => 
    p.name.toLowerCase().includes(patientSearch.toLowerCase()) ||
    p.phone.includes(patientSearch)
  );

  const filteredDoctorOptions = doctors.filter(d => 
    d.name.toLowerCase().includes(doctorSearch.toLowerCase())
  );

  const subtotal = calcSubtotal();
  let discountAmt = 0;
  if (billForm.discount_type === 'flat') {
    discountAmt = parseFloat(billForm.discount_value) || 0;
  } else {
    discountAmt = subtotal * (parseFloat(billForm.discount_value) || 0) / 100;
  }
  
  const afterDiscount = Math.max(0, subtotal - discountAmt);
  const taxAmt = afterDiscount * (parseFloat(billForm.tax_percent) || 0) / 100;
  const grandTotal = afterDiscount + taxAmt;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-surface-800">Billing</h1>
          <p className="text-surface-400 text-sm mt-1">{total} bills generated</p>
        </div>
        <button onClick={openCreateModal} className="btn-primary flex items-center justify-center gap-2 w-full sm:w-auto">
          <Plus className="w-4 h-4" /> Create Bill
        </button>
      </div>

      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
        <div className="flex-1">
          <SearchInput value={search} onChange={setSearch} placeholder="Search bill number or patient..." className="w-full" />
        </div>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="input-field sm:w-40">
          <option value="">All Status</option>
          <option value="paid">Paid</option>
          <option value="unpaid">Unpaid</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      {loading ? (
        <LoadingSpinner />
      ) : bills.length === 0 ? (
        <EmptyState
          icon={Receipt}
          title="No bills found"
          description="Create your first bill to start generating invoices."
          action={<button onClick={openCreateModal} className="btn-primary">Create Bill</button>}
        />
      ) : (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="glass-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1000px] sm:min-w-0">
              <thead>
                <tr className="bg-surface-50">
                  {['Bill No.', 'Patient', 'Doctor', 'Total', 'Status', 'Payment', 'Date', 'Actions'].map((h) => (
                    <th key={h} className="px-4 sm:px-5 py-3 text-left text-xs font-semibold text-surface-500 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-100">
                {bills.map((bill) => (
                  <tr key={bill.id} className="hover:bg-surface-50/50 transition-colors">
                    <td className="px-4 sm:px-5 py-4 text-sm font-medium text-primary-600">{bill.bill_number}</td>
                    <td className="px-4 sm:px-5 py-4 text-sm text-surface-700">{bill.patient?.name || 'N/A'}</td>
                    <td className="px-4 sm:px-5 py-4 text-sm text-surface-600">{bill.doctor?.name ? `Dr. ${bill.doctor.name}` : '—'}</td>
                    <td className="px-4 sm:px-5 py-4 text-sm font-semibold text-surface-800 whitespace-nowrap">₹{Number(bill.total).toLocaleString()}</td>
                    <td className="px-4 sm:px-5 py-4"><StatusBadge status={bill.status} /></td>
                    <td className="px-4 sm:px-5 py-4 text-sm text-surface-500 uppercase">{bill.payment_mode}</td>
                    <td className="px-4 sm:px-5 py-4 text-sm text-surface-400 whitespace-nowrap">
                      {bill.created_at ? format(new Date(bill.created_at), 'dd MMM yy') : '-'}
                    </td>
                    <td className="px-4 sm:px-5 py-4">
                      <div className="flex items-center gap-0.5">
                        <button onClick={() => viewBill(bill.id)} className="p-2 text-surface-400 hover:text-primary-500" title="View"><Eye className="w-4 h-4" /></button>
                        <button onClick={() => downloadPDF(bill.id)} className="p-2 text-surface-400 hover:text-primary-600" title="Download PDF"><Download className="w-4 h-4" /></button>
                        <button onClick={() => sendEmail(bill.id)} className="p-2 text-surface-400 hover:text-emerald-500" title="Email Receipt"><Mail className="w-4 h-4" /></button>
                        <button onClick={() => deleteBill(bill.id)} className="p-2 text-surface-400 hover:text-red-500" title="Delete"><Trash2 className="w-4 h-4" /></button>
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

      {/* ── Create Bill Modal ──────────────────────────────── */}
      <Modal isOpen={createModal} onClose={() => setCreateModal(false)} title="Create New Bill" size="xl">
        <form onSubmit={handleCreateBill} className="space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="label-text">Find Patient *</label>
              <div className="relative">
                <input 
                  type="text" 
                  placeholder="Search by name or phone..." 
                  value={patientSearch}
                  onFocus={() => setShowPatientDropdown(true)}
                  onBlur={() => setTimeout(() => setShowPatientDropdown(false), 200)}
                  onChange={(e) => {
                    setPatientSearch(e.target.value);
                    setBillForm({ ...billForm, patient_id: '' });
                  }}
                  className="input-field mb-2"
                />
                {showPatientDropdown && filteredPatientOptions.length > 0 && (
                  <ul className="absolute z-10 w-full bg-white border border-surface-200 mt-1 max-h-48 overflow-y-auto rounded-xl shadow-lg">
                    {filteredPatientOptions.map((p) => (
                      <li 
                        key={p.id} 
                        onClick={() => {
                          setBillForm({ ...billForm, patient_id: p.id });
                          setPatientSearch(`${p.name} - ${p.phone}`);
                          setShowPatientDropdown(false);
                        }}
                        className="px-4 py-2 hover:bg-primary-50 cursor-pointer text-sm text-surface-700"
                      >
                        {p.name} <span className="text-surface-400 text-xs">— {p.phone}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
            <div>
              <label className="label-text">Doctor *</label>
              <div className="relative">
                <input 
                  type="text" 
                  placeholder="Type to search doctor..." 
                  value={doctorSearch}
                  onFocus={() => setShowDoctorDropdown(true)}
                  onBlur={() => setTimeout(() => setShowDoctorDropdown(false), 200)}
                  onChange={(e) => {
                    setDoctorSearch(e.target.value);
                    setBillForm({ ...billForm, doctor_id: '', include_doctor_fee: false });
                  }}
                  className="input-field"
                />
                {showDoctorDropdown && filteredDoctorOptions.length > 0 && (
                  <ul className="absolute z-10 w-full bg-white border border-surface-200 mt-1 max-h-48 overflow-y-auto rounded-xl shadow-lg">
                    {filteredDoctorOptions.map((d) => (
                      <li 
                        key={d.id} 
                        onClick={() => {
                          setBillForm({ ...billForm, doctor_id: d.id, include_doctor_fee: false });
                          setDoctorSearch(`Dr. ${d.name}`);
                          setShowDoctorDropdown(false);
                        }}
                        className="px-4 py-2 hover:bg-primary-50 cursor-pointer text-sm text-surface-700 flex justify-between"
                      >
                        <span>Dr. {d.name}</span> <span className="text-surface-400 text-xs">₹{d.consultation_fee}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              {billForm.doctor_id && (
                 <label className="flex items-center gap-2 mt-2 text-sm text-surface-600 cursor-pointer">
                    <input type="checkbox" className="rounded text-primary-600" 
                       checked={billForm.include_doctor_fee}
                       onChange={(e) => setBillForm({ ...billForm, include_doctor_fee: e.target.checked })}
                    />
                    Include Consultation Fee
                 </label>
              )}
            </div>
          </div>

          {/* Line Items */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <label className="label-text mb-0">Bill Items *</label>
              <button type="button" onClick={addItem} className="text-sm text-primary-600 font-medium hover:text-primary-700">+ Add Item</button>
            </div>
            <div className="space-y-4">
              {billForm.items.map((item, i) => (
                <div key={i} className="relative p-4 bg-surface-50 rounded-2xl border border-surface-100">
                  <button 
                    type="button" 
                    onClick={() => removeItem(i)} 
                    className="absolute -top-2 -right-2 w-7 h-7 bg-white border border-red-100 rounded-full flex items-center justify-center text-red-500 shadow-sm hover:bg-red-50"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                  
                  <div className="grid grid-cols-1 sm:grid-cols-12 gap-3">
                    <div className="sm:col-span-4">
                      <label className="text-[10px] uppercase font-bold text-surface-400 mb-1 block tracking-wider">Select Test</label>
                      <select value={item.medical_test_id} onChange={(e) => updateItem(i, 'medical_test_id', e.target.value)} className="input-field text-sm py-2">
                        <option value="">Custom Item</option>
                        {tests.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
                      </select>
                    </div>
                    <div className="sm:col-span-4">
                      <label className="text-[10px] uppercase font-bold text-surface-400 mb-1 block tracking-wider">Description</label>
                      <input required value={item.description} onChange={(e) => updateItem(i, 'description', e.target.value)} className="input-field text-sm py-2" />
                    </div>
                    <div className="grid grid-cols-2 sm:col-span-4 gap-3">
                      <div>
                        <label className="text-[10px] uppercase font-bold text-surface-400 mb-1 block tracking-wider">Price</label>
                        <input type="number" required min="0" step="0.01" value={item.unit_price} onChange={(e) => updateItem(i, 'unit_price', e.target.value)} className="input-field text-sm py-2" />
                      </div>
                      <div>
                        <label className="text-[10px] uppercase font-bold text-surface-400 mb-1 block tracking-wider">Qty</label>
                        <input type="number" min="1" value={item.quantity} onChange={(e) => updateItem(i, 'quantity', e.target.value)} className="input-field text-sm py-2" />
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Payment Details */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div>
              <label className="label-text">Tax (%)</label>
              <input type="number" min="0" max="100" step="0.01" value={billForm.tax_percent} onChange={(e) => setBillForm({ ...billForm, tax_percent: e.target.value })} className="input-field" placeholder="18" />
            </div>
            <div>
              <label className="label-text">Discount</label>
              <div className="relative flex items-center">
                <input 
                   type="number" min="0" step="0.01" value={billForm.discount_value} 
                   onChange={(e) => setBillForm({ ...billForm, discount_value: e.target.value })} 
                   className="input-field pr-12 text-sm" placeholder="0" 
                />
                <select 
                   value={billForm.discount_type}
                   onChange={(e) => setBillForm({ ...billForm, discount_type: e.target.value })}
                   className="absolute right-[1px] h-[calc(100%-2px)] rounded-r-xl border-l border-surface-200 bg-surface-50 px-1 text-surface-600 text-xs focus:outline-none"
                >
                  <option value="percent">%</option>
                  <option value="flat">₹</option>
                </select>
              </div>
            </div>
            <div>
              <label className="label-text">Mode</label>
              <select value={billForm.payment_mode} onChange={(e) => setBillForm({ ...billForm, payment_mode: e.target.value, transaction_id: '' })} className="input-field text-sm">
                <option value="cash">Cash</option>
                <option value="card">Card</option>
                <option value="upi">UPI</option>
                <option value="online">Online</option>
              </select>
            </div>
            {['upi', 'card', 'online'].includes(billForm.payment_mode) && (
              <div>
                <label className="label-text">Transaction ID *</label>
                <input required value={billForm.transaction_id} onChange={(e) => setBillForm({ ...billForm, transaction_id: e.target.value })} className="input-field text-sm" placeholder="e.g. TXN12345" />
              </div>
            )}
            <div>
              <label className="label-text">Status</label>
              <select value={billForm.status} onChange={(e) => setBillForm({ ...billForm, status: e.target.value })} className="input-field text-sm">
                <option value="paid">Paid</option>
                <option value="unpaid">Unpaid</option>
              </select>
            </div>
          </div>

          <div>
            <label className="label-text">Notes</label>
            <textarea value={billForm.notes} onChange={(e) => setBillForm({ ...billForm, notes: e.target.value })} className="input-field resize-none text-sm" rows={2} />
          </div>

          {/* Totals Preview */}
          <div className="bg-surface-50 rounded-2xl p-4 space-y-2 text-sm border border-surface-100">
            <div className="flex justify-between"><span className="text-surface-500">Subtotal</span><span className="font-medium">₹{subtotal.toLocaleString()}</span></div>
            {discountAmt > 0 && <div className="flex justify-between text-emerald-600"><span>Discount</span><span>- ₹{discountAmt.toFixed(2)}</span></div>}
            <div className="flex justify-between"><span className="text-surface-500">GST ({billForm.tax_percent || 0}%)</span><span>₹{taxAmt.toFixed(2)}</span></div>
            <div className="flex justify-between pt-2 border-t border-surface-200 text-base font-bold text-surface-800">
              <span>Grand Total</span><span>₹{grandTotal.toFixed(2)}</span>
            </div>
          </div>

          <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 pt-2">
            <button type="button" onClick={() => setCreateModal(false)} className="btn-secondary w-full sm:w-auto">Cancel</button>
            <button type="submit" className="btn-primary w-full sm:w-auto">Create Bill</button>
          </div>
        </form>
      </Modal>

      {/* ── Bill Detail Modal ──────────────────────────────── */}
      <Modal isOpen={detailModal} onClose={() => setDetailModal(false)} title={`Bill #${selectedBill?.bill_number || ''}`} size="lg">
        {selectedBill && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-6">
              <div>
                <p className="text-xs text-surface-400 mb-1">Patient</p>
                <p className="font-semibold text-surface-800">{selectedBill.patient?.name || 'N/A'}</p>
                <p className="text-sm text-surface-500">{selectedBill.patient?.phone || '—'}</p>
              </div>
              <div>
                <p className="text-xs text-surface-400 mb-1">Doctor</p>
                <p className="font-semibold text-surface-800">
                  {selectedBill.doctor?.name ? `Dr. ${selectedBill.doctor.name}` : 'N/A'}
                </p>
              </div>
            </div>

            <div className="overflow-x-auto border border-surface-200 rounded-xl">
              <table className="w-full">
                <thead>
                  <tr className="bg-surface-50">
                    <th className="px-4 py-2 text-xs text-left font-semibold text-surface-500">#</th>
                    <th className="px-4 py-2 text-xs text-left font-semibold text-surface-500">Description</th>
                    <th className="px-4 py-2 text-xs text-right font-semibold text-surface-500">Qty</th>
                    <th className="px-4 py-2 text-xs text-right font-semibold text-surface-500">Price</th>
                    <th className="px-4 py-2 text-xs text-right font-semibold text-surface-500">Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-100">
                  {selectedBill.items?.map((item, i) => (
                    <tr key={item.id || i}>
                      <td className="px-4 py-2 text-sm text-surface-500">{i + 1}</td>
                      <td className="px-4 py-2 text-sm text-surface-800">{item.description}</td>
                      <td className="px-4 py-2 text-sm text-right">{item.quantity}</td>
                      <td className="px-4 py-2 text-sm text-right">₹{Number(item.unit_price || 0).toLocaleString()}</td>
                      <td className="px-4 py-2 text-sm text-right font-medium">₹{Number(item.total || 0).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="bg-surface-50 rounded-xl p-4 space-y-2 text-sm">
              <div className="flex justify-between">
                <span>Subtotal</span>
                <span>₹{Number(selectedBill.subtotal || 0).toLocaleString()}</span>
              </div>
              {Number(selectedBill.discount_amount) > 0 && (
                <div className="flex justify-between text-emerald-600">
                  <span>Discount ({selectedBill.discount_percent}%)</span>
                  <span>- ₹{Number(selectedBill.discount_amount).toLocaleString()}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span>GST ({selectedBill.tax_percent || 18}%)</span>
                <span>₹{Number(selectedBill.tax_amount || 0).toLocaleString()}</span>
              </div>
              <div className="flex justify-between pt-2 border-t border-surface-200 text-lg font-bold">
                <span>Total</span>
                <span className="text-primary-600">₹{Number(selectedBill.total || 0).toLocaleString()}</span>
              </div>
              <div className="mt-4 pt-4 border-t border-surface-200">
                <div className="flex justify-between text-sm">
                  <span className="text-surface-500">Payment Mode</span>
                  <span className="text-surface-900 font-medium capitalize">{selectedBill.payment_mode}</span>
                </div>
                {selectedBill.transaction_id && (
                  <div className="flex justify-between text-sm mt-1">
                    <span className="text-surface-500">Transaction ID</span>
                    <span className="text-surface-900 font-medium">{selectedBill.transaction_id}</span>
                  </div>
                )}
              </div>
            </div>

            <div className="flex gap-3 mt-8">
              {selectedBill.status === 'unpaid' && (
                <button onClick={openPayModal} className="btn-primary flex items-center gap-2 mr-auto">
                  Pay Now
                </button>
              )}
              <button onClick={() => downloadPDF(selectedBill.id)} className="btn-secondary flex items-center gap-2">
                <Download className="w-4 h-4" /> Download PDF
              </button>
              <button onClick={() => sendEmail(selectedBill.id)} className="btn-secondary flex items-center gap-2">
                <Mail className="w-4 h-4" /> Send Receipt
              </button>
            </div>
          </div>
        )}
      </Modal>

      {/* ── Pay Now Modal ──────────────────────────────── */}
      <Modal isOpen={payModal} onClose={() => setPayModal(false)} title="Record Payment" size="sm">
        <form onSubmit={handlePayNow} className="space-y-4">
          <div>
            <label className="label-text">Payment Mode</label>
            <select value={payForm.payment_mode} onChange={(e) => setPayForm({ ...payForm, payment_mode: e.target.value, transaction_id: '' })} className="input-field">
              <option value="cash">Cash</option>
              <option value="card">Card</option>
              <option value="upi">UPI</option>
              <option value="online">Online</option>
            </select>
          </div>
          {['upi', 'card', 'online'].includes(payForm.payment_mode) && (
            <div>
              <label className="label-text">Transaction ID *</label>
              <input required value={payForm.transaction_id} onChange={(e) => setPayForm({ ...payForm, transaction_id: e.target.value })} className="input-field" placeholder="e.g. TXN12345" />
            </div>
          )}
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={() => setPayModal(false)} className="btn-secondary">Cancel</button>
            <button type="submit" className="btn-primary">Confirm Payment</button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
