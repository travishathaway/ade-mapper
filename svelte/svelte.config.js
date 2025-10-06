import { svelte, vitePreprocess } from '@sveltejs/vite-plugin-svelte'
import tailwindcss from "@tailwindcss/vite";

/** @type {import("@sveltejs/vite-plugin-svelte").SvelteConfig} */
export default {
  // Consult https://svelte.dev/docs#compile-time-svelte-preprocess
  // for more information about preprocessors
  preprocess: vitePreprocess(),
  plugins: [
    tailwindcss(),
    svelte()
  ],
}
