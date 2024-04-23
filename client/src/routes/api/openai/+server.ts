import OpenAI from 'openai';
import { OpenAIStream, StreamingTextResponse, type OpenAIStreamCallbacks } from 'ai';
import type { RequestHandler } from './$types';
import { PUBLIC_API_SSR } from '$env/static/public';

async function getOptions(sessionid: string) {
  try {
    const response = await fetch(`${PUBLIC_API_SSR}/api/chat/clusters/default`, {
      headers: {
        'Cookie': `sessionid=${sessionid}`,
      }
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch options: ${response.status}`);
    }

    return (await response.json()).diagnoses;
  } catch (error) {
    console.error('Error fetching OpenAI options:', error);
    throw error;
  }
}

async function logResponse(sessionid: string, content: string, message: string, identifier: string) {
  try {
    const response = await fetch(`${PUBLIC_API_SSR}/api/chat/history`, {
      method: 'POST',
      headers: {
        'Cookie': `sessionid=${sessionid}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        config: identifier,
        prompt: message,
        response: content,
      }),
    });

    if (!response.ok) {
      console.error(`Failed to log history: ${response.status}`);
    }
  } catch (error) {
    console.error('Failed to log history:', error);
  }
}

export const POST: RequestHandler = async ({ request, cookies }) => {
  const sessionid = cookies.get('sessionid') as string;

  try {
    const { messages } = await request.json();
    const message = messages.map((m: any) => m.content).join('\n');
    const { api_key, endpoint, identifier, ...payload } = await getOptions(sessionid);

    let openai = new OpenAI({
      baseURL: endpoint,
      apiKey: api_key,
    });

    const response = await openai.chat.completions.create({
      ...payload,
      messages: [ ...payload.messages, ...messages.map((message: any) => ({
        content: message.content,
        role: message.role,
      }))],
    });

    if (payload.stream) {
      let content = '';

      const streamCallbacks: OpenAIStreamCallbacks = {
        onToken: (chunk) => {
          content += chunk;
        },
        onFinal() {
          logResponse(sessionid, content, message, identifier);
        },
      }
      const stream = OpenAIStream(response, streamCallbacks);


      return new StreamingTextResponse(stream);
    } else {
      return new Response(JSON.stringify(response));
    }
  } catch (error) {
    console.error('Error in OpenAI API request:', error);

    return new Response(JSON.stringify({ error: 'Failed to process the request' }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json'
      }
    });
  }
};
