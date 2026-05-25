// ─── Safety Gate Types ───────────────────────────────────────────────────
// ActionCategory, SafetyVerdict, SafetyCheckResult, SafetyRule, default_verdict, risk_score

use pyo3::prelude::*;

// ═══════════════════════════════════════════════════════════════
//  ActionCategory
// ═══════════════════════════════════════════════════════════════

/// Classification of action risk level.
///
/// Mirrors the Python ``ActionCategory`` string-enum exactly:
///
/// ======== ============ ===================================
/// Variant  Python value Meaning
/// ======== ============ ===================================
/// Safe     ``"safe"``   Read-only, non-destructive
/// Moderate ``"moderate"`` Write operations, single record
/// Destructive ``"destructive"`` Delete, drop, bulk operations
/// Financial ``"financial"`` Involves money, invoices, payments
/// System   ``"system"`` System-level changes
/// ======== ============ ===================================
#[pyclass(name = "ActionCategory", eq, eq_int, frozen, hash)]
#[derive(Clone, Debug, PartialEq, Eq, Hash, Copy)]
pub enum ActionCategory {
    Safe,
    Moderate,
    Destructive,
    Financial,
    System,
}

impl ActionCategory {
    /// Return the Python-enum string value (e.g. ``"safe"``).
    pub fn as_str(&self) -> &'static str {
        match self {
            ActionCategory::Safe => "safe",
            ActionCategory::Moderate => "moderate",
            ActionCategory::Destructive => "destructive",
            ActionCategory::Financial => "financial",
            ActionCategory::System => "system",
        }
    }
}

#[pymethods]
impl ActionCategory {
    /// Python ``str()`` → the enum value string.
    fn __str__(&self) -> &'static str {
        self.as_str()
    }

    /// Python ``repr()`` → ``ActionCategory.SAFE`` etc.
    fn __repr__(&self) -> String {
        match self {
            ActionCategory::Safe => "ActionCategory.SAFE".into(),
            ActionCategory::Moderate => "ActionCategory.MODERATE".into(),
            ActionCategory::Destructive => "ActionCategory.DESTRUCTIVE".into(),
            ActionCategory::Financial => "ActionCategory.FINANCIAL".into(),
            ActionCategory::System => "ActionCategory.SYSTEM".into(),
        }
    }
}

// ═══════════════════════════════════════════════════════════════
//  SafetyVerdict
// ═══════════════════════════════════════════════════════════════

/// Safety gate verdict.
///
/// Mirrors the Python ``SafetyVerdict`` string-enum:
///
/// ============ ==================================================
/// Variant      Meaning
/// ============ ==================================================
/// Allow        Action may proceed
/// Confirm      Requires user confirmation before proceeding
/// Approve      Requires higher-role approval
/// Deny         Absolutely denied — **no override**
/// RateLimited  Too many actions, slow down
/// ============ ==================================================
#[pyclass(name = "SafetyVerdict", eq, eq_int, frozen, hash)]
#[derive(Clone, Debug, PartialEq, Eq, Hash, Copy)]
pub enum SafetyVerdict {
    Allow,
    Confirm,
    Approve,
    Deny,
    RateLimited,
}

impl SafetyVerdict {
    pub fn as_str(&self) -> &'static str {
        match self {
            SafetyVerdict::Allow => "ALLOW",
            SafetyVerdict::Confirm => "CONFIRM",
            SafetyVerdict::Approve => "APPROVE",
            SafetyVerdict::Deny => "DENY",
            SafetyVerdict::RateLimited => "RATE_LIMITED",
        }
    }

    /// Delegate severity() to zenic-safety canonical implementation.
    pub fn severity(&self) -> u8 {
        let canonical: zenic_safety::SafetyVerdict = (*self).into();
        canonical.severity()
    }

    /// Delegate can_proceed() to zenic-safety canonical implementation.
    pub fn can_proceed(&self) -> bool {
        let canonical: zenic_safety::SafetyVerdict = (*self).into();
        canonical.can_proceed()
    }

    /// Delegate escalate() to zenic-safety canonical implementation.
    pub fn escalate(self) -> Self {
        let canonical: zenic_safety::SafetyVerdict = self.into();
        canonical.escalate().into()
    }

    /// Delegate is_blocked() to zenic-safety canonical implementation.
    pub fn is_blocked(&self) -> bool {
        let canonical: zenic_safety::SafetyVerdict = (*self).into();
        canonical.is_blocked()
    }
}

impl Default for SafetyVerdict {
    fn default() -> Self {
        SafetyVerdict::Allow
    }
}

impl Ord for SafetyVerdict {
    fn cmp(&self, other: &Self) -> std::cmp::Ordering {
        let a: zenic_safety::SafetyVerdict = (*self).into();
        let b: zenic_safety::SafetyVerdict = (*other).into();
        a.cmp(&b)
    }
}

impl PartialOrd for SafetyVerdict {
    fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> {
        Some(self.cmp(other))
    }
}

#[pymethods]
impl SafetyVerdict {
    fn __str__(&self) -> &'static str {
        self.as_str()
    }

    fn __repr__(&self) -> String {
        format!("SafetyVerdict.{}", self.as_str())
    }

    /// Severity level (0=Allow .. 4=Deny). Delegates to zenic-safety.
    #[getter]
    fn severity(&self) -> u8 {
        SafetyVerdict::severity(self)
    }

    /// Whether action can proceed. Delegates to zenic-safety.
    fn can_proceed(&self) -> bool {
        SafetyVerdict::can_proceed(self)
    }

    /// Escalate verdict one level. Delegates to zenic-safety.
    fn escalate(me: &Bound<'_, Self>) -> PyResult<Self> {
        let val: SafetyVerdict = me.extract()?;
        Ok(val.escalate())
    }

    /// Whether verdict is blocked (Deny or RateLimited).
    fn is_blocked(&self) -> bool {
        SafetyVerdict::is_blocked(self)
    }
}

// ═══════════════════════════════════════════════════════════════
//  SafetyCheckResult
// ═══════════════════════════════════════════════════════════════

/// Result of a safety gate check.
///
/// All fields are **read-only** from Python (private Rust fields
/// exposed via ``#[getter]``).  This guarantees the DENY invariant
/// at the type level — no Python code can mutate a verdict.
///
/// The ``action_id`` is a unique identifier generated per validation.
/// It is the ONLY key that confirm_action/approve_action accept
/// for checking the DENY invariant. This prevents the key-mismatch
/// bypass where denied actions were stored by rule_name but
/// confirm/approve checked by a user-provided action_id.
#[pyclass(name = "SafetyCheckResult")]
#[derive(Clone, Debug)]
pub struct SafetyCheckResult {
    /// Unique action identifier (UUID v4) for this validation result.
    /// Used as the key in DENIED_ACTIONS, CONFIRMATIONS, and APPROVALS.
    pub(crate) action_id: String,
    pub(crate) verdict: SafetyVerdict,
    pub(crate) category: ActionCategory,
    pub(crate) reason: String,
    pub(crate) rule_name: String,
    pub(crate) requires_confirmation: bool,
    pub(crate) requires_approval: bool,
    pub(crate) risk_score: f64,
}

#[pymethods]
impl SafetyCheckResult {
    // ── Read-only getters ──────────────────────────────────────

    #[getter]
    fn action_id(&self) -> &str {
        &self.action_id
    }

    #[getter]
    fn verdict(&self) -> SafetyVerdict {
        self.verdict.clone()
    }

    #[getter]
    fn category(&self) -> ActionCategory {
        self.category.clone()
    }

    #[getter]
    fn reason(&self) -> &str {
        &self.reason
    }

    #[getter]
    fn rule_name(&self) -> &str {
        &self.rule_name
    }

    #[getter]
    fn requires_confirmation(&self) -> bool {
        self.requires_confirmation
    }

    #[getter]
    fn requires_approval(&self) -> bool {
        self.requires_approval
    }

    #[getter]
    fn risk_score(&self) -> f64 {
        self.risk_score
    }

    // ── Convenience helpers ────────────────────────────────────

    /// Return ``True`` if the action can proceed (ALLOW, CONFIRM, or APPROVE).
    ///
    /// Returns ``False`` for DENY and RATE_LIMITED, enforcing the
    /// critical invariant that denied actions must never execute.
    fn can_proceed(&self) -> bool {
        !matches!(
            self.verdict,
            SafetyVerdict::Deny | SafetyVerdict::RateLimited
        )
    }

    fn __repr__(&self) -> String {
        format!(
            "SafetyCheckResult(action_id={}, verdict={}, category={}, reason={:?}, \
             rule_name={:?}, requires_confirmation={}, requires_approval={}, \
             risk_score={})",
            self.action_id,
            self.verdict.as_str(),
            self.category.as_str(),
            self.reason,
            self.rule_name,
            self.requires_confirmation,
            self.requires_approval,
            self.risk_score,
        )
    }
}

// ═══════════════════════════════════════════════════════════════
//  Internal SafetyRule
// ═══════════════════════════════════════════════════════════════

/// A deterministic safety rule with a pre-compiled regex pattern.
pub(crate) struct SafetyRule {
    pub name: &'static str,
    pub category: ActionCategory,
    pub pattern: regex::Regex,
    pub verdict: SafetyVerdict,
    pub message: &'static str,
}

/// Default verdict for a given category when no rule matches.
pub(crate) fn default_verdict(category: &ActionCategory) -> SafetyVerdict {
    match category {
        ActionCategory::Safe => SafetyVerdict::Allow,
        ActionCategory::Moderate => SafetyVerdict::Allow,
        ActionCategory::Destructive => SafetyVerdict::Confirm,
        ActionCategory::Financial => SafetyVerdict::Approve,
        ActionCategory::System => SafetyVerdict::Confirm,
    }
}

/// Risk score for a given category.
pub(crate) fn risk_score(category: &ActionCategory) -> f64 {
    match category {
        ActionCategory::Safe => 0.0,
        ActionCategory::Moderate => 0.3,
        ActionCategory::Destructive => 0.8,
        ActionCategory::Financial => 0.7,
        ActionCategory::System => 0.6,
    }
}

// ═══════════════════════════════════════════════════════════════
//  Interop with zenic-safety — From conversions
//
//  These impls allow seamless conversion between the PyO3-exposed
//  types in this module and the canonical zenic-safety types. This
//  eliminates the duplication while keeping the PyO3 #[pyclass]
//  attributes required for Python interop.
// ═══════════════════════════════════════════════════════════════

impl From<zenic_safety::SafetyVerdict> for SafetyVerdict {
    fn from(v: zenic_safety::SafetyVerdict) -> Self {
        match v {
            zenic_safety::SafetyVerdict::Allow => SafetyVerdict::Allow,
            zenic_safety::SafetyVerdict::Confirm => SafetyVerdict::Confirm,
            zenic_safety::SafetyVerdict::Approve => SafetyVerdict::Approve,
            zenic_safety::SafetyVerdict::Deny => SafetyVerdict::Deny,
            zenic_safety::SafetyVerdict::RateLimited => SafetyVerdict::RateLimited,
        }
    }
}

impl From<SafetyVerdict> for zenic_safety::SafetyVerdict {
    fn from(v: SafetyVerdict) -> Self {
        match v {
            SafetyVerdict::Allow => zenic_safety::SafetyVerdict::Allow,
            SafetyVerdict::Confirm => zenic_safety::SafetyVerdict::Confirm,
            SafetyVerdict::Approve => zenic_safety::SafetyVerdict::Approve,
            SafetyVerdict::Deny => zenic_safety::SafetyVerdict::Deny,
            SafetyVerdict::RateLimited => zenic_safety::SafetyVerdict::RateLimited,
        }
    }
}

impl From<zenic_safety::ActionCategory> for ActionCategory {
    fn from(c: zenic_safety::ActionCategory) -> Self {
        match c {
            zenic_safety::ActionCategory::Safe => ActionCategory::Safe,
            zenic_safety::ActionCategory::Moderate => ActionCategory::Moderate,
            zenic_safety::ActionCategory::Destructive => ActionCategory::Destructive,
            zenic_safety::ActionCategory::Financial => ActionCategory::Financial,
            zenic_safety::ActionCategory::System => ActionCategory::System,
        }
    }
}

impl From<ActionCategory> for zenic_safety::ActionCategory {
    fn from(c: ActionCategory) -> Self {
        match c {
            ActionCategory::Safe => zenic_safety::ActionCategory::Safe,
            ActionCategory::Moderate => zenic_safety::ActionCategory::Moderate,
            ActionCategory::Destructive => zenic_safety::ActionCategory::Destructive,
            ActionCategory::Financial => zenic_safety::ActionCategory::Financial,
            ActionCategory::System => zenic_safety::ActionCategory::System,
        }
    }
}
