//! Policy engine management tests: role, rule, veto, gate, and audit operations.
//!
//! The `impl PolicyEngine` methods that were previously here are now
//! consolidated in `engine_impl.rs`.

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use zenic_proto::{NodeId, NodeCriticality, SessionId, TenantId};

    use crate::gate::{CriticalityGateBuilder, SafetyVeto};
    use crate::permission::{Action, Permission, Resource};
    use crate::role::{CriticalityClearance, Role, RoleId};
    use crate::rule::PolicyRule;

    use super::super::engine_impl::PolicyEngine;
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
    // PolicyEngine: role management
    // -----------------------------------------------------------------------

    #[test]
    fn engine_register_role() {
        let mut engine = PolicyEngine::new();
        let role = make_admin_role();
        assert!(engine.register_role(role).is_ok());
        assert_eq!(engine.role_count(), 1);
    }

    #[test]
    fn engine_assign_role() {
        let mut engine = PolicyEngine::new();
        let role = make_admin_role();
        let role_id = role.id;
        engine.register_role(role).expect("register");
        let sid = SessionId::new();
        let tid = TenantId::new();
        assert!(engine.assign_role(role_id, sid, tid).is_ok());
        assert_eq!(engine.assignment_count(), 1);
    }

    #[test]
    fn engine_assign_nonexistent_role_fails() {
        let mut engine = PolicyEngine::new();
        let result = engine.assign_role(RoleId::new(), SessionId::new(), TenantId::new());
        assert!(result.is_err());
    }

    // -----------------------------------------------------------------------
    // PolicyEngine: rule and veto management
    // -----------------------------------------------------------------------

    #[test]
    fn engine_add_rule() {
        let mut engine = PolicyEngine::new();
        let rule = PolicyRule::allow(
            "allow_execute",
            "Allow executing nodes",
            Permission::new(Action::Execute, Resource::AllNodes),
        );
        assert!(engine.add_rule(rule).is_ok());
        assert_eq!(engine.rule_count(), 1);
    }

    #[test]
    fn engine_register_veto() {
        let mut engine = PolicyEngine::new();
        let veto = SafetyVeto::new(
            "no_delete_nodes",
            "Never delete nodes",
            Action::Delete,
            Resource::AllNodes,
        );
        assert!(engine.register_veto(veto).is_ok());
        assert_eq!(engine.veto_count(), 1);
    }

    // -----------------------------------------------------------------------
    // PolicyEngine: audit logging
    // -----------------------------------------------------------------------

    #[test]
    fn engine_audit_records_allowed_and_denied() {
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

        // Allowed.
        let ctx_allow = PolicyContext::new(
            sid,
            tid,
            Permission::new(Action::Execute, Resource::AllNodes),
        );
        let _ = engine.evaluate(&ctx_allow);

        // Denied (no permission).
        let ctx_deny = PolicyContext::new(
            sid,
            tid,
            Permission::new(Action::Delete, Resource::AllNodes),
        );
        let _ = engine.evaluate(&ctx_deny);

        assert_eq!(engine.audit_count(), 2);
        assert_eq!(engine.audit_denials().len(), 1);
    }

    // -----------------------------------------------------------------------
    // PolicyEngine: default
    // -----------------------------------------------------------------------

    #[test]
    fn engine_default_is_new() {
        let engine = PolicyEngine::default();
        assert_eq!(engine.role_count(), 0);
        assert_eq!(engine.assignment_count(), 0);
        assert_eq!(engine.rule_count(), 0);
        assert_eq!(engine.veto_count(), 0);
        assert_eq!(engine.audit_count(), 0);
    }

    // -----------------------------------------------------------------------
    // E-12 FIX: replace_criticality_gate test
    // -----------------------------------------------------------------------

    #[test]
    fn engine_replace_criticality_gate_with_builder() {
        let mut engine = PolicyEngine::new();

        // Default gate: Low clearance can access Low criticality.
        assert_eq!(engine.required_clearance(NodeCriticality::Low), CriticalityClearance::Low);

        // Replace with a stricter gate: require Critical clearance even for Low criticality.
        let strict_gate = CriticalityGateBuilder::new()
            .threshold(NodeCriticality::Low, CriticalityClearance::Critical)
            .threshold(NodeCriticality::Medium, CriticalityClearance::Critical)
            .threshold(NodeCriticality::High, CriticalityClearance::Critical)
            .threshold(NodeCriticality::Critical, CriticalityClearance::Critical)
            .build();

        engine.replace_criticality_gate(strict_gate);

        // Now Low criticality requires Critical clearance.
        assert_eq!(engine.required_clearance(NodeCriticality::Low), CriticalityClearance::Critical);

        // Verify that a Low-clearance role is now denied for Low-criticality nodes.
        let role = make_viewer_role(); // Low clearance
        let role_id = role.id;
        engine.register_role(role).expect("register");
        let sid = SessionId::new();
        let tid = TenantId::new();
        engine.assign_role(role_id, sid, tid).expect("assign");
        engine.add_rule(PolicyRule::allow("allow_exec", "Allow", Permission::new(Action::Execute, Resource::AllNodes))).expect("add rule");

        let node_id = NodeId::new();
        let ctx = PolicyContext::new(sid, tid, Permission::new(Action::Execute, Resource::Node(node_id)))
            .with_criticality(NodeCriticality::Low, node_id);

        // Should be denied because even Low criticality now requires Critical clearance.
        assert!(engine.evaluate(&ctx).is_err());
    }

    // -----------------------------------------------------------------------
    // PolicyEngine: criticality gate allows high clearance
    // -----------------------------------------------------------------------

    #[test]
    fn engine_evaluate_criticality_gate_allows_high_clearance() {
        let mut engine = PolicyEngine::new();
        let role = make_operator_role(); // High clearance
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
        .with_criticality(NodeCriticality::High, node_id);

        let result = engine.evaluate(&ctx);
        assert!(result.is_ok());
    }
}
