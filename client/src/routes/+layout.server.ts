import type { LayoutServerLoad } from './$types';
import { redirect, error } from '@sveltejs/kit';
import { PUBLIC_API_SSR } from '$env/static/public';

export const load: LayoutServerLoad = async ({ fetch, cookies }) => {
  const sessionid = cookies.get('sessionid');
  const django_language = cookies.get('django_language');

  const response = await fetch(`${PUBLIC_API_SSR}/cms/assistant`, {
    headers: {
      'Cookie': `sessionid=${sessionid}; django_language=${django_language}`,
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

  return { content, django_language };
};
