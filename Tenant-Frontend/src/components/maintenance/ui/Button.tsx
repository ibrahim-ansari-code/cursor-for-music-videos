import React from "react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
  variant?: "primary" | "secondary" | "danger" | "link";
}

const Button = ({
  children,
  className,
  variant = "primary",
  ...props
}: ButtonProps) => {
  const baseClasses =
    variant === "link"
      ? "font-semibold transition-colors"
      : "px-4 py-2 rounded-lg font-semibold transition-colors";

  const variantClasses = {
    primary:
      "bg-teal-600 text-white hover:bg-teal-700 disabled:bg-teal-400 disabled:cursor-not-allowed",
    secondary:
      "bg-gray-200 text-gray-800 hover:bg-gray-300 disabled:bg-gray-100 disabled:cursor-not-allowed",
    danger:
      "bg-red-600 text-white hover:bg-red-700 disabled:bg-red-400 disabled:cursor-not-allowed",
    link: "text-teal-600 hover:text-teal-700 disabled:text-gray-400 disabled:cursor-not-allowed",
  };

  return (
    <button
      className={`${baseClasses} ${variantClasses[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
};

export default Button;
