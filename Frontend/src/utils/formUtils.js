export const getInputClassName = (
  fieldName,
  fieldErrors,
  formSubmitted,
  formData
) => {
  const baseClass =
    "mt-1 block w-full border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm";
  return fieldErrors[fieldName] || (formSubmitted && !formData[fieldName])
    ? `${baseClass} border-red-300 text-red-900 placeholder-red-300 focus:outline-none focus:ring-red-500 focus:border-red-500`
    : baseClass;
};
