/**
 * React Query hooks for public data. Centralized so feature pages can share
 * caches (e.g. GalleryPage themes + LandingPage themes hit the same cache).
 */
import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '../services/queryClient';
import {
  getThemes,
  getIllustrations,
  getPublicPosters,
  getBooks,
  getBundles,
  getGames,
  getReviews,
  getSiteSettings,
  getBrandKit,
} from '../services/api';

export const useThemes = () =>
  useQuery({ queryKey: queryKeys.themes, queryFn: getThemes });

export const useIllustrations = (themeId) =>
  useQuery({
    queryKey: themeId ? ['illustrations', 'theme', themeId] : queryKeys.illustrations,
    queryFn: () => getIllustrations(themeId),
  });

export const usePosters = () =>
  useQuery({ queryKey: queryKeys.posters, queryFn: getPublicPosters });

export const useBooks = () =>
  useQuery({ queryKey: queryKeys.books, queryFn: getBooks });

export const useBundles = () =>
  useQuery({ queryKey: queryKeys.bundles, queryFn: getBundles });

export const useGames = () =>
  useQuery({ queryKey: queryKeys.games, queryFn: getGames });

export const useReviews = () =>
  useQuery({ queryKey: queryKeys.reviews, queryFn: getReviews });

export const useSiteSettings = () =>
  useQuery({ queryKey: queryKeys.siteSettings, queryFn: getSiteSettings });

export const useBrandKit = () =>
  useQuery({ queryKey: queryKeys.brandKit, queryFn: getBrandKit });
