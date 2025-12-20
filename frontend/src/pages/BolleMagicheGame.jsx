import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Pause, Play, Volume2, VolumeX, RotateCcw, Star } from 'lucide-react';
import { Button } from '../components/ui/button';

const BolleMagicheGame = () => {
  const [score, setScore] = useState(0);
  const [level, setLevel] = useState(1);
  const [isPaused, setIsPaused] = useState(false);
  const [isMuted, setIsMuted] = useState(true);
  const [bubbles, setBubbles] = useState([]);
  const [poppedBubbles, setPoppedBubbles] = useState([]);
  const [combo, setCombo] = useState(0);
  const [showCombo, setShowCombo] = useState(false);
  const gameRef = useRef(null);
  const animationRef = useRef(null);
  const lastTimeRef = useRef(0);

  // Generate initial bubbles
  const generateBubble = useCallback(() => {
    const colors = [
      { main: 'rgba(236, 72, 153, 0.25)', highlight: 'rgba(255, 182, 193, 0.6)' }, // Pink
      { main: 'rgba(147, 51, 234, 0.25)', highlight: 'rgba(216, 180, 254, 0.6)' }, // Purple
      { main: 'rgba(59, 130, 246, 0.25)', highlight: 'rgba(147, 197, 253, 0.6)' }, // Blue
      { main: 'rgba(16, 185, 129, 0.25)', highlight: 'rgba(110, 231, 183, 0.6)' }, // Green
      { main: 'rgba(245, 158, 11, 0.25)', highlight: 'rgba(252, 211, 77, 0.6)' }, // Amber
    ];
    const color = colors[Math.floor(Math.random() * colors.length)];
    const size = 50 + Math.random() * 40;
    
    return {
      id: Date.now() + Math.random(),
      x: 10 + Math.random() * 80,
      y: -15,
      size,
      color,
      speed: 0.3 + (level * 0.1) + Math.random() * 0.2,
      wobble: Math.random() * Math.PI * 2,
      wobbleSpeed: 0.02 + Math.random() * 0.02,
      wobbleAmount: 1 + Math.random() * 2,
    };
  }, [level]);

  // Initialize bubbles
  useEffect(() => {
    const initialBubbles = [];
    const bubbleCount = 8 + level * 2;
    for (let i = 0; i < bubbleCount; i++) {
      const bubble = generateBubble();
      bubble.y = Math.random() * 70;
      initialBubbles.push(bubble);
    }
    setBubbles(initialBubbles);
  }, [level, generateBubble]);

  // Game loop
  useEffect(() => {
    if (isPaused) return;

    const gameLoop = (timestamp) => {
      if (!lastTimeRef.current) lastTimeRef.current = timestamp;
      const delta = timestamp - lastTimeRef.current;
      
      if (delta > 16) { // ~60fps
        lastTimeRef.current = timestamp;
        
        setBubbles(prev => {
          let newBubbles = prev.map(bubble => ({
            ...bubble,
            y: bubble.y + bubble.speed,
            wobble: bubble.wobble + bubble.wobbleSpeed,
            x: bubble.x + Math.sin(bubble.wobble) * bubble.wobbleAmount * 0.1
          })).filter(b => b.y < 110);
          
          // Add new bubbles if needed
          const targetCount = 8 + level * 2;
          while (newBubbles.length < targetCount) {
            newBubbles.push(generateBubble());
          }
          
          return newBubbles;
        });
      }
      
      animationRef.current = requestAnimationFrame(gameLoop);
    };

    animationRef.current = requestAnimationFrame(gameLoop);
    
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isPaused, level, generateBubble]);

  // Pop bubble
  const popBubble = (bubble, e) => {
    e.stopPropagation();
    
    // Add to popped bubbles for animation
    setPoppedBubbles(prev => [...prev, { ...bubble, popTime: Date.now() }]);
    
    // Remove from active bubbles
    setBubbles(prev => prev.filter(b => b.id !== bubble.id));
    
    // Update score
    const points = Math.round(10 + (100 - bubble.size) / 10);
    setScore(prev => prev + points * (combo + 1));
    
    // Update combo
    setCombo(prev => prev + 1);
    setShowCombo(true);
    setTimeout(() => setShowCombo(false), 500);
    
    // Reset combo after delay
    setTimeout(() => setCombo(0), 1500);
  };

  // Clean up popped bubbles
  useEffect(() => {
    const cleanup = setInterval(() => {
      setPoppedBubbles(prev => prev.filter(b => Date.now() - b.popTime < 500));
    }, 100);
    return () => clearInterval(cleanup);
  }, []);

  // Level up
  useEffect(() => {
    if (score > 0 && score % 500 === 0) {
      setLevel(prev => Math.min(prev + 1, 10));
    }
  }, [score]);

  const resetGame = () => {
    setScore(0);
    setLevel(1);
    setCombo(0);
    setBubbles([]);
    setIsPaused(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-sky-100 via-pink-50 to-purple-100 relative overflow-hidden">
      {/* Header */}
      <div className="absolute top-0 left-0 right-0 z-20 p-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <Link to="/giochi/bolle-magiche" className="p-2 bg-white/80 backdrop-blur-sm rounded-full shadow-lg hover:bg-white transition-colors">
            <ArrowLeft className="w-6 h-6 text-gray-700" />
          </Link>
          
          <div className="flex items-center gap-3">
            {/* Level */}
            <div className="bg-white/80 backdrop-blur-sm rounded-full px-4 py-2 shadow-lg">
              <span className="text-sm font-bold text-purple-600">LV {level}</span>
            </div>
            
            {/* Score */}
            <div className="bg-white/80 backdrop-blur-sm rounded-full px-4 py-2 shadow-lg flex items-center gap-2">
              <Star className="w-4 h-4 text-amber-500 fill-amber-500" />
              <span className="text-sm font-bold text-gray-700">{score}</span>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsMuted(!isMuted)}
              className="p-2 bg-white/80 backdrop-blur-sm rounded-full shadow-lg hover:bg-white transition-colors"
            >
              {isMuted ? <VolumeX className="w-5 h-5 text-gray-500" /> : <Volume2 className="w-5 h-5 text-gray-700" />}
            </button>
            <button
              onClick={() => setIsPaused(!isPaused)}
              className="p-2 bg-white/80 backdrop-blur-sm rounded-full shadow-lg hover:bg-white transition-colors"
            >
              {isPaused ? <Play className="w-5 h-5 text-green-600" /> : <Pause className="w-5 h-5 text-gray-700" />}
            </button>
            <button
              onClick={resetGame}
              className="p-2 bg-white/80 backdrop-blur-sm rounded-full shadow-lg hover:bg-white transition-colors"
            >
              <RotateCcw className="w-5 h-5 text-gray-700" />
            </button>
          </div>
        </div>
      </div>

      {/* Combo Display */}
      {showCombo && combo > 1 && (
        <div className="absolute top-24 left-1/2 -translate-x-1/2 z-30 animate-combo-pop">
          <div className="bg-gradient-to-r from-amber-400 to-orange-500 text-white px-6 py-2 rounded-full font-bold text-xl shadow-lg">
            {combo}x COMBO! ✨
          </div>
        </div>
      )}

      {/* Game Area */}
      <div 
        ref={gameRef}
        className="absolute inset-0 pt-20 pb-32"
        style={{ touchAction: 'none' }}
      >
        {/* Active Bubbles */}
        {bubbles.map(bubble => (
          <div
            key={bubble.id}
            onClick={(e) => popBubble(bubble, e)}
            className="absolute cursor-pointer bubble-hover"
            style={{
              left: `${bubble.x}%`,
              top: `${bubble.y}%`,
              width: `${bubble.size}px`,
              height: `${bubble.size}px`,
              transform: 'translate(-50%, -50%)',
            }}
          >
            {/* Bubble Soap Effect */}
            <div
              className="w-full h-full rounded-full relative"
              style={{
                background: `
                  radial-gradient(circle at 30% 30%, ${bubble.color.highlight}, transparent 50%),
                  radial-gradient(circle at 70% 70%, rgba(255,255,255,0.1), transparent 40%),
                  radial-gradient(circle at 50% 50%, ${bubble.color.main}, transparent 70%)
                `,
                boxShadow: `
                  inset 0 0 ${bubble.size/3}px rgba(255,255,255,0.4),
                  inset ${bubble.size/10}px ${bubble.size/10}px ${bubble.size/4}px rgba(255,255,255,0.3),
                  0 0 ${bubble.size/4}px rgba(255,255,255,0.2),
                  0 ${bubble.size/10}px ${bubble.size/5}px rgba(0,0,0,0.05)
                `,
                border: '1px solid rgba(255,255,255,0.3)',
              }}
            >
              {/* Highlight reflection */}
              <div 
                className="absolute rounded-full"
                style={{
                  width: '30%',
                  height: '20%',
                  top: '15%',
                  left: '20%',
                  background: 'linear-gradient(135deg, rgba(255,255,255,0.8) 0%, transparent 100%)',
                  borderRadius: '50%',
                }}
              />
              {/* Secondary reflection */}
              <div 
                className="absolute rounded-full"
                style={{
                  width: '15%',
                  height: '10%',
                  bottom: '25%',
                  right: '20%',
                  background: 'rgba(255,255,255,0.3)',
                }}
              />
            </div>
          </div>
        ))}

        {/* Popped Bubbles Animation */}
        {poppedBubbles.map(bubble => (
          <div
            key={`pop-${bubble.id}`}
            className="absolute pointer-events-none animate-pop"
            style={{
              left: `${bubble.x}%`,
              top: `${bubble.y}%`,
              width: `${bubble.size}px`,
              height: `${bubble.size}px`,
              transform: 'translate(-50%, -50%)',
            }}
          >
            {/* Sparkles */}
            {[...Array(8)].map((_, i) => (
              <div
                key={i}
                className="absolute w-2 h-2 rounded-full animate-sparkle"
                style={{
                  left: '50%',
                  top: '50%',
                  background: bubble.color.highlight,
                  boxShadow: `0 0 6px ${bubble.color.highlight}`,
                  animationDelay: `${i * 0.05}s`,
                  '--angle': `${i * 45}deg`,
                }}
              />
            ))}
          </div>
        ))}
      </div>

      {/* Poppiconni Shooter (Placeholder) */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-10">
        <div className="w-24 h-24 bg-gradient-to-br from-pink-200 to-pink-300 rounded-full flex items-center justify-center shadow-xl border-4 border-white">
          <div className="text-center">
            <div className="text-3xl">🐘</div>
            <div className="text-xs font-bold text-pink-600 -mt-1">Poppi</div>
          </div>
        </div>
      </div>

      {/* Pause Overlay */}
      {isPaused && (
        <div className="absolute inset-0 bg-black/40 backdrop-blur-sm z-40 flex items-center justify-center">
          <div className="bg-white rounded-3xl p-8 shadow-2xl text-center max-w-sm mx-4">
            <h2 className="text-2xl font-bold text-gray-800 mb-4">Pausa</h2>
            <p className="text-gray-600 mb-6">Punteggio: {score}</p>
            <div className="space-y-3">
              <Button
                onClick={() => setIsPaused(false)}
                className="w-full bg-gradient-to-r from-pink-500 to-purple-500 hover:from-pink-600 hover:to-purple-600 rounded-xl py-5"
              >
                <Play className="w-5 h-5 mr-2" />
                Continua
              </Button>
              <Link to="/giochi/bolle-magiche">
                <Button variant="outline" className="w-full rounded-xl py-5">
                  Esci dal gioco
                </Button>
              </Link>
            </div>
          </div>
        </div>
      )}

      <style>{`
        .bubble-hover:hover {
          transform: translate(-50%, -50%) scale(1.1);
          transition: transform 0.15s ease-out;
        }
        
        @keyframes pop {
          0% { transform: translate(-50%, -50%) scale(1); opacity: 1; }
          100% { transform: translate(-50%, -50%) scale(1.5); opacity: 0; }
        }
        .animate-pop {
          animation: pop 0.3s ease-out forwards;
        }
        
        @keyframes sparkle {
          0% { transform: translate(-50%, -50%) rotate(var(--angle)) translateX(0); opacity: 1; }
          100% { transform: translate(-50%, -50%) rotate(var(--angle)) translateX(40px); opacity: 0; }
        }
        .animate-sparkle {
          animation: sparkle 0.4s ease-out forwards;
        }
        
        @keyframes combo-pop {
          0% { transform: translateX(-50%) scale(0.5); opacity: 0; }
          50% { transform: translateX(-50%) scale(1.2); }
          100% { transform: translateX(-50%) scale(1); opacity: 1; }
        }
        .animate-combo-pop {
          animation: combo-pop 0.3s ease-out;
        }
      `}</style>
    </div>
  );
};

export default BolleMagicheGame;
