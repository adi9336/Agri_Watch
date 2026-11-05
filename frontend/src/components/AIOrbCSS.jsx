import React, { useEffect, useRef } from 'react';

/**
 * AIOrbCSS — Beautiful CSS-animated glass orb using inline styles (no Tailwind bugs).
 * State: idle | listening | thinking | speaking
 */
export default function AIOrbCSS({ state = 'idle', volume = 0, onClick, size = 260 }) {
  const coreRef = useRef(null);

  // Drive volume-reactive scale
  useEffect(() => {
    if (!coreRef.current) return;
    const scale = state === 'speaking' ? 1 + volume * 0.1 : 1;
    coreRef.current.style.transform = `scale(${scale})`;
  }, [volume, state]);

  // Per-state design tokens
  const tokens = {
    idle: {
      core: 'radial-gradient(circle at 38% 32%, #065f46 0%, #064e3b 45%, #022c22 100%)',
      glow: '0 0 70px 20px rgba(16,185,129,0.22), 0 0 140px 50px rgba(16,185,129,0.09)',
      ring: 'rgba(52,211,153,0.2)',
      shine: 'rgba(255,255,255,0.08)',
      blob: '#10b981',
      anim: 'breathe 4s ease-in-out infinite',
    },
    listening: {
      core: 'radial-gradient(circle at 38% 32%, #059669 0%, #047857 45%, #064e3b 100%)',
      glow: '0 0 90px 28px rgba(52,211,153,0.35), 0 0 180px 70px rgba(52,211,153,0.14)',
      ring: 'rgba(52,211,153,0.4)',
      shine: 'rgba(255,255,255,0.14)',
      blob: '#34d399',
      anim: 'listenPulse 1.8s ease-in-out infinite',
    },
    thinking: {
      core: 'radial-gradient(circle at 38% 32%, #4f46e5 0%, #4338ca 45%, #1e1b4b 100%)',
      glow: '0 0 90px 28px rgba(99,102,241,0.35), 0 0 180px 70px rgba(99,102,241,0.14)',
      ring: 'rgba(129,140,248,0.4)',
      shine: 'rgba(199,210,254,0.12)',
      blob: '#818cf8',
      anim: 'thinkSpin 2.5s linear infinite',
    },
    speaking: {
      core: 'radial-gradient(circle at 38% 32%, #d97706 0%, #b45309 45%, #451a03 100%)',
      glow: '0 0 110px 32px rgba(245,158,11,0.4), 0 0 220px 90px rgba(245,158,11,0.16)',
      ring: 'rgba(251,191,36,0.5)',
      shine: 'rgba(255,236,153,0.18)',
      blob: '#fbbf24',
      anim: 'speakBounce 1s ease-in-out infinite',
    },
  };

  const t = tokens[state] ?? tokens.idle;
  const half = size / 2;

  return (
    <div
      onClick={onClick}
      style={{ width: size, height: size, position: 'relative', cursor: 'pointer', flexShrink: 0 }}
    >
      {/* Outer glow halo */}
      <div style={{
        position: 'absolute',
        inset: -24,
        borderRadius: '50%',
        boxShadow: t.glow,
        transition: 'box-shadow 0.8s ease',
        pointerEvents: 'none',
      }} />

      {/* Border ring */}
      <div style={{
        position: 'absolute',
        inset: 0,
        borderRadius: '50%',
        border: `1px solid ${t.ring}`,
        transition: 'border-color 0.6s ease',
        pointerEvents: 'none',
      }} />

      {/* Core orb */}
      <div
        ref={coreRef}
        style={{
          position: 'absolute',
          inset: 0,
          borderRadius: '50%',
          background: t.core,
          transition: 'background 0.7s ease, transform 80ms linear',
          overflow: 'hidden',
          animation: t.anim,
        }}
      >
        {/* Glass specular highlight — top-left "glint" */}
        <div style={{
          position: 'absolute',
          top: '8%',
          left: '10%',
          width: '44%',
          height: '38%',
          borderRadius: '50%',
          background: `radial-gradient(circle, ${t.shine} 0%, transparent 70%)`,
          filter: 'blur(6px)',
          pointerEvents: 'none',
        }} />

        {/* Secondary bottom-right soft fill */}
        <div style={{
          position: 'absolute',
          bottom: '8%',
          right: '10%',
          width: '30%',
          height: '28%',
          borderRadius: '50%',
          background: 'rgba(255,255,255,0.03)',
          filter: 'blur(8px)',
          pointerEvents: 'none',
        }} />

        {/* Rotating inner liquid blob */}
        <div style={{
          position: 'absolute',
          inset: 0,
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          animation: state === 'thinking' ? 'spin 2.5s linear infinite'
                   : state === 'speaking' ? 'spin 1.8s linear infinite reverse'
                   : 'spin 7s linear infinite',
        }}>
          <div style={{
            width: '55%',
            height: '55%',
            borderRadius: '50%',
            background: t.blob,
            opacity: 0.22,
            filter: 'blur(22px)',
            transform: 'translate(14%, -12%)',
          }} />
        </div>
      </div>

      {/* Hover outer ring */}
      <div style={{
        position: 'absolute',
        inset: -8,
        borderRadius: '50%',
        border: '1px solid rgba(255,255,255,0.05)',
        pointerEvents: 'none',
        transition: 'opacity 0.3s',
      }} />
    </div>
  );
}
