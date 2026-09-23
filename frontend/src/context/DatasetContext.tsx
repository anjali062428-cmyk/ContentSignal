"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { api, DatasetSummary } from "@/lib/api";

interface DatasetContextType {
  datasets: DatasetSummary[];
  activeDataset: DatasetSummary | null;
  isLoading: boolean;
  error: string | null;
  setActiveDataset: (dataset: DatasetSummary) => void;
  selectDatasetById: (datasetId: string) => void;
  refreshDatasets: (preferredId?: string) => Promise<void>;
}

const DatasetContext = createContext<DatasetContextType | undefined>(undefined);

const STORAGE_KEY = "ci_active_dataset_id";

export function DatasetProvider({ children }: { children: React.ReactNode }) {
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [activeDataset, setActiveDatasetState] = useState<DatasetSummary | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const setActiveDataset = useCallback((dataset: DatasetSummary) => {
    setActiveDatasetState(dataset);
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY, dataset.dataset_id);
    }
  }, []);

  const selectDatasetById = useCallback(
    (datasetId: string) => {
      const match = datasets.find((d) => d.dataset_id === datasetId);
      if (match) {
        setActiveDataset(match);
      }
    },
    [datasets, setActiveDataset]
  );

  const refreshDatasets = useCallback(
    async (preferredId?: string) => {
      setIsLoading(true);
      setError(null);
      try {
        const list = await api.getDatasets();
        setDatasets(list);

        const storedId = preferredId || (typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null);
        let selected: DatasetSummary | undefined;

        if (storedId) {
          selected = list.find((d) => d.dataset_id === storedId);
        }

        if (!selected) {
          selected = list.find((d) => d.is_starter) || list[0];
        }

        if (selected) {
          setActiveDatasetState(selected);
          if (typeof window !== "undefined") {
            localStorage.setItem(STORAGE_KEY, selected.dataset_id);
          }
        }
      } catch (err: any) {
        console.error("Failed to load datasets:", err);
        setError(err.message || "Failed to load datasets");
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    refreshDatasets();
  }, [refreshDatasets]);

  return (
    <DatasetContext.Provider
      value={{
        datasets,
        activeDataset,
        isLoading,
        error,
        setActiveDataset,
        selectDatasetById,
        refreshDatasets,
      }}
    >
      {children}
    </DatasetContext.Provider>
  );
}

export function useDataset(): DatasetContextType {
  const context = useContext(DatasetContext);
  if (!context) {
    throw new Error("useDataset must be used within a DatasetProvider");
  }
  return context;
}
