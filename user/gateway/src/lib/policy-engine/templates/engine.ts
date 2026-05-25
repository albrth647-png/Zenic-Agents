// ─── Zenic-Agents v3 — Template Engine ────────────────────────────────
// Phase 4: Declarative Versioned Policy Engine — Template Engine
//
// Provides the core template processing engine: variable substitution,
// document building, and template management.
// Complements the instantiateTemplate function in types.ts.
//
// Design Patterns:
//   - Builder: PolicyDocumentBuilder constructs PolicyDocument from template + params
//   - Interpreter: VariableSubstitutionInterpreter resolves {{variable}} placeholders

import { createHash } from "crypto";
import { db } from "@/lib/db";
import { computeContentHash } from "../yaml-loader";
import type {
  PolicyDocument,
  PolicyStatement,
  PolicyCondition,
  PolicyEffectV2,
  ConditionOperator,
} from "../types";
import {
  POLICY_API_VERSION,
  type TemplateMetadata,
  type TemplateParameter,
  type PolicyDocumentTemplate,
  type StatementTemplate,
  type ConditionTemplate,
  type TestCaseTemplate,
  type PolicyTemplate,
} from "./types";

// ─── Variable Substitution ────────────────────────────────────────────

/** Placeholder pattern: {{variableName}} */
const PLACEHOLDER_REGEX = /\{\{(\w+)\}\}/g;

/**
 * Substitute all {{variableName}} placeholders in a string with resolved values.
 */
export function substituteVariables(
  template: string,
  resolvedParams: Record<string, unknown>,
): string {
  return template.replace(PLACEHOLDER_REGEX, (match, varName: string) => {
    if (varName in resolvedParams) {
      return valueToString(resolvedParams[varName]);
    }
    return match;
  });
}

/**
 * Convert a parameter value to its string representation.
 */
export function valueToString(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number") return String(value);
  if (typeof value === "boolean") return value ? "true" : "false";
  if (Array.isArray(value)) return JSON.stringify(value);
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

/**
 * Check if a string contains any unresolved {{variable}} placeholders.
 */
export function hasUnresolvedVariables(str: string): string[] {
  const unresolved: string[] = [];
  let match: RegExpExecArray | null;
  const regex = new RegExp(PLACEHOLDER_REGEX.source, "g");
  while ((match = regex.exec(str)) !== null) {
    unresolved.push(match[1]!);
  }
  return unresolved;
}

/**
 * Recursively substitute variables in all string values within an object.
 */
export function substituteDeep<T>(obj: T, resolvedParams: Record<string, unknown>): T {
  if (typeof obj === "string") {
    return substituteVariables(obj, resolvedParams) as T;
  }
  if (Array.isArray(obj)) {
    return obj.map((item) => substituteDeep(item, resolvedParams)) as T;
  }
  if (obj !== null && typeof obj === "object") {
    const result: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(obj)) {
      result[key] = substituteDeep(value, resolvedParams);
    }
    return result as T;
  }
  return obj;
}

// ─── Policy Document Builder ──────────────────────────────────────────

/**
 * Builder for constructing a PolicyDocument from a template and resolved parameters.
 */
export class PolicyDocumentBuilder {
  private documentTemplate: PolicyDocumentTemplate;
  private resolvedParams: Record<string, unknown>;
  private templateMetadata: TemplateMetadata;

  constructor(
    documentTemplate: PolicyDocumentTemplate,
    resolvedParams: Record<string, unknown>,
    templateMetadata: TemplateMetadata,
  ) {
    this.documentTemplate = documentTemplate;
    this.resolvedParams = resolvedParams;
    this.templateMetadata = templateMetadata;
  }

  /**
   * Build a complete PolicyDocument from the template.
   */
  build(): PolicyDocument {
    const policyName = substituteVariables(this.documentTemplate.name, this.resolvedParams);
    const policyDescription = substituteVariables(this.documentTemplate.description, this.resolvedParams);

    const statements = this.documentTemplate.statements.map((stmt) =>
      this.buildStatement(stmt),
    );

    const tests = this.documentTemplate.tests
      ? this.documentTemplate.tests.map((tc) => this.buildTestCase(tc))
      : undefined;

    const compliance = this.documentTemplate.compliance
      ? substituteDeep(this.documentTemplate.compliance, this.resolvedParams)
      : undefined;

    const labels = this.documentTemplate.labels
      ? substituteDeep(this.documentTemplate.labels, this.resolvedParams)
      : undefined;

    return {
      apiVersion: POLICY_API_VERSION,
      kind: "PolicyDocument",
      metadata: {
        id: this.templateMetadata.id,
        name: policyName,
        version: this.templateMetadata.version,
        description: policyDescription,
        compliance,
        labels,
        author: this.templateMetadata.author,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      },
      statements,
      tests,
    };
  }

  private buildStatement(template: StatementTemplate): PolicyStatement {
    const id = substituteVariables(template.id, this.resolvedParams);
    const effect = substituteVariables(template.effect, this.resolvedParams) as PolicyEffectV2;
    const resource = substituteVariables(template.resource, this.resolvedParams);
    const action = substituteVariables(template.action, this.resolvedParams);
    const description = template.description
      ? substituteVariables(template.description, this.resolvedParams)
      : undefined;
    const requiredRole = template.requiredRole
      ? substituteVariables(template.requiredRole, this.resolvedParams)
      : undefined;
    const tags = template.tags
      ? template.tags.map((t) => substituteVariables(t, this.resolvedParams))
      : undefined;

    let priority: number;
    if (typeof template.priority === "number") {
      priority = template.priority;
    } else {
      const resolved = substituteVariables(template.priority, this.resolvedParams);
      const parsed = parseInt(resolved, 10);
      priority = isNaN(parsed) ? 0 : parsed;
    }

    const conditions = template.conditions
      ? template.conditions.map((ct) => this.buildCondition(ct))
      : undefined;

    return {
      id,
      effect,
      resource,
      action,
      conditions,
      priority,
      description,
      requiredRole,
      tags,
    };
  }

  private buildCondition(template: ConditionTemplate): PolicyCondition {
    const field = substituteVariables(template.field, this.resolvedParams);
    const valueStr = substituteVariables(template.value, this.resolvedParams);
    const description = template.description
      ? substituteVariables(template.description, this.resolvedParams)
      : undefined;

    let value: unknown = valueStr;
    if (/^-?\d+(\.\d+)?$/.test(valueStr)) {
      value = parseFloat(valueStr);
    } else if (valueStr === "true") {
      value = true;
    } else if (valueStr === "false") {
      value = false;
    } else if (valueStr.startsWith("[") || valueStr.startsWith("{")) {
      try {
        value = JSON.parse(valueStr);
      } catch {
        // Keep as string
      }
    }

    return {
      field,
      operator: template.operator as ConditionOperator,
      value,
      description,
    };
  }

  private buildTestCase(template: TestCaseTemplate): {
    name: string;
    resource: string;
    action: string;
    context: Record<string, unknown>;
    expected: string;
    description?: string;
  } {
    const name = substituteVariables(template.name, this.resolvedParams);
    const resource = substituteVariables(template.resource, this.resolvedParams);
    const action = substituteVariables(template.action, this.resolvedParams);
    const context = substituteDeep(template.context, this.resolvedParams) as Record<string, unknown>;
    const expected = substituteVariables(template.expected, this.resolvedParams);
    const description = template.description
      ? substituteVariables(template.description, this.resolvedParams)
      : undefined;

    return {
      name,
      resource,
      action,
      context,
      expected,
      description,
    };
  }
}

// ─── Template Content Hash ────────────────────────────────────────────

/**
 * Compute a SHA-256 content hash for a PolicyTemplate.
 */
export function computeTemplateContentHash(template: PolicyTemplate): string {
  const canonical = JSON.stringify(template, Object.keys(template).sort(), 2);
  return createHash("sha256").update(canonical).digest("hex");
}

// ─── DB Record Mapping ────────────────────────────────────────────────

/**
 * Flattened record from DB with parsed JSON fields.
 */
export interface TemplateDbRecord {
  id: string;
  templateId: string;
  name: string;
  version: string;
  description: string;
  category: string;
  industry: string | null;
  tags: string[];
  parameters: TemplateParameter[];
  documentTemplate: PolicyDocumentTemplate;
  defaults: Record<string, unknown>;
  constraints: TemplateConstraint[];
  generatedCount: number;
  isActive: boolean;
  author: string | null;
  sourceYaml: string | null;
  contentHash: string;
  createdAt: Date;
  updatedAt: Date;
}

/** Minimal import for TemplateConstraint */
type TemplateConstraint = import("./types").TemplateConstraint;

/**
 * Map a Prisma PolicyTemplate record to a typed TemplateDbRecord.
 */
export function mapDbToRecord(record: {
  id: string;
  templateId: string;
  name: string;
  version: string;
  description: string;
  category: string;
  industry: string | null;
  tags: string;
  parameters: string;
  documentTemplate: string;
  defaults: string;
  constraints: string;
  generatedCount: number;
  isActive: boolean;
  author: string | null;
  sourceYaml: string | null;
  contentHash: string;
  createdAt: Date;
  updatedAt: Date;
}): TemplateDbRecord {
  return {
    id: record.id,
    templateId: record.templateId,
    name: record.name,
    version: record.version,
    description: record.description,
    category: record.category,
    industry: record.industry,
    tags: JSON.parse(record.tags),
    parameters: JSON.parse(record.parameters),
    documentTemplate: JSON.parse(record.documentTemplate),
    defaults: JSON.parse(record.defaults),
    constraints: JSON.parse(record.constraints),
    generatedCount: record.generatedCount,
    isActive: record.isActive,
    author: record.author,
    sourceYaml: record.sourceYaml,
    contentHash: record.contentHash,
    createdAt: record.createdAt,
    updatedAt: record.updatedAt,
  };
}

/**
 * Convert a TemplateDbRecord back to a PolicyTemplate.
 */
export function dbRecordToTemplate(record: TemplateDbRecord): PolicyTemplate {
  return {
    apiVersion: "template.zenic.dev/v1",
    kind: "PolicyTemplate",
    metadata: {
      id: record.templateId,
      name: record.name,
      version: record.version,
      description: record.description,
      category: record.category,
      industry: record.industry ?? undefined,
      tags: record.tags,
      author: record.author ?? undefined,
    },
    parameters: record.parameters,
    documentTemplate: record.documentTemplate,
    defaults: record.defaults,
    constraints: record.constraints,
  };
}
