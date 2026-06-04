import { useEffect, useRef, useState } from 'react';
import { collector } from '../../api';
import type { CollectorSessionResponse } from '../../types';

interface Message {
  role: 'user' | 'agent';
  text: string;
  field?: string;
}

export default function Collector() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentValue, setCurrentValue] = useState('');
  const [sessionState, setSessionState] = useState<CollectorSessionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const startSession = async () => {
    setLoading(true);
    setError('');
    setMessages([]);
    try {
      const res = await collector.start({ niche_id: 'default' });
      setSessionId(res.session_id);
      setSessionState(res);
      setMessages([{
        role: 'agent',
        text: '¡Hola! Voy a ayudarte a recolectar información. ¿Qué datos necesitas registrar?',
      }]);
      if (res.questions && res.questions.length > 0) {
        const qs = formatQuestions(res.questions);
        setMessages(prev => [...prev, ...qs]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al iniciar sesión');
    } finally {
      setLoading(false);
    }
  };

  const submitAnswer = async () => {
    if (!sessionId || !currentValue.trim()) return;

    const fieldName: string = (sessionState?.questions?.[0]?.field_name as string) || 'respuesta';
    const msg: Message = { role: 'user', text: currentValue, field: fieldName };
    setMessages(prev => [...prev, msg]);
    setCurrentValue('');
    setLoading(true);

    try {
      const res = await collector.answer({
        session_id: sessionId,
        field_name: fieldName,
        value: currentValue,
      });
      setSessionState(res);

      if (res.questions && res.questions.length > 0) {
        const qs = formatQuestions(res.questions);
        setMessages(prev => [...prev, ...qs]);
      }

      if (res.is_complete) {
        setMessages(prev => [...prev, {
          role: 'agent',
          text: `✅ ¡Sesión completada! (${res.completion_pct.toFixed(0)}% completado)`,
        }]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al enviar respuesta');
      setMessages(prev => [...prev, {
        role: 'agent',
        text: '❌ Hubo un error al procesar tu respuesta. Intenta de nuevo.',
      }]);
    } finally {
      setLoading(false);
    }
  };

  const formatQuestions = (questions: Record<string, unknown>[]): Message[] => {
    return questions.map((q: Record<string, unknown>) => {
      const fieldName: string = typeof q.field_name === 'string' ? q.field_name : '';
      const questionText: string = typeof q.question_text === 'string' ? q.question_text : '';
      return {
        role: 'agent' as const,
        text: questionText || fieldName || 'Completa el campo requerido',
        field: fieldName,
      };
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submitAnswer();
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Colector de datos</h1>
        <p className="mt-1 text-sm text-gray-500">
          Sesión interactiva de recolección de datos
        </p>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
        {/* Chat area */}
        <div className="h-[400px] overflow-y-auto p-6 space-y-4">
          {!sessionId ? (
            <div className="flex h-full flex-col items-center justify-center text-center">
              <span className="text-4xl mb-3">🤖</span>
              <h3 className="text-lg font-semibold text-gray-900">¿Listo para empezar?</h3>
              <p className="mt-1 text-sm text-gray-500 max-w-sm">
                Inicia una sesión de recolección para registrar datos de tus clientes de forma interactiva.
              </p>
            </div>
          ) : messages.length === 0 ? (
            <p className="text-center text-sm text-gray-500">Iniciando sesión...</p>
          ) : (
            messages.map((msg, i) => (
              <div key={i} className={msg.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-agent'}>
                {msg.text}
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input area */}
        <div className="border-t border-gray-200 p-4">
          {sessionId ? (
            <div className="flex gap-3">
              <input
                type="text"
                value={currentValue}
                onChange={(e) => setCurrentValue(e.target.value)}
                onKeyDown={handleKeyDown}
        placeholder={sessionState?.questions?.[0]?.field_name
          ? `Ingresa ${String(sessionState.questions[0].field_name)}...`
          : 'Escribe tu respuesta...'}
                disabled={loading || !!(sessionState?.is_complete)}
                className="flex-1 rounded-lg border border-gray-300 px-4 py-2.5 text-sm focus:border-zenic-500 focus:ring-2 focus:ring-zenic-200 outline-none transition-colors disabled:bg-gray-50"
              />
              <button
                onClick={submitAnswer}
                disabled={loading || !currentValue.trim() || !!(sessionState?.is_complete)}
                className="rounded-lg bg-zenic-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-all hover:bg-zenic-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                    Enviando...
                  </span>
                ) : (
                  'Enviar'
                )}
              </button>
            </div>
          ) : (
            <button
              onClick={startSession}
              disabled={loading}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-zenic-600 px-4 py-3 text-sm font-semibold text-white shadow-sm transition-all hover:bg-zenic-700 disabled:opacity-50"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                  Iniciando...
                </span>
              ) : (
                <>
                  <span>🚀</span>
                  Iniciar sesión de recolección
                </>
              )}
            </button>
          )}

          {/* Session info */}
          {sessionState && (
            <div className="mt-3 flex items-center justify-between rounded-lg bg-gray-50 px-4 py-2 text-xs text-gray-500">
              <span>ID: {sessionState.session_id.slice(0, 12)}...</span>
              <span>Progreso: {sessionState.completion_pct.toFixed(0)}%</span>
              <span>Preguntas: {sessionState.questions.length}</span>
              <span>{sessionState.is_complete ? '✅ Completa' : '⏳ En curso'}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
