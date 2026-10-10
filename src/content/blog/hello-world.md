---
title: "Hello, world"
description: "A placeholder so the Writing section has something to show."
date: 2026-10-09
draft: true
---

This file is `src/content/blog/hello-world.md`. Drop another `.md` file next to
it and it shows up under **What I'm up to**, newest first — the filename becomes
the URL, so this one lives at `/writing/hello-world`.

## Frontmatter

Only `title` and `date` are required:

```yaml
---
title: "Three days above the clouds"
description: "Optional one-liner, shown under the title in the list."
date: 2026-10-12
draft: false
---
```

`draft: true` keeps a post visible in `npm run dev` but out of the built site —
which is why you can see this one locally and nobody else can. Delete this file
once you have a real post.

## What you can write

Regular markdown: **bold**, _italic_, [links](https://lucasdunker.com), lists,

- like
- this

> blockquotes,

and fenced code blocks, which get syntax highlighting:

```ts
const posts = await getPosts();
```
