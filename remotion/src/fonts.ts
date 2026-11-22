// Brand 3-font system, loaded from Google Fonts with safe offline fallbacks.
import { loadFont as loadDisplay } from '@remotion/google-fonts/SpaceGrotesk';
import { loadFont as loadBody } from '@remotion/google-fonts/Inter';
import { loadFont as loadMono } from '@remotion/google-fonts/JetBrainsMono';
import { loadFont as loadSerif } from '@remotion/google-fonts/Spectral';
import { loadFont as loadEditorial } from '@remotion/google-fonts/SourceSerif4';

function safeLoad(loader: () => { fontFamily: string }, fallback: string): string {
  try {
    return loader().fontFamily;
  } catch (e) {
    return fallback;
  }
}

export const FONT_DISPLAY = safeLoad(
  () => loadDisplay('normal', { weights: ['500', '600', '700'], subsets: ['latin'] }),
  "'Space Grotesk', -apple-system, BlinkMacSystemFont, sans-serif"
);

export const FONT_BODY = safeLoad(
  () => loadBody('normal', { weights: ['400', '500', '600'], subsets: ['latin'] }),
  "'Inter', -apple-system, BlinkMacSystemFont, sans-serif"
);

export const FONT_MONO = safeLoad(
  () => loadMono('normal', { weights: ['400', '500', '700'], subsets: ['latin'] }),
  "'JetBrains Mono', 'Fira Code', monospace"
);

export const FONT_SERIF = safeLoad(
  () => loadSerif('normal', { weights: ['500', '600'], subsets: ['latin'] }),
  "'Spectral', Georgia, serif"
);

export const FONT_EDITORIAL = safeLoad(
  () => loadEditorial('normal', { weights: ['600', '700', '900'], subsets: ['latin'] }),
  "'Source Serif 4', Georgia, serif"
);
