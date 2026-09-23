"use client";

import React from "react";
import { DatasetProvider } from "@/context/DatasetContext";

export function Providers({ children }: { children: React.ReactNode }) {
  return <DatasetProvider>{children}</DatasetProvider>;
}
