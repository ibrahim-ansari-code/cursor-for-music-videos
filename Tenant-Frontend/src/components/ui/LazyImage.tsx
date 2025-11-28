import React, { useState, useRef, useEffect } from 'react';
import { FaImage } from 'react-icons/fa';
import type { LazyImageProps } from '@/types';

/**
 * Lazy loading image component with fallback and error handling
 */
const LazyImage: React.FC<LazyImageProps & React.HTMLAttributes<HTMLDivElement>> = ({ 
  src, 
  alt, 
  className = '', 
  placeholder = null, 
  onLoad = undefined, 
  onError = undefined,
  ...props 
}) => {
  const [loaded, setLoaded] = useState<boolean>(false);
  const [error, setError] = useState<boolean>(false);
  const [inView, setInView] = useState<boolean>(false);
  const imgRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Guard for SSR/non-DOM environments
    if (typeof window === 'undefined' || !('IntersectionObserver' in window)) {
      setInView(true);
      return;
    }

    const currentRef = imgRef.current;
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setInView(true);
            observer.unobserve(entry.target);
          }
        });
      },
      {
        threshold: 0.1,
        rootMargin: '50px'
      }
    );

    if (currentRef) {
      observer.observe(currentRef);
    }

    return () => {
      if (currentRef) {
        observer.unobserve(currentRef);
      }
      observer.disconnect();
    };
  }, []);

  const handleLoad = () => {
    setLoaded(true);
    if (onLoad) onLoad();
  };

  const handleError = (e: React.SyntheticEvent<HTMLImageElement, Event>) => {
    setError(true);
    setLoaded(false);
    if (onError) onError(e);
  };

  return (
    <div ref={imgRef} className={`relative ${className}`} {...props}>
      {inView && (
        <img
          src={src}
          alt={alt}
          className={`transition-opacity duration-300 ${
            loaded ? 'opacity-100' : 'opacity-0'
          } ${className}`}
          onLoad={handleLoad}
          onError={handleError}
          loading="lazy"
        />
      )}
      
      {(!inView || (!loaded && !error)) && placeholder && (
        <div className="absolute inset-0 flex items-center justify-center">
          {placeholder}
        </div>
      )}
      
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-gray-100 text-gray-400">
          <FaImage className="text-2xl" />
        </div>
      )}
    </div>
  );
};

export default LazyImage;

