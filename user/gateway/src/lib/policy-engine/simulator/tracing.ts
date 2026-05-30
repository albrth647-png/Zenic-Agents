// ─── Zenic-Agents v3 — Simulation Tracing ────────────────────────────
// Phase 4: Declarative Versioned Policy Engine — Simulation Tracing
//
// Provides simulation tracing utilities for recording and analyzing
// the step-by-step evaluation of policy simulation requests.
// Complements the runSimulation function in types.ts.
//
// Design Patterns:
//   - Memento: Captures before/after evaluation snapshots
//   - Chain of Responsibility: Traces through policy evaluation chain

import type {
  PolicyDocument,
  PolicyEvaluationRequest,
  PolicyEvaluationResult,
  PolicyEffectV2,
  PolicyStatement,
  SimulationTrace,
  SimulationChange,
} from "./types";

// ─── Trace Entry ──────────────────────────────────────────────────────

/**
 * A single step in the simulation trace.
 */
export interface TraceStep {
  /** Step number in the evaluation chain */
  step: number;
  /** The policy document being evaluated */
  policyId: string;
  /** The statement that was matched (if any) */
  matchedStatementId?: string;
  /** The effect of the matched statement */
  effect?: PolicyEffectV2;
  /** The priority of the matched statement */
  priority?: number;
  /** Whether this step changed the final verdict */
  changedVerdict: boolean;
  /** Duration of this step in ms */
  duration: number;
}

// ─── Trace Builder ────────────────────────────────────────────────────

/**
 * Builder for constructing simulation traces.
 */
export class TraceBuilder {
  private steps: TraceStep[] = [];
  private currentVerdict: PolicyEffectV2 = "deny";
  private startTime: number;

  constructor() {
    this.startTime = Date.now();
  }

  /**
   * Record a policy evaluation step.
   */
  recordStep(
    policyId: string,
    result: PolicyEvaluationResult,
  ): void {
    const step: TraceStep = {
      step: this.steps.length + 1,
      policyId,
      matchedStatementId: result.matchedStatements[0]?.statementId,
      effect: result.effect !== "deny" || !result.denyByDefault ? result.effect : undefined,
      priority: result.matchedStatements[0]?.priority,
      changedVerdict: false,
      duration: result.duration,
    };

    // Check if this step changes the verdict
    if (result.effect !== "deny" || !result.denyByDefault) {
      if (result.effect !== this.currentVerdict) {
        step.changedVerdict = true;
        this.currentVerdict = result.effect;
      }
    }

    this.steps.push(step);
  }

  /**
   * Build the final trace steps.
   */
  build(): TraceStep[] {
    return [...this.steps];
  }

  /**
   * Get the current verdict after all recorded steps.
   */
  getCurrentVerdict(): PolicyEffectV2 {
    return this.currentVerdict;
  }

  /**
   * Get total duration of all steps.
   */
  getTotalDuration(): number {
    return Date.now() - this.startTime;
  }
}

// ─── Trace Analysis ───────────────────────────────────────────────────

/**
 * Analysis of a simulation trace.
 */
export interface TraceAnalysis {
  /** Total number of steps */
  totalSteps: number;
  /** Number of steps that changed the verdict */
  verdictChangingSteps: number;
  /** The final verdict */
  finalVerdict: PolicyEffectV2;
  /** Total evaluation duration */
  totalDuration: number;
  /** Policies that contributed to the final verdict */
  contributingPolicies: string[];
  /** Statements that were decisive */
  decisiveStatements: string[];
}

/**
 * Analyze a trace and extract key insights.
 */
export function analyzeTrace(trace: SimulationTrace): TraceAnalysis {
  const contributingPolicies: string[] = [];
  const decisiveStatements: string[] = [];
  let verdictChangingSteps = 0;

  // From before result
  if (trace.beforeResult && !trace.beforeResult.denyByDefault) {
    contributingPolicies.push(trace.beforeResult.policyId);
    if (trace.beforeResult.matchedStatementId) {
      decisiveStatements.push(trace.beforeResult.matchedStatementId);
    }
  }

  // From after result
  if (trace.afterResult && !trace.afterResult.denyByDefault) {
    if (!contributingPolicies.includes(trace.afterResult.policyId)) {
      contributingPolicies.push(trace.afterResult.policyId);
    }
    if (trace.afterResult.matchedStatementId) {
      if (!decisiveStatements.includes(trace.afterResult.matchedStatementId)) {
        decisiveStatements.push(trace.afterResult.matchedStatementId);
      }
    }
  }

  const finalVerdict = trace.afterResult?.effect ?? "deny";
  verdictChangingSteps = trace.beforeResult?.effect !== trace.afterResult?.effect ? 1 : 0;

  return {
    totalSteps: contributingPolicies.length,
    verdictChangingSteps,
    finalVerdict,
    totalDuration: (trace.beforeResult?.duration ?? 0) + (trace.afterResult?.duration ?? 0),
    contributingPolicies,
    decisiveStatements,
  };
}

// ─── Trace Formatting ─────────────────────────────────────────────────

/**
 * Format a simulation trace as a readable string.
 */
export function formatTrace(trace: SimulationTrace): string {
  const lines: string[] = [];

  lines.push(`Request: ${trace.request.resource}:${trace.request.action}`);
  lines.push("");

  lines.push("Before:");
  if (trace.beforeResult) {
    lines.push(`  Effect: ${trace.beforeResult.effect}`);
    lines.push(`  Policy: ${trace.beforeResult.policyId}`);
    if (trace.beforeResult.matchedStatementId) {
      lines.push(`  Statement: ${trace.beforeResult.matchedStatementId}`);
    }
    lines.push(`  Duration: ${trace.beforeResult.duration}ms`);
  } else {
    lines.push("  No result");
  }

  lines.push("");
  lines.push("After:");
  if (trace.afterResult) {
    lines.push(`  Effect: ${trace.afterResult.effect}`);
    lines.push(`  Policy: ${trace.afterResult.policyId}`);
    if (trace.afterResult.matchedStatementId) {
      lines.push(`  Statement: ${trace.afterResult.matchedStatementId}`);
    }
    lines.push(`  Duration: ${trace.afterResult.duration}ms`);
  } else {
    lines.push("  No result");
  }

  if (trace.causingChange) {
    lines.push("");
    lines.push(`Causing Change: ${trace.causingChange}`);
  }

  return lines.join("\n");
}

/**
 * Format multiple traces as a summary table.
 */
export function formatTracesSummary(traces: SimulationTrace[]): string {
  if (traces.length === 0) {
    return "No traces recorded.";
  }

  const lines: string[] = [];
  lines.push("Request                    | Before    | After     | Changed");
  lines.push("-".repeat(70));

  for (const trace of traces) {
    const request = `${trace.request.resource}:${trace.request.action}`.padEnd(25);
    const before = (trace.beforeResult?.effect ?? "N/A").padEnd(9);
    const after = (trace.afterResult?.effect ?? "N/A").padEnd(9);
    const changed = trace.beforeResult?.effect !== trace.afterResult?.effect ? "YES" : "no";
    lines.push(`${request} | ${before} | ${after} | ${changed}`);
  }

  return lines.join("\n");
}

// ─── Trace Comparison ─────────────────────────────────────────────────

/**
 * Compare two traces and highlight differences.
 */
export function compareTraces(
  beforeTraces: SimulationTrace[],
  afterTraces: SimulationTrace[],
): Array<{
  request: string;
  beforeEffect: PolicyEffectV2;
  afterEffect: PolicyEffectV2;
  changed: boolean;
}> {
  const results: Array<{
    request: string;
    beforeEffect: PolicyEffectV2;
    afterEffect: PolicyEffectV2;
    changed: boolean;
  }> = [];

  const afterMap = new Map(
    afterTraces.map((t) => [`${t.request.resource}:${t.request.action}`, t]),
  );

  for (const beforeTrace of beforeTraces) {
    const key = `${beforeTrace.request.resource}:${beforeTrace.request.action}`;
    const afterTrace = afterMap.get(key);

    const beforeEffect = beforeTrace.beforeResult?.effect ?? "deny";
    const afterEffect = afterTrace?.afterResult?.effect ?? "deny";

    results.push({
      request: key,
      beforeEffect,
      afterEffect,
      changed: beforeEffect !== afterEffect,
    });
  }

  return results;
}
