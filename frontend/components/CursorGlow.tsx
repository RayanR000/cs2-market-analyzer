'use client';

import { useEffect, useState, useRef, useSyncExternalStore } from 'react';
import { motion, useSpring, useMotionValue } from 'framer-motion';

function useReducedMotion() {
  return useSyncExternalStore(
    (callback) => {
      const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
      mq.addEventListener('change', callback);
      return () => mq.removeEventListener('change', callback);
    },
    () => window.matchMedia('(prefers-reduced-motion: reduce)').matches,
    () => true,
  );
}

export default function CursorGlow() {
  const [visible, setVisible] = useState(false);
  const reducedMotion = useReducedMotion();
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const springConfig = { damping: 25, stiffness: 120, mass: 0.5 };
  const glowX = useSpring(mouseX, springConfig);
  const glowY = useSpring(mouseY, springConfig);
  const rafRef = useRef<number>(0);
  const visibleRef = useRef(false);

  useEffect(() => {
    const isTouchDevice = window.matchMedia('(pointer: coarse)').matches || navigator.maxTouchPoints > 0;
    if (isTouchDevice) return;

    const handleMouseMove = (e: MouseEvent) => {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(() => {
        mouseX.set(e.clientX);
        mouseY.set(e.clientY);
        if (!visibleRef.current) {
          visibleRef.current = true;
          setVisible(true);
        }
      });
    };

    const handleMouseLeave = () => { visibleRef.current = false; setVisible(false); };
    const handleMouseEnter = () => { visibleRef.current = true; setVisible(true); };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    document.addEventListener('mouseleave', handleMouseLeave);
    document.addEventListener('mouseenter', handleMouseEnter);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseleave', handleMouseLeave);
      document.removeEventListener('mouseenter', handleMouseEnter);
      cancelAnimationFrame(rafRef.current);
    };
  }, [mouseX, mouseY]);

  if (reducedMotion) return null;

  return (
    <motion.div
      aria-hidden
      style={{
        x: glowX,
        y: glowY,
        translateX: '-50%',
        translateY: '-50%',
      }}
      className="pointer-events-none fixed z-[999] h-[300px] w-[300px] rounded-full opacity-0"
      animate={{ opacity: visible ? 1 : 0 }}
      transition={{ duration: 0.3 }}
    >
      <div
        className="h-full w-full rounded-full"
        style={{
          background: `radial-gradient(circle, oklch(52% 0.12 var(--brand-hue) / 0.07) 0%, oklch(52% 0.12 var(--brand-hue) / 0.02) 40%, transparent 70%)`,
        }}
      />
    </motion.div>
  );
}
