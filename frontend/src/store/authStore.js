import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { authAPI } from '../services/api';

export const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      // Tokens are now managed as HttpOnly cookies by the browser.
      // We keep these fields for backwards compatibility with the request interceptor,
      // but they are NOT persisted to localStorage (see partialize below).
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,

      setAuth: (user, accessToken, refreshToken) => {
        // Ensure is_approved is captured and defaulted for safety
        const userWithApproval = { 
          ...user, 
          is_approved: user?.is_approved ?? false 
        };
        set({
          user: userWithApproval,
          accessToken,
          refreshToken,
          isAuthenticated: true,
        });
      },

      setTokens: (accessToken, refreshToken) =>
        set({ accessToken, refreshToken }),

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
          accessToken: null,
          refreshToken: null,
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
