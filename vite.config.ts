import { defineConfig } from 'vite';

export default defineConfig({
  // '/' locally; the GitHub Pages workflow sets BASE_PATH=/<repo>/ (project page under javda4.github.io)
  base: process.env.BASE_PATH ?? '/',
  build: {
    target: 'es2023',
    chunkSizeWarningLimit: 2000,
  },
  // Debug tooling is compiled out of production via this flag (see src/debug).
  define: {
    __DEBUG__: JSON.stringify(process.env.NODE_ENV !== 'production'),
  },
});
