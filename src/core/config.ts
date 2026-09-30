import type { QualityTier } from './events';

/** Runtime configuration derived from the URL, e.g. `?debug&quality=medium&webgl`. */
export interface AppConfig {
  quality: QualityTier;
  forceWebGL: boolean;
  debug: boolean;
}

export function readConfig(search = location.search): AppConfig {
  const p = new URLSearchParams(search);
  const q = p.get('quality');
  return {
    quality: q === 'medium' || q === 'low' ? q : 'high',
    forceWebGL: p.has('webgl'),
    debug: __DEBUG__ && p.has('debug'),
  };
}
