"use client";

import React, { useState } from "react";

interface UrlInputBoxProps {
  onUrlChange: (url: string | string[]) => void;
  onValidationChange?: (isValid: boolean) => void;
  multiple?: boolean;
  accentColor?: string;
  title: string;
  description: string;
  placeholder?: string;
  icon?: React.ReactNode;
}

export default function UrlInputBox({
  onUrlChange,
  onValidationChange,
  multiple = false,
  accentColor = "bg-comic-blue",
  title,
  description,
  placeholder,
  icon,
}: UrlInputBoxProps) {
  const [multiUrls, setMultiUrls] = useState<string[]>([""]);
  const [singleUrl, setSingleUrl] = useState<string>("");
  const [singleError, setSingleError] = useState<boolean>(false);
  const [multiErrors, setMultiErrors] = useState<boolean[]>([false]);

  const isValidUrl = (url: string) => {
    if (!url.trim()) return true; // Don't show error for empty input
    try {
      const parsedUrl = new URL(url);
      return parsedUrl.protocol === "http:" || parsedUrl.protocol === "https:";
    } catch {
      return false;
    }
  };

  const handleSingleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.trim();
    setSingleUrl(value);
    const isValid = isValidUrl(value);
    setSingleError(!isValid);
    onUrlChange(value);
    if (onValidationChange) {
      onValidationChange(isValid && value !== "");
    }
  };

  const handleMultiChange = (index: number, value: string) => {
    const newUrls = [...multiUrls];
    newUrls[index] = value;
    setMultiUrls(newUrls);

    const newErrors = [...multiErrors];
    const isValidEntry = isValidUrl(value);
    newErrors[index] = !isValidEntry;
    setMultiErrors(newErrors);

    const filteredUrls = newUrls.filter((u) => u.trim() !== "");
    onUrlChange(filteredUrls);

    if (onValidationChange) {
      const allValid = newUrls.every((u) => u.trim() === "" || isValidUrl(u));
      const atLeastOne = filteredUrls.length > 0;
      onValidationChange(allValid && atLeastOne);
    }
  };

  const addField = () => {
    setMultiUrls([...multiUrls, ""]);
    setMultiErrors([...multiErrors, false]);
    // Since we added an empty field, the overall validity might change if we require at least one
    // But empty is considered "valid" (no error shown) until text is entered.
  };

  const removeField = (index: number) => {
    let finalUrls: string[];
    let finalErrors: boolean[];

    if (multiUrls.length > 1) {
      finalUrls = multiUrls.filter((_, i) => i !== index);
      finalErrors = multiErrors.filter((_, i) => i !== index);
    } else {
      finalUrls = [""];
      finalErrors = [false];
    }

    setMultiUrls(finalUrls);
    setMultiErrors(finalErrors);
    
    const filteredUrls = finalUrls.filter((u) => u.trim() !== "");
    onUrlChange(filteredUrls);

    if (onValidationChange) {
      const allValid = finalUrls.every((u) => u.trim() === "" || isValidUrl(u));
      const atLeastOne = filteredUrls.length > 0;
      onValidationChange(allValid && atLeastOne);
    }
  };

  return (
    <div className="relative w-full p-8 bg-white comic-border rounded-2xl transition-all h-full flex flex-col">
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
                d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
              />
            </svg>
          )}
        </div>

        <h3 className="font-bangers text-2xl mb-1 text-black">{title}</h3>
        <p className="font-comic text-center text-sm text-gray-600 mb-6 px-4">
          {description}
        </p>

        <div className="w-full space-y-3">
          {multiple ? (
            <>
              <div className="max-h-48 overflow-y-auto w-full space-y-3 pr-2 scrollbar-thin scrollbar-thumb-gray-300">
                {multiUrls.map((url, index) => (
                  <div key={index} className="flex flex-col space-y-1">
                    <div className="flex items-center space-x-2">
                      <input
                        type="text"
                        value={url}
                        onChange={(e) => handleMultiChange(index, e.target.value)}
                        placeholder={`Image URL #${index + 1}`}
                        className={`flex-1 p-3 font-comic text-sm comic-border rounded-lg focus:ring-2 focus:ring-black/5 outline-none ${multiErrors[index] ? 'border-comic-red' : ''}`}
                      />
                      <button
                        type="button"
                        onClick={() => removeField(index)}
                        className="w-10 h-10 flex flex-shrink-0 items-center justify-center bg-comic-red text-white comic-border rounded-lg hover:brightness-110 active:translate-y-0.5 transition-all"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                    {multiErrors[index] && (
                      <p className="text-comic-red text-[10px] font-bold px-1 uppercase tracking-tight">
                        Invalid URL! Check your link.
                      </p>
                    )}
                  </div>
                ))}
              </div>
              <button
                type="button"
                onClick={addField}
                className="w-full py-2 flex items-center justify-center space-x-2 bg-white comic-border rounded-lg font-comic text-sm hover:bg-gray-50 active:translate-y-0.5 transition-all mt-2"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                <span>ADD ANOTHER URL</span>
              </button>
            </>
          ) : (
            <div className="w-full">
              <input
                type="text"
                value={singleUrl}
                onChange={handleSingleChange}
                placeholder={placeholder || "Paste audio URL here..."}
                className={`w-full p-4 font-comic text-sm comic-border rounded-lg focus:ring-2 focus:ring-black/5 outline-none ${singleError ? 'border-comic-red' : ''}`}
              />
              {singleError && (
                <p className="text-comic-red text-xs mt-2 font-bold animate-pulse text-left uppercase">
                  Wait! That&apos;s an invalid URL!
                </p>
              )}
            </div>
          )}
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
