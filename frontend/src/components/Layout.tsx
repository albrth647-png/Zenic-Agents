import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const navItems = {
  admin: [
    { label: 'Dashboard', path: '/', icon: '📊' },
    { label: 'Tenants', path: '/tenants', icon: '🏢' },
    { label: 'Planes', path: '/plans', icon: '📋' },
    { label: 'Salud', path: '/health', icon: '❤️' },
    { label: 'Auditoría', path: '/audit', icon: '📝' },
  ],
  client: [
    { label: 'Dashboard', path: '/', icon: '📊' },
    { label: 'Colector', path: '/collector', icon: '🤖' },
    { label: 'Canales', path: '/channels', icon: '📡' },
    { label: 'Uso', path: '/usage', icon: '📈' },
  ],
};

export default function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout, isAdmin } = useAuth();
  const location = useLocation();

  if (!user) return <>{children}</>;

  const items = isAdmin ? navItems.admin : navItems.client;

  return (
    <div className="flex h-screen overflow-hidden bg-gray-50">
      {/* Sidebar */}
      <aside className="flex w-64 flex-col bg-white border-r border-gray-200">
        {/* Logo */}
        <div className="flex h-16 items-center gap-3 border-b border-gray-200 px-6">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-zenic-600 text-sm font-bold text-white">
            Z
          </span>
          <div className="flex flex-col">
            <span className="text-sm font-semibold text-gray-900">Zenic Agents</span>
            <span className="text-xs text-gray-500">{isAdmin ? 'Admin' : `${(user?.tenant_id || '').slice(0, 8)}...`}</span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 overflow-y-auto p-4">
          {items.map((item) => {
            const active = item.path === '/'
              ? location.pathname === '/'
              : location.pathname.startsWith(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                  active
                    ? 'bg-zenic-50 text-zenic-700'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                }`}
              >
                <span className="text-lg">{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* User footer */}
        <div className="border-t border-gray-200 p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-zenic-100 text-xs font-bold text-zenic-700">
              {user.email.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="truncate text-sm font-medium text-gray-900">
                {user.name || user.email}
              </p>
              <p className="truncate text-xs text-gray-500">{user.email}</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg border border-gray-200 px-3 py-2 text-sm font-medium text-gray-600 transition-colors hover:bg-gray-50 hover:text-gray-900"
          >
            Cerrar sesión
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-7xl px-6 py-8">
          {children}
        </div>
      </main>
    </div>
  );
}
