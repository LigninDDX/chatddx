import OpenAI from 'openai';
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

export const POST: RequestHandler = async ({ request, cookies }) => {
  try {
    const { messages } = await request.json();
    const { api_key, endpoint, identifier, ...payload } = await getOptions(cookies.get('sessionid') as string);

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

    return new Response(JSON.stringify(response));
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
