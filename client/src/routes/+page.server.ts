import type { PageServerLoad, Actions } from './$types';
import { redirect } from '@sveltejs/kit';

export const load: PageServerLoad = async ({ parent }) => {
  const data = await parent();
  return data;
}

export const actions = {
  setlang: async ({ cookies, request, url }) => {
    const data = await request.formData();
    const lang = data.get('lang') as string;
    cookies.set('django_language', lang, {
      path: '/',
    });
    if (url.searchParams.has('redirectTo')) {
      redirect(303, url.searchParams.get('redirectTo') as string);
    }
    return { lang };
  },
} satisfies Actions;
