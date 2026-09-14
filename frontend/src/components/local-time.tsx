"use client";

import { useEffect, useState } from "react";

export function LocalTime({
  value,
  empty = "Never",
  className,
}: {
  value: string | null;
  empty?: string;
  className?: string;
}) {
  const [label, setLabel] = useState(value ?? empty);

  useEffect(() => {
    setLabel(value ? new Date(value).toLocaleString() : empty);
  }, [empty, value]);

  return (
    <span className={className} suppressHydrationWarning>
      {label}
    </span>
  );
}
