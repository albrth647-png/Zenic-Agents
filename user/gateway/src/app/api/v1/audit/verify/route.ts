// Merkle Audit Trail — Verification endpoint
// Allows verification of audit trail integrity and generation of compliance certificates

import { NextRequest, NextResponse } from "next/server";
import { getMerkleAuditService } from "@/lib/mcp-gateway/audit/merkle-audit";

export async function GET(request: NextRequest) {
  try {
    const merkleService = getMerkleAuditService();
    const verification = merkleService.verify();

    return NextResponse.json({
      success: true,
      verification: {
        valid: verification.valid,
        totalEntries: verification.totalEntries,
        latestHash: merkleService.getLatestHash(),
        chainLength: merkleService.length,
        verifiedAt: new Date().toISOString(),
      },
    });
  } catch (error) {
    return NextResponse.json(
      { success: false, error: "Audit verification failed" },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const { action } = (await request.json()) as { action: string };

    const merkleService = getMerkleAuditService();

    switch (action) {
      case "verify": {
        const verification = merkleService.verify();
        return NextResponse.json({
          success: true,
          verification,
          complianceCertificate: verification.valid
            ? {
                issuedAt: new Date().toISOString(),
                chainLength: merkleService.length,
                rootHash: merkleService.getLatestHash(),
                status: "COMPLIANT",
              }
            : null,
        });
      }

      case "root-hash": {
        return NextResponse.json({
          success: true,
          rootHash: merkleService.getLatestHash(),
          chainLength: merkleService.length,
        });
      }

      default:
        return NextResponse.json(
          {
            success: false,
            error: "Unknown action. Use 'verify' or 'root-hash'",
          },
          { status: 400 }
        );
    }
  } catch (error) {
    return NextResponse.json(
      { success: false, error: "Audit verification failed" },
      { status: 500 }
    );
  }
}
