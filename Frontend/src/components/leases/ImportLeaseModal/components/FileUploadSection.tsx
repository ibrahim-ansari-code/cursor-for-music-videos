import React from 'react';
import * as Select from '@radix-ui/react-select';
import { ChevronDown, CheckCircle } from 'lucide-react';
import { Label } from '../../../ui/SharedModalComponents';
import type { Property } from '../../../../types/lease';
import type { FieldErrors } from '../types';

interface FileUploadSectionProps {
  properties: Property[];
  selectedPropertyId: string;
  file: File | null;
  fieldErrors: FieldErrors;
  onPropertyChange: (value: string) => void;
  onFileChange: (file: File | null) => void;
}

export const FileUploadSection: React.FC<FileUploadSectionProps> = ({
  properties,
  selectedPropertyId,
  file,
  fieldErrors,
  onPropertyChange,
  onFileChange,
}) => {
  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="file-property_id" required>Property</Label>
        <Select.Root 
          value={selectedPropertyId} 
          onValueChange={onPropertyChange}
        >
          <Select.Trigger 
            className={`w-full px-4 py-2.5 border ${
              fieldErrors.property_id
                ? 'border-red-300 dark:border-red-600'
                : 'border-gray-200 dark:border-gray-600'
            } rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent transition-all bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 flex items-center justify-between hover:border-gray-300 dark:hover:border-gray-500`}
          >
            <Select.Value placeholder="Choose a property" />
            <Select.Icon>
              <ChevronDown className="h-4 w-4 text-gray-500 dark:text-gray-400" />
            </Select.Icon>
          </Select.Trigger>
          <Select.Portal>
            <Select.Content 
              className="overflow-hidden bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-600 shadow-lg z-[10001]"
              position="popper"
              side="bottom"
              align="start"
              sideOffset={4}
            >
              <Select.Viewport className="p-1">
                {properties.map((property) => (
                  <Select.Item
                    key={property.id}
                    value={property.id.toString()}
                    className="relative flex items-center pl-7 pr-3 py-2 text-sm text-gray-900 dark:text-gray-100 rounded cursor-pointer hover:bg-green-50 dark:hover:bg-green-900/20 focus:bg-green-50 dark:focus:bg-green-900/20 outline-none select-none data-[state=checked]:bg-green-50 dark:data-[state=checked]:bg-green-900/30"
                  >
                    <Select.ItemText>{property.name}</Select.ItemText>
                    <Select.ItemIndicator className="absolute left-1 inline-flex items-center">
                      <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
                    </Select.ItemIndicator>
                  </Select.Item>
                ))}
              </Select.Viewport>
            </Select.Content>
          </Select.Portal>
        </Select.Root>
      </div>

      <div>
        <Label htmlFor="lease-file" required>Lease Document</Label>
        <input
          id="lease-file"
          type="file"
          accept=".pdf"
          onChange={(e) => {
            const files = e.target?.files;
            onFileChange(files && files.length > 0 ? files[0] : null);
          }}
          className="w-full border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-md px-3 py-2 text-sm file:mr-4 file:py-1 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-blue-50 dark:file:bg-blue-900/20 file:text-blue-700 dark:file:text-blue-400 hover:file:bg-blue-100 dark:hover:file:bg-blue-900/30"
        />
        {file && (
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Selected: {file.name}
          </p>
        )}
      </div>
    </div>
  );
};

