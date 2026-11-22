import React from 'react';
import { AbsoluteFill, Sequence } from 'remotion';
import { Captions, ProgressBar } from '../../lib/shorts';
import { KenBurnsImage, StoryVignette } from '../../lib/story';
import { VO } from './vo.gen';

// =============================================================================
// COMPOSITION CONFIG — "Cute 3D Dancing Girl"
// 4 vibrant 3D cartoon beats (15 seconds, 450 frames @ 30fps).
// Dynamic Ken-Burns motion pan & zoom, word-synced animated captions over Kokoro AI voice.
// =============================================================================
export const compositionConfig = {
  id: 'Short14Dance',
  durationInSeconds: 15,
  fps: 30,
  width: 1080,
  height: 1920,
};

const PINK_ACCENT = '#ff6b9d';
const TAIL = 15; // Crossfade underlap

const BEATS = [
  { src: 'projects/dancing-girl/b1-dance.png', start: 0, end: 114, variant: 0, fadeIn: 0 },
  { src: 'projects/dancing-girl/b2-dance.png', start: 114, end: 234, variant: 2 },
  { src: 'projects/dancing-girl/b3-dance.png', start: 234, end: 354, variant: 4 },
  { src: 'projects/dancing-girl/b4-dance.png', start: 354, end: 450, variant: 5 },
] as const;

const Short14Dance: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: '#110d1a' }}>
      {BEATS.map((b, i) => {
        const isLast = i === BEATS.length - 1;
        const dur = b.end - b.start + (isLast ? 0 : TAIL);
        return (
          <Sequence key={i} from={b.start} durationInFrames={dur}>
            <KenBurnsImage 
              src={b.src} 
              dur={dur} 
              variant={b.variant} 
              fadeIn={'fadeIn' in b ? b.fadeIn : 15} 
            />
          </Sequence>
        );
      })}
      <StoryVignette strength={0.35} />
      <Captions lines={VO} y={1380} size={56} accent={PINK_ACCENT} maxWords={4} plate />
      <ProgressBar color={PINK_ACCENT} />
    </AbsoluteFill>
  );
};

export default Short14Dance;
