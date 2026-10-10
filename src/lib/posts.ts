import { getCollection, type CollectionEntry } from "astro:content";

export type Post = CollectionEntry<"blog">;

/** Newest first. Drafts are visible in dev and dropped from the build. */
export async function getPosts(): Promise<Post[]> {
  const posts = await getCollection(
    "blog",
    ({ data }) => import.meta.env.DEV || !data.draft,
  );
  return posts.sort((a, b) => b.data.date.valueOf() - a.data.date.valueOf());
}

export const postHref = (post: Post) => `/writing/${post.id}`;

// Frontmatter dates are usually bare (2026-10-09), which parse as midnight UTC;
// formatting in local time would show the day before for anyone west of it.
export const formatDate = (d: Date) =>
  d.toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  });
