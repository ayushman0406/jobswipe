export const CAT_COLOR = {
  technology: "#2457d6",
  sales: "#e23d12",
  management: "#6b3fa0",
  retail: "#b86e00",
  mechanical: "#2f6284",
  finance: "#0f7a5a",
  healthcare: "#c4375b",
  hospitality: "#b45309",
  education: "#1d4e89",
  logistics: "#3f6212",
  hr: "#6d28d9",
  marketing: "#be185d",
  support: "#0e7490",
  legal: "#44403c",
  trades: "#9a3412",
  agriculture: "#4d7c0f",
  creative: "#9d174d",
  operations: "#57534e",
};

export function lpa(n) {
  if (n == null) return "";
  const v = n / 100000;
  const rounded = Math.round(v * 10) / 10;
  return String(rounded).replace(/\.0$/, "");
}

export function salary(job) {
  const a = job.salary_min;
  const b = job.salary_max;
  if (!a && !b) return "Not listed";
  if (a && b) return `₹${lpa(a)}–${lpa(b)} LPA`;
  if (a) return `₹${lpa(a)}+ LPA`;
  return `up to ₹${lpa(b)} LPA`;
}

export function catLabel(meta, slug) {
  return meta?.categories?.find((c) => c.slug === slug)?.label || slug || "Role";
}

export const PAY_OPTIONS = [
  { value: 0, label: "Any pay" },
  { value: 300000, label: "₹3 LPA+" },
  { value: 500000, label: "₹5 LPA+" },
  { value: 800000, label: "₹8 LPA+" },
  { value: 1200000, label: "₹12 LPA+" },
  { value: 2000000, label: "₹20 LPA+" },
];