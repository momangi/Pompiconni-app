/**
 * React Query client — shared config for all public list endpoints.
 *
 * Conservative defaults:
 * - staleTime 5 min for public lists (illustrations, posters, books, bundles)
 * - 1 retry on failure (avoid hammering the API on transient issues)
 * - refetch-on-window-focus OFF (common UX glitch for editorial content)
 * - refetch-on-mount uses stale check (no waste on hot navigation)
 *
 * Admin mutations should NOT rely on this cache; they manage their own state.
 */
import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,       // 5 minutes
      gcTime: 30 * 60 * 1000,         // keep unused queries for 30 min
      retry: 1,
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 8000),
      refetchOnWindowFocus: false,
      refetchOnReconnect: 'always',
    },
    mutations: {
      retry: 0,
    },
  },
});

/** Query keys — centralized to avoid typos and enable invalidation. */
export const queryKeys = {
  illustrations: ['illustrations'],
  illustration: (id) => ['illustration', id],
  posters: ['posters'],
  poster: (id) => ['poster', id],
  books: ['books'],
  book: (id) => ['book', id],
  bundles: ['bundles'],
  bundle: (id) => ['bundle', id],
  themes: ['themes'],
  games: ['games'],
  siteSettings: ['siteSettings'],
  brandKit: ['brandKit'],
  reviews: ['reviews'],
};

export default queryClient;
