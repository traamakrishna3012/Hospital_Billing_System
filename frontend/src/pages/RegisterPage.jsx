import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Building2, Eye, EyeOff } from 'lucide-react';
import toast from 'react-hot-toast';
import { authAPI } from '../services/api';
import { useAuthStore } from '../store/authStore';

export default function RegisterPage() {
  const navigate = useNavigate();
  const { setAuth } = useAuthStore();
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState(1);
  const [form, setForm] = useState({
    clinic_name: '',
    email: '',
    clinic_phone: '',
    clinic_address: '',
    admin_name: '',
    admin_password: '',
  });

  const update = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (step === 1) return setStep(2);

    setLoading(true);
    try {
      const { data } = await authAPI.register(form);
      setAuth(data.user);

      toast.success('Clinic registered successfully!');
      // Redirection logic will be handled by the Route Guard in App.jsx but we'll push them to root/dashboard
      navigate('/'); 
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left Panel */}
      <div className="hidden lg:flex lg:w-1/2 gradient-primary relative overflow-hidden items-center justify-center p-12">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-20 right-20 w-72 h-72 bg-white rounded-full blur-3xl" />
          <div className="absolute bottom-10 left-10 w-96 h-96 bg-purple-300 rounded-full blur-3xl" />
        </div>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="relative z-10 text-white max-w-lg"
        >
          <div className="w-16 h-16 bg-white/20 backdrop-blur-xl rounded-2xl flex items-center justify-center mb-8">
            <Building2 className="w-8 h-8" />
          </div>
          <h1 className="text-4xl font-bold mb-4">Get Started Today</h1>
          <p className="text-lg text-indigo-100 leading-relaxed mb-8">
            Register your clinic in minutes and start managing billing, patients, and analytics with our powerful platform.
          </p>
          <div className="space-y-4">
            {[
              '✓ Free plan available — no credit card required',
              '✓ Set up patients, doctors & tests in minutes',
              '✓ Professional branded PDF receipts',
              '✓ Real-time revenue analytics dashboard',
            ].map((item) => (
              <p key={item} className="text-indigo-100 flex items-center gap-2">{item}</p>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Right Panel — Registration Form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-surface-50">
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="w-full max-w-md"
        >
          <h2 className="text-2xl font-bold text-surface-800 mb-1">Register Your Clinic</h2>
          <p className="text-surface-400 mb-2">Step {step} of 2 — {step === 1 ? 'Clinic Details' : 'Admin Account'}</p>

          {/* Progress Bar */}
          <div className="flex gap-2 mb-8">
            <div className={`h-1.5 flex-1 rounded-full ${step >= 1 ? 'bg-primary-600' : 'bg-surface-200'}`} />
            <div className={`h-1.5 flex-1 rounded-full ${step >= 2 ? 'bg-primary-600' : 'bg-surface-200'}`} />
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {step === 1 ? (
              <>
                <div>
                  <label className="label-text">Clinic / Hospital Name *</label>
                  <input id="clinic_name" name="clinic_name" required value={form.clinic_name} onChange={update('clinic_name')} className="input-field" placeholder="e.g., City Health Clinic" autoComplete="organization" />
                </div>
                <div>
                  <label className="label-text">Email *</label>
                  <input id="email" name="email" type="email" required value={form.email} onChange={update('email')} className="input-field" placeholder="admin@clinic.com" autoComplete="email" />
                  <p className="text-xs text-surface-400 mt-1">This email will be used for login and all communications</p>
                </div>
                <div>
                  <label className="label-text">Phone Number</label>
                  <input id="clinic_phone" name="clinic_phone" value={form.clinic_phone} onChange={update('clinic_phone')} className="input-field" placeholder="+91 98765 43210" autoComplete="tel" />
                </div>
                <div>
                  <label className="label-text">Address</label>
                  <textarea id="clinic_address" name="clinic_address" value={form.clinic_address} onChange={update('clinic_address')} className="input-field resize-none" rows={2} placeholder="Full clinic address" autoComplete="street-address" />
                </div>
                <button type="submit" className="btn-primary w-full py-3">Continue →</button>
              </>
            ) : (
              <>
                <div>
                  <label className="label-text">Your Full Name *</label>
                  <input id="admin_name" name="admin_name" required value={form.admin_name} onChange={update('admin_name')} className="input-field" placeholder="Dr. John Doe" autoComplete="name" />
                </div>
                <div>
                  <label className="label-text">Password *</label>
                  <div className="relative">
                    <input
                      id="admin_password"
                      name="admin_password"
                      type={showPassword ? 'text' : 'password'}
                      required
                      minLength={8}
                      value={form.admin_password}
                      onChange={update('admin_password')}
                      className="input-field pr-12"
                      placeholder="Min 8 chars, 1 uppercase, 1 number"
                      autoComplete="new-password"
                    />
                    <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-surface-400">
                      {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                    </button>
                  </div>
                </div>
                <div className="bg-primary-50 border border-primary-100 rounded-lg p-3">
                  <p className="text-sm text-primary-700">You will log in using: <strong>{form.email}</strong></p>
                </div>
                <div className="flex gap-3">
                  <button type="button" onClick={() => setStep(1)} className="btn-secondary flex-1 py-3">← Back</button>
                  <button type="submit" disabled={loading} className="btn-primary flex-1 py-3">
                    {loading ? 'Creating...' : 'Create Account'}
                  </button>
                </div>
              </>
            )}
          </form>

          <p className="text-center text-sm text-surface-400 mt-8">
            Already have an account?{' '}
            <Link to="/login" className="text-primary-600 font-medium hover:text-primary-700">Sign in</Link>
          </p>
        </motion.div>
      </div>
    </div>
  );
}
