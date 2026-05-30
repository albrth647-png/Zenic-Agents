//! Policy Engine — PolicyEngine implementation.

use zenic_proto::{NodeCriticality, SessionId, TenantId};

use crate::audit::{AuditLog, DenialReason, PolicyDecision};
use crate::errors::PolicyError;
use crate::gate::{CriticalityGate, SafetyVeto, SafetyVetoRegistry};
use crate::role::{CriticalityClearance, Role, RoleAssignment, RoleId, RoleRegistry};
use crate::rule::{RuleEffect, RuleSet};

use super::types::PolicyContext;

// ---------------------------------------------------------------------------
// PolicyEngine
// ---------------------------------------------------------------------------

/// The main policy evaluation engine.
///
/// The engine coordinates all policy sub-systems:
/// - [`RoleRegistry`] — RBAC role definitions and lookup.
/// - [`RuleSet`] — explicit allow/deny policy rules.
/// - [`SafetyVetoRegistry`] — immutable deny rules.
/// - [`CriticalityGate`] — criticality clearance enforcement.
/// - [`AuditLog`] — decision audit trail.
///
/// Evaluation follows a strict order where the first failure
/// stops the evaluation and returns a denial. This ensures
/// that safety vetoes are always checked first, followed by
/// RBAC, rules, and criticality gates.
pub struct PolicyEngine {
    /// RBAC role registry.
    pub(crate) role_registry: RoleRegistry,
    /// Role assignments (session → role mappings).
    pub(crate) role_assignments: Vec<RoleAssignment>,
    /// Policy rule set.
    pub(crate) rule_set: RuleSet,
    /// Safety veto registry (immutable once registered).
    pub(crate) veto_registry: SafetyVetoRegistry,
    /// Criticality gate.
    pub(crate) criticality_gate: CriticalityGate,
    /// Audit log for all decisions.
    pub(crate) audit_log: AuditLog,
}

impl PolicyEngine {
    /// Creates a new policy engine with empty registries.
    pub fn new() -> Self {
        Self {
            role_registry: RoleRegistry::new(),
            role_assignments: Vec::new(),
            rule_set: RuleSet::new(),
            veto_registry: SafetyVetoRegistry::new(),
            criticality_gate: CriticalityGate::new(),
            audit_log: AuditLog::new(),
        }
    }

    // -----------------------------------------------------------------------
    // Role management
    // -----------------------------------------------------------------------

    /// Registers a role in the engine.
    pub fn register_role(&mut self, role: Role) -> Result<(), PolicyError> {
        self.role_registry.register(role)
    }

    /// Assigns a role to a session within a tenant.
    pub fn assign_role(
        &mut self,
        role_id: RoleId,
        session_id: SessionId,
        tenant_id: TenantId,
    ) -> Result<(), PolicyError> {
        if !self.role_registry.contains(&role_id) {
            return Err(PolicyError::RoleNotFound(role_id));
        }
        let assignment = RoleAssignment::new(role_id, session_id, tenant_id);
        self.role_assignments.push(assignment);
        Ok(())
    }

    /// Returns the number of registered roles.
    pub fn role_count(&self) -> usize {
        self.role_registry.len()
    }

    /// Returns the number of role assignments.
    pub fn assignment_count(&self) -> usize {
        self.role_assignments.len()
    }

    // -----------------------------------------------------------------------
    // Rule management
    // -----------------------------------------------------------------------

    /// Adds a policy rule to the engine.
    pub fn add_rule(
        &mut self,
        rule: crate::rule::PolicyRule,
    ) -> Result<(), PolicyError> {
        self.rule_set.add(rule)
    }

    /// Returns the number of policy rules.
    pub fn rule_count(&self) -> usize {
        self.rule_set.len()
    }

    // -----------------------------------------------------------------------
    // Safety veto management
    // -----------------------------------------------------------------------

    /// Registers a safety veto (immutable once added).
    pub fn register_veto(&mut self, veto: SafetyVeto) -> Result<(), PolicyError> {
        self.veto_registry.register(veto)
    }

    /// Returns the number of safety vetoes.
    pub fn veto_count(&self) -> usize {
        self.veto_registry.len()
    }

    // -----------------------------------------------------------------------
    // Criticality gate management
    // -----------------------------------------------------------------------

    /// Replaces the criticality gate with a new one built from the provided
    /// thresholds.
    pub fn replace_criticality_gate(&mut self, gate: CriticalityGate) {
        self.criticality_gate = gate;
    }

    /// Returns the clearance required for a given criticality level.
    pub fn required_clearance(&self, criticality: NodeCriticality) -> CriticalityClearance {
        self.criticality_gate.required_clearance(criticality)
    }

    // -----------------------------------------------------------------------
    // Audit log queries
    // -----------------------------------------------------------------------

    /// Returns the number of audit log entries.
    pub fn audit_count(&self) -> usize {
        self.audit_log.len()
    }

    /// Returns all audit log entries.
    pub fn audit_entries(&self) -> &[crate::audit::PolicyAuditEntry] {
        self.audit_log.entries()
    }

    /// Returns denial entries from the audit log.
    pub fn audit_denials(&self) -> Vec<&crate::audit::PolicyAuditEntry> {
        self.audit_log.denials()
    }

    // -----------------------------------------------------------------------
    // Evaluation
    // -----------------------------------------------------------------------

    /// Evaluates a policy request and returns the decision.
    ///
    /// Evaluation order:
    /// 1. Safety veto check — if any veto blocks the permission, deny.
    /// 2. RBAC check — if no role grants the permission, deny.
    /// 3. Rule evaluation — if an explicit deny rule matches, deny.
    ///    If an explicit allow rule matches, allow.
    /// 4. Criticality gate — if the target has a criticality level
    ///    and the session's roles lack clearance, deny.
    /// 5. Default deny — if nothing matched, deny.
    pub fn evaluate(&mut self, ctx: &PolicyContext) -> Result<PolicyDecision, PolicyError> {
        let roles = self.role_registry.roles_for_session(
            &self.role_assignments,
            &ctx.session_id,
            &ctx.tenant_id,
        );
        let role_ids: Vec<RoleId> = roles.iter().map(|r| r.id).collect();

        // Step 1: Safety veto check.
        if let Some(veto) = self.veto_registry.blocking_veto(&ctx.permission) {
            self.audit_log.record_denied(
                ctx.session_id,
                ctx.tenant_id,
                ctx.permission.clone(),
                DenialReason::SafetyVeto(veto.name.clone()),
                role_ids,
            );
            return Err(PolicyError::SafetyVetoTriggered {
                rule_name: veto.name.clone(),
                resource: ctx.permission.resource.to_string(),
            });
        }

        // Step 2: RBAC permission check.
        let has_rbac_permission = roles.iter().any(|r| r.implies_permission(&ctx.permission));
        if !has_rbac_permission {
            self.audit_log.record_denied(
                ctx.session_id,
                ctx.tenant_id,
                ctx.permission.clone(),
                DenialReason::NoMatchingRole,
                role_ids,
            );
            return Err(PolicyError::PermissionDenied {
                session_id: ctx.session_id,
                permission: ctx.permission.clone(),
                tenant_id: ctx.tenant_id,
            });
        }

        // Step 3: Policy rule evaluation.
        let rule_effect = self.rule_set.evaluate(&ctx.permission, ctx.domain);
        match rule_effect {
            Some(RuleEffect::Deny) => {
                self.audit_log.record_denied(
                    ctx.session_id,
                    ctx.tenant_id,
                    ctx.permission.clone(),
                    DenialReason::RuleDenied("explicit_deny".to_string()),
                    role_ids,
                );
                return Err(PolicyError::PermissionDenied {
                    session_id: ctx.session_id,
                    permission: ctx.permission.clone(),
                    tenant_id: ctx.tenant_id,
                });
            }
            Some(RuleEffect::Allow) => {
                // Rule explicitly allows. Continue to criticality gate.
            }
            None => {
                // No rule matched. Default deny.
                self.audit_log.record_denied(
                    ctx.session_id,
                    ctx.tenant_id,
                    ctx.permission.clone(),
                    DenialReason::DefaultDeny,
                    role_ids,
                );
                return Err(PolicyError::PermissionDenied {
                    session_id: ctx.session_id,
                    permission: ctx.permission.clone(),
                    tenant_id: ctx.tenant_id,
                });
            }
        }

        // Step 4: Criticality gate check.
        if let (Some(criticality), Some(node_id)) = (ctx.criticality, ctx.node_id) {
            if let Err(e) = self.criticality_gate.check(
                &roles,
                criticality,
                ctx.session_id,
                node_id,
            ) {
                self.audit_log.record_denied(
                    ctx.session_id,
                    ctx.tenant_id,
                    ctx.permission.clone(),
                    DenialReason::CriticalityGate,
                    role_ids,
                );
                return Err(e);
            }
        }

        // Step 5: All checks passed. Allow.
        self.audit_log.record_allowed(
            ctx.session_id,
            ctx.tenant_id,
            ctx.permission.clone(),
            role_ids,
        );
        Ok(PolicyDecision::Allowed)
    }

    /// Convenience method: checks if a session is allowed to perform
    /// an action, returning a boolean without error details.
    pub fn is_allowed(&mut self, ctx: &PolicyContext) -> bool {
        self.evaluate(ctx).is_ok()
    }

    // -----------------------------------------------------------------------
    // Zero-copy rkyv evaluation (stub)
    // -----------------------------------------------------------------------

    /// Evaluates a policy request using a pre-serialized rkyv byte buffer.
    ///
    /// **STUB**: Full integration will be in Phase 3 when the SharedMemoryBus
    /// uses rkyv for zero-copy transit.
    pub fn evaluate_rkyv(&mut self, _buffer: &[u8]) -> Result<PolicyDecision, PolicyError> {
        tracing::warn!(
            "evaluate_rkyv called but not yet implemented; \
             full integration arrives in Phase 3 (SharedMemoryBus)"
        );
        Err(PolicyError::General(
            "evaluate_rkyv is a stub — not yet integrated with SharedMemoryBus".to_string(),
        ))
    }
}

impl Default for PolicyEngine {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// Tests (consolidated from evaluator.rs)
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use zenic_proto::{NodeId, NodeCriticality, SessionId, TenantId};

    use crate::audit::PolicyDecision;
    use crate::gate::SafetyVeto;
    use crate::permission::{Action, Permission, Resource};
    use crate::role::{CriticalityClearance, Role};
    use crate::rule::PolicyRule;

    use super::PolicyEngine;
    use super::super::types::PolicyContext;

    // -----------------------------------------------------------------------
    // Test helpers
    // -----------------------------------------------------------------------

    fn make_admin_role() -> Role {
        let mut role = Role::new("admin", "Administrator")
            .with_priority(crate::role::RolePriority::Admin)
            .with_clearance(CriticalityClearance::Critical);
        role.add_permission(Permission::new(Action::Admin, Resource::AllNodes));
        role.add_permission(Permission::new(Action::Execute, Resource::AllNodes));
        role.add_permission(Permission::new(Action::Read, Resource::AllNodes));
        role.add_permission(Permission::new(Action::Write, Resource::AllNodes));
        role.add_permission(Permission::new(Action::Delete, Resource::AllNodes));
        role.add_permission(Permission::new(Action::Cancel, Resource::AllWorkflows));
        role.add_permission(Permission::new(Action::ViewAudit, Resource::AuditLog));
        role.add_permission(Permission::new(Action::ManageRoles, Resource::RoleRegistry));
        role
    }

    fn make_viewer_role() -> Role {
        let mut role = Role::new("viewer", "View-only")
            .with_priority(crate::role::RolePriority::Viewer)
            .with_clearance(CriticalityClearance::Low);
        role.add_permission(Permission::new(Action::Read, Resource::AllNodes));
        role
    }

    fn make_operator_role() -> Role {
        let mut role = Role::new("operator", "Standard operator")
            .with_priority(crate::role::RolePriority::Standard)
            .with_clearance(CriticalityClearance::High);
        role.add_permission(Permission::new(Action::Execute, Resource::AllNodes));
        role.add_permission(Permission::new(Action::Read, Resource::AllNodes));
        role.add_permission(Permission::new(Action::Write, Resource::AllNodes));
        role
    }

    // -----------------------------------------------------------------------
    // PolicyEngine: full evaluation — allowed
    // -----------------------------------------------------------------------

    #[test]
    fn engine_evaluate_allowed() {
        let mut engine = PolicyEngine::new();
        let role = make_operator_role();
        let role_id = role.id;
        engine.register_role(role).expect("register");

        let sid = SessionId::new();
        let tid = TenantId::new();
        engine.assign_role(role_id, sid, tid).expect("assign");

        // Add an allow rule.
        engine
            .add_rule(PolicyRule::allow(
                "allow_execute",
                "Allow execute",
                Permission::new(Action::Execute, Resource::AllNodes),
            ))
            .expect("add rule");

        let ctx = PolicyContext::new(
            sid,
            tid,
            Permission::new(Action::Execute, Resource::AllNodes),
        );

        let result = engine.evaluate(&ctx);
        assert!(result.is_ok());
        assert_eq!(result.unwrap(), PolicyDecision::Allowed);
        assert_eq!(engine.audit_count(), 1);
    }

    #[test]
    fn engine_is_allowed_convenience() {
        let mut engine = PolicyEngine::new();
        let role = make_operator_role();
        let role_id = role.id;
        engine.register_role(role).expect("register");

        let sid = SessionId::new();
        let tid = TenantId::new();
        engine.assign_role(role_id, sid, tid).expect("assign");

        engine
            .add_rule(PolicyRule::allow(
                "allow_execute",
                "Allow execute",
                Permission::new(Action::Execute, Resource::AllNodes),
            ))
            .expect("add rule");

        let ctx = PolicyContext::new(
            sid,
            tid,
            Permission::new(Action::Execute, Resource::AllNodes),
        );

        assert!(engine.is_allowed(&ctx));
    }

    // -----------------------------------------------------------------------
    // PolicyEngine: veto blocks
    // -----------------------------------------------------------------------

    #[test]
    fn engine_evaluate_veto_blocks() {
        let mut engine = PolicyEngine::new();
        let role = make_admin_role();
        let role_id = role.id;
        engine.register_role(role).expect("register");

        let sid = SessionId::new();
        let tid = TenantId::new();
        engine.assign_role(role_id, sid, tid).expect("assign");

        engine
            .add_rule(PolicyRule::allow(
                "allow_delete",
                "Allow delete",
                Permission::new(Action::Delete, Resource::AllNodes),
            ))
            .expect("add rule");

        // Register a safety veto that blocks deletion.
        engine
            .register_veto(SafetyVeto::new(
                "no_delete",
                "Never delete",
                Action::Delete,
                Resource::AllNodes,
            ))
            .expect("register veto");

        let ctx = PolicyContext::new(
            sid,
            tid,
            Permission::new(Action::Delete, Resource::AllNodes),
        );

        let result = engine.evaluate(&ctx);
        assert!(result.is_err());
        assert!(!engine.audit_denials().is_empty());
    }

    // -----------------------------------------------------------------------
    // PolicyEngine: no role denies
    // -----------------------------------------------------------------------

    #[test]
    fn engine_evaluate_no_role_denies() {
        let mut engine = PolicyEngine::new();
        engine
            .add_rule(PolicyRule::allow(
                "allow_execute",
                "Allow execute",
                Permission::new(Action::Execute, Resource::AllNodes),
            ))
            .expect("add rule");

        let ctx = PolicyContext::new(
            SessionId::new(),
            TenantId::new(),
            Permission::new(Action::Execute, Resource::AllNodes),
        );

        let result = engine.evaluate(&ctx);
        assert!(result.is_err());
    }

    // -----------------------------------------------------------------------
    // PolicyEngine: explicit deny rule
    // -----------------------------------------------------------------------

    #[test]
    fn engine_evaluate_explicit_deny_rule() {
        let mut engine = PolicyEngine::new();
        let role = make_operator_role();
        let role_id = role.id;
        engine.register_role(role).expect("register");

        let sid = SessionId::new();
        let tid = TenantId::new();
        engine.assign_role(role_id, sid, tid).expect("assign");

        engine
            .add_rule(PolicyRule::deny(
                "deny_delete",
                "Deny delete",
                Permission::new(Action::Delete, Resource::AllNodes),
            ))
            .expect("add rule");

        let ctx = PolicyContext::new(
            sid,
            tid,
            Permission::new(Action::Delete, Resource::AllNodes),
        );

        let result = engine.evaluate(&ctx);
        assert!(result.is_err());
    }

    // -----------------------------------------------------------------------
    // PolicyEngine: default deny (no rule matches)
    // -----------------------------------------------------------------------

    #[test]
    fn engine_evaluate_default_deny() {
        let mut engine = PolicyEngine::new();
        let role = make_operator_role();
        let role_id = role.id;
        engine.register_role(role).expect("register");

        let sid = SessionId::new();
        let tid = TenantId::new();
        engine.assign_role(role_id, sid, tid).expect("assign");

        // No rule added — should default-deny.
        let ctx = PolicyContext::new(
            sid,
            tid,
            Permission::new(Action::Execute, Resource::AllNodes),
        );

        let result = engine.evaluate(&ctx);
        assert!(result.is_err());
    }

    // -----------------------------------------------------------------------
    // PolicyEngine: criticality gate blocks
    // -----------------------------------------------------------------------

    #[test]
    fn engine_evaluate_criticality_gate_blocks() {
        let mut engine = PolicyEngine::new();
        let role = make_viewer_role(); // Low clearance
        let role_id = role.id;
        engine.register_role(role).expect("register");

        let sid = SessionId::new();
        let tid = TenantId::new();
        engine.assign_role(role_id, sid, tid).expect("assign");

        engine
            .add_rule(PolicyRule::allow(
                "allow_execute",
                "Allow execute",
                Permission::new(Action::Execute, Resource::AllNodes),
            ))
            .expect("add rule");

        let node_id = NodeId::new();
        let ctx = PolicyContext::new(
            sid,
            tid,
            Permission::new(Action::Execute, Resource::Node(node_id)),
        )
        .with_criticality(NodeCriticality::Critical, node_id);

        let result = engine.evaluate(&ctx);
        assert!(result.is_err());
    }
}
