import React from 'react';

interface SearchInputProps {
  searchTerm: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

export const SearchInput: React.FC<SearchInputProps> = ({
  searchTerm,
  onChange,
}) => (
  <div className="relative flex-1 max-w-md">
    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
      <i className="fas fa-search text-gray-400"></i>
    </div>
    <input
      type="text"
      className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-600 focus:border-blue-600 sm:text-sm"
      placeholder="Search properties..."
      value={searchTerm}
      onChange={onChange}
    />
  </div>
);