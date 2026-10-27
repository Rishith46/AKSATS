"use client";

import { useEffect, useState } from "react";
import { getVisaOptions, type VisaOption } from "@/lib/api";

// One place that loads the visa list from the API, so every screen shows the same labels.
export function useVisa(token: string) {
  const [options, setOptions] = useState<VisaOption[]>([]);
  useEffect(() => {
    let cancelled = false;
    getVisaOptions(token)
      .then((o) => {
        if (!cancelled) setOptions(o);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [token]);
  const label = (v: string | null | undefined): string | null =>
    v ? (options.find((o) => o.value === v)?.label ?? v) : null;
  return { options, label };
}