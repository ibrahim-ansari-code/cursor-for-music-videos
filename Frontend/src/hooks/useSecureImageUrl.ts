import { useState, useEffect, useMemo } from 'react';
import { propertyImagesApi } from '../utils/api/propertyImages';

/**
 * Custom hook to fetch secure URLs for Azure blob images
 * 
 * Automatically detects Azure URLs and fetches SAS tokens for private containers.
 * Handles preview URLs (blob:) and already-secured URLs (with ?sv= SAS token).
 * 
 * @param imageUrl - The original image URL (Azure blob URL, blob: preview, or null)
 * @param enabled - Whether to fetch the secure URL (default: true)
 * @returns The secure URL with SAS token, or the original URL if not needed
 * 
 * @example
 * ```typescript
 * const PropertyImage = ({ url }) => {
 *   const secureUrl = useSecureImageUrl(url);
 *   return <img src={secureUrl || url} />;
 * };
 * ```
 */
export const useSecureImageUrl = (
  imageUrl: string | null | undefined,
  enabled: boolean = true
): string | null => {
  const [secureUrl, setSecureUrl] = useState<string | null>(null);

  useEffect(() => {
    const fetchSecureUrl = async () => {
      if (!imageUrl || !enabled) {
        setSecureUrl(null);
        return;
      }

      // Check if it's an Azure blob URL that needs a SAS token
      const isAzureUrl = imageUrl.startsWith('https://') && imageUrl.includes('blob.core.windows.net');
      const alreadyHasSAS = imageUrl.includes('?sv=');
      const isPreviewUrl = imageUrl.startsWith('blob:');

      // If it's a preview URL or already has SAS, use as-is
      if (isPreviewUrl || alreadyHasSAS) {
        setSecureUrl(imageUrl);
        return;
      }

      // If it's an Azure URL without SAS, fetch secure URL
      if (isAzureUrl) {
        try {
          const { secure_url } = await propertyImagesApi.getSecureImageUrl(imageUrl);
          setSecureUrl(secure_url);
        } catch (error) {
          console.error('Failed to fetch secure URL for image:', imageUrl, error);
          // Fallback to original URL (will likely fail but shows error state)
          setSecureUrl(imageUrl);
        }
      } else {
        // Not an Azure URL
        setSecureUrl(imageUrl);
      }
    };

    fetchSecureUrl();
  }, [imageUrl, enabled]);

  return secureUrl;
};

/**
 * Hook to fetch secure URLs for multiple images at once
 * More efficient than calling useSecureImageUrl multiple times
 * 
 * @param imageUrls - Array of image URLs
 * @param enabled - Whether to fetch secure URLs (default: true)
 * @returns Object mapping original URLs to secure URLs
 * 
 * @example
 * ```typescript
 * const PropertyGallery = ({ images }) => {
 *   const secureUrls = useSecureImageUrls(images.map(img => img.url));
 *   return images.map(img => <img src={secureUrls[img.url] || img.url} />);
 * };
 * ```
 */
export const useSecureImageUrls = (
  imageUrls: (string | null | undefined)[],
  enabled: boolean = true
): Record<string, string> => {
  const [secureUrls, setSecureUrls] = useState<Record<string, string>>({});

  // Memoize stringified URLs to prevent unnecessary re-renders
  const stringifiedUrls = useMemo(() => imageUrls.join(','), [imageUrls.join(',')]);

  useEffect(() => {
    const fetchSecureUrls = async () => {
      if (!enabled || imageUrls.length === 0) {
        setSecureUrls({});
        return;
      }

      // Filter for Azure URLs that need SAS tokens
      const azureUrls = imageUrls.filter((url): url is string => 
        !!url && 
        url.startsWith('https://') && 
        url.includes('blob.core.windows.net') &&
        !url.includes('?sv=')  // Don't re-fetch if already has SAS
      );

      if (azureUrls.length === 0) {
        // No Azure URLs to process, use originals
        const urlMap: Record<string, string> = {};
        imageUrls.forEach(url => {
          if (url) urlMap[url] = url;
        });
        setSecureUrls(urlMap);
        return;
      }

      const urlMap: Record<string, string> = {};

      try {
        // Fetch secure URLs in parallel
        const secureUrlPromises = azureUrls.map(async (url) => {
          try {
            const { secure_url } = await propertyImagesApi.getSecureImageUrl(url);
            return { original: url, secure: secure_url };
          } catch (error) {
            console.error(`Failed to get secure URL for image: ${url}`, error);
            return { original: url, secure: url };  // Fallback to original
          }
        });

        const results = await Promise.all(secureUrlPromises);
        
        // Map results
        results.forEach(({ original, secure }) => {
          urlMap[original] = secure;
        });

        // Also map non-Azure URLs to themselves
        imageUrls.forEach(url => {
          if (url && !urlMap[url]) {
            urlMap[url] = url;
          }
        });

        setSecureUrls(urlMap);
      } catch (error) {
        console.error('Failed to fetch secure image URLs:', error);
      }
    };

    fetchSecureUrls();
  }, [stringifiedUrls, enabled]);

  return secureUrls;
};

