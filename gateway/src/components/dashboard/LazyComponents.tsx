"use client";

import dynamic from 'next/dynamic';
import { Skeleton } from '@/components/ui/skeleton';

function ComponentSkeleton() {
  return (
    <div className="space-y-4 p-4">
      <Skeleton className="h-10 w-full max-w-md" />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-40 rounded-xl" />
        ))}
      </div>
    </div>
  );
}

export const LazyNichosSelector = dynamic(
  () => import('@/components/nichos/NichosSelector').then((mod) => mod.default),
  { loading: () => <ComponentSkeleton />, ssr: false }
);

export const LazyApisMcpTab = dynamic(
  () => import('@/components/apis-mcp/ApisMcpTab').then((mod) => mod.default),
  { loading: () => <ComponentSkeleton />, ssr: false }
);
