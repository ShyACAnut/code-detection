import React, { useEffect, useRef } from 'react';

const AuroraBackground: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationId: number;
    let time = 0;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };

    const colorStops = [
      { r: 30, g: 27, b: 75 },    // #1e1b4b
      { r: 49, g: 46, b: 129 },   // #312e81
      { r: 76, g: 29, b: 149 },   // #4c1d95
      { r: 30, g: 58, b: 138 },   // #1e3a8a
    ];

    const blobs = [
      { x: 0.3, y: 0.4, radius: 0.5, color: 0, speed: 0.0003, phase: 0 },
      { x: 0.7, y: 0.6, radius: 0.4, color: 1, speed: 0.00025, phase: Math.PI * 0.5 },
      { x: 0.5, y: 0.3, radius: 0.45, color: 2, speed: 0.00035, phase: Math.PI },
      { x: 0.2, y: 0.7, radius: 0.35, color: 3, speed: 0.0002, phase: Math.PI * 1.5 },
    ];

    const draw = () => {
      if (!ctx || !canvas) return;

      const w = canvas.width;
      const h = canvas.height;

      // 深色背景底色
      ctx.fillStyle = '#0a0a1a';
      ctx.fillRect(0, 0, w, h);

      // 绘制每个极光色块
      blobs.forEach((blob) => {
        const cx = w * (blob.x + Math.sin(time * blob.speed + blob.phase) * 0.15);
        const cy = h * (blob.y + Math.cos(time * blob.speed * 0.7 + blob.phase) * 0.1);
        const r = Math.min(w, h) * blob.radius;

        const color = colorStops[blob.color];

        const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
        gradient.addColorStop(0, `rgba(${color.r}, ${color.g}, ${color.b}, 0.35)`);
        gradient.addColorStop(0.5, `rgba(${color.r}, ${color.g}, ${color.b}, 0.15)`);
        gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');

        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, w, h);
      });

      // 叠加一层微妙的噪点纹理
      const imageData = ctx.getImageData(0, 0, w, h);
      const data = imageData.data;
      for (let i = 0; i < data.length; i += 16) {
        const noise = (Math.random() - 0.5) * 4;
        data[i] = Math.min(255, Math.max(0, data[i] + noise));
        data[i + 1] = Math.min(255, Math.max(0, data[i + 1] + noise));
        data[i + 2] = Math.min(255, Math.max(0, data[i + 2] + noise));
      }
      ctx.putImageData(imageData, 0, 0);

      time += 1;
      animationId = requestAnimationFrame(draw);
    };

    resize();
    window.addEventListener('resize', resize);
    animationId = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        zIndex: 0,
        pointerEvents: 'none',
      }}
    />
  );
};

export default AuroraBackground;
