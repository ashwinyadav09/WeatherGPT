import { MOCK_PLACES, MOCK_ALERTS, MOCK_EVIDENCE_PACKETS } from './mockData';

export const handleMockRequest = async (
  input: RequestInfo | URL,
  init?: RequestInit
): Promise<Response | null> => {
  const urlStr = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;
  const method = (init?.method || 'GET').toUpperCase();

  // /v1/places/search or /v1/places/saved
  if (urlStr.includes('/v1/places/search') || urlStr.includes('/v1/places/saved')) {
    const parsed = new URL(urlStr, 'http://localhost');
    const q = parsed.searchParams.get('q')?.toLowerCase() || '';
    const filtered = q
      ? MOCK_PLACES.filter(
          (p) =>
            p.names.en.toLowerCase().includes(q) ||
            p.names.hi?.toLowerCase().includes(q) ||
            p.district?.toLowerCase().includes(q)
        )
      : MOCK_PLACES;

    return new Response(JSON.stringify(filtered), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  // /v1/alerts
  if (urlStr.includes('/v1/alerts')) {
    return new Response(JSON.stringify(MOCK_ALERTS), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  // /v1/voice/transcribe
  if (urlStr.includes('/v1/voice/transcribe') && method === 'POST') {
    return new Response(
      JSON.stringify({
        text: 'कल पुणे में बारिश होगी क्या?',
        language: 'hi',
        confidence: 0.95,
        provider: 'mock',
      }),
      {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }

  // /v1/voice/speak
  if (urlStr.includes('/v1/voice/speak') && method === 'POST') {
    // Generate minimal valid RIFF WAV bytes
    const header = new Uint8Array([
      0x52, 0x49, 0x46, 0x46, 0x24, 0x00, 0x00, 0x00,
      0x57, 0x41, 0x56, 0x45, 0x66, 0x6d, 0x74, 0x20,
      0x10, 0x00, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00,
      0x80, 0x3e, 0x00, 0x00, 0x00, 0x7d, 0x00, 0x00,
      0x02, 0x00, 0x10, 0x00, 0x64, 0x61, 0x74, 0x61,
      0x00, 0x00, 0x00, 0x00,
    ]);
    return new Response(header, {
      status: 200,
      headers: { 'Content-Type': 'audio/wav' },
    });
  }

  // /v1/chat or /v1/conversation/message mock streaming response
  if (urlStr.includes('/v1/chat') && method === 'POST') {
    let bodyObj: { text?: string; language?: string } = {};
    if (init?.body) {
      try {
        bodyObj = JSON.parse(init.body as string);
      } catch {
        // ignore parse error
      }
    }

    const lang = bodyObj.language || 'en';
    const isHindi = lang === 'hi';

    const tokens = isHindi
      ? ['हाँ, ', 'कल ', 'पुणे ', 'में ', 'बारिश ', 'होने ', 'की ', 'संभावना ', 'है। ', 'अनुमानित ', 'वर्षा ', 'लगभग ', '12 मिमी ', 'है।']
      : ['Yes, ', 'rain ', 'is ', 'likely ', 'tomorrow ', 'in ', 'Pune. ', 'Expected ', 'precipitation ', 'is ', 'around ', '12 mm.'];

    const headline = isHindi ? 'कल पुणे में बारिश की संभावना' : 'Rain likely tomorrow in Pune';
    const sourceLine = 'Data: Open-Meteo (global model) | issued 05:30 IST';
    const caveat = '';

    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      async start(controller) {
        // 1. Meta event
        controller.enqueue(
          encoder.encode(`event: meta\ndata: ${JSON.stringify({ session_id: 'mock_session', timestamp: new Date().toISOString() })}\n\n`)
        );

        // 2. Stream tokens with slight delay
        for (const token of tokens) {
          controller.enqueue(
            encoder.encode(`event: token\ndata: ${JSON.stringify({ text: token })}\n\n`)
          );
        }

        // 3. Evidence packets event
        for (const packet of MOCK_EVIDENCE_PACKETS) {
          controller.enqueue(
            encoder.encode(`event: evidence\ndata: ${JSON.stringify(packet)}\n\n`)
          );
        }

        // 4. Structured card event
        controller.enqueue(
          encoder.encode(
            `event: card\ndata: ${JSON.stringify({
              headline,
              key_values: { rain: '12 mm', probability: '85%' },
              source_line: sourceLine,
              caveat,
            })}\n\n`
          )
        );

        // 5. Done event
        controller.enqueue(encoder.encode(`event: done\ndata: {}\n\n`));
        controller.close();
      },
    });

    return new Response(stream, {
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });
  }

  return null;
};

/**
 * Installs mock API interceptor on window.fetch if backend is unreachable
 */
export const installMockApiFallback = () => {
  if (typeof window === 'undefined') return;

  const originalFetch = window.fetch;
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    try {
      const response = await originalFetch(input, init);
      if (response.status === 404 || response.status === 502 || response.status === 503) {
        const mockRes = await handleMockRequest(input, init);
        if (mockRes) return mockRes;
      }
      return response;
    } catch {
      const mockRes = await handleMockRequest(input, init);
      if (mockRes) return mockRes;
      throw new Error(`Failed to fetch and no mock available for ${input}`);
    }
  };
};
