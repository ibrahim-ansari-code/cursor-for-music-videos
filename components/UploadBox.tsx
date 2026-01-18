"use client";

import React, { useState, useRef } from "react";

interface UploadBoxProps {
  onFilesSelect: (files: File[]) => void;
  accept?: string;
  multiple?: boolean;
  accentColor?: string;
  title: string;
  description: string;
  icon?: React.ReactNode;
}

export default function UploadBox({
  onFilesSelect,
  accept = "*/*",
  multiple = false,
  accentColor = "bg-comic-blue",
  title,
  description,
  icon,
}: UploadBoxProps) {
  const [dragActive, setDragActive] = useState(false);
  const [fileCount, setFileCount] = useState(0);
  const [mainFileName, setMainFileName] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleFiles = (files: FileList | null) => {
    if (files && files.length > 0) {
      const fileArray = Array.from(files);
      setFileCount(fileArray.length);
      setMainFileName(fileArray[0].name);
      onFilesSelect(fileArray);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    handleFiles(e.dataTransfer.files);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    handleFiles(e.target.files);
  };

  const onButtonClick = () => {
    inputRef.current?.click();
  };

  return (
    <div
      className={`relative w-full p-8 bg-white comic-border rounded-2xl transition-all h-full flex flex-col ${
        dragActive ? "scale-105 ring-4 ring-black/10" : ""
      }`}
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={handleDrop}
    >
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        accept={accept}
        multiple={multiple}
        onChange={handleChange}
      />

      <div className="flex-1 flex flex-col items-center justify-center border-2 border-dashed border-black/20 rounded-xl p-6 bg-comic-bg/30">
        <div className={`w-16 h-16 ${accentColor} rounded-full flex items-center justify-center mb-4 comic-border transform -rotate-3`}>
          {icon || (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-8 w-8 text-white"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 4v16m8-8H4"
              />
            </svg>
          )}
        </div>

        <h3 className="font-bangers text-2xl mb-1">{title}</h3>
        <p className="font-comic text-center text-sm text-gray-600 mb-4 px-4">
          {description}
        </p>

        <div className="flex flex-col items-center w-full">
          {fileCount > 0 ? (
            <div className="text-center w-full">
              <p className="text-comic-blue font-bold truncate max-w-full px-2">
                {multiple && fileCount > 1 
                  ? `${fileCount} files selected` 
                  : mainFileName}
              </p>
            </div>
          ) : (
            <p className="text-xs text-gray-400 italic mb-2">Drag & drop or click browse</p>
          )}

          <button
            type="button"
            onClick={onButtonClick}
            className={`mt-4 ${accentColor} comic-button text-sm py-2 px-6 hover:brightness-110`}
          >
            {fileCount > 0 ? "CHANGE FILES" : "BROWSE"}
          </button>
        </div>
      </div>

      {/* Decorative corner elements */}
      <div className="absolute top-3 right-3 flex space-x-1.5">
        <div className="w-2.5 h-2.5 rounded-full bg-comic-red border border-black" />
        <div className="w-2.5 h-2.5 rounded-full bg-comic-blue border border-black" />
      </div>
    </div>
  );
}
