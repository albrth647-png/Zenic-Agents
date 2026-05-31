// A2A Protocol — Agent Card endpoint
// Returns the Zenic agent card and allows registration of external agents

import { NextRequest, NextResponse } from "next/server";

/** Local Zenic agent card — describes this Zenic instance's capabilities */
const ZENIC_AGENT_CARD = {
  id: "zenic-agents-main",
  name: "Zenic Agents Hub",
  description: "Zenic-Agents governance hub with Niche DNA, Policy Engine, and HITL",
  capabilities: [
    "policy-evaluation",
    "hitl-approval",
    "niche-dna-generation",
    "merkle-audit",
    "agent-orchestration",
    "safety-validation",
  ],
  endpoint: "",
  nicheDna: "multi-domain",
  requiresHitl: false,
  policyConstraints: [
    "all-delegations-require-policy-check",
    "critical-tasks-require-hitl",
    "merkle-audit-enabled",
  ],
};

// GET — Return this Zenic instance's agent card
export async function GET() {
  return NextResponse.json({
    success: true,
    agentCard: ZENIC_AGENT_CARD,
  });
}

// POST — Register an external agent's card
export async function POST(request: NextRequest) {
  try {
    const agentCard = await request.json();

    if (!agentCard.id || !agentCard.name) {
      return NextResponse.json(
        { success: false, error: "Agent card must have id and name" },
        { status: 400 }
      );
    }

    // In production, this would persist to the A2A registry
    // For MVP, we acknowledge and return success
    return NextResponse.json({
      success: true,
      registeredAgent: {
        id: agentCard.id,
        name: agentCard.name,
        registeredAt: new Date().toISOString(),
      },
    });
  } catch (error) {
    return NextResponse.json(
      { success: false, error: "Failed to register agent card" },
      { status: 500 }
    );
  }
}
