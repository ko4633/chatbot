import { defineConfig } from 'vitest/config';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  base: './',
  plugins: [
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg'],
      manifest: {
        name: '삼한쟁패 551–676',
        short_name: '삼한쟁패',
        description: '한국 삼국시대 what-if 역사 전략 시뮬레이션',
        theme_color: '#2A2622',
        background_color: '#3B4B50',
        display: 'standalone',
        icons: []
      }
    })
  ],
  test: {
    environment: 'node',
    include: ['src/test/**/*.test.ts']
  }
});
