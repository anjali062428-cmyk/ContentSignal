"use client";

import React, { useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { DatasetProvider } from "@/context/DatasetContext";
import { registerClerkTokenGetter, setToken, removeToken } from "@/lib/api";

function ClerkSessionSync() {
  const { getToken, isSignedIn } = useAuth();

  useEffect(() => {
    // Register Clerk's dynamic token getter
    registerClerkTokenGetter(async () => {
      try {
        return await getToken();
      } catch {
        return null;
      }
    });

    if (isSignedIn) {
      getToken()
        .then((tok) => {
          if (tok) setToken(tok);
        })
        .catch(() => {});
    } else {
      removeToken();
    }
  }, [isSignedIn, getToken]);

  return null;
}

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <DatasetProvider>
      <ClerkSessionSync />
      {children}
    </DatasetProvider>
  );
}
