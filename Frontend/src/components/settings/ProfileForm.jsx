import React, { useState, useEffect, useMemo } from "react";
import { Label, Input, Button } from "../ui/SharedModalComponents";
import { updateUserProfile } from "../../utils/api/users";
import { toast } from "react-toastify";

// Format phone number as (XXX) XXX-XXXX
const formatPhoneNumber = (value) => {
  // Remove all non-digit characters
  let phoneNumber = value.replace(/\D/g, '');
  
  // Remove country code if present (assumes North American +1)
  if (phoneNumber.length === 11 && phoneNumber.startsWith('1')) {
    phoneNumber = phoneNumber.substring(1);
  }
  
  // Limit to 10 digits (removes extensions)
  const limitedNumber = phoneNumber.slice(0, 10);
  
  // Format the number
  if (limitedNumber.length === 0) {
    return '';
  } else if (limitedNumber.length <= 3) {
    return `(${limitedNumber}`;
  } else if (limitedNumber.length <= 6) {
    return `(${limitedNumber.slice(0, 3)}) ${limitedNumber.slice(3)}`;
  } else {
    return `(${limitedNumber.slice(0, 3)}) ${limitedNumber.slice(3, 6)}-${limitedNumber.slice(6)}`;
  }
};

// Initial state constant to avoid duplication
const INITIAL_FORM_STATE = {
  first_name: "",
  last_name: "",
  email: "",
  phone: "",
  address: "",
  city: "",
  province: "",
  postal_code: "",
};

const ProfileForm = ({ user, onProfileUpdate }) => {
  const [formData, setFormData] = useState(INITIAL_FORM_STATE);
  const [initialData, setInitialData] = useState(INITIAL_FORM_STATE);
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState({});

  useEffect(() => {
    if (user) {
      const userData = {
        first_name: (user.first_name || "").trim(),
        last_name: (user.last_name || "").trim(),
        email: user.email || "",
        phone: user.phone ? formatPhoneNumber(user.phone) : "",
        address: (user.address || "").trim(),
        city: (user.city || "").trim(),
        province: (user.province || "").trim(),
        postal_code: (user.postal_code || "").trim(),
      };
      setFormData(userData);
      setInitialData(userData);
    }
  }, [user]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    
    // Special handling for phone number
    if (name === 'phone') {
      const formattedPhone = formatPhoneNumber(value);
      setFormData(prev => ({ ...prev, [name]: formattedPhone }));
    } else {
      setFormData(prev => ({ ...prev, [name]: value }));
    }
    
    // Clear error for this field
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: null }));
    }
  };

  const validateForm = () => {
    const newErrors = {};
    if (!(formData.first_name || '').trim()) {
      newErrors.first_name = "First name is required";
    }
    if (!(formData.last_name || '').trim()) {
      newErrors.last_name = "Last name is required";
    }
    if (formData.phone) {
      // Extract digits for validation
      let phoneDigits = formData.phone.replace(/\D/g, '');
      
      // Handle country codes (remove leading 1 for North American numbers)
      if (phoneDigits.length === 11 && phoneDigits.startsWith('1')) {
        phoneDigits = phoneDigits.substring(1);
      }
      
      // Validate phone number
      if (phoneDigits.length > 0) {
        if (phoneDigits.length < 10) {
          newErrors.phone = "Phone number is too short (10 digits required)";
        } else if (phoneDigits.length > 10) {
          newErrors.phone = "Phone number is too long (extensions not supported)";
        } else if (!/^[2-9]\d{2}[2-9]\d{6}$/.test(phoneDigits)) {
          // North American phone validation: area code can't start with 0 or 1
          newErrors.phone = "Please enter a valid North American phone number";
        }
      }
    }
    return newErrors;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const validationErrors = validateForm();
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    setIsLoading(true);
    setErrors({});

    // Remove formatting from phone number before sending to backend
    const phoneDigits = (formData.phone || '').replace(/\D/g, '');
    
    // Build data object, only including non-empty values for optional fields
    // This ensures the backend stores NULL instead of empty strings in the database,
    // and properly utilizes the exclude_unset=True behavior in the API endpoint
    const dataToUpdate = {
      first_name: (formData.first_name || '').trim(),
      last_name: (formData.last_name || '').trim(),
    };

    // Only add optional fields if they have actual content
    if (phoneDigits) {
      dataToUpdate.phone = phoneDigits;
    }
    
    const trimmedAddress = (formData.address || '').trim();
    if (trimmedAddress) {
      dataToUpdate.address = trimmedAddress;
    }
    
    const trimmedCity = (formData.city || '').trim();
    if (trimmedCity) {
      dataToUpdate.city = trimmedCity;
    }
    
    const trimmedProvince = (formData.province || '').trim();
    if (trimmedProvince) {
      dataToUpdate.province = trimmedProvince;
    }
    
    const trimmedPostalCode = (formData.postal_code || '').trim();
    if (trimmedPostalCode) {
      dataToUpdate.postal_code = trimmedPostalCode;
    }

    try {
      await updateUserProfile(user.id, dataToUpdate);
      toast.success("Profile updated successfully!");
      
      // Update form state with trimmed values
      const updatedFormData = {
        ...formData,
        first_name: dataToUpdate.first_name,
        last_name: dataToUpdate.last_name,
        phone: formData.phone, // Keep the formatted phone number in the form
        address: trimmedAddress || "",
        city: trimmedCity || "",
        province: trimmedProvince || "",
        postal_code: trimmedPostalCode || "",
      };
      setFormData(updatedFormData);
      setInitialData(updatedFormData);
      
      // Notify parent component with the actual data sent
      if (onProfileUpdate) {
        onProfileUpdate(dataToUpdate);
      }
    } catch (error) {
      console.error("Error updating profile:", error);
      toast.error(`Failed to update profile: ${error.message || "Server error"}`);
      setErrors({ form: "Failed to update profile. Please try again." });
    } finally {
      setIsLoading(false);
    }
  };

  const hasChanges = useMemo(() => {
    // Compare each field directly without creating intermediate objects
    return (formData.first_name || '').trim() !== (initialData.first_name || '').trim() ||
           (formData.last_name || '').trim() !== (initialData.last_name || '').trim() ||
           (formData.phone || '').replace(/\D/g, '') !== (initialData.phone || '').replace(/\D/g, '') ||
           (formData.address || '').trim() !== (initialData.address || '').trim() ||
           (formData.city || '').trim() !== (initialData.city || '').trim() ||
           (formData.province || '').trim() !== (initialData.province || '').trim() ||
           (formData.postal_code || '').trim() !== (initialData.postal_code || '').trim();
  }, [formData, initialData]);

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-900 mb-6">Personal Information</h2>
      
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Name Fields */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div>
            <Label htmlFor="first_name" required>First Name</Label>
            <Input
              id="first_name"
              name="first_name"
              value={formData.first_name}
              onChange={handleChange}
              placeholder="Enter your first name"
            />
            {errors.first_name && (
              <p className="mt-1 text-sm text-red-600">{errors.first_name}</p>
            )}
          </div>
          
          <div>
            <Label htmlFor="last_name" required>Last Name</Label>
            <Input
              id="last_name"
              name="last_name"
              value={formData.last_name}
              onChange={handleChange}
              placeholder="Enter your last name"
            />
            {errors.last_name && (
              <p className="mt-1 text-sm text-red-600">{errors.last_name}</p>
            )}
          </div>
        </div>

        {/* Contact Information */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 pt-2">
          <div>
            <Label htmlFor="email">Email Address</Label>
            <Input
              id="email"
              name="email"
              type="email"
              value={formData.email}
              readOnly
              disabled
              className="bg-gray-50 cursor-not-allowed"
            />
            <p className="mt-1 text-xs text-gray-500">
              Email address cannot be changed for security reasons.
            </p>
          </div>

          <div>
            <Label htmlFor="phone">Phone Number</Label>
            <Input
              id="phone"
              name="phone"
              type="tel"
              value={formData.phone}
              onChange={handleChange}
              placeholder="(555) 123-4567"
            />
            {errors.phone && (
              <p className="mt-1 text-sm text-red-600">{errors.phone}</p>
            )}
          </div>
        </div>

        {/* Address Section */}
        <div className="pt-6 border-t border-gray-200">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Address Information</h3>
          
          <div className="space-y-5">
            <div>
              <Label htmlFor="address">Street Address</Label>
              <Input
                id="address"
                name="address"
                value={formData.address}
                onChange={handleChange}
                placeholder="123 Main Street"
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              <div>
                <Label htmlFor="city">City</Label>
                <Input
                  id="city"
                  name="city"
                  value={formData.city}
                  onChange={handleChange}
                  placeholder="Toronto"
                />
              </div>

              <div>
                <Label htmlFor="province">Province</Label>
                <Input
                  id="province"
                  name="province"
                  value={formData.province}
                  onChange={handleChange}
                  placeholder="Ontario"
                />
              </div>

              <div>
                <Label htmlFor="postal_code">Postal Code</Label>
                <Input
                  id="postal_code"
                  name="postal_code"
                  value={formData.postal_code}
                  onChange={handleChange}
                  placeholder="M5H 2N2"
                />
              </div>
            </div>
          </div>
        </div>

        {errors.form && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-600">{errors.form}</p>
          </div>
        )}

        <div className="flex justify-end pt-4 border-t border-gray-200">
          <Button
            type="submit"
            variant="primary"
            disabled={!hasChanges || isLoading}
            isLoading={isLoading}
            loadingText="Saving..."
          >
            Save Changes
          </Button>
        </div>
      </form>
    </div>
  );
};

export default ProfileForm;