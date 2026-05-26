/* ============================================================
   Zenic Agents v3.0.0 — Authentication Module (auth.js)
   Register, Login, Session, Password Reset
   Uses SHA-256 via SubtleCrypto for hashing
   ============================================================ */

const ZenicAuth = (function() {
  'use strict';

  const SESSION_KEY = 'zenic_session';
  const TOKEN_PREFIX = 'zenic_tok_';

  let currentUser = null;
  let currentSession = null;

  // ============================================================
  // REGISTER
  // ============================================================
  async function register(name, email, password, org) {
    // Validation
    if (!name || name.trim().length < 2) {
      return { success: false, error: 'El nombre debe tener al menos 2 caracteres' };
    }
    if (!email || !email.includes('@')) {
      return { success: false, error: 'Correo electrónico inválido' };
    }
    if (!password || password.length < 6) {
      return { success: false, error: 'La contraseña debe tener al menos 6 caracteres' };
    }

    // Check if email exists
    const existing = await ZenicDB.findByField('users', 'email', email.toLowerCase());
    if (existing && existing.length > 0) {
      return { success: false, error: 'Este correo ya está registrado' };
    }

    // Hash password
    const passwordHash = await ZenicDB.hashPassword(password);

    // Create user
    const userId = ZenicDB.generateId('user');
    const userData = {
      id: userId,
      email: email.toLowerCase(),
      name: name.trim(),
      password_hash: passwordHash,
      organization: org || '',
      role_id: 'role-operator',
      is_active: 1
    };

    await ZenicDB.create('users', userData);

    // Create subscription
    await ZenicDB.create('subscriptions', {
      id: ZenicDB.generateId('sub'),
      user_id: userId,
      tier: 'starter',
      status: 'active',
      features: '{"agents":5,"tools":10,"policies":20,"hitl_monthly":50,"storage_mb":100}',
      usage_counters: '{"agents_used":0,"tools_used":0,"policies_used":0,"hitl_used":0,"storage_used_mb":0}'
    });

    // Audit
    await ZenicDB.addAudit(userId, 'user.registered', 'auth', userId, { email, name });

    // Auto-login
    const session = await _createSession(userId);
    return { success: true, user: session.user, token: session.token };
  }

  // ============================================================
  // LOGIN
  // ============================================================
  async function login(email, password) {
    if (!email || !password) {
      return { success: false, error: 'Correo y contraseña son requeridos' };
    }

    // Find user
    const users = await ZenicDB.findByField('users', 'email', email.toLowerCase());
    if (!users || users.length === 0) {
      return { success: false, error: 'Credenciales inválidas' };
    }

    const user = users[0];

    // Check active
    if (!user.is_active) {
      return { success: false, error: 'Cuenta desactivada. Contacta al administrador.' };
    }

    // Verify password
    const hash = await ZenicDB.hashPassword(password);
    if (hash !== user.password_hash) {
      // Audit failed attempt
      await ZenicDB.addAudit(user.id, 'auth.login_failed', 'auth', user.id, { email }, 'warning');
      return { success: false, error: 'Credenciales inválidas' };
    }

    // Update last login
    await ZenicDB.run(`UPDATE users SET last_login = datetime('now') WHERE id = ?`, [user.id]);

    // Create session
    const session = await _createSession(user.id);

    // Audit success
    await ZenicDB.addAudit(user.id, 'auth.login_success', 'auth', user.id, { method: 'password' });

    return { success: true, user: session.user, token: session.token };
  }

  // ============================================================
  // SESSION MANAGEMENT
  // ============================================================
  async function _createSession(userId) {
    const user = await ZenicDB.findById('users', userId);
    if (!user) return null;

    // Get role
    const role = await ZenicDB.findById('roles', user.role_id);
    const roleName = role ? role.name : 'Operador';

    // Generate token
    const token = TOKEN_PREFIX + Date.now().toString(36) + Math.random().toString(36).substr(2, 12);

    // Store session in DB
    await ZenicDB.create('sessions', {
      id: ZenicDB.generateId('sess'),
      user_id: userId,
      token: token,
      device_info: JSON.stringify({ platform: 'mobile', version: '3.0.0' }),
      expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString()
    });

    // Store in localStorage
    const sessionData = {
      userId: user.id,
      email: user.email,
      name: user.name,
      role: roleName,
      roleId: user.role_id,
      organization: user.organization,
      token: token,
      createdAt: new Date().toISOString()
    };

    localStorage.setItem(SESSION_KEY, JSON.stringify(sessionData));

    currentUser = sessionData;
    currentSession = sessionData;

    return { user: sessionData, token };
  }

  function getSession() {
    if (currentSession) return currentSession;

    try {
      const saved = localStorage.getItem(SESSION_KEY);
      if (saved) {
        currentSession = JSON.parse(saved);
        currentUser = currentSession;
        return currentSession;
      }
    } catch(e) {}

    return null;
  }

  function isAuthenticated() {
    const session = getSession();
    if (!session) return false;

    // Check expiration (7 days)
    const created = new Date(session.createdAt);
    const expires = new Date(created.getTime() + 7 * 24 * 60 * 60 * 1000);
    return new Date() < expires;
  }

  async function logout() {
    const session = getSession();
    if (session) {
      // Audit
      await ZenicDB.addAudit(session.userId, 'auth.logout', 'auth', session.userId, {});
    }

    // Clear session
    localStorage.removeItem(SESSION_KEY);
    currentUser = null;
    currentSession = null;
  }

  // ============================================================
  // CHANGE PASSWORD
  // ============================================================
  async function changePassword(userId, currentPassword, newPassword) {
    if (!newPassword || newPassword.length < 6) {
      return { success: false, error: 'La nueva contraseña debe tener al menos 6 caracteres' };
    }

    // Verify current password
    const user = await ZenicDB.findById('users', userId);
    if (!user) {
      return { success: false, error: 'Usuario no encontrado' };
    }

    const currentHash = await ZenicDB.hashPassword(currentPassword);
    if (currentHash !== user.password_hash) {
      return { success: false, error: 'Contraseña actual incorrecta' };
    }

    // Update password
    const newHash = await ZenicDB.hashPassword(newPassword);
    await ZenicDB.run(`UPDATE users SET password_hash = ?, updated_at = datetime('now') WHERE id = ?`, [newHash, userId]);

    // Audit
    await ZenicDB.addAudit(userId, 'auth.password_changed', 'auth', userId, {}, 'warning');

    return { success: true };
  }

  // ============================================================
  // PASSWORD RESET (local - generates new password)
  // ============================================================
  async function resetPassword(email) {
    const users = await ZenicDB.findByField('users', 'email', email.toLowerCase());
    if (!users || users.length === 0) {
      return { success: false, error: 'No se encontró cuenta con ese correo' };
    }

    const user = users[0];
    const tempPassword = 'zenic_' + Math.random().toString(36).substr(2, 8);
    const hash = await ZenicDB.hashPassword(tempPassword);

    await ZenicDB.run(`UPDATE users SET password_hash = ?, updated_at = datetime('now') WHERE id = ?`, [hash, user.id]);

    await ZenicDB.addAudit(user.id, 'auth.password_reset', 'auth', user.id, {}, 'warning');

    return { success: true, tempPassword };
  }

  // ============================================================
  // GET CURRENT USER (from DB, fresh)
  // ============================================================
  async function getCurrentUser() {
    const session = getSession();
    if (!session) return null;

    const user = await ZenicDB.findById('users', session.userId);
    if (!user) return null;

    const role = await ZenicDB.findById('roles', user.role_id);

    return {
      id: user.id,
      email: user.email,
      name: user.name,
      organization: user.organization,
      role: role ? role.name : 'Operador',
      roleId: user.role_id,
      lastLogin: user.last_login,
      createdAt: user.created_at
    };
  }

  // ============================================================
  // UPDATE PROFILE
  // ============================================================
  async function updateProfile(userId, data) {
    const updates = {};
    if (data.name) updates.name = data.name;
    if (data.organization) updates.organization = data.organization;

    await ZenicDB.update('users', userId, updates);

    // Update session
    const session = getSession();
    if (session) {
      Object.assign(session, updates);
      localStorage.setItem(SESSION_KEY, JSON.stringify(session));
      currentUser = session;
    }

    await ZenicDB.addAudit(userId, 'user.profile_updated', 'user', userId, updates);

    return { success: true };
  }

  // ============================================================
  // PERMISSIONS CHECK
  // ============================================================
  async function hasPermission(permissionName) {
    const session = getSession();
    if (!session) return false;

    // Admin has all permissions
    if (session.roleId === 'role-admin') return true;

    const perms = await ZenicDB.query(
      `SELECT p.name FROM permissions p
       JOIN role_permissions rp ON p.id = rp.permission_id
       WHERE rp.role_id = ? AND p.name = ?`,
      [session.roleId, permissionName]
    );

    return perms && perms.length > 0;
  }

  // ============================================================
  // PUBLIC API
  // ============================================================
  return {
    register,
    login,
    logout,
    getSession,
    isAuthenticated,
    getCurrentUser,
    changePassword,
    resetPassword,
    updateProfile,
    hasPermission
  };
})();
