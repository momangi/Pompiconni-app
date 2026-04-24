import React, { useState } from 'react';
import { SUPPORTED_WIDTHS, DEFAULT_SIZES } from '../../services/imageUrl';

/**
 * SmartImage — responsive <picture> + srcset + WebP + lazy + async decode.
 *
 * Backend contract:
 *   - every image endpoint accepts ?w=400|800|1600 and ?format=webp|jpg|png
 *   - unknown variants fall back SAFELY to the original (never 500)
 *   - ETag per-variant is enforced; browser cache stays correct
 *
 * Props:
 *   - builder(idOrSlug, {width, format}) -> URL           (required)
 *       e.g. buildIllustrationImageUrl / buildPosterImageUrl / ...
 *   - idOrSlug         — passed to builder (required unless fallbackSrc)
 *   - alt              — REQUIRED (a11y)
 *   - widths           — optional override of variant widths (default 400/800/1600)
 *   - defaultWidth     — width used for the <img src=...> (default 800)
 *   - sizes            — responsive sizes attr (default tuned for cards)
 *   - priority         — true → loading=eager + fetchpriority=high (use only for LCP)
 *   - className        — passthrough
 *   - style            — passthrough
 *   - onClick/onLoad/onError — passthrough
 *   - fallbackSrc      — shown if builder returns empty
 *   - aspectRatio      — optional wrapper aspect (e.g. '4/3')
 *   - rounded          — 'none'|'md'|'lg'|'2xl' — convenience only
 *
 * Fallback strategy:
 *   - If the WebP source fails, the browser silently uses the <img> JPG.
 *   - If everything fails, onError marks a broken state and renders a
 *     neutral placeholder (never a raw broken-image icon).
 */
const roundedMap = {
  none: '',
  md: 'rounded-md',
  lg: 'rounded-lg',
  xl: 'rounded-xl',
  '2xl': 'rounded-2xl',
  full: 'rounded-full',
};

const SmartImage = ({
  builder,
  idOrSlug,
  alt,
  widths = SUPPORTED_WIDTHS,
  defaultWidth = 800,
  sizes = DEFAULT_SIZES,
  priority = false,
  className = '',
  style,
  onClick,
  onLoad,
  onError,
  fallbackSrc = '',
  aspectRatio,
  rounded = 'none',
  objectFit = 'cover',
  'data-testid': dataTestId,
}) => {
  const [broken, setBroken] = useState(false);

  if (!builder || (!idOrSlug && !fallbackSrc)) {
    return (
      <div
        className={`bg-gray-100 ${roundedMap[rounded] || ''} ${className}`}
        style={{ aspectRatio, ...style }}
        data-testid={dataTestId}
        aria-label={alt}
      />
    );
  }

  // If id missing but a static fallbackSrc is provided, serve it plainly.
  if (!idOrSlug && fallbackSrc) {
    return (
      <img
        src={fallbackSrc}
        alt={alt}
        className={`${roundedMap[rounded] || ''} ${className}`}
        style={{ aspectRatio, objectFit, ...style }}
        loading={priority ? 'eager' : 'lazy'}
        decoding="async"
        fetchPriority={priority ? 'high' : 'auto'}
        onClick={onClick}
        onLoad={onLoad}
        onError={onError}
        data-testid={dataTestId}
      />
    );
  }

  if (broken) {
    return (
      <div
        className={`bg-gradient-to-br from-pink-50 to-amber-50 ${roundedMap[rounded] || ''} ${className}`}
        style={{ aspectRatio, ...style }}
        data-testid={dataTestId}
        aria-label={alt}
      />
    );
  }

  const webpSrcSet = widths.map((w) => `${builder(idOrSlug, { width: w, format: 'webp' })} ${w}w`).join(', ');
  const jpgSrcSet  = widths.map((w) => `${builder(idOrSlug, { width: w, format: 'jpg'  })} ${w}w`).join(', ');
  const defaultSrc = builder(idOrSlug, { width: defaultWidth, format: 'jpg' });

  return (
    <picture>
      <source type="image/webp" srcSet={webpSrcSet} sizes={sizes} />
      <source type="image/jpeg" srcSet={jpgSrcSet} sizes={sizes} />
      <img
        src={defaultSrc}
        alt={alt}
        className={`${roundedMap[rounded] || ''} ${className}`}
        style={{ aspectRatio, objectFit, ...style }}
        loading={priority ? 'eager' : 'lazy'}
        decoding="async"
        fetchPriority={priority ? 'high' : 'auto'}
        sizes={sizes}
        onClick={onClick}
        onLoad={onLoad}
        onError={(e) => {
          setBroken(true);
          if (onError) onError(e);
        }}
        data-testid={dataTestId}
      />
    </picture>
  );
};

export default SmartImage;
export { SmartImage };
