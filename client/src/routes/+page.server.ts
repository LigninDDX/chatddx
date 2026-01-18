import { fail } from '@sveltejs/kit';
import type { Actions } from './$types';
import { PUBLIC_API_SSR } from '$env/static/public';

export const actions: Actions = {
  diagnose: async ({ request, cookies }) => {
    const sessionid = cookies.get('sessionid');
    const formData = await request.formData();
    const symptoms = formData.get('symptoms');

    if (!symptoms) {
      return fail(400, { message: 'Symptoms are required' });
    }

    try {
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };

      if (sessionid) {
        headers['Cookie'] = `sessionid=${sessionid}`;
      }

      const response = await fetch(`${PUBLIC_API_SSR}/api/diagnose`, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify({ symptoms })
      });

      if (!response.ok) {
        console.error('Django API Error:', response.status, data);
        return fail(response.status, {
          message: data.error || 'Ett fel uppstod vid kontakt med servern.',
          symptoms
        });
      }

      const data = await response.json();
      return { success: true, results: data };
    } catch (err) {
      console.error('Network/Server Error:', err);
      return fail(500, {
        message: 'Kunde inte ansluta till diagnostikservern.',
        symptoms
      });
    }
  }
};
