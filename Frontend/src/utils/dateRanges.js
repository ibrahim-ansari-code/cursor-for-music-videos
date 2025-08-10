export const startOfMonth = (d = new Date()) => new Date(d.getFullYear(), d.getMonth(), 1);
export const endOfMonth = (d = new Date()) => new Date(d.getFullYear(), d.getMonth() + 1, 0);

export const startOfQuarter = (d = new Date()) => {
  const qStartMonth = Math.floor(d.getMonth() / 3) * 3;
  return new Date(d.getFullYear(), qStartMonth, 1);
};
export const endOfQuarter = (d = new Date()) => {
  const qEndMonth = Math.floor(d.getMonth() / 3) * 3 + 2;
  return new Date(d.getFullYear(), qEndMonth + 1, 0);
};

export const startOfYear = (d = new Date()) => new Date(d.getFullYear(), 0, 1);
export const endOfYear = (d = new Date()) => new Date(d.getFullYear(), 11, 31);

export const toIsoDate = (d) => d.toISOString().slice(0, 10);

export const getPresetRange = (preset, ref = new Date()) => {
  switch (preset) {
    case "this_month":
      return { start: startOfMonth(ref), end: ref };
    case "last_month": {
      const lastMonth = new Date(ref.getFullYear(), ref.getMonth() - 1, 1);
      return { start: startOfMonth(lastMonth), end: endOfMonth(lastMonth) };
    }
    case "this_quarter":
      return { start: startOfQuarter(ref), end: ref };
    case "last_quarter": {
      const lastQRef = new Date(ref.getFullYear(), ref.getMonth() - 3, 15);
      return { start: startOfQuarter(lastQRef), end: endOfQuarter(lastQRef) };
    }
    case "ytd":
      return { start: startOfYear(ref), end: ref };
    case "last_year": {
      const lastYearRef = new Date(ref.getFullYear() - 1, ref.getMonth(), ref.getDate());
      return { start: startOfYear(lastYearRef), end: endOfYear(lastYearRef) };
    }
    default:
      return { start: startOfMonth(ref), end: ref };
  }
};


