import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';

export default function TacticalClock() {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const timeString = time.toLocaleTimeString('en-GB', {
    timeZone: 'Asia/Jerusalem',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  });

  const dateString = time.toLocaleDateString('en-GB', {
    timeZone: 'Asia/Jerusalem',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  }).replace(/\//g, '.');

  return (
    <motion.div
      className="tactical-clock"
      aria-label={`Jerusalem time ${dateString} ${timeString}`}
      initial={false}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="clock-date">{dateString}</div>
      <div className="clock-time">{timeString}</div>
    </motion.div>
  );
}
