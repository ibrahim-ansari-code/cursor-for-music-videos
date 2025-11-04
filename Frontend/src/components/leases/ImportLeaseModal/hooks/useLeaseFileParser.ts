import { useState } from "react";
import * as Sentry from "@sentry/react";
import { parseLease, uploadLeasePDF } from "../../../../utils/api";
import type { LeaseAnalysisResponse } from "../../../../types/lease";
import type { Tenant } from "../../../../types/tenant";
import type { FormData, Unit } from "../types";

interface UseLeaseFileParserReturn {
  file: File | null;
  parsedFileUrl: string | null;
  isAnalyzing: boolean;
  analyzeError: string | null;
  setFile: (file: File | null) => void;
  analyzeLease: (
    propertyId: string,
    availableUnits: Unit[],
    loadTenantsForProperty: (propertyId: number) => Promise<Tenant[]>
  ) => Promise<{
    formUpdates: Partial<FormData>;
    matchedTenant: Tenant | null;
  } | null>;
}

export const useLeaseFileParser = (): UseLeaseFileParserReturn => {
  const [file, setFile] = useState<File | null>(null);
  const [parsedFileUrl, setParsedFileUrl] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);

  const analyzeLease = async (
    propertyId: string,
    availableUnits: Unit[],
    loadTenantsForProperty: (propertyId: number) => Promise<Tenant[]>
  ) => {
    if (!file || !propertyId) {
      setAnalyzeError("Please select a property and upload a lease file.");
      return null;
    }

    setIsAnalyzing(true);
    setAnalyzeError(null);

    try {
      // Create FormData for file upload
      const uploadFormData = new FormData();
      uploadFormData.append('file', file);

      // Parse the lease file
      const parsedData = (await parseLease(uploadFormData)) as LeaseAnalysisResponse;
      Sentry.logger.debug("Parsed lease data successfully", {
        hasMonthlyRent: !!parsedData.monthly_rent,
        hasSecurityDeposit: !!parsedData.security_deposit,
        hasDates: !!(parsedData.start_date && parsedData.end_date),
        hasTenantName: !!parsedData.tenant_name,
        hasUnit: !!parsedData.unit,
      });

      // Upload PDF to blob storage if it's a PDF
      let fileUrl: string | null = null;
      if (file.type === 'application/pdf') {
        fileUrl = await uploadLeasePDF(file);
        setParsedFileUrl(fileUrl);
      }

      // Load available tenants for matching
      const tenantsForMatching = await loadTenantsForProperty(parseInt(propertyId));

      // Try to find a matching tenant by name
      let matchedTenant: Tenant | null = null;
      if (parsedData.tenant_name) {
        const nameToMatch = parsedData.tenant_name.toLowerCase();
        matchedTenant = tenantsForMatching.find(tenant => {
          // Check company name for company tenants (case-insensitive)
          if (tenant.tenant_type?.toLowerCase() === 'company' && tenant.company_name) {
            return tenant.company_name.toLowerCase().includes(nameToMatch) || 
                   nameToMatch.includes(tenant.company_name.toLowerCase());
          }
          // Check full name for individual tenants
          const fullName = `${tenant.first_name || ''} ${tenant.last_name || ''}`.toLowerCase();
          return fullName.includes(nameToMatch) || nameToMatch.includes(fullName);
        }) || null;
      }

      // Try to match unit if parsed
      let matchedUnitId: string | undefined;
      if (parsedData.unit && availableUnits.length > 0) {
        const matchedUnit = availableUnits.find(
          unit => (unit.name || '').toLowerCase() === parsedData.unit?.toLowerCase()
        );
        if (matchedUnit) {
          matchedUnitId = matchedUnit.id.toString();
        }
      }

      // Return form updates
      const formUpdates: Partial<FormData> = {
        monthly_rent: parsedData.monthly_rent ? String(parsedData.monthly_rent) : undefined,
        security_deposit: parsedData.security_deposit ? String(parsedData.security_deposit) : undefined,
        start_date: parsedData.start_date || undefined,
        end_date: parsedData.end_date || undefined,
        tenant_id: matchedTenant?.id || undefined,
        unit_id: matchedUnitId,
      };

      return { formUpdates, matchedTenant };
    } catch (err: any) {
      Sentry.logger.error("Failed to analyze lease", {
        error: err.message,
        propertyId,
        hasFile: !!file,
        fileType: file?.type,
        fileSize: file?.size,
        component: 'ImportLeaseModal',
      });
      
      Sentry.captureException(err, {
        tags: {
          component: 'ImportLeaseModal',
          action: 'parse_lease',
          feature: 'leases',
        },
        contexts: {
          file: {
            type: file?.type,
            size: file?.size,
            name: file?.name,
          },
        },
      });
      
      // Provide more user-friendly error messages
      let errorMessage = "Failed to analyze lease file. Please try again.";
      
      if (err.message) {
        if (err.message.includes("No text could be extracted")) {
          errorMessage = "This PDF appears to be an image or doesn't contain selectable text. Please try uploading a different PDF file with selectable text.";
        } else if (err.message.includes("document could not be processed")) {
          errorMessage = err.message;
        } else if (err.message.includes("Failed to parse JSON")) {
          errorMessage = "The document analysis service is temporarily unavailable. Please try again in a few moments.";
        } else if (err.message.includes("Authentication") || err.message.includes("401")) {
          errorMessage = "Session expired. Please refresh the page and try again.";
        } else {
          errorMessage = err.message;
        }
      }
      
      setAnalyzeError(errorMessage);
      return null;
    } finally {
      setIsAnalyzing(false);
    }
  };

  return {
    file,
    parsedFileUrl,
    isAnalyzing,
    analyzeError,
    setFile,
    analyzeLease,
  };
};

