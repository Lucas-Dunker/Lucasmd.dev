import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

// Add a blog post by creating a .md file under src/content/blog.
// The filename becomes the URL.
const blog = defineCollection({
  loader: glob({ base: "./src/content/blog", pattern: "**/*.md" }),
  schema: z.object({
    title: z.string(),
    description: z.string().optional(),
    date: z.coerce.date(),
    draft: z.boolean().default(false),
  }),
});

export const collections = { blog };
