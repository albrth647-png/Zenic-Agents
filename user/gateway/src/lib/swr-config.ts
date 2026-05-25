import useSWR, { SWRConfiguration, mutate } from 'swr';
import { apiFetch } from '@/lib/api-client';

/** Auth-aware fetcher that uses our existing apiFetch under the hood */
export const swrFetcher = async <T>(url: string): Promise<T> => {
  return apiFetch<T>(url);
};

/** Default SWR config for the app */
export const defaultSWRConfig: SWRConfiguration = {
  fetcher: swrFetcher,
  revalidateOnFocus: false,
  revalidateOnReconnect: true,
  shouldRetryOnError: (err: unknown) => {
    // Don't retry on 4xx errors (auth, not found, etc.)
    if (typeof err === 'object' && err !== null && 'status' in err) {
      const status = (err as { status: number }).status;
      if (status >= 400 && status < 500) return false;
    }
    return true;
  },
  errorRetryCount: 2,
  errorRetryInterval: 3000,
  dedupingInterval: 5000,
};

/** Re-export SWR hooks for convenience */
export { useSWR, mutate };
export type { SWRConfiguration };
