"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchSimCatalog } from "@/lib/api";

export function useSimCatalog() {
  return useQuery({
    queryKey: ["sim-catalog"],
    queryFn: fetchSimCatalog,
    refetchInterval: 15_000,
  });
}
