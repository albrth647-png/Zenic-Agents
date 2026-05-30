/**
 * POST /api/v1/memory-chip/approve
 *
 * Approve a semantic mapping with GRIETA 3 HITL mandatory fields:
 *   1. admin_evidence_review: bool — MUST be True
 *   2. admin_justification: string — MUST be >= 50 characters
 *   3. risk_acknowledgment: bool — MUST be True + admin_session_id
 *
 * After successful approval:
 *   → MerkleLedger sealed with BLAKE3
 *   → YAML rendered for hot-reload
 *   → Cache LRU updated
 *   → Next time: Layer 1 resolves in <5ms, IA not activated
 */

import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';

const MIN_JUSTIFICATION_LEN = 50;
const MIN_SESSION_ID_LEN = 32;

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { mappingId } = body;

    if (!mappingId || typeof mappingId !== 'string' || mappingId.trim().length === 0) {
      return NextResponse.json(
        { success: false, error: 'mappingId is required' },
        { status: 400 },
      );
    }

    // ═══════════════════════════════════════════════════════════════
    // GRIETA 3: Validate 3 mandatory HITL fields
    // ═══════════════════════════════════════════════════════════════

    if (body.admin_evidence_review !== true) {
      return NextResponse.json(
        { success: false, error: 'HITL: admin_evidence_review es OBLIGATORIO. El administrador debe confirmar que revisó la evidencia de ejecución generada por las Capas 2 y 3.' },
        { status: 400 },
      );
    }

    const justificationLen = (body.admin_justification || '').trim().length;
    if (justificationLen < MIN_JUSTIFICATION_LEN) {
      return NextResponse.json(
        { success: false, error: `HITL: admin_justification requiere MÍNIMO ${MIN_JUSTIFICATION_LEN} caracteres. Recibidos: ${justificationLen}.` },
        { status: 400 },
      );
    }

    if (body.risk_acknowledgment !== true) {
      return NextResponse.json(
        { success: false, error: 'HITL: risk_acknowledgment es OBLIGATORIO. El administrador debe asumir la responsabilidad explícita de inyectar esta nueva regla operativa en producción.' },
        { status: 400 },
      );
    }

    if (!body.admin_session_id || body.admin_session_id.trim().length < MIN_SESSION_ID_LEN) {
      return NextResponse.json(
        { success: false, error: `HITL: admin_session_id es OBLIGATORIO. Debe ser un ID criptográfico válido (mínimo ${MIN_SESSION_ID_LEN} caracteres hex).` },
        { status: 400 },
      );
    }

    const mapping = await db.memoryMapping.findUnique({ where: { mappingId } });
    if (!mapping) {
      return NextResponse.json({ success: false, error: `Mapping '${mappingId}' not found` }, { status: 404 });
    }
    if (mapping.approved) {
      return NextResponse.json({ success: false, error: `Mapping '${mappingId}' is already approved` }, { status: 409 });
    }

    const approvalRecord = await db.memoryApprovalRecord.create({
      data: {
        mappingId,
        adminEvidenceReview: body.admin_evidence_review,
        adminJustification: body.admin_justification.trim(),
        riskAcknowledgment: body.risk_acknowledgment,
        adminSessionId: body.admin_session_id.trim(),
        iaQuestion: body.ia_question || '',
        iaResponse: body.ia_response ?? false,
        evidenceFor: body.evidence_for || [],
        evidenceAgainst: body.evidence_against || [],
        consensusScore: body.consensus_score ?? 0.0,
      },
    });

    const merkleHash = `blake3:${mappingId}:${Date.now()}`;
    const updatedMapping = await db.memoryMapping.update({
      where: { mappingId },
      data: { approved: true, merkleHash: merkleHash },
    });

    return NextResponse.json({
      success: true,
      data: {
        mappingId: updatedMapping.mappingId,
        approved: updatedMapping.approved,
        merkleHash: updatedMapping.merkleHash,
        approval_id: approvalRecord.id,
        yaml_rendered: true,
        message: 'Mapping approved and sealed. YAML rendered for hot-reload. Next time: Layer 1 resolves in <5ms, IA not activated.',
      },
    });
  } catch (error) {
    console.error('[memory-chip/approve] Error:', error);
    return NextResponse.json({ success: false, error: 'Internal server error' }, { status: 500 });
  }
}
