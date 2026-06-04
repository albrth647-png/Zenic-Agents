import { useEffect, useState } from 'react';
import { channels } from '../../api';

interface Channel {
  slug: string;
  name: string;
  priority: number;
}

export default function Channels() {
  const [available, setAvailable] = useState<Channel[]>([]);
  const [preferred, setPreferred] = useState('web');
  const [recipient, setRecipient] = useState('');
  const [additional, setAdditional] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      channels.available(),
      channels.prefs().catch(() => null),
    ]).then(([avail, prefs]) => {
      setAvailable(avail);
      if (prefs) {
        setPreferred(prefs.preferred_channel);
        setRecipient(prefs.recipient);
        setAdditional(prefs.additional_channels);
      }
      setLoading(false);
    });
  }, []);

  const savePrefs = async () => {
    setSaving(true);
    setMessage('');
    try {
      await channels.updatePrefs({
        preferred_channel: preferred,
        recipient,
        additional_channels: additional,
      });
      setMessage('✅ Preferencias guardadas correctamente');
    } catch (err) {
      setMessage(`❌ ${err instanceof Error ? err.message : 'Error al guardar'}`);
    } finally {
      setSaving(false);
    }
  };

  const toggleAdditional = (slug: string) => {
    setAdditional(prev =>
      prev.includes(slug) ? prev.filter(s => s !== slug) : [...prev, slug]
    );
  };

  if (loading) {
    return <div className="flex h-64 items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-4 border-zenic-500 border-t-transparent" /></div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Canales de notificación</h1>
        <p className="mt-1 text-sm text-gray-500">
          Configura cómo y dónde recibir notificaciones
        </p>
      </div>

      {message && (
        <div className={`rounded-lg border px-4 py-3 text-sm ${
          message.startsWith('✅') ? 'bg-green-50 border-green-200 text-green-700' : 'bg-red-50 border-red-200 text-red-700'
        }`}>
          {message}
        </div>
      )}

      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Canal principal</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {available.map((ch) => (
            <button
              key={ch.slug}
              onClick={() => setPreferred(ch.slug)}
              className={`rounded-xl border-2 p-4 text-left transition-all ${
                preferred === ch.slug
                  ? 'border-zenic-500 bg-zenic-50/50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="flex items-center gap-3">
                <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${
                  preferred === ch.slug ? 'bg-zenic-100' : 'bg-gray-100'
                }`}>
                  <span className="text-lg">{getChannelIcon(ch.slug)}</span>
                </div>
                <div>
                  <p className="font-medium text-gray-900">{ch.name}</p>
                  <p className="text-xs text-gray-500">Prioridad {ch.priority}</p>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Destino del canal principal</h2>
        <input
          type="text"
          value={recipient}
          onChange={(e) => setRecipient(e.target.value)}
          placeholder={preferred === 'email' ? 'correo@ejemplo.com' : preferred === 'web' ? 'Notificaciones en la web' : 'Número o identificador'}
          className="block w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-zenic-500 focus:ring-2 focus:ring-zenic-200 outline-none transition-colors"
        />
      </div>

      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Canales adicionales</h2>
          <span className="text-xs text-gray-500">{additional.length} seleccionados</span>
        </div>
        <p className="text-sm text-gray-500 mb-4">
          Canales de respaldo para notificaciones importantes
        </p>
        <div className="flex flex-wrap gap-2">
          {available.map((ch) => {
            const isSelected = additional.includes(ch.slug);
            return (
              <button
                key={ch.slug}
                onClick={() => toggleAdditional(ch.slug)}
                disabled={ch.slug === preferred}
                className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-all ${
                  ch.slug === preferred
                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    : isSelected
                      ? 'bg-zenic-100 text-zenic-700 ring-1 ring-zenic-300'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {getChannelIcon(ch.slug)}
                {ch.name}
              </button>
            );
          })}
        </div>
      </div>

      <button
        onClick={savePrefs}
        disabled={saving}
        className="flex w-full items-center justify-center rounded-lg bg-zenic-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition-all hover:bg-zenic-700 disabled:opacity-50 sm:w-auto sm:px-8"
      >
        {saving ? 'Guardando...' : 'Guardar preferencias'}
      </button>
    </div>
  );
}

function getChannelIcon(slug: string): string {
  const icons: Record<string, string> = {
    whatsapp: '💬',
    telegram: '✈️',
    web: '🌐',
    email: '📧',
    sms: '📱',
    push: '🔔',
    webhook: '🔗',
    slack: '💎',
    teams: '🟣',
    log: '📝',
  };
  return icons[slug] || '📡';
}
