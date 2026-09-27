import { defineConfig } from 'vite';

export default defineConfig({
  build: {
    outDir: '../preview_static',
    emptyOutDir: true,
    cssCodeSplit: false,
    rolldownOptions: {
      output: {
        entryFileNames: 'app.js',
        assetFileNames: 'styles.css',
      },
    },
  },
});
