import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Pause, Play, Volume2, VolumeX, RotateCcw, Star, Eye, EyeOff } from 'lucide-react';
import { Button } from '../components/ui/button';

// Constants
const BUBBLE_SIZE = 44;
const GRID_COLS = 11;
const GRID_ROWS = 12;
const COLORS = [
  { name: 'pink', main: 'rgba(236, 72, 153, 0.35)', highlight: 'rgba(255, 182, 193, 0.7)', solid: '#ec4899' },
  { name: 'purple', main: 'rgba(147, 51, 234, 0.35)', highlight: 'rgba(216, 180, 254, 0.7)', solid: '#9333ea' },
  { name: 'blue', main: 'rgba(59, 130, 246, 0.35)', highlight: 'rgba(147, 197, 253, 0.7)', solid: '#3b82f6' },
  { name: 'green', main: 'rgba(16, 185, 129, 0.35)', highlight: 'rgba(110, 231, 183, 0.7)', solid: '#10b981' },
  { name: 'amber', main: 'rgba(245, 158, 11, 0.35)', highlight: 'rgba(252, 211, 77, 0.7)', solid: '#f59e0b' },
];

const BolleMagicheGame = () => {
  // Game state
  const [grid, setGrid] = useState([]);
  const [currentBubble, setCurrentBubble] = useState(null);
  const [nextBubble, setNextBubble] = useState(null);
  const [shooterAngle, setShooterAngle] = useState(-90);
  const [isAiming, setIsAiming] = useState(false);
  const [isShooting, setShooting] = useState(false);
  const [bulletPos, setBulletPos] = useState(null);
  const [bulletVel, setBulletVel] = useState(null);
  
  // UI state
  const [score, setScore] = useState(0);
  const [level, setLevel] = useState(1);
  const [isPaused, setIsPaused] = useState(false);
  const [isMuted, setIsMuted] = useState(true);
  const [showTrajectory, setShowTrajectory] = useState(true);
  const [isVibrating, setIsVibrating] = useState(false);
  const [fallingBubbles, setFallingBubbles] = useState([]);
  const [poppingBubbles, setPoppingBubbles] = useState([]);
  const [gameOver, setGameOver] = useState(false);
  const [levelComplete, setLevelComplete] = useState(false);
  
  const gameRef = useRef(null);
  const animationRef = useRef(null);
  const dropTimerRef = useRef(null);
  
  // Get available colors based on level
  const getAvailableColors = useCallback(() => {
    const numColors = Math.min(2 + Math.floor(level / 2), COLORS.length);
    return COLORS.slice(0, numColors);
  }, [level]);
  
  // Generate random bubble color
  const getRandomColor = useCallback(() => {
    const colors = getAvailableColors();
    return colors[Math.floor(Math.random() * colors.length)];
  }, [getAvailableColors]);
  
  // Initialize grid for a level
  const initializeGrid = useCallback(() => {
    const newGrid = [];
    const rowsToFill = 3 + Math.min(level, 5); // More rows as level increases
    
    for (let row = 0; row < GRID_ROWS; row++) {
      const gridRow = [];
      const isOffsetRow = row % 2 === 1;
      const cols = isOffsetRow ? GRID_COLS - 1 : GRID_COLS;
      
      for (let col = 0; col < cols; col++) {
        if (row < rowsToFill) {
          gridRow.push({
            color: getRandomColor(),
            id: `${row}-${col}-${Date.now()}-${Math.random()}`
          });
        } else {
          gridRow.push(null);
        }
      }
      newGrid.push(gridRow);
    }
    
    return newGrid;
  }, [level, getRandomColor]);
  
  // Initialize game
  useEffect(() => {
    setGrid(initializeGrid());
    setCurrentBubble(getRandomColor());
    setNextBubble(getRandomColor());
    setScore(0);
    setGameOver(false);
    setLevelComplete(false);
  }, [level, initializeGrid, getRandomColor]);
  
  // Drop timer - add new row periodically
  useEffect(() => {
    if (isPaused || gameOver || levelComplete) return;
    
    const dropInterval = Math.max(15000 - (level * 1000), 8000); // 15s to 8s based on level
    
    dropTimerRef.current = setInterval(() => {
      addNewRow();
    }, dropInterval);
    
    return () => {
      if (dropTimerRef.current) clearInterval(dropTimerRef.current);
    };
  }, [isPaused, level, gameOver, levelComplete]);
  
  // Add new row from top
  const addNewRow = useCallback(() => {
    setGrid(prev => {
      const newGrid = [...prev];
      
      // Check if bottom row has bubbles (game over)
      if (newGrid[GRID_ROWS - 1].some(b => b !== null)) {
        setGameOver(true);
        return prev;
      }
      
      // Shift all rows down
      for (let row = GRID_ROWS - 1; row > 0; row--) {
        newGrid[row] = newGrid[row - 1];
      }
      
      // Add new top row
      const isOffsetRow = 0 % 2 === 1;
      const cols = isOffsetRow ? GRID_COLS - 1 : GRID_COLS;
      const newRow = [];
      for (let col = 0; col < cols; col++) {
        newRow.push({
          color: getRandomColor(),
          id: `new-${Date.now()}-${col}-${Math.random()}`
        });
      }
      newGrid[0] = newRow;
      
      return newGrid;
    });
  }, [getRandomColor]);
  
  // Get grid position from pixel coordinates
  const getGridPos = (x, y) => {
    const row = Math.floor(y / (BUBBLE_SIZE * 0.866));
    const isOffsetRow = row % 2 === 1;
    const offset = isOffsetRow ? BUBBLE_SIZE / 2 : 0;
    const col = Math.floor((x - offset) / BUBBLE_SIZE);
    return { row, col };
  };
  
  // Get pixel position from grid coordinates
  const getPixelPos = (row, col) => {
    const isOffsetRow = row % 2 === 1;
    const offset = isOffsetRow ? BUBBLE_SIZE / 2 : 0;
    const x = col * BUBBLE_SIZE + offset + BUBBLE_SIZE / 2;
    const y = row * (BUBBLE_SIZE * 0.866) + BUBBLE_SIZE / 2;
    return { x, y };
  };
  
  // Find connected bubbles of same color
  const findConnected = (startRow, startCol, targetColor, visited = new Set()) => {
    const key = `${startRow}-${startCol}`;
    if (visited.has(key)) return [];
    
    if (startRow < 0 || startRow >= GRID_ROWS) return [];
    const isOffsetRow = startRow % 2 === 1;
    const maxCol = isOffsetRow ? GRID_COLS - 1 : GRID_COLS;
    if (startCol < 0 || startCol >= maxCol) return [];
    
    const bubble = grid[startRow]?.[startCol];
    if (!bubble || bubble.color.name !== targetColor.name) return [];
    
    visited.add(key);
    const connected = [{ row: startRow, col: startCol }];
    
    // Get neighbors (hexagonal grid)
    const neighbors = getNeighbors(startRow, startCol);
    for (const { row, col } of neighbors) {
      connected.push(...findConnected(row, col, targetColor, visited));
    }
    
    return connected;
  };
  
  // Get neighbor positions in hexagonal grid
  const getNeighbors = (row, col) => {
    const isOffsetRow = row % 2 === 1;
    const neighbors = [];
    
    // Same row
    neighbors.push({ row, col: col - 1 });
    neighbors.push({ row, col: col + 1 });
    
    // Row above
    if (isOffsetRow) {
      neighbors.push({ row: row - 1, col });
      neighbors.push({ row: row - 1, col: col + 1 });
    } else {
      neighbors.push({ row: row - 1, col: col - 1 });
      neighbors.push({ row: row - 1, col });
    }
    
    // Row below
    if (isOffsetRow) {
      neighbors.push({ row: row + 1, col });
      neighbors.push({ row: row + 1, col: col + 1 });
    } else {
      neighbors.push({ row: row + 1, col: col - 1 });
      neighbors.push({ row: row + 1, col });
    }
    
    return neighbors.filter(({ row: r, col: c }) => {
      if (r < 0 || r >= GRID_ROWS) return false;
      const maxCol = r % 2 === 1 ? GRID_COLS - 1 : GRID_COLS;
      return c >= 0 && c < maxCol;
    });
  };
  
  // Find floating bubbles (not connected to top)
  const findFloating = () => {
    const visited = new Set();
    const connected = new Set();
    
    // BFS from top row
    const queue = [];
    const firstRow = grid[0];
    firstRow.forEach((bubble, col) => {
      if (bubble) {
        queue.push({ row: 0, col });
        connected.add(`0-${col}`);
      }
    });
    
    while (queue.length > 0) {
      const { row, col } = queue.shift();
      const key = `${row}-${col}`;
      if (visited.has(key)) continue;
      visited.add(key);
      
      const neighbors = getNeighbors(row, col);
      for (const { row: nr, col: nc } of neighbors) {
        const nKey = `${nr}-${nc}`;
        if (!visited.has(nKey) && grid[nr]?.[nc]) {
          connected.add(nKey);
          queue.push({ row: nr, col: nc });
        }
      }
    }
    
    // Find all bubbles not in connected set
    const floating = [];
    grid.forEach((row, rowIdx) => {
      row.forEach((bubble, colIdx) => {
        if (bubble && !connected.has(`${rowIdx}-${colIdx}`)) {
          floating.push({ row: rowIdx, col: colIdx, bubble });
        }
      });
    });
    
    return floating;
  };
  
  // Pop bubbles and handle chain reactions
  const popBubbles = (bubblesToPop) => {
    if (bubblesToPop.length < 3) return false;
    
    // Add to popping animation
    const poppingData = bubblesToPop.map(({ row, col }) => ({
      ...getPixelPos(row, col),
      color: grid[row][col].color,
      id: grid[row][col].id
    }));
    setPoppingBubbles(poppingData);
    
    // Remove from grid
    setGrid(prev => {
      const newGrid = prev.map(row => [...row]);
      bubblesToPop.forEach(({ row, col }) => {
        newGrid[row][col] = null;
      });
      return newGrid;
    });
    
    // Update score
    setScore(prev => prev + bubblesToPop.length * 10);
    
    // Trigger vibration effect
    setIsVibrating(true);
    setTimeout(() => setIsVibrating(false), 800);
    
    // Clear popping animation after delay
    setTimeout(() => {
      setPoppingBubbles([]);
      
      // Check for floating bubbles
      setTimeout(() => {
        const floating = findFloating();
        if (floating.length > 0) {
          // Add floating bubbles to falling animation
          const fallingData = floating.map(({ row, col, bubble }) => ({
            ...getPixelPos(row, col),
            color: bubble.color,
            id: bubble.id
          }));
          setFallingBubbles(fallingData);
          
          // Remove from grid
          setGrid(prev => {
            const newGrid = prev.map(row => [...row]);
            floating.forEach(({ row, col }) => {
              newGrid[row][col] = null;
            });
            return newGrid;
          });
          
          // Bonus score for falling bubbles
          setScore(prev => prev + floating.length * 20);
          
          // Clear falling animation
          setTimeout(() => {
            setFallingBubbles([]);
            checkLevelComplete();
          }, 600);
        } else {
          checkLevelComplete();
        }
      }, 100);
    }, 300);
    
    return true;
  };
  
  // Check if level is complete
  const checkLevelComplete = () => {
    setGrid(prev => {
      const hasAnyBubble = prev.some(row => row.some(b => b !== null));
      if (!hasAnyBubble) {
        setLevelComplete(true);
      }
      return prev;
    });
  };
  
  // Attach bubble to grid
  const attachBubble = (row, col, color) => {
    // Clamp to valid position
    const isOffsetRow = row % 2 === 1;
    const maxCol = isOffsetRow ? GRID_COLS - 1 : GRID_COLS;
    const clampedCol = Math.max(0, Math.min(col, maxCol - 1));
    const clampedRow = Math.max(0, Math.min(row, GRID_ROWS - 1));
    
    // Find empty spot near target
    let targetRow = clampedRow;
    let targetCol = clampedCol;
    
    // If spot is occupied, find nearest empty
    if (grid[targetRow]?.[targetCol]) {
      const neighbors = getNeighbors(targetRow, targetCol);
      for (const { row: nr, col: nc } of neighbors) {
        if (nr >= 0 && nr < GRID_ROWS && !grid[nr]?.[nc]) {
          targetRow = nr;
          targetCol = nc;
          break;
        }
      }
    }
    
    // Add bubble to grid
    setGrid(prev => {
      const newGrid = prev.map(row => [...row]);
      if (!newGrid[targetRow][targetCol]) {
        newGrid[targetRow][targetCol] = {
          color,
          id: `placed-${Date.now()}-${Math.random()}`
        };
      }
      return newGrid;
    });
    
    // Check for matches
    setTimeout(() => {
      const connected = findConnected(targetRow, targetCol, color);
      if (connected.length >= 3) {
        popBubbles(connected);
      } else {
        checkLevelComplete();
      }
    }, 50);
    
    // Next bubble
    setCurrentBubble(nextBubble);
    setNextBubble(getRandomColor());
    setShooting(false);
    setBulletPos(null);
    setBulletVel(null);
  };
  
  // Calculate trajectory for preview
  const calculateTrajectory = useCallback((angle, startX, startY) => {
    const points = [];
    const speed = 15;
    let x = startX;
    let y = startY;
    let vx = Math.cos(angle * Math.PI / 180) * speed;
    let vy = Math.sin(angle * Math.PI / 180) * speed;
    
    const gameWidth = GRID_COLS * BUBBLE_SIZE;
    
    for (let i = 0; i < 50; i++) {
      points.push({ x, y });
      x += vx;
      y += vy;
      
      // Wall bounce
      if (x < BUBBLE_SIZE / 2) {
        x = BUBBLE_SIZE / 2;
        vx = -vx;
      } else if (x > gameWidth - BUBBLE_SIZE / 2) {
        x = gameWidth - BUBBLE_SIZE / 2;
        vx = -vx;
      }
      
      // Stop at top or collision
      if (y < BUBBLE_SIZE / 2) break;
      
      // Check collision with grid
      const { row, col } = getGridPos(x, y);
      if (row >= 0 && row < GRID_ROWS && grid[row]?.[col]) {
        break;
      }
    }
    
    return points;
  }, [grid]);
  
  // Handle mouse move for aiming
  const handleMouseMove = useCallback((e) => {
    if (isShooting || isPaused || gameOver || levelComplete) return;
    
    const rect = gameRef.current?.getBoundingClientRect();
    if (!rect) return;
    
    const gameWidth = GRID_COLS * BUBBLE_SIZE;
    const shooterX = gameWidth / 2;
    const shooterY = GRID_ROWS * BUBBLE_SIZE * 0.866 + 60;
    
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    
    const dx = mouseX - shooterX;
    const dy = mouseY - shooterY;
    
    let angle = Math.atan2(dy, dx) * 180 / Math.PI;
    // Clamp angle to -160 to -20 degrees (mostly upward)
    angle = Math.max(-160, Math.min(-20, angle));
    
    setShooterAngle(angle);
    setIsAiming(true);
  }, [isShooting, isPaused, gameOver, levelComplete]);
  
  // Handle click to shoot
  const handleClick = useCallback(() => {
    if (isShooting || isPaused || !currentBubble || gameOver || levelComplete) return;
    
    const gameWidth = GRID_COLS * BUBBLE_SIZE;
    const shooterX = gameWidth / 2;
    const shooterY = GRID_ROWS * BUBBLE_SIZE * 0.866 + 40;
    
    const speed = 18;
    const vx = Math.cos(shooterAngle * Math.PI / 180) * speed;
    const vy = Math.sin(shooterAngle * Math.PI / 180) * speed;
    
    setBulletPos({ x: shooterX, y: shooterY });
    setBulletVel({ vx, vy });
    setShooting(true);
  }, [isShooting, isPaused, currentBubble, shooterAngle, gameOver, levelComplete]);
  
  // Bullet animation loop
  useEffect(() => {
    if (!isShooting || !bulletPos || !bulletVel) return;
    
    const gameWidth = GRID_COLS * BUBBLE_SIZE;
    const gameHeight = GRID_ROWS * BUBBLE_SIZE * 0.866;
    
    const animate = () => {
      setBulletPos(prev => {
        if (!prev) return null;
        
        let newX = prev.x + bulletVel.vx;
        let newY = prev.y + bulletVel.vy;
        let newVx = bulletVel.vx;
        
        // Wall bounce
        if (newX < BUBBLE_SIZE / 2) {
          newX = BUBBLE_SIZE / 2;
          newVx = -newVx;
          setBulletVel(v => ({ ...v, vx: -v.vx }));
        } else if (newX > gameWidth - BUBBLE_SIZE / 2) {
          newX = gameWidth - BUBBLE_SIZE / 2;
          newVx = -newVx;
          setBulletVel(v => ({ ...v, vx: -v.vx }));
        }
        
        // Top collision
        if (newY < BUBBLE_SIZE / 2) {
          const { row, col } = getGridPos(newX, BUBBLE_SIZE / 2);
          attachBubble(0, col, currentBubble);
          return null;
        }
        
        // Grid collision
        const { row, col } = getGridPos(newX, newY);
        if (row >= 0 && row < GRID_ROWS) {
          const isOffsetRow = row % 2 === 1;
          const maxCol = isOffsetRow ? GRID_COLS - 1 : GRID_COLS;
          if (col >= 0 && col < maxCol && grid[row]?.[col]) {
            // Find attachment point
            const attachRow = row + 1;
            const attachCol = col;
            attachBubble(attachRow, attachCol, currentBubble);
            return null;
          }
        }
        
        return { x: newX, y: newY };
      });
      
      animationRef.current = requestAnimationFrame(animate);
    };
    
    animationRef.current = requestAnimationFrame(animate);
    
    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
    };
  }, [isShooting, bulletVel, currentBubble, grid]);
  
  // Next level
  const nextLevel = () => {
    setLevel(prev => prev + 1);
    setLevelComplete(false);
  };
  
  // Reset game
  const resetGame = () => {
    setLevel(1);
    setScore(0);
    setGameOver(false);
    setLevelComplete(false);
    setGrid(initializeGrid());
    setCurrentBubble(getRandomColor());
    setNextBubble(getRandomColor());
    setShooting(false);
    setBulletPos(null);
  };
  
  // Render bubble
  const renderBubble = (color, x, y, size = BUBBLE_SIZE, isVibrating = false, key) => (
    <div
      key={key}
      className={`absolute rounded-full ${isVibrating ? 'animate-vibrate' : ''}`}
      style={{
        left: x - size / 2,
        top: y - size / 2,
        width: size,
        height: size,
        background: `
          radial-gradient(circle at 30% 30%, ${color.highlight}, transparent 50%),
          radial-gradient(circle at 70% 70%, rgba(255,255,255,0.15), transparent 40%),
          radial-gradient(circle at 50% 50%, ${color.main}, transparent 70%),
          ${color.solid}22
        `,
        boxShadow: `
          inset 0 0 ${size/3}px rgba(255,255,255,0.5),
          inset ${size/10}px ${size/10}px ${size/4}px rgba(255,255,255,0.4),
          0 0 ${size/4}px rgba(255,255,255,0.3)
        `,
        border: '1px solid rgba(255,255,255,0.4)',
      }}
    >
      {/* Highlight */}
      <div 
        className="absolute rounded-full"
        style={{
          width: '35%',
          height: '25%',
          top: '12%',
          left: '18%',
          background: 'linear-gradient(135deg, rgba(255,255,255,0.9) 0%, transparent 100%)',
        }}
      />
    </div>
  );
  
  const gameWidth = GRID_COLS * BUBBLE_SIZE;
  const gameHeight = GRID_ROWS * BUBBLE_SIZE * 0.866 + 120;
  const shooterX = gameWidth / 2;
  const shooterY = GRID_ROWS * BUBBLE_SIZE * 0.866 + 60;
  
  return (
    <div className="min-h-screen bg-gradient-to-b from-sky-100 via-pink-50 to-purple-100 flex flex-col items-center">
      {/* Header */}
      <div className="w-full max-w-lg px-4 py-3">
        <div className="flex items-center justify-between">
          <Link to="/giochi/bolle-magiche" className="p-2 bg-white/80 backdrop-blur-sm rounded-full shadow-lg hover:bg-white transition-colors">
            <ArrowLeft className="w-5 h-5 text-gray-700" />
          </Link>
          
          <div className="flex items-center gap-2">
            <div className="bg-white/80 backdrop-blur-sm rounded-full px-3 py-1.5 shadow-lg">
              <span className="text-sm font-bold text-purple-600">LV {level}</span>
            </div>
            <div className="bg-white/80 backdrop-blur-sm rounded-full px-3 py-1.5 shadow-lg flex items-center gap-1">
              <Star className="w-4 h-4 text-amber-500 fill-amber-500" />
              <span className="text-sm font-bold text-gray-700">{score}</span>
            </div>
          </div>
          
          <div className="flex items-center gap-1">
            <button
              onClick={() => setShowTrajectory(!showTrajectory)}
              className={`p-2 backdrop-blur-sm rounded-full shadow-lg transition-colors ${showTrajectory ? 'bg-purple-100' : 'bg-white/80'}`}
              title={showTrajectory ? "Nascondi traiettoria" : "Mostra traiettoria"}
            >
              {showTrajectory ? <Eye className="w-4 h-4 text-purple-600" /> : <EyeOff className="w-4 h-4 text-gray-500" />}
            </button>
            <button
              onClick={() => setIsMuted(!isMuted)}
              className="p-2 bg-white/80 backdrop-blur-sm rounded-full shadow-lg hover:bg-white transition-colors"
            >
              {isMuted ? <VolumeX className="w-4 h-4 text-gray-500" /> : <Volume2 className="w-4 h-4 text-gray-700" />}
            </button>
            <button
              onClick={() => setIsPaused(!isPaused)}
              className="p-2 bg-white/80 backdrop-blur-sm rounded-full shadow-lg hover:bg-white transition-colors"
            >
              {isPaused ? <Play className="w-4 h-4 text-green-600" /> : <Pause className="w-4 h-4 text-gray-700" />}
            </button>
            <button
              onClick={resetGame}
              className="p-2 bg-white/80 backdrop-blur-sm rounded-full shadow-lg hover:bg-white transition-colors"
            >
              <RotateCcw className="w-4 h-4 text-gray-700" />
            </button>
          </div>
        </div>
      </div>

      {/* Game Area */}
      <div 
        ref={gameRef}
        className="relative bg-white/30 backdrop-blur-sm rounded-3xl shadow-2xl overflow-hidden cursor-crosshair"
        style={{ width: gameWidth, height: gameHeight }}
        onMouseMove={handleMouseMove}
        onClick={handleClick}
      >
        {/* Grid bubbles */}
        {grid.map((row, rowIdx) => 
          row.map((bubble, colIdx) => {
            if (!bubble) return null;
            const { x, y } = getPixelPos(rowIdx, colIdx);
            return renderBubble(bubble.color, x, y, BUBBLE_SIZE, isVibrating, bubble.id);
          })
        )}
        
        {/* Popping bubbles animation */}
        {poppingBubbles.map((bubble) => (
          <div
            key={`pop-${bubble.id}`}
            className="absolute animate-pop pointer-events-none"
            style={{ left: bubble.x, top: bubble.y }}
          >
            {[...Array(8)].map((_, i) => (
              <div
                key={i}
                className="absolute w-2 h-2 rounded-full animate-sparkle"
                style={{
                  left: 0,
                  top: 0,
                  background: bubble.color.solid,
                  boxShadow: `0 0 6px ${bubble.color.solid}`,
                  '--angle': `${i * 45}deg`,
                }}
              />
            ))}
          </div>
        ))}
        
        {/* Falling bubbles animation */}
        {fallingBubbles.map((bubble) => (
          <div
            key={`fall-${bubble.id}`}
            className="absolute animate-fall pointer-events-none"
            style={{ left: bubble.x - BUBBLE_SIZE/2, top: bubble.y - BUBBLE_SIZE/2 }}
          >
            {renderBubble(bubble.color, BUBBLE_SIZE/2, BUBBLE_SIZE/2, BUBBLE_SIZE, false, `falling-${bubble.id}`)}
          </div>
        ))}
        
        {/* Trajectory preview */}
        {showTrajectory && isAiming && !isShooting && currentBubble && (
          <>
            {calculateTrajectory(shooterAngle, shooterX, shooterY - 20).map((point, i) => (
              <div
                key={i}
                className="absolute rounded-full bg-white/60"
                style={{
                  left: point.x - 3,
                  top: point.y - 3,
                  width: 6,
                  height: 6,
                  opacity: 1 - (i / 50) * 0.8
                }}
              />
            ))}
          </>
        )}
        
        {/* Shooting bubble */}
        {bulletPos && currentBubble && renderBubble(currentBubble, bulletPos.x, bulletPos.y, BUBBLE_SIZE, false, 'bullet')}
        
        {/* Shooter area */}
        <div 
          className="absolute bottom-0 left-0 right-0 h-28 bg-gradient-to-t from-pink-100/80 to-transparent"
        >
          {/* Shooter */}
          <div 
            className="absolute"
            style={{ 
              left: shooterX - 35, 
              top: 20,
              transform: `rotate(${shooterAngle + 90}deg)`,
              transformOrigin: '35px 35px'
            }}
          >
            {/* Cannon */}
            <div className="w-[70px] h-[70px] bg-gradient-to-br from-pink-200 to-pink-300 rounded-full flex items-center justify-center shadow-xl border-4 border-white relative">
              {/* Cannon barrel */}
              <div 
                className="absolute w-4 h-12 bg-gradient-to-b from-pink-300 to-pink-400 rounded-full"
                style={{ top: -30, left: '50%', transform: 'translateX(-50%)' }}
              />
              <div className="text-2xl">🐘</div>
            </div>
          </div>
          
          {/* Current bubble preview */}
          {currentBubble && !isShooting && (
            <div className="absolute" style={{ left: shooterX - BUBBLE_SIZE/2, top: 20 }}>
              {renderBubble(currentBubble, BUBBLE_SIZE/2, BUBBLE_SIZE/2, BUBBLE_SIZE, false, 'current')}
            </div>
          )}
          
          {/* Next bubble */}
          {nextBubble && (
            <div className="absolute flex flex-col items-center" style={{ left: shooterX + 60, top: 30 }}>
              <span className="text-xs text-gray-500 mb-1">Prossima</span>
              {renderBubble(nextBubble, 15, 15, 30, false, 'next')}
            </div>
          )}
        </div>
      </div>

      {/* Pause Overlay */}
      {isPaused && !gameOver && !levelComplete && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40 flex items-center justify-center">
          <div className="bg-white rounded-3xl p-8 shadow-2xl text-center max-w-sm mx-4">
            <h2 className="text-2xl font-bold text-gray-800 mb-2">Pausa</h2>
            <p className="text-gray-600 mb-6">Livello {level} • Punteggio: {score}</p>
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
      
      {/* Game Over Overlay */}
      {gameOver && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40 flex items-center justify-center">
          <div className="bg-white rounded-3xl p-8 shadow-2xl text-center max-w-sm mx-4">
            <h2 className="text-3xl font-bold text-gray-800 mb-2">Game Over</h2>
            <p className="text-gray-600 mb-2">Livello raggiunto: {level}</p>
            <p className="text-2xl font-bold text-purple-600 mb-6">Punteggio: {score}</p>
            <div className="space-y-3">
              <Button
                onClick={resetGame}
                className="w-full bg-gradient-to-r from-pink-500 to-purple-500 hover:from-pink-600 hover:to-purple-600 rounded-xl py-5"
              >
                <RotateCcw className="w-5 h-5 mr-2" />
                Gioca ancora
              </Button>
              <Link to="/giochi/bolle-magiche">
                <Button variant="outline" className="w-full rounded-xl py-5">
                  Torna al menu
                </Button>
              </Link>
            </div>
          </div>
        </div>
      )}
      
      {/* Level Complete Overlay */}
      {levelComplete && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40 flex items-center justify-center">
          <div className="bg-white rounded-3xl p-8 shadow-2xl text-center max-w-sm mx-4">
            <div className="text-5xl mb-4">🎉</div>
            <h2 className="text-3xl font-bold text-gray-800 mb-2">Livello Completato!</h2>
            <p className="text-gray-600 mb-2">Livello {level} superato</p>
            <p className="text-2xl font-bold text-purple-600 mb-6">Punteggio: {score}</p>
            <Button
              onClick={nextLevel}
              className="w-full bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600 rounded-xl py-5 text-lg"
            >
              Livello {level + 1} →
            </Button>
          </div>
        </div>
      )}

      <style>{`
        @keyframes vibrate {
          0%, 100% { transform: translate(0, 0); }
          20% { transform: translate(-2px, 1px); }
          40% { transform: translate(2px, -1px); }
          60% { transform: translate(-1px, 2px); }
          80% { transform: translate(1px, -2px); }
        }
        .animate-vibrate {
          animation: vibrate 0.1s linear infinite;
        }
        
        @keyframes pop {
          0% { transform: scale(1); opacity: 1; }
          100% { transform: scale(1.8); opacity: 0; }
        }
        .animate-pop {
          animation: pop 0.3s ease-out forwards;
        }
        
        @keyframes sparkle {
          0% { transform: translate(-50%, -50%) rotate(var(--angle)) translateX(0); opacity: 1; }
          100% { transform: translate(-50%, -50%) rotate(var(--angle)) translateX(50px); opacity: 0; }
        }
        .animate-sparkle {
          animation: sparkle 0.4s ease-out forwards;
        }
        
        @keyframes fall {
          0% { transform: translateY(0); opacity: 1; }
          100% { transform: translateY(200px); opacity: 0; }
        }
        .animate-fall {
          animation: fall 0.6s ease-in forwards;
        }
      `}</style>
    </div>
  );
};

export default BolleMagicheGame;
