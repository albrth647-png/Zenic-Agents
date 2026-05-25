// ─── Zenic-Agents v3 — Playbook Engine (core motor) ──────────────────────
// CRUD operations, evaluation, and activation for industry playbooks.
// Singleton pattern matching policy-engine/evaluator.ts.
// Lazy imports for cross-module dependencies (roi-calculator, pricing-engine).
//
// Design Patterns:
//   - Singleton: single PlaybookEngine instance for the running service
//   - Strategy: evaluation scoring varies by industry
//   - Repository: DB access through Prisma abstraction

import { db } from "@/lib/db";
import type {
  PlaybookDocument,
  PlaybookMetadata,
  PlaybookCapability,
  PolicyReference,
  PlaybookRoiConfig,
  RoiBaseline,
  RoiProjected,
  RoiCalculation,
  PlaybookPricing,
  PricingTier,
  PricingTierName,
  PlaybookOnboardingConfig,
  PlaybookCertification,
  PlaybookEvaluationResult,
  PlaybookActivationRequest,
  PlaybookActivationResult,
  PlaybookSearchCriteria,
  PlaybookSearchResult,
  PlaybookEngineConfig,
  Industry,
  CertificationStatus,
  PlaybookStatus,
} from "./types";
import {
  DEFAULT_PLAYBOOK_ENGINE_CONFIG,
  PricingTierName as PricingTierNameEnum,
  CertificationStatus as CertificationStatusEnum,
  PlaybookStatus as PlaybookStatusEnum,
} from "./types";
import { computePlaybookContentHash, PlaybookCompilationError } from "./yaml-loader";

// ─── Lazy Import Types ────────────────────────────────────────────────
// Cross-module dependencies loaded lazily to avoid circular imports

type RoiCalculatorModule = {
  calculateRoi: (input: {
    baseline: RoiBaseline;
    projected: RoiProjected;
    monthlyCostUsd: number;
    workingHoursPerMonth?: number;
    hourlyCostUsd?: number;
  }) => RoiCalculation;
};

type PricingEngineModule = {
  calculatePricing: (input: {
    pricing: PlaybookPricing;
    selectedTier: PricingTierName;
    actionsPerMonth: number;
  }) => {
    selected_tier: PricingTierName;
    monthly_cost_usdt: number;
    annual_cost_usdt: number;
    setup_fee_usdt: number;
    per_action_cost: number;
    break_even_actions: number;
    payment_currency: string;
    payment_network: string;
  };
};

// ─── Playbook Engine ──────────────────────────────────────────────────

export class PlaybookEngine {
  private config: PlaybookEngineConfig;
  private cache: Map<string, { document: PlaybookDocument; expiresAt: number }> = new Map();

  constructor(config?: Partial<PlaybookEngineConfig>) {
    this.config = { ...DEFAULT_PLAYBOOK_ENGINE_CONFIG, ...config };
  }

  // ─── CRUD Operations ──────────────────────────────────────────────

  /**
   * Create a new playbook from a compiled PlaybookDocument.
   * Stores the document in the database with content hash.
   */
  async createPlaybook(
    doc: PlaybookDocument,
    sourceYaml?: string,
  ): Promise<PlaybookDbRecord> {
    try {
      const contentHash = computePlaybookContentHash(doc);

      // Check for duplicate content hash
      const existing = await db.playbook.findFirst({
        where: { contentHash },
      });

      if (existing) {
        throw new PlaybookCompilationError(
          `Playbook with identical content already exists (id: ${existing.playbookId})`,
          doc.metadata.id,
        );
      }

      // Check for duplicate playbook ID
      const existingById = await db.playbook.findFirst({
        where: { playbookId: doc.metadata.id },
      });

      if (existingById) {
        throw new PlaybookCompilationError(
          `Playbook with id "${doc.metadata.id}" already exists`,
          doc.metadata.id,
        );
      }

      const playbook = await db.playbook.create({
        data: {
          playbookId: doc.metadata.id,
          name: doc.metadata.name,
          nameEn: doc.metadata.name_en,
          industry: doc.metadata.industry,
          subIndustry: doc.metadata.sub_industry,
          apiVersion: doc.apiVersion,
          version: doc.metadata.version,
          description: doc.metadata.description,
          icon: doc.metadata.icon,
          color: doc.metadata.color,
          labels: JSON.stringify(doc.metadata.labels),
          compliance: JSON.stringify(doc.metadata.compliance),
          capabilities: JSON.stringify(doc.capabilities),
          policies: JSON.stringify(doc.policies),
          roiConfig: JSON.stringify(doc.roi),
          pricing: JSON.stringify(doc.pricing),
          onboarding: JSON.stringify(doc.onboarding),
          certificationStatus: doc.certification.status,
          certificationSignedBy: doc.certification.signedBy,
          certificationSignedAt: doc.certification.signedAt ? new Date(doc.certification.signedAt) : null,
          certificationSignature: doc.certification.signature,
          certificationHash: doc.certification.contentHash,
          sourceYaml: sourceYaml ?? null,
          contentHash,
          isActive: true,
          author: doc.metadata.author,
        },
      });

      return mapDbToRecord(playbook);
    } catch (error) {
      if (error instanceof PlaybookCompilationError) throw error;
      throw new PlaybookCompilationError(
        `Failed to create playbook: ${error instanceof Error ? error.message : String(error)}`,
        doc.metadata.id,
      );
    }
  }

  /**
   * Get a single playbook by its playbook ID.
   */
  async getPlaybook(playbookId: string): Promise<PlaybookDbRecord | null> {
    try {
      const playbook = await db.playbook.findFirst({
        where: { playbookId },
      });

      if (!playbook) return null;

      return mapDbToRecord(playbook);
    } catch (error) {
      throw new PlaybookCompilationError(
        `Failed to get playbook: ${error instanceof Error ? error.message : String(error)}`,
        playbookId,
      );
    }
  }

  /**
   * List playbooks with optional filters.
   */
  async listPlaybooks(filters?: {
    industry?: Industry;
    isActive?: boolean;
    certificationStatus?: CertificationStatus;
  }): Promise<PlaybookDbRecord[]> {
    try {
      const where: Record<string, unknown> = {};

      if (filters?.industry) {
        where.industry = filters.industry;
      }
      if (filters?.isActive !== undefined) {
        where.isActive = filters.isActive;
      }
      if (filters?.certificationStatus) {
        where.certificationStatus = filters.certificationStatus;
      }

      const playbooks = await db.playbook.findMany({
        where,
        orderBy: { updatedAt: "desc" },
      });

      return playbooks.map(mapDbToRecord);
    } catch (error) {
      throw new PlaybookCompilationError(
        `Failed to list playbooks: ${error instanceof Error ? error.message : String(error)}`,
      );
    }
  }

  /**
   * Update an existing playbook with a new PlaybookDocument.
   */
  async updatePlaybook(
    playbookId: string,
    doc: PlaybookDocument,
  ): Promise<PlaybookDbRecord> {
    try {
      const existing = await db.playbook.findFirst({
        where: { playbookId },
      });

      if (!existing) {
        throw new PlaybookCompilationError(
          `Playbook "${playbookId}" not found`,
          playbookId,
        );
      }

      const contentHash = computePlaybookContentHash(doc);

      const playbook = await db.playbook.update({
        where: { id: existing.id },
        data: {
          name: doc.metadata.name,
          nameEn: doc.metadata.name_en,
          industry: doc.metadata.industry,
          subIndustry: doc.metadata.sub_industry,
          version: doc.metadata.version,
          description: doc.metadata.description,
          icon: doc.metadata.icon,
          color: doc.metadata.color,
          labels: JSON.stringify(doc.metadata.labels),
          compliance: JSON.stringify(doc.metadata.compliance),
          capabilities: JSON.stringify(doc.capabilities),
          policies: JSON.stringify(doc.policies),
          roiConfig: JSON.stringify(doc.roi),
          pricing: JSON.stringify(doc.pricing),
          onboarding: JSON.stringify(doc.onboarding),
          certificationStatus: doc.certification.status,
          certificationSignedBy: doc.certification.signedBy,
          certificationSignedAt: doc.certification.signedAt ? new Date(doc.certification.signedAt) : null,
          certificationSignature: doc.certification.signature,
          certificationHash: doc.certification.contentHash,
          contentHash,
          author: doc.metadata.author,
        },
      });

      // Invalidate cache
      this.invalidateCache(playbookId);

      return mapDbToRecord(playbook);
    } catch (error) {
      if (error instanceof PlaybookCompilationError) throw error;
      throw new PlaybookCompilationError(
        `Failed to update playbook: ${error instanceof Error ? error.message : String(error)}`,
        playbookId,
      );
    }
  }

  /**
   * Deactivate a playbook (soft delete — sets isActive to false).
   */
  async deactivatePlaybook(playbookId: string): Promise<PlaybookDbRecord> {
    try {
      const existing = await db.playbook.findFirst({
        where: { playbookId },
      });

      if (!existing) {
        throw new PlaybookCompilationError(
          `Playbook "${playbookId}" not found`,
          playbookId,
        );
      }

      const playbook = await db.playbook.update({
        where: { id: existing.id },
        data: { isActive: false },
      });

      this.invalidateCache(playbookId);

      return mapDbToRecord(playbook);
    } catch (error) {
      if (error instanceof PlaybookCompilationError) throw error;
      throw new PlaybookCompilationError(
        `Failed to deactivate playbook: ${error instanceof Error ? error.message : String(error)}`,
        playbookId,
      );
    }
  }

  /**
   * Search playbooks by structured criteria.
   */
  async searchPlaybooks(criteria: PlaybookSearchCriteria): Promise<PlaybookSearchResult> {
    try {
      const where: Record<string, unknown> = {};

      if (criteria.industry) {
        where.industry = criteria.industry;
      }
      if (criteria.sub_industry) {
        where.subIndustry = { contains: criteria.sub_industry };
      }
      if (criteria.certificationStatus) {
        where.certificationStatus = criteria.certificationStatus;
      }
      if (criteria.status === PlaybookStatusEnum.ACTIVE) {
        where.isActive = true;
      }
      if (criteria.maxPriceUsdt !== undefined) {
        // Price filtering requires post-query JSON parsing
      }

      const playbooks = await db.playbook.findMany({
        where,
        orderBy: { updatedAt: "desc" },
      });

      // Post-filter with criteria that require JSON field inspection
      let results = playbooks.map(mapDbToRecord);

      if (criteria.capabilityId) {
        results = results.filter((p) =>
          p.capabilities.some((c) => c.id === criteria.capabilityId),
        );
      }

      if (criteria.minRoiPercentage !== undefined) {
        results = results.filter((p) => {
          const roi = p.roiConfig.calculated;
          return roi && roi.roi_percentage >= (criteria.minRoiPercentage ?? 0);
        });
      }

      if (criteria.maxPriceUsdt !== undefined) {
        results = results.filter((p) => {
          const starterTier = p.pricing.tiers[0];
          return starterTier && starterTier.price_usdt <= (criteria.maxPriceUsdt ?? Infinity);
        });
      }

      if (criteria.compliance) {
        results = results.filter((p) =>
          p.compliance.includes(criteria.compliance!),
        );
      }

      if (criteria.searchQuery) {
        const query = criteria.searchQuery.toLowerCase();
        results = results.filter((p) =>
          p.name.toLowerCase().includes(query) ||
          p.description.toLowerCase().includes(query) ||
          Object.values(p.labels).some((v) => v.toLowerCase().includes(query)),
        );
      }

      if (criteria.labels) {
        for (const [key, value] of Object.entries(criteria.labels)) {
          results = results.filter((p) => p.labels[key] === value);
        }
      }

      return {
        playbooks: results.map((r) => r.document),
        total: results.length,
        offset: 0,
        limit: 100,
      };
    } catch (error) {
      throw new PlaybookCompilationError(
        `Failed to search playbooks: ${error instanceof Error ? error.message : String(error)}`,
      );
    }
  }

  // ─── Evaluation ───────────────────────────────────────────────────

  /**
   * Evaluate a playbook's compatibility for a tenant.
   * Scores based on industry match, capabilities coverage, and policy availability.
   */
  async evaluatePlaybook(
    playbookId: string,
    tenantId?: string,
  ): Promise<PlaybookEvaluationResult> {
    try {
      const playbook = await db.playbook.findFirst({
        where: { playbookId },
      });

      if (!playbook) {
        return {
          compatible: false,
          score: 0,
          missingPolicies: [],
          suggestedPolicies: [],
          warnings: [`Playbook "${playbookId}" not found`],
        };
      }

      const warnings: string[] = [];
      const missingPolicies: string[] = [];
      const suggestedPolicies: string[] = [];

      // Check if playbook is active
      if (!playbook.isActive) {
        warnings.push(`Playbook "${playbookId}" is not active`);
      }

      // Check certification status
      if (playbook.certificationStatus !== CertificationStatusEnum.CERTIFIED) {
        warnings.push(
          `Playbook "${playbookId}" is not certified (status: ${playbook.certificationStatus}). ` +
          "Certified playbooks are recommended for production use.",
        );
      }

      // Parse policies and check availability
      const policies: PolicyReference[] = JSON.parse(playbook.policies);
      const requiredPolicyIds = policies
        .filter((p) => p.required)
        .map((p) => p.policyId);
      const optionalPolicyIds = policies
        .filter((p) => !p.required)
        .map((p) => p.policyId);

      // Check which policies exist in the system
      const existingPolicies = await db.declPolicy.findMany({
        where: {
          policyId: { in: [...requiredPolicyIds, ...optionalPolicyIds] },
          isActive: true,
        },
        select: { policyId: true },
      });
      const existingPolicyIds = new Set(existingPolicies.map((p) => p.policyId));

      for (const policyId of requiredPolicyIds) {
        if (!existingPolicyIds.has(policyId)) {
          missingPolicies.push(policyId);
        }
      }

      for (const policyId of optionalPolicyIds) {
        if (!existingPolicyIds.has(policyId)) {
          suggestedPolicies.push(policyId);
        }
      }

      // Calculate score (0-100)
      let score = 0;

      // Base score for active playbook (40 points)
      if (playbook.isActive) {
        score += 40;
      }

      // Certification bonus (20 points)
      if (playbook.certificationStatus === CertificationStatusEnum.CERTIFIED) {
        score += 20;
      } else if (playbook.certificationStatus === CertificationStatusEnum.PENDING) {
        score += 10;
      }

      // Policy coverage score (30 points)
      const totalRequired = requiredPolicyIds.length;
      const coveredRequired = requiredPolicyIds.filter((id) => existingPolicyIds.has(id)).length;
      if (totalRequired > 0) {
        score += Math.round((coveredRequired / totalRequired) * 30);
      } else {
        // No required policies — full coverage score
        score += 30;
      }

      // Capabilities score (10 points)
      const capabilities: PlaybookCapability[] = JSON.parse(playbook.capabilities);
      const autoEnabledCount = capabilities.filter((c) => c.autoEnabled).length;
      if (capabilities.length > 0) {
        score += Math.min(10, Math.round((autoEnabledCount / capabilities.length) * 10));
      }

      const compatible = playbook.isActive && missingPolicies.length === 0;

      return {
        compatible,
        score: Math.min(100, score),
        missingPolicies,
        suggestedPolicies,
        warnings,
      };
    } catch (error) {
      return {
        compatible: false,
        score: 0,
        missingPolicies: [],
        suggestedPolicies: [],
        warnings: [`Evaluation error: ${error instanceof Error ? error.message : String(error)}`],
      };
    }
  }

  // ─── Activation ───────────────────────────────────────────────────

  /**
   * Activate a playbook for a tenant.
   * Links policies, configures tools, and calculates ROI projection.
   */
  async activatePlaybook(
    request: PlaybookActivationRequest,
  ): Promise<PlaybookActivationResult> {
    try {
      // 1. Validate playbook exists and is active
      const playbook = await db.playbook.findFirst({
        where: { playbookId: request.playbookId },
      });

      if (!playbook) {
        return {
          success: false,
          activatedPolicies: [],
          configuredTools: [],
          roiProjection: createDefaultRoiCalculation(),
          message: `Playbook "${request.playbookId}" not found`,
        };
      }

      if (!playbook.isActive) {
        return {
          success: false,
          activatedPolicies: [],
          configuredTools: [],
          roiProjection: createDefaultRoiCalculation(),
          message: `Playbook "${request.playbookId}" is not active`,
        };
      }

      // 2. Link policies — create DeclPolicy entries if needed
      const policies: PolicyReference[] = JSON.parse(playbook.policies);
      const activatedPolicies: string[] = [];

      for (const policyRef of policies) {
        // Check if policy already exists
        const existingPolicy = await db.declPolicy.findFirst({
          where: { policyId: policyRef.policyId },
        });

        if (existingPolicy) {
          // Ensure it's active
          if (!existingPolicy.isActive && policyRef.required) {
            await db.declPolicy.update({
              where: { id: existingPolicy.id },
              data: { isActive: true },
            });
          }
          activatedPolicies.push(policyRef.policyId);
        } else if (policyRef.required) {
          // Create a placeholder DeclPolicy for required policies
          await db.declPolicy.create({
            data: {
              policyId: policyRef.policyId,
              name: `Auto-created for playbook ${request.playbookId}`,
              description: policyRef.reason ?? `Auto-created policy reference from playbook "${request.playbookId}"`,
              apiVersion: "policy.zenic.dev/v1",
              version: "1.0.0",
              labels: JSON.stringify({ source: "playbook", playbookId: request.playbookId }),
              compliance: "[]",
              statements: JSON.stringify([{
                id: `${policyRef.policyId}-auto-allow`,
                effect: "allow",
                resource: "*",
                action: "*",
                priority: 0,
              }]),
              tests: "[]",
              isActive: true,
              contentHash: computePlaybookContentHash({
                apiVersion: "playbook.zenic.dev/v1",
                kind: "Playbook",
                metadata: {
                  id: policyRef.policyId,
                  name: `Auto-created for playbook ${request.playbookId}`,
                  name_en: "",
                  industry: playbook.industry as Industry,
                  sub_industry: "",
                  compliance: [],
                  icon: "",
                  color: "",
                  version: "1.0.0",
                  description: policyRef.reason ?? "",
                  author: "system",
                  labels: {},
                },
                capabilities: [],
                policies: [],
                roi: {
                  baseline: {
                    manual_time_per_action_min: 0,
                    error_rate_pct: 0,
                    actions_per_month: 0,
                    cost_per_error_usd: 0,
                    violations_per_year: 0,
                    penalty_per_violation_usd: 0,
                  },
                  projected: {
                    automated_time_per_action_min: 0,
                    reduced_error_rate_pct: 0,
                    compliance_score_target: 0,
                    automation_rate_pct: 0,
                  },
                  assumptions: [],
                },
                pricing: {
                  currency: "USDT",
                  network: "TRC20",
                  tiers: [
                    { name: PricingTierNameEnum.STARTER, price_usdt: 0, setup_fee_usdt: 0, features: [], limits: {}, recommended_for: "", payment_currency: "USDT", payment_network: "TRC20" },
                    { name: PricingTierNameEnum.BUSINESS, price_usdt: 0, setup_fee_usdt: 0, features: [], limits: {}, recommended_for: "", payment_currency: "USDT", payment_network: "TRC20" },
                    { name: PricingTierNameEnum.ENTERPRISE, price_usdt: 0, setup_fee_usdt: 0, features: [], limits: {}, recommended_for: "", payment_currency: "USDT", payment_network: "TRC20" },
                  ],
                },
                onboarding: { steps: [], estimated_minutes: 0 },
                certification: { status: CertificationStatusEnum.UNSIGNED },
              }),
            },
          });
          activatedPolicies.push(policyRef.policyId);
        }
      }

      // 3. Extract configured tools from capabilities
      const capabilities: PlaybookCapability[] = JSON.parse(playbook.capabilities);
      const configuredTools = capabilities
        .filter((c) => c.autoEnabled)
        .map((c) => c.id);

      // 4. Calculate ROI projection
      const roiConfig: PlaybookRoiConfig = JSON.parse(playbook.roiConfig);
      const pricingConfig: PlaybookPricing = JSON.parse(playbook.pricing);
      const selectedTier = pricingConfig.tiers.find((t) => t.name === request.selectedTier);
      const monthlyCostUsdt = selectedTier?.price_usdt ?? 0;

      let roiProjection: RoiCalculation;

      // Try lazy import of roi-calculator module
      try {
        const roiModule = await loadRoiCalculator();
        roiProjection = roiModule.calculateRoi({
          baseline: roiConfig.baseline,
          projected: roiConfig.projected,
          monthlyCostUsd: monthlyCostUsdt,
          workingHoursPerMonth: 160,
          hourlyCostUsd: 50,
        });
      } catch {
        // Fallback to inline calculation
        roiProjection = calculateRoiInline(roiConfig.baseline, roiConfig.projected, monthlyCostUsd);
      }

      // 5. Record activation in DB
      await db.playbookActivation.create({
        data: {
          playbookDbId: playbook.id,
          tenantId: request.tenantId,
          selectedTier: request.selectedTier,
          customConfig: JSON.stringify(request.customConfig ?? {}),
          activatedPolicies: JSON.stringify(activatedPolicies),
          configuredTools: JSON.stringify(configuredTools),
          roiProjection: JSON.stringify(roiProjection),
          status: "active",
        },
      });

      return {
        success: true,
        activatedPolicies,
        configuredTools,
        roiProjection,
        message: `Playbook "${request.playbookId}" activated successfully with ${activatedPolicies.length} policies and ${configuredTools.length} tools on ${request.selectedTier} tier`,
      };
    } catch (error) {
      return {
        success: false,
        activatedPolicies: [],
        configuredTools: [],
        roiProjection: createDefaultRoiCalculation(),
        message: `Activation failed: ${error instanceof Error ? error.message : String(error)}`,
      };
    }
  }

  /**
   * Deactivate a playbook activation.
   */
  async deactivateActivation(activationId: string): Promise<void> {
    try {
      const activation = await db.playbookActivation.findFirst({
        where: { id: activationId },
      });

      if (!activation) {
        throw new PlaybookCompilationError(
          `Activation "${activationId}" not found`,
        );
      }

      await db.playbookActivation.update({
        where: { id: activationId },
        data: {
          status: "deactivated",
          deactivatedAt: new Date(),
        },
      });
    } catch (error) {
      if (error instanceof PlaybookCompilationError) throw error;
      throw new PlaybookCompilationError(
        `Failed to deactivate activation: ${error instanceof Error ? error.message : String(error)}`,
      );
    }
  }

  // ─── Cache Management ─────────────────────────────────────────────

  /**
   * Clear the document cache.
   */
  clearCache(): void {
    this.cache.clear();
  }

  /**
   * Invalidate cache for a specific playbook.
   */
  private invalidateCache(playbookId: string): void {
    this.cache.delete(playbookId);
  }
}
