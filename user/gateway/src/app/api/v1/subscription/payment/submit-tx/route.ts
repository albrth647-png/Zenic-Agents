// ─── Zenic-Agents v3 — Subscription API: Submit TX Hash ──────────────
// POST /api/v1/subscription/payment/submit-tx — Submit TRON tx hash for a payment

import { NextRequest, NextResponse } from 'next/server';
import { db } from '@/lib/db';

const TRON_TX_HASH_REGEX = /^[0-9a-fA-F]{64}$/;
const TRON_WALLET_REGEX = /^T[A-Za-z1-9]{33}$/;

export async function POST(req: NextRequest) {
  try {
    const body = await req.json() as {
      paymentId?: string;
      txHash?: string;
      sourceWallet?: string;
    };

    if (!body.paymentId || !body.txHash) {
      return NextResponse.json(
        { error: 'paymentId and txHash are required' },
        { status: 400 },
      );
    }

    const { paymentId, txHash, sourceWallet } = body;

    // Validate TRON tx hash format (64 hex chars)
    if (!TRON_TX_HASH_REGEX.test(txHash)) {
      return NextResponse.json(
        { error: 'Invalid TRON transaction hash. Must be 64 hexadecimal characters.' },
        { status: 400 },
      );
    }

    // Validate source wallet if provided (starts with T, 34 chars)
    if (sourceWallet && !TRON_WALLET_REGEX.test(sourceWallet)) {
      return NextResponse.json(
        { error: 'Invalid TRON wallet address. Must start with T and be 34 characters long.' },
        { status: 400 },
      );
    }

    // Find payment by paymentId
    const payment = await db.subscriptionPayment.findUnique({
      where: { paymentId },
    });

    if (!payment) {
      return NextResponse.json(
        { error: 'Payment not found' },
        { status: 404 },
      );
    }

    // Check if payment can accept tx submission
    if (!['pending', 'awaiting_tx_hash', 'awaiting_payment'].includes(payment.status)) {
      return NextResponse.json(
        { error: `Payment cannot accept tx hash in current status: ${payment.status}` },
        { status: 400 },
      );
    }

    // Check if payment has expired
    if (payment.expiresAt && new Date(payment.expiresAt) < new Date()) {
      await db.subscriptionPayment.update({
        where: { paymentId },
        data: { status: 'expired' },
      });
      return NextResponse.json(
        { error: 'Payment has expired' },
        { status: 400 },
      );
    }

    // Update payment with tx hash
    const updatedPayment = await db.subscriptionPayment.update({
      where: { paymentId },
      data: {
        txHash,
        walletFrom: sourceWallet ?? payment.walletFrom,
        status: 'awaiting_confirmation',
        metadata: JSON.stringify({
          ...JSON.parse(payment.metadata || '{}'),
          txSubmittedAt: new Date().toISOString(),
          previousStatus: payment.status,
        }),
      },
    });

    return NextResponse.json({
      data: updatedPayment,
      message: 'Transaction hash submitted. Payment will be verified manually.',
    });
  } catch (error) {
    console.error('[Subscription Submit TX POST]', error);
    return NextResponse.json(
      { error: 'Internal server error', details: String(error) },
      { status: 500 },
    );
  }
}
