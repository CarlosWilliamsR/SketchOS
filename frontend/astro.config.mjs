// @ts-check
import { defineConfig } from 'astro/config';
import react from '@astrojs/react';

// https://astro.build/config
export default defineConfig({
  integrations: [react()],
  vite: {
    server: {
      proxy: {
        // Backend (FastAPI) is prefix-less: /extract-rules, /validate-geometry,
        // /autocorrect. The rewrite strips /api so same-origin browser fetches
        // to /api/* land on the correct backend route. LOAD-BEARING: removing
        // the rewrite makes every proxied fetch 404.
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },
  },
});
