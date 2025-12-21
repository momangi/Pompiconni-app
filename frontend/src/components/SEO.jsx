import { useEffect } from 'react';

/**
 * SEO Component - Gestisce title e meta description per ogni pagina
 * Pattern: "Nome Pagina – Poppiconni"
 */
const SEO = ({ 
  title, 
  description,
  canonical,
  noindex = false 
}) => {
  useEffect(() => {
    // Imposta il title
    const fullTitle = title 
      ? `${title} – Poppiconni` 
      : 'Poppiconni – Disegni da colorare per bambini';
    document.title = fullTitle;

    // Meta description
    const metaDescription = document.querySelector('meta[name="description"]');
    if (metaDescription && description) {
      metaDescription.setAttribute('content', description);
    }

    // Open Graph title
    const ogTitle = document.querySelector('meta[property="og:title"]');
    if (ogTitle) {
      ogTitle.setAttribute('content', fullTitle);
    }

    // Open Graph description
    const ogDesc = document.querySelector('meta[property="og:description"]');
    if (ogDesc && description) {
      ogDesc.setAttribute('content', description);
    }

    // Twitter title
    const twitterTitle = document.querySelector('meta[name="twitter:title"]');
    if (twitterTitle) {
      twitterTitle.setAttribute('content', fullTitle);
    }

    // Twitter description
    const twitterDesc = document.querySelector('meta[name="twitter:description"]');
    if (twitterDesc && description) {
      twitterDesc.setAttribute('content', description);
    }

    // Canonical URL
    let canonicalTag = document.querySelector('link[rel="canonical"]');
    if (canonical) {
      if (!canonicalTag) {
        canonicalTag = document.createElement('link');
        canonicalTag.setAttribute('rel', 'canonical');
        document.head.appendChild(canonicalTag);
      }
      canonicalTag.setAttribute('href', canonical);
    }

    // Robots noindex
    let robotsTag = document.querySelector('meta[name="robots"]');
    if (noindex) {
      if (!robotsTag) {
        robotsTag = document.createElement('meta');
        robotsTag.setAttribute('name', 'robots');
        document.head.appendChild(robotsTag);
      }
      robotsTag.setAttribute('content', 'noindex, nofollow');
    } else if (robotsTag) {
      robotsTag.setAttribute('content', 'index, follow');
    }

  }, [title, description, canonical, noindex]);

  return null; // Componente invisibile
};

export default SEO;
