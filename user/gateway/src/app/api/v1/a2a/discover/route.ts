// A2A Protocol — Agent discovery endpoint
// Find agents by capability or niche

import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const capability = searchParams.get("capability");
  const niche = searchParams.get("niche");

  // MVP: Return the local Zenic agent card as the only discoverable agent
  const localAgent = {
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
  };

  let agents = [localAgent];

  // Filter by capability if specified
  if (capability) {
    agents = agents.filter((a) =>
      a.capabilities.some((c) => c.toLowerCase().includes(capability.toLowerCase()))
    );
  }

  // Filter by niche if specified
  if (niche) {
    agents = agents.filter((a) =>
      a.nicheDna?.toLowerCase().includes(niche.toLowerCase())
    );
  }

  return NextResponse.json({
    success: true,
    agents,
    total: agents.length,
    query: { capability: capability || null, niche: niche || null },
  });
}
