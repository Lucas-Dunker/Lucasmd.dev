# lucasdunker.com

My personal website!

**Live:** [lucasdunker.com](https://lucasdunker.com/)

## Stack

- [Astro 7](https://astro.build/) — static site generator
- [Tailwind CSS 4](https://tailwindcss.com/) — CSS-first styling via `@tailwindcss/vite`
- [TypeScript 6](https://www.typescriptlang.org/)
- Deployed to [Cloudflare Pages](https://pages.cloudflare.com/)

## Design

- Fonts: [Mansalva](https://fontsource.org/fonts/mansalva) (display) · [Inter](https://fontsource.org/fonts/inter) (body) · [IBM Plex Mono](https://fontsource.org/fonts/ibm-plex-mono) (labels)
- ASCII + Lawn Chair animations: the amazingly talented [Sorindra Birjah](https://steamcommunity.com/id/thisguyisprettycoolandsingle/images/)

## Development

```sh
nvm use 26
npm install
npm run dev        # http://localhost:4321
npm run build      # astro check + static build
npm run preview    # preview the built site
```

## Deploy

```sh
npm run pages:deploy   # builds + ships dist/ to Cloudflare Pages
```
