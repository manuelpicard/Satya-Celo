import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const upstreamBase = (process.env.SATYA_X402_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export async function POST(request: NextRequest) {
  const payment = request.headers.get("x-payment");
  if (payment && payment.length > 16_384) {
    return NextResponse.json({ error: "x402-Zahlungsbeleg ist zu groß." }, { status: 413 });
  }

  try {
    const headers = new Headers({ Accept: "application/json" });
    if (payment) headers.set("X-PAYMENT", payment);

    let body: FormData | undefined;
    if (payment) {
      const incoming = await request.formData();
      body = new FormData();
      incoming.forEach((value, key) => body!.append(key, value));
    }

    const response = await fetch(`${upstreamBase}/api/x402/verify`, {
      method: "POST",
      headers,
      body,
      cache: "no-store",
      signal: AbortSignal.timeout(120_000),
    });
    const text = await response.text();
    let payload: unknown;
    try { payload = JSON.parse(text); }
    catch { payload = { error: "Der x402-Dienst lieferte keine JSON-Antwort.", detail: text.slice(0, 500) }; }
    const outHeaders = new Headers({ "Cache-Control": "no-store" });
    const receipt = response.headers.get("X-PAYMENT-RESPONSE");
    if (receipt) outHeaders.set("X-PAYMENT-RESPONSE", receipt);
    return NextResponse.json(payload, { status: response.status, headers: outHeaders });
  } catch {
    return NextResponse.json({ error: "x402-Prüfdienst ist derzeit nicht erreichbar. Es wurde keine Zahlung ausgelöst." }, { status: 503 });
  }
}
