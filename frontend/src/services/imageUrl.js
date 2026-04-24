/**
 * Image URL builder — single source of truth for backend media endpoints.
 *
 * Usage:
 *   import { buildIllustrationImageUrl, buildImageSrcSet } from '../services/imageUrl';
 *   const src = buildIllustrationImageUrl(id, { width: 400, format: 'webp' });
 *
 * Philosophy:
 * - Never concatenate image URLs inline. Always go through here.
 * - Always pass through REACT_APP_BACKEND_URL so prod + preview work identically.
 * - Supported widths: 400, 800, 1600. Backend falls back to original on others.
 */

const API_BASE = (process.env.REACT_APP_BACKEND_URL || '').replace(/\/$/, '');

export const SUPPORTED_WIDTHS = [400, 800, 1600];
export const DEFAULT_SIZES = '(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 400px';

function _qs({ width, format } = {}) {
  const parts = [];
  if (width) parts.push(`w=${encodeURIComponent(width)}`);
  if (format) parts.push(`format=${encodeURIComponent(format)}`);
  return parts.length ? `?${parts.join('&')}` : '';
}

/* ---------- Primary endpoint builders ---------- */

export const buildIllustrationImageUrl = (id, opts = {}) =>
  id ? `${API_BASE}/api/illustrations/${encodeURIComponent(id)}/image${_qs(opts)}` : '';

export const buildPosterImageUrl = (id, opts = {}) =>
  id ? `${API_BASE}/api/posters/${encodeURIComponent(id)}/image${_qs(opts)}` : '';

export const buildBookCoverUrl = (id, opts = {}) =>
  id ? `${API_BASE}/api/books/${encodeURIComponent(id)}/cover${_qs(opts)}` : '';

export const buildThemeBackgroundUrl = (id, opts = {}) =>
  id ? `${API_BASE}/api/themes/${encodeURIComponent(id)}/background-image${_qs(opts)}` : '';

export const buildBundleBackgroundUrl = (id, opts = {}) =>
  id ? `${API_BASE}/api/bundles/${encodeURIComponent(id)}/background-image${_qs(opts)}` : '';

export const buildHeroImageUrl = (opts = {}) =>
  `${API_BASE}/api/site/hero-image${_qs(opts)}`;

export const buildBrandLogoUrl = (opts = {}) =>
  `${API_BASE}/api/site/brand-logo${_qs(opts)}`;

export const buildGameThumbnailUrl = (slug, opts = {}) =>
  slug ? `${API_BASE}/api/games/${encodeURIComponent(slug)}/thumbnail${_qs(opts)}` : '';

export const buildGameCardImageUrl = (slug, opts = {}) =>
  slug ? `${API_BASE}/api/games/${encodeURIComponent(slug)}/card-image${_qs(opts)}` : '';

export const buildGamePageImageUrl = (slug, opts = {}) =>
  slug ? `${API_BASE}/api/games/${encodeURIComponent(slug)}/page-image${_qs(opts)}` : '';

export const buildCharacterImageUrl = (trait, opts = {}) =>
  trait ? `${API_BASE}/api/character-images/${encodeURIComponent(trait)}/image${_qs(opts)}` : '';

/* ---------- srcset helpers ---------- */

/**
 * Build a srcset string for the 3 supported widths.
 * Example:
 *   buildImageSrcSet(buildIllustrationImageUrl, id, 'webp')
 *   -> "…/image?w=400&format=webp 400w, …/image?w=800&format=webp 800w, …"
 */
export const buildImageSrcSet = (builderFn, idOrSlug, format) =>
  SUPPORTED_WIDTHS
    .map((w) => `${builderFn(idOrSlug, { width: w, format })} ${w}w`)
    .join(', ');

export default {
  buildIllustrationImageUrl,
  buildPosterImageUrl,
  buildBookCoverUrl,
  buildThemeBackgroundUrl,
  buildBundleBackgroundUrl,
  buildHeroImageUrl,
  buildBrandLogoUrl,
  buildGameThumbnailUrl,
  buildGameCardImageUrl,
  buildGamePageImageUrl,
  buildCharacterImageUrl,
  buildImageSrcSet,
  SUPPORTED_WIDTHS,
  DEFAULT_SIZES,
};
