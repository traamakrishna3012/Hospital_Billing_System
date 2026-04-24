import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { authAPI } from '../services/api';

export const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,

      setAuth: (user) => {
        // Ensure is_approved is captured and defaulted for safety
        const userWithApproval = { 
          ...user, 
          is_approved: user?.is_approved ?? false 
        };
        set({
          user: userWithApproval,
          isAuthenticated: true,
        });
      },

      setUser: (user) => set({ user }),

      logout: async () => {
        try {
          // Server clears HttpOnly cookies in the response
          await authAPI.logout({});
        } catch (e) {
          console.error('Logout API failed:', e);
        }
        set({
          user: null,
          isAuthenticated: false,
        });
      },


      isAdmin: () => get().user?.role === 'admin',
      isSuperAdmin: () => get().user?.role === 'superadmin',
    }),
    {
      name: 'hbs-auth',
      // Only persist user profile and auth flag — NOT tokens.
      // Tokens live in HttpOnly cookies managed by the browser.
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
