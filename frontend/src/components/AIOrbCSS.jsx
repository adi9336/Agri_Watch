import React, { useEffect, useRef } from 'react';

/**
 * AIOrbCSS - Beautiful CSS-animated glass orb that reacts to voice state.
 * Replaces the broken Three.js shader with a smooth, reliable animated gradient.
 * State: idle | listening | thinking | speaking
 */
export default function AIOrbCSS({ state = 'idle', volume = 0, onClick, size = 280 }) {
  const orbRef = useRef(null);

  // Drive subtle scale pulsing via JS using volume
  useEffect(() => {
    if (!orbRef.current) return;
    const baseScale = 1;
    const pulse = state === 'speaking' ? baseScale + volume * 0.08 : baseScale;
    orbRef.current.style.transform = `scale(${pulse})`;
  }, [volume, state]);

  const configs = {
    idle: {
      outer: 'shadow-[0_0_60px_8px_rgba(16,185,129,0.18),0_0_120px_20px_rgba(16,185,129,0.08)]',
      grad: 'from-emerald-900/80 via-teal-800/60 to-emerald-950/90',
      shine: 'from-white/10 via-transparent to-transparent',
      ring: 'border-emerald-500/20',
      glint: 'bg-emerald-400/30',
      anim: 'animate-[breathe_4s_ease-in-out_infinite]',
    },
    listening: {
      outer: 'shadow-[0_0_80px_16px_rgba(52,211,153,0.3),0_0_160px_40px_rgba(52,211,153,0.12)]',
      grad: 'from-emerald-700/90 via-teal-600/70 to-green-900/80',
      shine: 'from-white/20 via-white/5 to-transparent',
      ring: 'border-emerald-400/40',
      glint: 'bg-emerald-300/50',
      anim: 'animate-[listenPulse_1.8s_ease-in-out_infinite]',
    },
    thinking: {
      outer: 'shadow-[0_0_80px_16px_rgba(99,102,241,0.3),0_0_160px_40px_rgba(99,102,241,0.12)]',
      grad: 'from-indigo-700/80 via-violet-600/60 to-purple-900/80',
      shine: 'from-white/15 via-indigo-200/10 to-transparent',
      ring: 'border-indigo-400/40',
      glint: 'bg-indigo-300/40',
      anim: 'animate-[thinkSpin_2s_linear_infinite]',
    },
    speaking: {
      outer: 'shadow-[0_0_100px_20px_rgba(245,158,11,0.35),0_0_200px_60px_rgba(245,158,11,0.15)]',
      grad: 'from-amber-600/90 via-orange-500/70 to-yellow-900/80',
      shine: 'from-white/25 via-amber-100/10 to-transparent',
      ring: 'border-amber-400/50',
      glint: 'bg-amber-200/60',
      anim: 'animate-[speakBounce_1s_ease-in-out_infinite]',
    },
  };

  const c = configs[state] || configs.idle;

  return (
    <div
      onClick={onClick}
      style={{ width: size, height: size }}
      className={`relative cursor-pointer select-none group transition-transform duration-300 ${c.anim}`}
    >
      {/* Outer glow halo */}
      <div className={`absolute inset-0 rounded-full ${c.outer} transition-all duration-700`} />

      {/* Glass ring border */}
      <div className={`absolute inset-0 rounded-full border ${c.ring} transition-all duration-500`} />

      {/* Core orb gradient */}
      <div
        ref={orbRef}
        className={`absolute inset-0 rounded-full bg-gradient-radial ${c.grad} transition-all duration-700 overflow-hidden`}
        style={{ transition: 'transform 80ms linear, background 700ms' }}
      >
        {/* Glass specular highlight - top left */}
        <div className={`absolute top-[8%] left-[12%] w-[42%] h-[36%] rounded-full bg-gradient-to-br ${c.shine} blur-sm`} />

        {/* Secondary inner glow */}
        <div className="absolute bottom-[10%] right-[10%] w-[30%] h-[30%] rounded-full bg-white/[0.04] blur-md" />

        {/* Rotating color blobs inside (liquid glass look) */}
        <div className={`absolute inset-0 rounded-full ${
          state === 'thinking' ? 'animate-[spin_3s_linear_infinite]' :
          state === 'speaking' ? 'animate-[spin_2s_linear_infinite_reverse]' :
          'animate-[spin_8s_linear_infinite]'
        } opacity-40`}>
          <div className={`absolute top-1/4 left-1/4 w-1/2 h-1/2 rounded-full ${c.glint} blur-xl`} />
        </div>
      </div>

      {/* Hover glow ring */}
      <div className="absolute inset-[-6px] rounded-full border border-white/[0.06] opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
    </div>
  );
}
