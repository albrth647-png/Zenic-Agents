import { useEffect, useState } from 'react';
import { plans } from '../../api';
import type { PlanResponse, UsageResponse } from '../../types';

export default function Usage() {
  const [usage, setUsage] = useState<UsageResponse | null>(null);
  const [allPlans, setAllPlans] = useState<PlanResponse[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      plans.usage(),
      plans.list(),
    ]).then(([u, p]) => {
      setUsage(u);
      setAllPlans(p);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return <div className="flex h-64 items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-4 border-zenic-500 border-t-transparent" /></div>;
  }

  if (!usage) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6 text-center">
        <p className="text-red-700">No se pudo cargar la información de uso</p>
      </div>
    );
  }

  const metrics = [
    {
      label: 'Clientes',
      current: usage.total_clients,
      limit: usage.total_clients_limit,
      unit: '',
      color: 'bg-zenic-500',
    },
    {
      label: 'Mensajes enviados (hoy)',
      current: usage.daily?.['messages_sent'] || 0,
      limit: allPlans.find(p => p.slug === usage.plan)?.max_messages_per_day || 50,
      unit: '',
      color: 'bg-blue-500',
    },
    {
      label: 'Sesiones de collector (hoy)',
      current: usage.daily?.['collector_sessions'] || 0,
      limit: allPlans.find(p => p.slug === usage.plan)?.max_collector_sessions || 1,
      unit: '',
      color: 'bg-purple-500',
    },
  ];

  const currentPlan = allPlans.find(p => p.slug === usage.plan);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Uso y límites</h1>
        <p className="mt-1 text-sm text-gray-500">
          Plan actual: <span className="font-semibold capitalize">{usage.plan_name}</span>
        </p>
      </div>

      {/* Usage meters */}
      <div className="space-y-6">
        {metrics.map((m) => {
          const pct = m.limit > 0 ? Math.min((m.current / m.limit) * 100, 100) : 0;
          const isNearLimit = pct >= 80;
          const isOverLimit = pct >= 100;

          return (
            <div key={m.label} className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <p className="text-sm font-medium text-gray-700">{m.label}</p>
                  <p className="text-xs text-gray-500">{m.unit}</p>
                </div>
                <div className="text-right">
                  <span className={`text-2xl font-bold ${isOverLimit ? 'text-red-600' : isNearLimit ? 'text-yellow-600' : 'text-gray-900'}`}>
                    {m.current.toLocaleString()}
                  </span>
                  <span className="text-sm text-gray-400"> / {m.limit === 99999 || m.limit === 9999 ? '∞' : m.limit.toLocaleString()}</span>
                </div>
              </div>
              <div className="h-3 rounded-full bg-gray-100 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    isOverLimit ? 'bg-red-500' : isNearLimit ? 'bg-yellow-500' : m.color
                  }`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <p className={`mt-2 text-xs ${isOverLimit ? 'text-red-600' : isNearLimit ? 'text-yellow-600' : 'text-gray-500'}`}>
                {isOverLimit ? 'Límite alcanzado — actualiza tu plan' :
                 isNearLimit ? `Queda poco — ${(m.limit - m.current).toLocaleString()} disponible${m.unit ? ` ${m.unit}` : ''}` :
                 `${(m.limit - m.current).toLocaleString()} disponible${m.unit ? ` ${m.unit}` : ''}`}
              </p>
            </div>
          );
        })}
      </div>

      {/* Plan comparison mini */}
      {currentPlan && (
        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Características de {currentPlan.name}</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {currentPlan.features.map((f, i) => (
              <div key={i} className="flex items-center gap-2 text-sm text-gray-700">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-green-100 text-xs text-green-600">✓</span>
                {f}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Daily usage detail */}
      {usage.daily && Object.keys(usage.daily).length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Uso diario detallado</h2>
          <div className="space-y-2">
            {Object.entries(usage.daily).map(([key, val]) => (
              <div key={key} className="flex items-center justify-between rounded-lg bg-gray-50 px-4 py-2.5">
                <span className="text-sm font-medium text-gray-700 capitalize">
                  {key.replace(/_/g, ' ')}
                </span>
                <span className="text-sm font-semibold text-gray-900">{val}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
