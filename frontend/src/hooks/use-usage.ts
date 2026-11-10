"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchUsageStats } from "@/lib/api";

export function useUsageStats(days = 30) {
  return useQuery({
    queryKey: ["usage-stats", days],
    queryFn: () => fetchUsageStats(days),
    staleTime: 15_000,
  });
}
