"use client";

import { useCallback, useEffect, useRef, useState } from "react";

// Loads data from the API when a component mounts. Returns the data, loading/error state and
// a reload() function to fetch again (e.g. after a change). Pass `deps` (values the loader
// uses) to fetch again automatically when they change.
// Usage: const { data, error, loading } = useApi(() => api.reports.get(days), [days]);
export function useApi<T>(loader: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [version, setVersion] = useState(0); // bumping this re-runs the fetch effect
  const depsKey = JSON.stringify(deps);

  const loaderRef = useRef(loader); // always call the newest loader without re-fetching on every render
  useEffect(() => {
    loaderRef.current = loader;
  });

  useEffect(() => {
    let cancelled = false; // ignore the result if the component unmounted or a newer fetch started
    loaderRef
      .current()
      .then((result) => {
        if (cancelled) return;
        setData(result);
        setError(null);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Something went wrong");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [version, depsKey]);

  const reload = useCallback(() => {
    setLoading(true);
    setVersion((v) => v + 1);
  }, []);

  return { data, error, loading, reload };
}

// Like useApi, but fetches again every `ms` milliseconds (for live screens such as tracking).
// Errors keep the last good data on screen and only set `error`.
export function usePolling<T>(loader: () => Promise<T>, ms: number) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const loaderRef = useRef(loader);
  useEffect(() => {
    loaderRef.current = loader;
  });

  useEffect(() => {
    let cancelled = false;
    const tick = () =>
      loaderRef
        .current()
        .then((result) => {
          if (cancelled) return;
          setData(result);
          setError(null);
        })
        .catch((e: unknown) => {
          if (!cancelled) setError(e instanceof Error ? e.message : "Something went wrong");
        });
    tick();
    const timer = setInterval(tick, ms);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [ms]);

  return { data, error };
}
