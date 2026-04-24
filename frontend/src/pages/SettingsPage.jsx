import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Settings, Upload, Building2, Save, Key } from 'lucide-react';
import toast from 'react-hot-toast';
import { clinicAPI, authAPI } from '../services/api';
import { LoadingSpinner } from '../components/UI';

export default function SettingsPage() {
  const [clinic, setClinic] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({});

  // Password change state
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  });
  const [changing, setChanging] = useState(false);
  
  useEffect(() => {
    loadClinic();
  }, []);

  const loadClinic = async () => {
    try {
      const { data } = await clinicAPI.getProfile();
      setClinic(data);
      setForm({
        name: data.name || '', email: data.email || '', phone: data.phone || '',
        address: data.address || '', city: data.city || '', state: data.state || '',
        pincode: data.pincode || '', website: data.website || '', tagline: data.tagline || '',
        biller_header: data.biller_header || '',
        tax_percent: String(data.tax_percent || 18), currency: data.currency || 'INR',
      });
    } catch (err) {
      toast.error('Failed to load clinic settings');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = { ...form, tax_percent: parseFloat(form.tax_percent) };
      const { data } = await clinicAPI.updateProfile(payload);
      setClinic(data);
      toast.success('Settings saved');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const handleLogoUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
      const { data } = await clinicAPI.uploadLogo(formData);
      setClinic(data);
      toast.success('Logo uploaded');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Upload failed');
    }
  };

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      return toast.error('New passwords do not match');
    }
    
    setChanging(true);
    try {
      await authAPI.changePassword({
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password,
      });
      toast.success('Password updated successfully');
      setPasswordForm({ current_password: '', new_password: '', confirm_password: '' });
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update password');
    } finally {
      setChanging(false);
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="space-y-6 max-w-4xl pb-10">
      <div>
        <h1 className="text-2xl font-bold text-surface-800">Clinic Settings</h1>
        <p className="text-surface-400 mt-1">Manage your clinic's profile and billing defaults</p>
      </div>

      <div className="grid grid-cols-1 gap-6">
        {/* Logo Section */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="glass-card p-6">
          <h2 className="text-lg font-semibold text-surface-800 mb-4">Clinic Logo</h2>
          <div className="flex items-center gap-6">
            <div className="w-24 h-24 rounded-2xl bg-surface-100 border-2 border-dashed border-surface-300 flex items-center justify-center overflow-hidden">
              {clinic?.logo_url ? (
                <img 
                  src={clinic.logo_url} 
                  alt="Clinic Logo" 
                  className="w-full h-full object-cover" 
                />
              ) : (
                <Building2 className="w-10 h-10 text-surface-300" />
              )}
            </div>
            <div>
              <label className="btn-secondary cursor-pointer inline-flex items-center gap-2">
                <Upload className="w-4 h-4" /> Upload Logo
                <input type="file" accept="image/*" onChange={handleLogoUpload} className="hidden" />
              </label>
              <p className="text-xs text-surface-400 mt-2">PNG, JPG, or WebP. Max 5MB.</p>
            </div>
          </div>
        </motion.div>

        {/* Clinic Details */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="glass-card p-6">
          <h2 className="text-lg font-semibold text-surface-800 mb-4">Clinic Information</h2>
          <form onSubmit={handleSave} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label-text">Clinic Name</label>
                <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="input-field" />
              </div>
              <div>
                <label className="label-text">Email</label>
                <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="input-field" />
              </div>
              <div>
                <label className="label-text">Phone</label>
                <input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} className="input-field" />
              </div>
              <div>
                <label className="label-text">Website</label>
                <input value={form.website} onChange={(e) => setForm({ ...form, website: e.target.value })} className="input-field" />
              </div>
            </div>

            <div>
              <label className="label-text">Address</label>
              <textarea value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} className="input-field resize-none" rows={2} />
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div><label className="label-text">City</label><input value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} className="input-field" /></div>
              <div><label className="label-text">State</label><input value={form.state} onChange={(e) => setForm({ ...form, state: e.target.value })} className="input-field" /></div>
              <div><label className="label-text">Pincode</label><input value={form.pincode} onChange={(e) => setForm({ ...form, pincode: e.target.value })} className="input-field" /></div>
            </div>

            <div>
              <label className="label-text">Tagline (shown on receipts)</label>
              <input value={form.tagline} onChange={(e) => setForm({ ...form, tagline: e.target.value })} className="input-field" placeholder="e.g., Caring for your health since 1990" />
            </div>

            <div>
              <label className="label-text">Biller Header (Full address/GST details for Invoice)</label>
              <textarea value={form.biller_header} onChange={(e) => setForm({ ...form, biller_header: e.target.value })} className="input-field resize-none" rows={3} placeholder="Enter full clinic name, address, GSTIN, and License info to show on bills" />
              <p className="text-[10px] text-surface-400 mt-1">This will be printed prominently on the bill header.</p>
            </div>

            <h3 className="text-md font-semibold text-surface-800 pt-4">Billing Defaults</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label-text">Default Tax Rate (%)</label>
                <input type="number" min="0" max="100" step="0.01" value={form.tax_percent} onChange={(e) => setForm({ ...form, tax_percent: e.target.value })} className="input-field" />
              </div>
              <div>
                <label className="label-text">Currency</label>
                <select value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })} className="input-field">
                  <option value="INR">INR (₹)</option>
                  <option value="USD">USD ($)</option>
                  <option value="EUR">EUR (€)</option>
                </select>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button type="submit" disabled={saving} className="btn-primary flex items-center gap-2">
                <Save className="w-4 h-4" /> {saving ? 'Saving...' : 'Save Settings'}
              </button>
            </div>
          </form>
        </motion.div>

        {/* Change Password Section */}
        <motion.div 
          initial={{ opacity: 0, y: 10 }} 
          animate={{ opacity: 1, y: 0 }} 
          transition={{ delay: 0.2 }}
          className="glass-card p-6 border-t-4 border-t-primary-500"
        >
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-indigo-50 rounded-lg text-indigo-600">
              <Key className="w-5 h-5" />
            </div>
            <h2 className="text-lg font-semibold text-surface-800">Security & Password</h2>
          </div>

          <form onSubmit={handlePasswordChange} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="label-text">Current Password</label>
                <input 
                  type="password" 
                  required
                  value={passwordForm.current_password}
                  onChange={(e) => setPasswordForm({ ...passwordForm, current_password: e.target.value })}
                  className="input-field" 
                  placeholder="••••••••"
                />
              </div>
              <div>
                <label className="label-text">New Password</label>
                <input 
                  type="password" 
                  required
                  minLength={8}
                  value={passwordForm.new_password}
                  onChange={(e) => setPasswordForm({ ...passwordForm, new_password: e.target.value })}
                  className="input-field" 
                  placeholder="••••••••"
                />
              </div>
              <div>
                <label className="label-text">Confirm New Password</label>
                <input 
                  type="password" 
                  required
                  value={passwordForm.confirm_password}
                  onChange={(e) => setPasswordForm({ ...passwordForm, confirm_password: e.target.value })}
                  className="input-field" 
                  placeholder="••••••••"
                />
              </div>
            </div>
            
            <p className="text-[10px] text-surface-400">
              Password must be at least 8 characters long and include an uppercase letter and a digit.
            </p>

            <div className="flex justify-end pt-2">
              <button 
                type="submit" 
                disabled={changing} 
                className="btn-primary flex items-center gap-2"
              >
                <Key className="w-4 h-4" /> 
                {changing ? 'Updating...' : 'Update Password'}
              </button>
            </div>
          </form>
        </motion.div>
      </div>
    </div>
  );
}

