import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { clients, plans, channels } from '../../api';
import type { StatsResponse, UsageResponse } from '../../types';

export default function ClientDashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [usage, setUsage] = useState<UsageResponse | null>(null);
  const [channelPref, setChannelPref] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      clients.stats().catch(() => null),
      plans.usage().catch(() => null),
      channels.prefs().catch(() => null),
    ]).then(([s, u, c]) => {
      setStats(s);
      setUsage(u);
      setChannelPref(c?.preferred_channel || 'web');
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-zenic-500 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Mi Panel</h1>
        <p className="mt-1 text-sm text-gray-500">
          Bienvenido, {user?.name || user?.email}
        </p>
      </div>

      {/* Metric cards */}
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">Clientes</p>
              <p className="mt-2 text-2xl font-bold text-gray-900">{stats?.total_clients || 0}</p>
            </div>
            <span className="text-2xl">👥</span>
          </div>
          <div className="mt-3 flex items-center gap-2">
            <div className="flex-1 h-1.5 rounded-full bg-gray-100 overflow-hidden">
              <div
                className="h-full rounded-full bg-zenic-500"
                style={{ width: `${usage ? Math.min((usage.total_clients / (usage.total_clients_limit || 1)) * 100, 100) : 0}%` }}
              />
            </div>
            <span className="text-xs text-gray-500">
              {usage?.total_clients || 0}/{usage?.total_clients_limit || 1}
            </span>
          </div>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">Plan</p>
              <p className="mt-2 text-2xl font-bold text-gray-900">{usage?.plan_name || '—'}</p>
            </div>
            <span className="text-2xl">📋</span>
          </div>
          <p className="mt-3 text-xs text-gray-500 capitalize">{usage?.plan || 'free'}</p>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">Canal preferido</p>
              <p className="mt-2 text-2xl font-bold text-gray-900 capitalize">{channelPref || 'web'}</p>
            </div>
            <span className="text-2xl">📡</span>
          </div>
          <Link to="/channels" className="mt-3 inline-block text-xs font-medium text-zenic-600 hover:text-zenic-700">
            Configurar →
          </Link>
        </div>

        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-gray-500">Mensajes hoy</p>
              <p className="mt-2 text-2xl font-bold text-gray-900">
                {usage?.daily ? (usage.daily['messages_sent'] || 0) : 0}
              </p>
            </div>
            <span className="text-2xl">💬</span>
          </div>
          <Link to="/usage" className="mt-3 inline-block text-xs font-medium text-zenic-600 hover:text-zenic-700">
            Ver uso →
          </Link>
        </div>
      </div>

      {/* Pipeline preview */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Pipeline de clientes</h2>
          <Link to="/" className="text-sm font-medium text-zenic-600 hover:text-zenic-700">
            Gestionar clientes →
          </Link>
        </div>
        {stats && Object.keys(stats.by_stage).length > 0 ? (
          <div className="space-y-3">
            {Object.entries(stats.by_stage).map(([stage, count]) => (
              <div key={stage} className="flex items-center gap-4">
                <span className="w-24 text-sm font-medium text-gray-700 capitalize">{stage}</span>
                <div className="flex-1 h-2 rounded-full bg-gray-100 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-zenic-500 transition-all"
                    style={{ width: `${(count / stats.total_clients) * 100}%` }}
                  />
                </div>
                <span className="w-10 text-right text-sm font-medium text-gray-600">{count}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-500">No hay clientes registrados</p>
        )}
      </div>

      {/* Quick actions */}
      <div className="grid gap-4 sm:grid-cols-2">
        <Link
          to="/collector"
          className="flex items-center gap-4 rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition-all hover:shadow-md hover:border-zenic-200"
        >
          <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-zenic-100 text-2xl">
            🤖
          </span>
          <div>
            <h3 className="font-semibold text-gray-900">Colector de datos</h3>
            <p className="text-sm text-gray-500">Inicia una sesión de recolección interactiva</p>
          </div>
        </Link>
        <Link
          to="/channels"
          className="flex items-center gap-4 rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition-all hover:shadow-md hover:border-zenic-200"
        >
          <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-zenic-100 text-2xl">
            📡
          </span>
          <div>
            <h3 className="font-semibold text-gray-900">Canales de notificación</h3>
            <p className="text-sm text-gray-500">Configura cómo recibir notificaciones</p>
          </div>
        </Link>
      </div>
    </div>
  );
}
