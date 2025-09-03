import { useState, useEffect, useRef } from 'react';

export const usePropertiesUI = () => {
  const [showFilterMenu, setShowFilterMenu] = useState(false);
  const [showSortMenu, setShowSortMenu] = useState(false);
  const filterMenuRef = useRef<HTMLDivElement>(null);
  const sortMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      const target = event.target as Node;
      if (
        filterMenuRef.current &&
        !filterMenuRef.current.contains(target)
      ) {
        setShowFilterMenu(false);
      }
      if (sortMenuRef.current && !sortMenuRef.current.contains(target)) {
        setShowSortMenu(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleFilterToggle = () => {
    setShowFilterMenu(!showFilterMenu);
    setShowSortMenu(false);
  };

  const handleSortToggle = () => {
    setShowSortMenu(!showSortMenu);
    setShowFilterMenu(false);
  };

  return {
    showFilterMenu,
    showSortMenu,
    filterMenuRef,
    sortMenuRef,
    handleFilterToggle,
    handleSortToggle,
  };
};