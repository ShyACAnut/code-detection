import React, { useEffect, useRef } from 'react';
import '../styles/global.css';

interface CrackLine {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  opacity: number;
  width: number;
  glow: number;
}

interface IceShard {
  x: number;
  y: number;
  size: number;
  rotation: number;
  opacity: number;
  speed: number;
  drift: number;
}

const CrackedIce: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const cracksRef = useRef<CrackLine[]>([]);
  const shardsRef = useRef<IceShard[]>([]);
  const mouseRef = useRef({ x: 0, y: 0 });
  const frameRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
      generateCracks();
      generateShards();
    };

    const generateCracks = () => {
      const cracks: CrackLine[] = [];
      const w = canvas.width;
      const h = canvas.height;

      // 主裂缝从中心向外辐射
      const centerX = w * 0.5;
      const centerY = h * 0.45;
      const numMainCracks = 12;

      for (let i = 0; i < numMainCracks; i++) {
        const angle = (Math.PI * 2 * i) / numMainCracks + Math.random() * 0.3;
        const length = Math.min(w, h) * (0.3 + Math.random() * 0.4);
        const endX = centerX + Math.cos(angle) * length;
        const endY = centerY + Math.sin(angle) * length;

        // 主裂缝
        cracks.push({
          x1: centerX,
          y1: centerY,
          x2: endX,
          y2: endY,
          opacity: 0.15 + Math.random() * 0.25,
          width: 1 + Math.random() * 2,
          glow: 8 + Math.random() * 12,
        });

        // 分支裂缝
        const branches = 2 + Math.floor(Math.random() * 3);
        for (let b = 0; b < branches; b++) {
          const t = 0.3 + Math.random() * 0.5;
          const branchX = centerX + (endX - centerX) * t;
          const branchY = centerY + (endY - centerY) * t;
          const branchAngle = angle + (Math.random() - 0.5) * 1.2;
          const branchLen = length * (0.15 + Math.random() * 0.25);

          cracks.push({
            x1: branchX,
            y1: branchY,
            x2: branchX + Math.cos(branchAngle) * branchLen,
            y2: branchY + Math.sin(branchAngle) * branchLen,
            opacity: 0.08 + Math.random() * 0.15,
            width: 0.5 + Math.random() * 1,
            glow: 4 + Math.random() * 8,
          });
        }
      }

      // 随机细小裂缝
      for (let i = 0; i < 30; i++) {
        const x = Math.random() * w;
        const y = Math.random() * h;
        const angle = Math.random() * Math.PI * 2;
        const len = 30 + Math.random() * 100;

        cracks.push({
          x1: x,
          y1: y,
          x2: x + Math.cos(angle) * len,
          y2: y + Math.sin(angle) * len,
          opacity: 0.03 + Math.random() * 0.08,
          width: 0.3 + Math.random() * 0.7,
          glow: 2 + Math.random() * 5,
        });
      }

      cracksRef.current = cracks;
    };

    const generateShards = () => {
      const shards: IceShard[] = [];
      const w = canvas.width;
      const h = canvas.height;

      for (let i = 0; i < 20; i++) {
        shards.push({
          x: Math.random() * w,
          y: Math.random() * h,
          size: 2 + Math.random() * 6,
          rotation: Math.random() * Math.PI * 2,
          opacity: 0.1 + Math.random() * 0.3,
          speed: 0.2 + Math.random() * 0.5,
          drift: (Math.random() - 0.5) * 0.3,
        });
      }

      shardsRef.current = shards;
    };

    const handleMouseMove = (e: MouseEvent) => {
      mouseRef.current.x = e.clientX;
      mouseRef.current.y = e.clientY;
    };

    const draw = () => {
      if (!ctx || !canvas) return;

      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const time = Date.now() * 0.001;
      const mx = mouseRef.current.x;
      const my = mouseRef.current.y;

      // 绘制裂缝
      cracksRef.current.forEach((crack) => {
        const dx = (crack.x1 + crack.x2) / 2 - mx;
        const dy = (crack.y1 + crack.y2) / 2 - my;
        const dist = Math.sqrt(dx * dx + dy * dy);
        const mouseGlow = Math.max(0, 1 - dist / 200) * 0.3;
        const pulse = Math.sin(time * 2 + crack.x1 * 0.01) * 0.05;

        const finalOpacity = Math.min(1, crack.opacity + mouseGlow + pulse);

        // 发光效果
        ctx.shadowColor = 'rgba(165, 216, 243, 0.6)';
        ctx.shadowBlur = crack.glow + mouseGlow * 20;

        ctx.beginPath();
        ctx.moveTo(crack.x1, crack.y1);
        ctx.lineTo(crack.x2, crack.y2);
        ctx.strokeStyle = `rgba(200, 230, 255, ${finalOpacity})`;
        ctx.lineWidth = crack.width;
        ctx.lineCap = 'round';
        ctx.stroke();

        ctx.shadowBlur = 0;

        // 裂缝中心亮点
        if (crack.width > 1) {
          const midX = (crack.x1 + crack.x2) / 2;
          const midY = (crack.y1 + crack.y2) / 2;
          ctx.beginPath();
          ctx.arc(midX, midY, crack.width * 1.5, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(220, 240, 255, ${finalOpacity * 0.5})`;
          ctx.fill();
        }
      });

      // 绘制冰晶碎片
      shardsRef.current.forEach((shard) => {
        shard.y += shard.speed;
        shard.x += shard.drift;
        shard.rotation += 0.005;

        if (shard.y > canvas.height + 10) {
          shard.y = -10;
          shard.x = Math.random() * canvas.width;
        }

        const dx = shard.x - mx;
        const dy = shard.y - my;
        const dist = Math.sqrt(dx * dx + dy * dy);
        const mouseGlow = Math.max(0, 1 - dist / 150) * 0.4;

        ctx.save();
        ctx.translate(shard.x, shard.y);
        ctx.rotate(shard.rotation);

        // 六边形冰晶
        ctx.beginPath();
        for (let i = 0; i < 6; i++) {
          const angle = (Math.PI / 3) * i;
          const x = Math.cos(angle) * shard.size;
          const y = Math.sin(angle) * shard.size;
          if (i === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.closePath();

        const finalOpacity = Math.min(1, shard.opacity + mouseGlow);
        ctx.fillStyle = `rgba(180, 220, 255, ${finalOpacity * 0.3})`;
        ctx.strokeStyle = `rgba(200, 235, 255, ${finalOpacity * 0.6})`;
        ctx.lineWidth = 0.5;
        ctx.fill();
        ctx.stroke();

        ctx.restore();
      });

      frameRef.current = requestAnimationFrame(draw);
    };

    resize();
    window.addEventListener('resize', resize);
    window.addEventListener('mousemove', handleMouseMove);
    frameRef.current = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(frameRef.current);
      window.removeEventListener('resize', resize);
      window.removeEventListener('mousemove', handleMouseMove);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="cracked-ice-canvas"
    />
  );
};

export default CrackedIce;
