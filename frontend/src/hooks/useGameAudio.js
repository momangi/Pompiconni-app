/**
 * 🎧 GAME AUDIO MANAGER - Minimal & Elegant
 * 
 * Centralized audio system for Bolle Magiche game.
 * Uses Web Audio API for lightweight synthesized sounds.
 * 
 * Features:
 * - Single AudioContext (initialized on first user interaction)
 * - Mute state persisted in localStorage
 * - Debounced high-frequency sounds
 * - Mobile/autoplay policy compliant
 */

import { useCallback, useEffect, useRef, useState } from 'react';

// ============================================
// 🎵 SOUND CONFIGURATION
// ============================================
const SOUND_CONFIG = {
  shoot: {
    frequency: 400,
    type: 'sine',
    duration: 0.12,
    volume: 0.15,
    decay: 0.1,
    pitchSlide: -200, // Slide down for whoosh effect
  },
  pop: {
    frequency: 800,
    type: 'sine',
    duration: 0.15,
    volume: 0.25,
    decay: 0.12,
    pitchSlide: 400, // Slide up for pop effect
  },
  bounce: {
    frequency: 300,
    type: 'triangle',
    duration: 0.05,
    volume: 0.1,
    decay: 0.05,
    pitchSlide: 0,
  },
  miss: {
    frequency: 150,
    type: 'sine',
    duration: 0.2,
    volume: 0.12,
    decay: 0.18,
    pitchSlide: -50, // Slight slide down for thud
  },
};

// Debounce times (ms) to prevent sound spam
const DEBOUNCE_TIMES = {
  shoot: 50,
  pop: 30,
  bounce: 100,
  miss: 200,
};

// LocalStorage key for mute state
const MUTE_STORAGE_KEY = 'bollemagiche_audio_muted';

/**
 * Custom hook for game audio management
 */
export const useGameAudio = () => {
  const audioContextRef = useRef(null);
  const lastPlayTimeRef = useRef({});
  const isInitializedRef = useRef(false);
  
  // Load mute state from localStorage
  const [isMuted, setIsMuted] = useState(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(MUTE_STORAGE_KEY);
      return stored === 'true';
    }
    return false;
  });

  // ============================================
  // 🔧 INITIALIZE AUDIO CONTEXT
  // Called on first user interaction
  // ============================================
  const initAudio = useCallback(() => {
    if (isInitializedRef.current) return;
    
    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      audioContextRef.current = new AudioContext();
      isInitializedRef.current = true;
      
      // Resume if suspended (for autoplay policy)
      if (audioContextRef.current.state === 'suspended') {
        audioContextRef.current.resume();
      }
    } catch (error) {
      console.warn('Audio initialization failed:', error);
    }
  }, []);

  // ============================================
  // 🔊 PLAY SYNTHESIZED SOUND
  // ============================================
  const playSound = useCallback((soundName) => {
    // Skip if muted or not initialized
    if (isMuted || !audioContextRef.current) return;
    
    const config = SOUND_CONFIG[soundName];
    if (!config) return;
    
    // Debounce check
    const now = Date.now();
    const lastPlay = lastPlayTimeRef.current[soundName] || 0;
    const debounceTime = DEBOUNCE_TIMES[soundName] || 50;
    
    if (now - lastPlay < debounceTime) return;
    lastPlayTimeRef.current[soundName] = now;
    
    try {
      const ctx = audioContextRef.current;
      const currentTime = ctx.currentTime;
      
      // Create oscillator
      const oscillator = ctx.createOscillator();
      oscillator.type = config.type;
      oscillator.frequency.setValueAtTime(config.frequency, currentTime);
      
      // Apply pitch slide if configured
      if (config.pitchSlide !== 0) {
        oscillator.frequency.linearRampToValueAtTime(
          config.frequency + config.pitchSlide,
          currentTime + config.duration
        );
      }
      
      // Create gain node for volume envelope
      const gainNode = ctx.createGain();
      gainNode.gain.setValueAtTime(config.volume, currentTime);
      gainNode.gain.exponentialRampToValueAtTime(
        0.001,
        currentTime + config.duration
      );
      
      // Connect and play
      oscillator.connect(gainNode);
      gainNode.connect(ctx.destination);
      
      oscillator.start(currentTime);
      oscillator.stop(currentTime + config.duration + 0.01);
      
    } catch (error) {
      // Silent fail - don't break the game
    }
  }, [isMuted]);

  // ============================================
  // 🎵 INDIVIDUAL SOUND METHODS
  // ============================================
  const playShoot = useCallback(() => {
    playSound('shoot');
  }, [playSound]);

  const playPop = useCallback((comboMultiplier = 1) => {
    // Slightly increase volume for combos
    if (comboMultiplier > 1 && audioContextRef.current && !isMuted) {
      const config = { ...SOUND_CONFIG.pop };
      config.volume = Math.min(0.35, config.volume * (1 + comboMultiplier * 0.1));
      
      // Play with modified config
      try {
        const ctx = audioContextRef.current;
        const currentTime = ctx.currentTime;
        
        const oscillator = ctx.createOscillator();
        oscillator.type = config.type;
        oscillator.frequency.setValueAtTime(config.frequency, currentTime);
        oscillator.frequency.linearRampToValueAtTime(
          config.frequency + config.pitchSlide,
          currentTime + config.duration
        );
        
        const gainNode = ctx.createGain();
        gainNode.gain.setValueAtTime(config.volume, currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.001, currentTime + config.duration);
        
        oscillator.connect(gainNode);
        gainNode.connect(ctx.destination);
        oscillator.start(currentTime);
        oscillator.stop(currentTime + config.duration + 0.01);
      } catch (e) {
        // Silent fail
      }
    } else {
      playSound('pop');
    }
  }, [playSound, isMuted]);

  const playBounce = useCallback(() => {
    playSound('bounce');
  }, [playSound]);

  const playMiss = useCallback(() => {
    playSound('miss');
  }, [playSound]);

  // ============================================
  // 🔇 MUTE TOGGLE
  // ============================================
  const toggleMute = useCallback(() => {
    setIsMuted(prev => {
      const newValue = !prev;
      localStorage.setItem(MUTE_STORAGE_KEY, String(newValue));
      return newValue;
    });
  }, []);

  // ============================================
  // 🧹 CLEANUP
  // ============================================
  useEffect(() => {
    return () => {
      if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
        audioContextRef.current.close();
      }
    };
  }, []);

  return {
    // State
    isMuted,
    
    // Methods
    initAudio,
    toggleMute,
    
    // Sound triggers
    playShoot,
    playPop,
    playBounce,
    playMiss,
  };
};

export default useGameAudio;
