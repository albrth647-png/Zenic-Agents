// ─── Zenic-Agents v3 — Saga Compensation Handlers ───────────────────────
// USDT TRC20 ONLY. Compensation handlers that revert the effects of
// saga steps when the saga needs to roll back. Each compensation handler
// undoes the side effects of its corresponding step handler.

import { db } from "@/lib/db";
import type { CompensationHandler } from "./types";

// ═══════════════════════════════════════════════════════════════════════════
// Compensation Handlers
// ═══════════════════════════════════════════════════════════════════════════

export const compensationHandlers: Record<string, CompensationHandler> = {
  // ─── Validation steps: no-op (pure checks, no state to revert) ───
  validate_email_uniqueness: async () => {},
  validate_trc20_address: async () => {},
  validate_subscription_status: async () => {},
  validate_trc20_tx_hash: async () => {},
  check_tx_hash_uniqueness: async () => {},
  validate_subscription_cancellable: async () => {},
  validate_subscription_renewable: async () => {},
  validate_upgrade_path: async () => {},
  validate_downgrade_path: async () => {},
  validate_subscription_reactivatable: async () => {},
  identify_features_to_revoke: async () => {},

  // ─── Pricing steps: no-op (pure computation) ───
  calculate_subscription_pricing: async () => {},
  calculate_proration_amount: async () => {},
  calculate_proration_credit: async () => {},

  // ─── DB mutation steps: REVERT the changes ───
  async db_create_subscription(_input, stepOutput) {
    const dbId = stepOutput.dbId as string;
    if (dbId) {
      await db.subscription.delete({ where: { id: dbId } }).catch(() => {});
    }
  },

  async db_create_payment_request(_input, stepOutput) {
    const dbId = stepOutput.dbId as string;
    if (dbId) {
      await db.subscriptionPayment.delete({ where: { id: dbId } }).catch(() => {});
    }
  },

  async db_update_subscription(input, _stepOutput) {
    const { tenantId } = input as { tenantId: string; previousTier?: string; previousStatus?: string };
    const previousTier = input.previousTier as string | undefined;
    const previousStatus = input.previousStatus as string | undefined;
    if (previousTier || previousStatus) {
      await db.subscription.update({
        where: { tenantId },
        data: {
          ...(previousTier ? { tier: previousTier } : {}),
          ...(previousStatus ? { status: previousStatus } : {}),
          updatedAt: new Date(),
        },
      }).catch(() => {});
    }
  },

  async db_cancel_subscription(input, _stepOutput) {
    const { tenantId } = input as { tenantId: string };
    await db.subscription.update({
      where: { tenantId },
      data: { status: "active", cancelledAt: null, cancellationReason: null, updatedAt: new Date() },
    }).catch(() => {});
  },

  async db_create_payment(_input, stepOutput) {
    const dbId = stepOutput.dbId as string;
    if (dbId) {
      await db.subscriptionPayment.delete({ where: { id: dbId } }).catch(() => {});
    }
  },

  async db_update_subscription_status(input, _stepOutput) {
    const { tenantId, previousStatus } = input as { tenantId: string; previousStatus?: string };
    if (previousStatus) {
      await db.subscription.update({
        where: { tenantId },
        data: { status: previousStatus, updatedAt: new Date() },
      }).catch(() => {});
    }
  },

  // Feature gate steps: informational, no compensation needed
  initialize_feature_gates: async () => {},
  revoke_feature_gates: async () => {},
  update_feature_gates_for_tier: async () => {},
  revert_feature_gates_to_trial: async () => {},
  revert_feature_gates_to_previous_tier: async () => {},
  revoke_all_feature_gates: async () => {},
  restore_feature_gates: async () => {},
  revoke_features_for_downgrade: async () => {},
  restore_revoked_features: async () => {},

  // Audit steps: no compensation needed (audit log is append-only)
  create_audit_entry: async () => {},
  mark_audit_as_rolled_back: async () => {},

  // Payment steps
  async finalize_payment_confirmation(_input, stepOutput) {
    const { paymentDbId } = _input as { paymentDbId?: string };
    if (paymentDbId) {
      await db.subscriptionPayment.update({
        where: { id: paymentDbId },
        data: { status: "pending", confirmedAt: null, adminConfirmedAt: null },
      }).catch(() => {});
    }
  },

  initiate_refund_process: async () => {},

  // ─── DB revert steps (used as compensating actions) ───
  async db_delete_subscription(input, _stepOutput) {
    // This is also used as a step handler; as compensation it's typically a no-op
    // because the subscription was already deleted by the step
    void input;
  },

  async db_delete_payment_request(input, _stepOutput) {
    void input;
  },

  async db_revert_subscription_to_trial(input, _stepOutput) {
    // Reverting the revert means going back to the original state
    // This is a best-effort operation
    const { tenantId } = input as { tenantId: string };
    await db.subscription.update({
      where: { tenantId },
      data: { tier: "trial", status: "trial", updatedAt: new Date() },
    }).catch(() => {});
  },

  async db_revert_subscription_status(input, _stepOutput) {
    const { tenantId, previousStatus } = input as { tenantId: string; previousStatus?: string };
    if (previousStatus) {
      await db.subscription.update({
        where: { tenantId },
        data: { status: previousStatus, updatedAt: new Date() },
      }).catch(() => {});
    }
  },

  async db_reactivate_subscription(input, _stepOutput) {
    const { tenantId } = input as { tenantId: string };
    const now = new Date();
    await db.subscription.update({
      where: { tenantId },
      data: {
        status: "active",
        cancelledAt: null,
        cancellationReason: null,
        currentPeriodEnd: new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000),
        updatedAt: now,
      },
    }).catch(() => {});
  },

  async db_revert_subscription_period(input, _stepOutput) {
    const { tenantId, previousPeriodEnd } = input as { tenantId: string; previousPeriodEnd: string };
    await db.subscription.update({
      where: { tenantId },
      data: { currentPeriodEnd: new Date(previousPeriodEnd), updatedAt: new Date() },
    }).catch(() => {});
  },

  async db_restore_usage_records(_input, _stepOutput) {
    // Best-effort — usage records are not critical to revert
  },

  async db_revert_subscription_tier(input, _stepOutput) {
    const { tenantId, previousTier } = input as { tenantId: string; previousTier: string };
    await db.subscription.update({
      where: { tenantId },
      data: { tier: previousTier, updatedAt: new Date() },
    }).catch(() => {});
  },

  async db_delete_payment(input, _stepOutput) {
    const { dbId } = input as { dbId?: string };
    if (dbId) {
      await db.subscriptionPayment.delete({ where: { id: dbId } }).catch(() => {});
    }
  },

  async revert_payment_to_awaiting(input, _stepOutput) {
    const { paymentDbId } = input as { paymentDbId: string };
    await db.subscriptionPayment.update({
      where: { id: paymentDbId },
      data: { status: "pending", confirmedAt: null, adminConfirmedAt: null },
    }).catch(() => {});
  },

  async mark_payment_as_expired(input, _stepOutput) {
    const { paymentDbId } = input as { paymentDbId: string };
    await db.subscriptionPayment.update({
      where: { id: paymentDbId },
      data: { status: "expired" },
    }).catch(() => {});
  },

  async cancel_refund_process(_input, _stepOutput) {
    // No-op: refund cancellation has no persistent side effects
  },
};
