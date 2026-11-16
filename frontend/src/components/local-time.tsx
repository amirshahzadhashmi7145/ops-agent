"use client";

export function LocalTime({
  value,
  empty = "Never",
  className,
}: {
  value: string | null;
  empty?: string;
  className?: string;
}) {
  const label = value ? new Date(value).toLocaleString() : empty;

  return (
    <span className={className} suppressHydrationWarning>
      {label}
    </span>
  );
}
