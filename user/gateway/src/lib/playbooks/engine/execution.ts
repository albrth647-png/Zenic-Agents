// ─── Zenic-Agents v3 — Playbook Engine Execution Pipeline ───────────────
// Execution helpers for playbook evaluation, activation, and deactivation.
// Provides a functional API alongside the class-based PlaybookEngine.

import type {
  PlaybookEvaluationResult,
  PlaybookActivationRequest,
  PlaybookActivationResult,
  PlaybookSearchCriteria,
} from "../types";
import { getPlaybookEngine } from "./types";
import type { PlaybookDbRecord } from "./types";

// ─── Evaluation Pipeline ─────────────────────────────────────────────

/**
 * Evaluate a playbook's compatibility for a tenant.
 * Uses the singleton PlaybookEngine instance.
 */
export async function evaluatePlaybook(
  playbookId: string,
  tenantId?: string,
): Promise<PlaybookEvaluationResult> {
  const engine = getPlaybookEngine();
  return engine.evaluatePlaybook(playbookId, tenantId);
}

/**
 * Batch-evaluate multiple playbooks for a tenant.
 * Returns evaluation results keyed by playbook ID.
 */
export async function batchEvaluatePlaybooks(
  playbookIds: string[],
  tenantId?: string,
): Promise<Map<string, PlaybookEvaluationResult>> {
  const results = new Map<string, PlaybookEvaluationResult>();

  await Promise.all(
    playbookIds.map(async (id) => {
      const result = await evaluatePlaybook(id, tenantId);
      results.set(id, result);
    }),
  );

  return results;
}

/**
 * Find the best compatible playbook from a list of candidates.
 * Returns the playbook with the highest compatibility score, or null if none are compatible.
 */
export async function findBestCompatiblePlaybook(
  playbookIds: string[],
  tenantId?: string,
): Promise<{ playbookId: string; result: PlaybookEvaluationResult } | null> {
  const evaluations = await batchEvaluatePlaybooks(playbookIds, tenantId);

  let best: { playbookId: string; result: PlaybookEvaluationResult } | null = null;

  for (const [playbookId, result] of evaluations) {
    if (!result.compatible) continue;
    if (!best || result.score > best.result.score) {
      best = { playbookId, result };
    }
  }

  return best;
}

// ─── Activation Pipeline ─────────────────────────────────────────────

/**
 * Activate a playbook for a tenant.
 * Uses the singleton PlaybookEngine instance.
 */
export async function activatePlaybook(
  request: PlaybookActivationRequest,
): Promise<PlaybookActivationResult> {
  const engine = getPlaybookEngine();
  return engine.activatePlaybook(request);
}

/**
 * Deactivate a playbook activation by its ID.
 * Uses the singleton PlaybookEngine instance.
 */
export async function deactivateActivation(activationId: string): Promise<void> {
  const engine = getPlaybookEngine();
  return engine.deactivateActivation(activationId);
}

// ─── Activation Validation ───────────────────────────────────────────

/**
 * Pre-validate a playbook activation request before executing it.
 * Checks playbook existence, active status, and tenant eligibility.
 * Returns validation result without performing any mutations.
 */
export async function validateActivationRequest(
  request: PlaybookActivationRequest,
): Promise<{ valid: boolean; errors: string[]; warnings: string[] }> {
  const errors: string[] = [];
  const warnings: string[] = [];

  // Check playbook exists and is active
  const engine = getPlaybookEngine();
  const playbook = await engine.getPlaybook(request.playbookId);

  if (!playbook) {
    errors.push(`Playbook "${request.playbookId}" not found`);
  } else {
    if (!playbook.isActive) {
      errors.push(`Playbook "${request.playbookId}" is not active`);
    }

    // Check certification
    if (playbook.certificationStatus !== "certified") {
      warnings.push(
        `Playbook "${request.playbookId}" is not certified (status: ${playbook.certificationStatus})`,
      );
    }

    // Evaluate compatibility
    const evaluation = await engine.evaluatePlaybook(request.playbookId, request.tenantId);

    if (!evaluation.compatible) {
      warnings.push(
        `Playbook "${request.playbookId}" is not fully compatible (score: ${evaluation.score})`,
      );
    }

    if (evaluation.missingPolicies.length > 0) {
      warnings.push(
        `Missing required policies: ${evaluation.missingPolicies.join(", ")}`,
      );
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  };
}

// ─── Execution Context ───────────────────────────────────────────────

/**
 * Execution context for a playbook activation.
 * Tracks the state and progress of an activation pipeline.
 */
export interface PlaybookExecutionContext {
  /** The activation request being processed */
  request: PlaybookActivationRequest;
  /** Current phase of the execution */
  phase: "validating" | "linking_policies" | "configuring_tools" | "calculating_roi" | "recording" | "completed" | "failed";
  /** Timestamp when execution started */
  startedAt: Date;
  /** Timestamp when execution completed (if done) */
  completedAt: Date | null;
  /** Any error message if execution failed */
  error: string | null;
  /** Activated policy IDs collected during execution */
  activatedPolicies: string[];
  /** Configured tool IDs collected during execution */
  configuredTools: string[];
}

/**
 * Create a new execution context for a playbook activation request.
 */
export function createExecutionContext(
  request: PlaybookActivationRequest,
): PlaybookExecutionContext {
  return {
    request,
    phase: "validating",
    startedAt: new Date(),
    completedAt: null,
    error: null,
    activatedPolicies: [],
    configuredTools: [],
  };
}
