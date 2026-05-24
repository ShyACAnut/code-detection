import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import '../styles/global.css';

interface MagicRingsProps {
  color?: string;
  colorTwo?: string;
  ringCount?: number;
  speed?: number;
  attenuation?: number;
  lineThickness?: number;
  baseRadius?: number;
  radiusStep?: number;
  scaleRate?: number;
  opacity?: number;
  blur?: number;
  noiseAmount?: number;
  rotation?: number;
  ringGap?: number;
  fadeIn?: number;
  fadeOut?: number;
  followMouse?: boolean;
  mouseInfluence?: number;
  hoverScale?: number;
  parallax?: number;
  clickBurst?: boolean;
}

const vertexShader = `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const fragmentShader = `
  precision highp float;

  uniform float uTime;
  uniform vec2 uResolution;
  uniform vec2 uMouse;
  uniform float uMouseInfluence;
  uniform vec3 uColor;
  uniform vec3 uColorTwo;
  uniform float uRingCount;
  uniform float uSpeed;
  uniform float uAttenuation;
  uniform float uLineThickness;
  uniform float uBaseRadius;
  uniform float uRadiusStep;
  uniform float uScaleRate;
  uniform float uOpacity;
  uniform float uNoiseAmount;
  uniform float uRotation;
  uniform float uRingGap;
  uniform float uFadeIn;
  uniform float uFadeOut;
  uniform float uHoverAmount;
  uniform float uHoverScale;
  uniform float uParallax;
  uniform float uBurst;

  #define CYCLE 3.45
  #define HP 1.5707963

  float random(vec2 st) {
    return fract(sin(dot(st.xy, vec2(12.9898, 78.233))) * 43758.5453);
  }

  float fade(float t) {
    if (t < uFadeIn) {
      return smoothstep(0.0, uFadeIn, t);
    }
    return 1.0 - smoothstep(uFadeOut, CYCLE - 0.2, t);
  }

  float ring(vec2 p, float ri, float cut, float t0, float px) {
    float t = mod(uTime + t0, CYCLE);
    float r = ri + t / CYCLE * uScaleRate;
    float d = abs(length(p) - r);
    float a = atan(abs(p.y), abs(p.x)) / HP;
    float th = max(1.0 - a, 0.5) * px * uLineThickness;
    float h = (1.0 - smoothstep(th, th * 1.5, d)) + 1.0;
    d += pow(cut * a, 3.0) * r;
    return h * exp(-uAttenuation * d) * fade(t);
  }

  void main() {
    float px = 1.0 / min(uResolution.x, uResolution.y);
    vec2 p = (gl_FragCoord.xy - 0.5 * uResolution.xy) * px;

    float rot = uRotation * 0.0174533;
    p = mat2(cos(rot), -sin(rot), sin(rot), cos(rot)) * p;

    float hoverScale = mix(1.0, uHoverScale, uHoverAmount);
    p /= hoverScale + uBurst * 0.3;

    vec2 mouseOffset = uMouse * uMouseInfluence;
    p -= mouseOffset;

    vec3 col = vec3(0.0);

    for (float i = 0.0; i < 10.0; i++) {
      if (i >= uRingCount) break;

      float fi = i;
      float ri = uBaseRadius + fi * uRadiusStep;
      float cut = pow(uRingGap, fi);
      float t0 = 2.95 * fi;

      vec2 ringP = p;
      ringP -= fi * uParallax * mouseOffset;

      float r = ring(ringP, ri, cut, t0, px);

      vec3 ringCol = mix(uColor, uColorTwo, fi / max(uRingCount - 1.0, 1.0));
      ringCol += uNoiseAmount * (random(ringP * 100.0 + fi) - 0.5);

      col += ringCol * r;
    }

    col *= uBurst > 0.0 ? 3.0 : 1.0;

    float alpha = max(col.r, max(col.g, col.b)) * uOpacity;
    gl_FragColor = vec4(col, alpha);
  }
`;

const MagicRings: React.FC<MagicRingsProps> = ({
  color = '#fc42ff',
  colorTwo = '#42fcff',
  ringCount = 6,
  speed = 1,
  attenuation = 10,
  lineThickness = 2,
  baseRadius = 0.35,
  radiusStep = 0.1,
  scaleRate = 0.1,
  opacity = 1,
  blur = 0,
  noiseAmount = 0.1,
  rotation = 0,
  ringGap = 1.5,
  fadeIn = 0.7,
  fadeOut = 0.5,
  followMouse = true,
  mouseInfluence = 0.2,
  hoverScale = 1.2,
  parallax = 0.05,
  clickBurst = true,
}) => {
  const mountRef = useRef<HTMLDivElement>(null);
  const propsRef = useRef({
    color,
    colorTwo,
    ringCount,
    speed,
    attenuation,
    lineThickness,
    baseRadius,
    radiusStep,
    scaleRate,
    opacity,
    noiseAmount,
    rotation,
    ringGap,
    fadeIn,
    fadeOut,
    followMouse,
    mouseInfluence,
    hoverScale,
    parallax,
    clickBurst,
  });
  const mouseRef = useRef({ x: 0, y: 0 });
  const smoothMouseRef = useRef({ x: 0, y: 0 });
  const hoverAmountRef = useRef(0);
  const isHoveredRef = useRef(false);
  const burstRef = useRef(0);

  useEffect(() => {
    propsRef.current = {
      color,
      colorTwo,
      ringCount,
      speed,
      attenuation,
      lineThickness,
      baseRadius,
      radiusStep,
      scaleRate,
      opacity,
      noiseAmount,
      rotation,
      ringGap,
      fadeIn,
      fadeOut,
      followMouse,
      mouseInfluence,
      hoverScale,
      parallax,
      clickBurst,
    };
  }, [
    color,
    colorTwo,
    ringCount,
    speed,
    attenuation,
    lineThickness,
    baseRadius,
    radiusStep,
    scaleRate,
    opacity,
    noiseAmount,
    rotation,
    ringGap,
    fadeIn,
    fadeOut,
    followMouse,
    mouseInfluence,
    hoverScale,
    parallax,
    clickBurst,
  ]);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    const dpr = Math.min(window.devicePixelRatio, 2);
    renderer.setPixelRatio(dpr);

    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

    const geometry = new THREE.PlaneGeometry(2, 2);

    const hexToVec3 = (hex: string) => {
      const r = parseInt(hex.slice(1, 3), 16) / 255;
      const g = parseInt(hex.slice(3, 5), 16) / 255;
      const b = parseInt(hex.slice(5, 7), 16) / 255;
      return new THREE.Vector3(r, g, b);
    };

    const material = new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader,
      uniforms: {
        uTime: { value: 0 },
        uResolution: { value: new THREE.Vector2() },
        uMouse: { value: new THREE.Vector2() },
        uMouseInfluence: { value: mouseInfluence },
        uColor: { value: hexToVec3(color) },
        uColorTwo: { value: hexToVec3(colorTwo) },
        uRingCount: { value: ringCount },
        uSpeed: { value: speed },
        uAttenuation: { value: attenuation },
        uLineThickness: { value: lineThickness },
        uBaseRadius: { value: baseRadius },
        uRadiusStep: { value: radiusStep },
        uScaleRate: { value: scaleRate },
        uOpacity: { value: opacity },
        uNoiseAmount: { value: noiseAmount },
        uRotation: { value: rotation },
        uRingGap: { value: ringGap },
        uFadeIn: { value: fadeIn },
        uFadeOut: { value: fadeOut },
        uHoverAmount: { value: 0 },
        uHoverScale: { value: hoverScale },
        uParallax: { value: parallax },
        uBurst: { value: 0 },
      },
      transparent: true,
      depthWrite: false,
    });

    const mesh = new THREE.Mesh(geometry, material);
    scene.add(mesh);

    mount.appendChild(renderer.domElement);
    renderer.domElement.style.width = '100%';
    renderer.domElement.style.height = '100%';
    renderer.domElement.style.display = 'block';

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        renderer.setSize(width, height);
        material.uniforms.uResolution.value.set(width * dpr, height * dpr);
      }
    });
    resizeObserver.observe(mount);

    const handleMouseMove = (e: MouseEvent) => {
      const rect = mount.getBoundingClientRect();
      mouseRef.current.x = ((e.clientX - rect.left) / rect.width - 0.5) * 2;
      mouseRef.current.y = -((e.clientY - rect.top) / rect.height - 0.5) * 2;
    };

    const handleMouseEnter = () => {
      isHoveredRef.current = true;
    };

    const handleMouseLeave = () => {
      isHoveredRef.current = false;
    };

    const handleClick = () => {
      if (propsRef.current.clickBurst) {
        burstRef.current = 1.0;
      }
    };

    mount.addEventListener('mousemove', handleMouseMove);
    mount.addEventListener('mouseenter', handleMouseEnter);
    mount.addEventListener('mouseleave', handleMouseLeave);
    mount.addEventListener('click', handleClick);

    let animationId: number;
    const animate = (time: number) => {
      animationId = requestAnimationFrame(animate);

      const t = time * 0.001 * propsRef.current.speed;
      material.uniforms.uTime.value = t;

      smoothMouseRef.current.x += (mouseRef.current.x - smoothMouseRef.current.x) * 0.08;
      smoothMouseRef.current.y += (mouseRef.current.y - smoothMouseRef.current.y) * 0.08;

      if (propsRef.current.followMouse) {
        material.uniforms.uMouse.value.set(
          smoothMouseRef.current.x,
          smoothMouseRef.current.y
        );
      }

      const targetHover = isHoveredRef.current ? 1.0 : 0.0;
      hoverAmountRef.current += (targetHover - hoverAmountRef.current) * 0.08;
      material.uniforms.uHoverAmount.value = hoverAmountRef.current;

      burstRef.current *= 0.95;
      material.uniforms.uBurst.value = burstRef.current;

      material.uniforms.uColor.value = hexToVec3(propsRef.current.color);
      material.uniforms.uColorTwo.value = hexToVec3(propsRef.current.colorTwo);
      material.uniforms.uRingCount.value = propsRef.current.ringCount;
      material.uniforms.uAttenuation.value = propsRef.current.attenuation;
      material.uniforms.uLineThickness.value = propsRef.current.lineThickness;
      material.uniforms.uBaseRadius.value = propsRef.current.baseRadius;
      material.uniforms.uRadiusStep.value = propsRef.current.radiusStep;
      material.uniforms.uScaleRate.value = propsRef.current.scaleRate;
      material.uniforms.uOpacity.value = propsRef.current.opacity;
      material.uniforms.uNoiseAmount.value = propsRef.current.noiseAmount;
      material.uniforms.uRotation.value = propsRef.current.rotation;
      material.uniforms.uRingGap.value = propsRef.current.ringGap;
      material.uniforms.uFadeIn.value = propsRef.current.fadeIn;
      material.uniforms.uFadeOut.value = propsRef.current.fadeOut;
      material.uniforms.uMouseInfluence.value = propsRef.current.mouseInfluence;
      material.uniforms.uHoverScale.value = propsRef.current.hoverScale;
      material.uniforms.uParallax.value = propsRef.current.parallax;

      renderer.render(scene, camera);
    };

    animationId = requestAnimationFrame(animate);

    return () => {
      cancelAnimationFrame(animationId);
      resizeObserver.disconnect();
      mount.removeEventListener('mousemove', handleMouseMove);
      mount.removeEventListener('mouseenter', handleMouseEnter);
      mount.removeEventListener('mouseleave', handleMouseLeave);
      mount.removeEventListener('click', handleClick);
      geometry.dispose();
      material.dispose();
      renderer.dispose();
      if (mount.contains(renderer.domElement)) {
        mount.removeChild(renderer.domElement);
      }
    };
  }, []);

  return (
    <div
      ref={mountRef}
      className="magic-rings-container"
      style={blur > 0 ? { filter: `blur(${blur}px)` } : undefined}
    />
  );
};

export default MagicRings;
