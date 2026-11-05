import React, { useRef, useEffect } from 'react';
import * as THREE from 'three';

// ==============================================================================
// 3D Simplex Noise & Glass Orb GLSL Shaders
// ==============================================================================
const vertexShader = `
  uniform float uTime;
  uniform float uSpeed;
  uniform float uNoiseScale;
  uniform float uNoiseStrength;
  uniform float uVolume;
  uniform float uState; // 0: idle, 1: listening, 2: thinking, 3: speaking

  varying vec3 vNormal;
  varying vec3 vPosition;
  varying vec3 vWorldNormal;
  varying vec3 vViewPosition;
  varying float vDisplacement;

  // Ashima / Stefan Gustavson Simplex 3D Noise
  vec4 permute(vec4 x) { return mod(((x * 34.0) + 1.0) * x, 289.0); }
  vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }

  float snoise(vec3 v) {
    const vec2 C = vec2(1.0 / 6.0, 1.0 / 3.0);
    const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
    vec3 i  = floor(v + dot(v, C.yyy));
    vec3 x0 = v - i + dot(i, C.xxx);
    vec3 g = step(x0.yzx, x0.xyz);
    vec3 l = 1.0 - g;
    vec3 i1 = min(g.xyz, l.zxy);
    vec3 i2 = max(g.xyz, l.zxy);
    vec3 x1 = x0 - i1 + 1.0 * C.xxx;
    vec3 x2 = x0 - i2 + 2.0 * C.xxx;
    vec3 x3 = x0 - 1.0 + 3.0 * C.xxx;
    i = mod(i, 289.0);
    vec4 p = permute(permute(permute(
               i.z + vec4(0.0, i1.z, i2.z, 1.0))
             + i.y + vec4(0.0, i1.y, i2.y, 1.0))
             + i.x + vec4(0.0, i1.x, i2.x, 1.0));
    float n_ = 0.142857142857;
    vec3  ns = n_ * D.wyz - D.xzx;
    vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
    vec4 x_ = floor(j * ns.z);
    vec4 y_ = floor(j - 7.0 * x_);
    vec4 x = x_ * ns.x + ns.yyyy;
    vec4 y = y_ * ns.x + ns.yyyy;
    vec4 h = 1.0 - abs(x) - abs(y);
    vec4 b0 = vec4(x.xy, y.xy);
    vec4 b1 = vec4(x.zw, y.zw);
    vec4 s0 = floor(b0) * 2.0 + 1.0;
    vec4 s1 = floor(b1) * 2.0 + 1.0;
    vec4 sh = -step(h, vec4(0.0));
    vec4 a0 = b0.xzyw + s0.xzyw * sh.xxyy;
    vec4 a1 = b1.xzyw + s1.xzyw * sh.zzww;
    vec3 p0 = vec3(a0.xy, h.x);
    vec3 p1 = vec3(a0.zw, h.y);
    vec3 p2 = vec3(a1.xy, h.z);
    vec3 p3 = vec3(a1.zw, h.w);
    vec4 norm = taylorInvSqrt(vec4(dot(p0, p0), dot(p1, p1), dot(p2, p2), dot(p3, p3)));
    p0 *= norm.x; p1 *= norm.y; p2 *= norm.z; p3 *= norm.w;
    vec4 m = max(0.6 - vec4(dot(x0, x0), dot(x1, x1), dot(x2, x2), dot(x3, x3)), 0.0);
    m = m * m;
    return 42.0 * dot(m * m, vec4(dot(p0, x0), dot(p1, x1), dot(p2, x2), dot(p3, x3)));
  }

  void main() {
    vNormal = normal;
    vWorldNormal = normalize(mat3(modelMatrix) * normal);

    float t = uTime * uSpeed;
    vec3 coord = position * uNoiseScale;

    // Twist deformation when thinking
    if (uState > 1.5 && uState < 2.5) {
      float twistAngle = position.y * 1.5 + t;
      float s = sin(twistAngle);
      float c = cos(twistAngle);
      coord.xz = mat2(c, -s, s, c) * coord.xz;
    }

    // Two-octave simplex displacement
    float n1 = snoise(coord + vec3(0.0, t * 0.8, t * 0.3));
    float n2 = snoise(coord * 2.2 - vec3(t * 0.4, 0.0, t * 0.6)) * 0.5;
    float noise = n1 + n2;

    // Dynamic amplitude based on volume and state
    float amp = uNoiseStrength + (uVolume * 0.45);
    if (uState > 2.5) {
      // Speaking pulse swell
      amp += sin(t * 8.0) * 0.05 * (uVolume + 0.3);
    }

    vec3 displaced = position + normal * (noise * amp);
    vPosition = displaced;
    vDisplacement = noise;

    vec4 mvPosition = modelViewMatrix * vec4(displaced, 1.0);
    vViewPosition = -mvPosition.xyz;
    gl_Position = projectionMatrix * mvPosition;
  }
`;

const fragmentShader = `
  uniform float uTime;
  uniform float uState; // 0: idle, 1: listening, 2: thinking, 3: speaking
  uniform float uVolume;
  uniform vec2 uMouse;
  uniform vec3 uColorCore;
  uniform vec3 uColorBody;
  uniform vec3 uColorRim;
  uniform vec3 uColorActive;

  varying vec3 vNormal;
  varying vec3 vPosition;
  varying vec3 vWorldNormal;
  varying vec3 vViewPosition;
  varying float vDisplacement;

  void main() {
    vec3 viewDir = normalize(vViewPosition);
    vec3 normal = normalize(vNormal);

    // Fresnel Rim Glow
    float fresnel = 1.0 - max(dot(viewDir, normal), 0.0);
    float rim = pow(fresnel, 2.5);
    float deepRim = pow(fresnel, 5.0);

    // Specular Glint following pointer
    vec3 lightDir = normalize(vec3(uMouse.x * 2.0, uMouse.y * 2.0, 1.8));
    vec3 halfVector = normalize(lightDir + viewDir);
    float spec = pow(max(dot(normal, halfVector), 0.0), 36.0);
    float softSpec = pow(max(dot(normal, halfVector), 0.0), 8.0);

    // Core liquid color gradient
    vec3 core = uColorCore;
    vec3 body = uColorBody;
    vec3 rimCol = uColorRim;

    // State-based coloration shifts
    if (uState > 0.5 && uState < 1.5) {
      // Listening: Bright electric emerald-cyan rim
      rimCol = mix(uColorRim, uColorActive, 0.85);
      body = mix(body, vec3(0.05, 0.85, 0.6), 0.4);
    } else if (uState > 1.5 && uState < 2.5) {
      // Thinking: Swirling golden amber and indigo vortex
      float swirl = sin(vPosition.y * 3.0 + uTime * 4.0) * 0.5 + 0.5;
      body = mix(body, vec3(0.95, 0.55, 0.1), swirl * 0.8);
      core = mix(core, vec3(0.98, 0.8, 0.2), 0.9);
      rimCol = mix(rimCol, vec3(0.3, 0.9, 0.95), 0.7);
    } else if (uState > 2.5) {
      // Speaking: Radiant gold core with energized emerald halo
      float voicePulse = uVolume * 0.8;
      core = mix(core, vec3(1.0, 0.75, 0.2), 0.9 + voicePulse * 0.1);
      rimCol = mix(uColorRim, vec3(0.4, 1.0, 0.7), 0.8);
      rim *= (1.2 + voicePulse * 1.5);
    }

    // Liquid Glass Shading Composition
    float dispFactor = clamp((vDisplacement + 0.5) * 0.8, 0.0, 1.0);
    vec3 baseColor = mix(core, body, dispFactor);

    // Glass translucency with internal refractive depth
    vec3 finalColor = mix(baseColor, rimCol, rim * 0.85);

    // Add glowing highlights and rim dispersion
    finalColor += rimCol * deepRim * 1.8;
    finalColor += vec3(1.0, 1.0, 0.95) * spec * 0.9;
    finalColor += rimCol * softSpec * 0.3;

    // Soft core transparency (glass look)
    float alpha = clamp(0.65 + rim * 0.45 + spec * 0.5, 0.0, 1.0);

    gl_FragColor = vec4(finalColor, alpha);
  }
`;

/**
 * AIBlob - 3D Glass Shader AI Orb Component
 *
 * Visually reacts to:
 * - 'idle': Gentle breathing fluid glass
 * - 'listening': Energized bright rim, attentive ripple
 * - 'thinking': Rapid rotational twist and gold vortex
 * - 'speaking': Volumetric swelling dynamically driven by audio volume
 */
export default function AIBlob({
  state = 'idle', // 'idle' | 'listening' | 'thinking' | 'speaking'
  volume = 0.0,   // 0.0 to 1.0
  size = 280,
  interactive = true,
  onClick,
  className = '',
  colors = {
    core: '#f59e0b',  // Vibrant Golden Amber
    body: '#10b981',  // Agricultural Emerald Green
    rim: '#06b6d4',   // Electric Cyan
    active: '#22c55e' // Bright Spring Green
  }
}) {
  const mountRef = useRef(null);
  const uniformsRef = useRef(null);
  const mouseRef = useRef(new THREE.Vector2(0, 0));
  const targetMouseRef = useRef(new THREE.Vector2(0, 0));
  const sceneRef = useRef(null);
  const cameraRef = useRef(null);
  const rendererRef = useRef(null);
  const sphereRef = useRef(null);
  const animFrameIdRef = useRef(null);

  // Map state to numeric enum for shader
  const getStateNumber = (st) => {
    switch (st) {
      case 'listening': return 1.0;
      case 'thinking': return 2.0;
      case 'speaking': return 3.0;
      case 'idle':
      default: return 0.0;
    }
  };

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    // 1. Setup Three.js Scene & Camera
    const scene = new THREE.Scene();
    sceneRef.current = scene;

    const width = container.clientWidth || size;
    const height = container.clientHeight || size;

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    camera.position.z = 4.2;
    cameraRef.current = camera;

    // 2. Setup WebGL Renderer with Alpha transparency and high-DPI scaling
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // 3. High-density Icosahedron Geometry for smooth displacement
    const geometry = new THREE.IcosahedronGeometry(1.4, 50);

    // 4. Uniforms
    const uniforms = {
      uTime: { value: 0.0 },
      uSpeed: { value: 0.4 },
      uNoiseScale: { value: 1.1 },
      uNoiseStrength: { value: 0.12 },
      uVolume: { value: 0.0 },
      uState: { value: getStateNumber(state) },
      uMouse: { value: new THREE.Vector2(0, 0) },
      uColorCore: { value: new THREE.Color(colors.core) },
      uColorBody: { value: new THREE.Color(colors.body) },
      uColorRim: { value: new THREE.Color(colors.rim) },
      uColorActive: { value: new THREE.Color(colors.active) },
    };
    uniformsRef.current = uniforms;

    const material = new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader,
      uniforms,
      transparent: true,
      depthWrite: false,
      blending: THREE.NormalBlending,
    });

    const sphere = new THREE.Mesh(geometry, material);
    scene.add(sphere);
    sphereRef.current = sphere;

    // 5. Mouse Interaction
    const handleMouseMove = (e) => {
      if (!interactive) return;
      const rect = container.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      const y = -(((e.clientY - rect.top) / rect.height) * 2 - 1);
      targetMouseRef.current.set(x, y);
    };

    const handleMouseLeave = () => {
      targetMouseRef.current.set(0, 0);
    };

    container.addEventListener('mousemove', handleMouseMove);
    container.addEventListener('mouseleave', handleMouseLeave);

    // 6. Animation Clock & Render Loop
    const clock = new THREE.Clock();

    const animate = () => {
      animFrameIdRef.current = requestAnimationFrame(animate);

      const delta = clock.getDelta();
      const elapsed = clock.getElapsedTime();

      // Smooth pointer lerp
      mouseRef.current.lerp(targetMouseRef.current, 0.08);

      if (uniformsRef.current) {
        uniformsRef.current.uTime.value = elapsed;
        uniformsRef.current.uMouse.value.copy(mouseRef.current);
      }

      // Interactive 3D Sphere Tilt
      if (sphereRef.current) {
        sphereRef.current.rotation.y = elapsed * 0.15 + mouseRef.current.x * 0.4;
        sphereRef.current.rotation.x = mouseRef.current.y * 0.3;
      }

      renderer.render(scene, camera);
    };

    animate();

    // 7. Handle Resize
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width: newW, height: newH } = entry.contentRect;
        if (newW > 0 && newH > 0 && rendererRef.current && cameraRef.current) {
          cameraRef.current.aspect = newW / newH;
          cameraRef.current.updateProjectionMatrix();
          rendererRef.current.setSize(newW, newH);
        }
      }
    });
    resizeObserver.observe(container);

    // Cleanup
    return () => {
      cancelAnimationFrame(animFrameIdRef.current);
      resizeObserver.disconnect();
      container.removeEventListener('mousemove', handleMouseMove);
      container.removeEventListener('mouseleave', handleMouseLeave);

      if (rendererRef.current) {
        container.removeChild(rendererRef.current.domElement);
        rendererRef.current.dispose();
      }
      geometry.dispose();
      material.dispose();
    };
  }, []);

  // Update dynamic state uniforms
  useEffect(() => {
    if (!uniformsRef.current) return;

    const numState = getStateNumber(state);
    uniformsRef.current.uState.value = numState;

    switch (state) {
      case 'listening':
        uniformsRef.current.uSpeed.value = 0.85;
        uniformsRef.current.uNoiseStrength.value = 0.16;
        break;
      case 'thinking':
        uniformsRef.current.uSpeed.value = 1.8;
        uniformsRef.current.uNoiseStrength.value = 0.24;
        break;
      case 'speaking':
        uniformsRef.current.uSpeed.value = 1.3;
        uniformsRef.current.uNoiseStrength.value = 0.2;
        break;
      case 'idle':
      default:
        uniformsRef.current.uSpeed.value = 0.35;
        uniformsRef.current.uNoiseStrength.value = 0.1;
        break;
    }
  }, [state]);

  // Update dynamic volume uniform
  useEffect(() => {
    if (uniformsRef.current) {
      uniformsRef.current.uVolume.value = THREE.MathUtils.clamp(volume, 0.0, 1.0);
    }
  }, [volume]);

  // Update colors when prop changes
  useEffect(() => {
    if (uniformsRef.current && colors) {
      if (colors.core) uniformsRef.current.uColorCore.value.set(colors.core);
      if (colors.body) uniformsRef.current.uColorBody.value.set(colors.body);
      if (colors.rim) uniformsRef.current.uColorRim.value.set(colors.rim);
      if (colors.active) uniformsRef.current.uColorActive.value.set(colors.active);
    }
  }, [colors]);

  return (
    <div
      ref={mountRef}
      onClick={onClick}
      className={`relative flex items-center justify-center cursor-pointer select-none transition-transform duration-300 hover:scale-[1.03] active:scale-[0.98] ${className}`}
      style={{
        width: typeof size === 'number' ? `${size}px` : size,
        height: typeof size === 'number' ? `${size}px` : size,
      }}
    />
  );
}
