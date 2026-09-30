/**
 * Resolves a site-root asset path from the delivery contract (manifest, textures.json, art.json all use
 * `/assets/...`) against the deployed base path, so the build works at `/` and under a sub-path such as
 * GitHub Pages' `/<repo>/`. Absolute URLs and relative paths pass through unchanged.
 */
export function assetUrl(path: string): string {
  return path.startsWith('/') && !path.startsWith('//') ? import.meta.env.BASE_URL + path.slice(1) : path;
}
