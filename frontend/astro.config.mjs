import { defineConfig } from 'astro/config';

export default defineConfig({
  output: 'server',
  vite: {
    ssr: {
      external: ['pg']
    }
  }
});
