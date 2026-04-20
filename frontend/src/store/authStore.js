import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { authAPI } from '../services/api';

export const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
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
        const { refreshToken } = get();
        if (refreshToken) {
          try {
            await authAPI.logout({ refresh_token: refreshToken });
          } catch (e) {
            console.error('Logout API failed:', e);
          }
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
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
