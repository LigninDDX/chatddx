import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vitest/config';
import fs from 'fs';

export default defineConfig({
  plugins: [sveltekit()],
  test: {
    include: ['src/**/*.{test,spec}.{js,ts}']
  },
  server: {
    host: '0.0.0.0',
    //https: {
    //  key: fs.readFileSync('./dev.chatddx.com-key.pem'),
    //  cert: fs.readFileSync('./dev.chatddx.com.pem'),
    //},
    proxy: {
      '/admin': 'http://localhost:8000',
      '/static': 'http://localhost:8000'
    }
  }
});
