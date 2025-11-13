export const formatCurrency = (value) => {
  const num = Number(value) || 0;
  return num.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
};

export const clampPercent = (value) => {
  const num = Number(value) || 0;
  return Math.max(0, Math.min(100, num));
};

export const getInitials = (name) => {
  if (!name) return "";
  return name
    .trim()
    .split(/\s+/)
    .map((n) => n[0])
    .join("")
    .toUpperCase();
};

export const getAvatarColor = (name) => {
  if (!name) return "bg-gray-300";
  const colors = [
    "bg-green-500",
    "bg-blue-500",
    "bg-purple-500",
    "bg-indigo-500",
    "bg-pink-500",
    "bg-yellow-500",
    "bg-red-500",
    "bg-teal-500",
  ];
  const index = name.charCodeAt(0) % colors.length;
  return colors[index];
};

export const percentChange = (current, previous) => {
  const currentNum = Number(current);
  const previousNum = Number(previous);
  if (!isFinite(currentNum) || !isFinite(previousNum)) return 0;
  if (previousNum === 0) return currentNum > 0 ? 100 : currentNum < 0 ? -100 : 0;
  return ((currentNum - previousNum) / previousNum) * 100;
};

// Returns a rich delta object to drive modern delta chips
export const computeDelta = ({
  current,
  previous,
  minPercent = 0.5, // suppress noise under 0.5%
  minAbsolute = 100, // or less than $100 change
}) => {
  const cur = Number(current) || 0;
  const prev = Number(previous) || 0;

  // No previous and no current
  if (prev === 0 && cur === 0) {
    return { show: false };
  }

  // Previous is zero but current is not: treat as new
  if (prev === 0) {
    return {
      show: true,
      direction: cur > 0 ? "new" : "cleared",
      percent: null,
      absolute: cur,
      sign: cur >= 0 ? "+" : "-",
      colorClass: cur >= 0 ? "text-green-600" : "text-red-600",
      iconName: cur >= 0 ? "arrow-up" : "arrow-down",
    };
  }

  const absChange = cur - prev;
  const pct = ((cur - prev) / Math.abs(prev)) * 100;
  const show = Math.abs(pct) >= minPercent || Math.abs(absChange) >= minAbsolute;
  if (!show) return { show: false };

  const positive = absChange >= 0;
  return {
    show: true,
    direction: positive ? "up" : "down",
    percent: pct,
    absolute: absChange,
    sign: positive ? "+" : "-",
    colorClass: positive ? "text-green-600" : "text-red-600",
    iconName: positive ? "arrow-up" : "arrow-down",
  };
};

export const humanizePeriodLabel = (timePeriod, activeRange) => {
  if (timePeriod === "custom" && activeRange?.start && activeRange?.end) {
    const start = new Date(activeRange.start);
    const end = new Date(activeRange.end);
    const days = Math.max(1, Math.round((end - start) / (1000 * 60 * 60 * 24)) + 1);
    return `prior ${days} day${days === 1 ? "" : "s"}`;
  }
  const mapping = {
    this_month: "month",
    last_month: "month",
    this_quarter: "quarter",
    last_quarter: "quarter",
    ytd: "period",
    last_year: "year",
    month: "month",
    quarter: "quarter",
    year: "year",
  };
  return mapping[timePeriod] || "period";
};

/**
 * Format phone number as (xxx) xxx-xxxx
 * @deprecated Use formatPhoneNumber from utils/validation.ts instead
 */
export const formatPhoneNumber = (value) => {
  if (!value) return '';
  const numbers = value.replace(/\D/g, '');
  if (numbers.length <= 3) {
    return numbers;
  } else if (numbers.length <= 6) {
    return `(${numbers.slice(0, 3)}) ${numbers.slice(3)}`;
  } else {
    return `(${numbers.slice(0, 3)}) ${numbers.slice(3, 6)}-${numbers.slice(6, 10)}`;
  }
};
