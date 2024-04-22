import type { LayoutServerLoad } from './$types';
import { redirect, error } from '@sveltejs/kit';
import { PUBLIC_API_SSR } from '$env/static/public';

export const load: LayoutServerLoad = async ({ fetch, cookies }) => {
  const response = await fetch(`${PUBLIC_API_SSR}/en/cms/assistant`, {
    headers: {
      'Cookie': `sessionid=${cookies.get('sessionid')}`,
    }
  });
  let content;
  if(response.ok) {
    content = await response.json();
  } else if (response.status === 401) {
    redirect(307, '/admin/login/?next=/');
  } else if (response.status === 404) {
    error(response.status, await response.text());
  } else {
    console.log(response);
    error(response.status, response.statusText);
  }

  return { content };
};
