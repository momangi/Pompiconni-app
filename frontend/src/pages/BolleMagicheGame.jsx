import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Pause, Play, Volume2, VolumeX, RotateCcw, Star, Eye, EyeOff } from 'lucide-react';
import { Button } from '../components/ui/button';
import { getLevelBackgrounds } from '../services/api';

// ============================================
// 🎮 BOLLE MAGICHE DI POPPICONNI
// Arcade Bubble Puzzle – Game Design Ufficiale
// ============================================

// 🐘 URL IMMAGINE POPPICONNI UFFICIALE (fissa, non interattiva)
const POPPICONNI_IMAGE_URL = "https://customer-assets.emergentagent.com/job_kids-gaming/artifacts/pbiw74iv_POPPICONNI%20EMERGENT.png";

// 🎀 URL IMMAGINE CANNONE UFFICIALE
const CANNON_IMAGE_URL = "https://customer-assets.emergentagent.com/job_kids-gaming/artifacts/oi77jaaf_CANNONE.png";

// Constants
const BUBBLE_SIZE = 44;
const GRID_COLS = 11;
const GRID_ROWS = 12;

// 🌈 COLORI – PROGRESSIONE ARCOBALENO
// Ordinati per progressione: partendo da 3 colori base
const COLORS = [
  // Livello 1-3: 3 colori base (Azzurro, Verde, Giallo chiaro)
  { name: 'sky', main: 'rgba(56, 189, 248, 0.35)', highlight: 'rgba(186, 230, 253, 0.75)', solid: '#38bdf8', label: 'Azzurro' },
  { name: 'green', main: 'rgba(74, 222, 128, 0.35)', highlight: 'rgba(187, 247, 208, 0.75)', solid: '#4ade80', label: 'Verde' },
  { name: 'yellow', main: 'rgba(253, 224, 71, 0.35)', highlight: 'rgba(254, 249, 195, 0.75)', solid: '#fde047', label: 'Giallo' },
  // Livello 4+: Rosa
  { name: 'pink', main: 'rgba(244, 114, 182, 0.35)', highlight: 'rgba(251, 207, 232, 0.75)', solid: '#f472b6', label: 'Rosa' },
  // Livello 7+: Viola
  { name: 'purple', main: 'rgba(168, 85, 247, 0.35)', highlight: 'rgba(233, 213, 255, 0.75)', solid: '#a855f7', label: 'Viola' },
  // Livello 10+: Arancione
  { name: 'orange', main: 'rgba(251, 146, 60, 0.35)', highlight: 'rgba(254, 215, 170, 0.75)', solid: '#fb923c', label: 'Arancio' },
  // Livello 13+: Rosso corallo
  { name: 'coral', main: 'rgba(251, 113, 133, 0.35)', highlight: 'rgba(254, 205, 211, 0.75)', solid: '#fb7185', label: 'Corallo' },
  // Livello 16+: Turchese (8 colori = ARCOBALENO COMPLETO)
  { name: 'teal', main: 'rgba(45, 212, 191, 0.35)', highlight: 'rgba(153, 246, 228, 0.75)', solid: '#2dd4bf', label: 'Turchese' },
];

// Bolle speciali (livelli avanzati)
const SPECIAL_BUBBLES = {
  rainbow: { name: 'rainbow', isJoker: true, label: 'Arcobaleno' },
  light: { name: 'light', glow: true, label: 'Luce' },
  party: { name: 'party', extraSparkle: true, label: 'Festa' },
};

// ⏱️ DIFFICOLTÀ KIDS-FRIENDLY (tempi aumentati per livelli iniziali più semplici)
const getDifficultySettings = (level) => {
  if (level <= 3) return { dropInterval: 25000, colors: 3 }; // 25s, 3 colori - molto facile
  if (level <= 6) return { dropInterval: 20000, colors: 4 }; // 20s, 4 colori - facile
  if (level <= 9) return { dropInterval: 16000, colors: 5 }; // 16s, 5 colori
  if (level <= 12) return { dropInterval: 13000, colors: 6 }; // 13s, 6 colori
  if (level <= 15) return { dropInterval: 10000, colors: 7 }; // 10s, 7 colori
  return { dropInterval: 8000, colors: 8 }; // 8s minimo, 8 colori (ARCOBALENO)
};

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
  const [isMuted, setIsMuted] = useState(false);
  const [showTrajectory, setShowTrajectory] = useState(true);
  const [isVibrating, setIsVibrating] = useState(false);
  const [fallingBubbles, setFallingBubbles] = useState([]);
  const [poppingBubbles, setPoppingBubbles] = useState([]);
  const [gameOver, setGameOver] = useState(false);
  const [levelComplete, setLevelComplete] = useState(false);
  const [comboCount, setComboCount] = useState(0);
  
  // Level backgrounds state
  const [levelBackgrounds, setLevelBackgrounds] = useState([]);
  const [currentBackground, setCurrentBackground] = useState(null);
  
  const gameRef = useRef(null);
  const animationRef = useRef(null);
  const dropTimerRef = useRef(null);
  
  // Load level backgrounds on mount
  useEffect(() => {
    const fetchBackgrounds = async () => {
      try {
        const backgrounds = await getLevelBackgrounds();
        setLevelBackgrounds(backgrounds);
      } catch (error) {
        console.log('No level backgrounds configured');
      }
    };
    fetchBackgrounds();
  }, []);
  
  // Update current background based on level (changes every 5 levels)
  useEffect(() => {
    if (levelBackgrounds.length > 0) {
      const bg = levelBackgrounds.find(
        b => level >= b.levelRangeStart && level <= b.levelRangeEnd
      );
      setCurrentBackground(bg || null);
    }
  }, [level, levelBackgrounds]);
  
  // Get available colors based on level
  const getAvailableColors = useCallback(() => {
    const { colors } = getDifficultySettings(level);
    return COLORS.slice(0, colors);
  }, [level]);
  
  // Generate random bubble color
  const getRandomColor = useCallback(() => {
    const colors = getAvailableColors();
    return colors[Math.floor(Math.random() * colors.length)];
  }, [getAvailableColors]);
  
  // Initialize grid for a level
  const initializeGrid = useCallback(() => {
    const newGrid = [];
    const rowsToFill = Math.min(3 + Math.floor(level / 3), 6); // Gradual increase
    
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
    setGameOver(false);
    setLevelComplete(false);
    
  }, [level, initializeGrid, getRandomColor]);
  
  // Drop timer - add new row periodically
  useEffect(() => {
    if (isPaused || gameOver || levelComplete) return;
    
    const { dropInterval } = getDifficultySettings(level);
    
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
         // Poppiconni stays neutral, never sad
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
  const findConnected = useCallback((startRow, startCol, targetColor, gridState, visited = new Set()) => {
    const key = `${startRow}-${startCol}`;
    if (visited.has(key)) return [];
    
    if (startRow < 0 || startRow >= GRID_ROWS) return [];
    const isOffsetRow = startRow % 2 === 1;
    const maxCol = isOffsetRow ? GRID_COLS - 1 : GRID_COLS;
    if (startCol < 0 || startCol >= maxCol) return [];
    
    const bubble = gridState[startRow]?.[startCol];
    if (!bubble || bubble.color.name !== targetColor.name) return [];
    
    visited.add(key);
    const connected = [{ row: startRow, col: startCol }];
    
    // Get neighbors (hexagonal grid)
    const neighbors = getNeighbors(startRow, startCol);
    for (const { row, col } of neighbors) {
      connected.push(...findConnected(row, col, targetColor, gridState, visited));
    }
    
    return connected;
  }, []);
  
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
  const findFloating = useCallback((gridState) => {
    const visited = new Set();
    const connected = new Set();
    
    // BFS from top row
    const queue = [];
    const firstRow = gridState[0];
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
        if (!visited.has(nKey) && gridState[nr]?.[nc]) {
          connected.add(nKey);
          queue.push({ row: nr, col: nc });
        }
      }
    }
    
    // Find all bubbles not in connected set
    const floating = [];
    gridState.forEach((row, rowIdx) => {
      row.forEach((bubble, colIdx) => {
        if (bubble && !connected.has(`${rowIdx}-${colIdx}`)) {
          floating.push({ row: rowIdx, col: colIdx, bubble });
        }
      });
    });
    
    return floating;
  }, []);
  
  // Pop bubbles and handle chain reactions
  const popBubbles = useCallback((bubblesToPop, gridState) => {
    if (bubblesToPop.length < 3) return { newGrid: gridState, popped: false };
    
    // Add to popping animation
    const poppingData = bubblesToPop.map(({ row, col }) => ({
      ...getPixelPos(row, col),
      color: gridState[row][col].color,
      id: gridState[row][col].id
    }));
    setPoppingBubbles(poppingData);
    
    // Remove from grid
    const newGrid = gridState.map(row => [...row]);
    bubblesToPop.forEach(({ row, col }) => {
      newGrid[row][col] = null;
    });
    
    // Update score - più bolle = più punti (combo feeling)
    const basePoints = bubblesToPop.length * 10;
    const comboBonus = bubblesToPop.length > 3 ? (bubblesToPop.length - 3) * 15 : 0;
    setScore(prev => prev + basePoints + comboBonus);
    setComboCount(bubblesToPop.length);
    
    // 💥 Trigger vibration effect - TUTTE le bolle vibrano!
    setIsVibrating(true);
    setTimeout(() => setIsVibrating(false), 800);
    
    return { newGrid, popped: true };
  }, []);
  
  // Check if level is complete
  const checkLevelComplete = useCallback((gridState) => {
    const hasAnyBubble = gridState.some(row => row.some(b => b !== null));
    if (!hasAnyBubble) {
      setLevelComplete(true);
      
    }
  }, []);
  
  // Process after bubble placement
  const processAfterPlacement = useCallback((targetRow, targetCol, color, gridState) => {
    // Check for matches
    const connected = findConnected(targetRow, targetCol, color, gridState);
    
    if (connected.length >= 3) {
      const { newGrid, popped } = popBubbles(connected, gridState);
      
      if (popped) {
        // Clear popping animation after delay, then check floating
        setTimeout(() => {
          setPoppingBubbles([]);
          
          // Check for floating bubbles
          setTimeout(() => {
            const floating = findFloating(newGrid);
            if (floating.length > 0) {
              // Add floating bubbles to falling animation
              const fallingData = floating.map(({ row, col, bubble }) => ({
                ...getPixelPos(row, col),
                color: bubble.color,
                id: bubble.id
              }));
              setFallingBubbles(fallingData);
              
              // Remove from grid
              const finalGrid = newGrid.map(row => [...row]);
              floating.forEach(({ row, col }) => {
                finalGrid[row][col] = null;
              });
              setGrid(finalGrid);
              
              // Bonus score for falling bubbles (extra reward!)
              setScore(prev => prev + floating.length * 25);
              
              // Clear falling animation
              setTimeout(() => {
                setFallingBubbles([]);
                checkLevelComplete(finalGrid);
              }, 600);
            } else {
              setGrid(newGrid);
              checkLevelComplete(newGrid);
            }
          }, 100);
        }, 300);
      }
    } else {
      setGrid(gridState);
      checkLevelComplete(gridState);
    }
  }, [findConnected, popBubbles, findFloating, checkLevelComplete]);
  
  // Flag to prevent double-snap (guardrail)
  const hasSnappedRef = useRef(false);
  
  // Attach bubble to grid - FIXED: removes projectile BEFORE processing matches
  const attachBubble = useCallback((row, col, color) => {
    // Guardrail: prevent double-snap
    if (hasSnappedRef.current) {
      return;
    }
    hasSnappedRef.current = true;
    
    // FIRST: Remove projectile from flight state IMMEDIATELY
    // This ensures the bullet is not rendered while we process
    setShooting(false);
    setBulletPos(null);
    setBulletVel(null);
    bulletVelRef.current = null;
    
    // 🎭 Poppiconni recoil animation
    
    // THEN: Add bubble to grid and process matches
    setGrid(prevGrid => {
      // Clamp to valid position
      const clampedRow = Math.max(0, Math.min(row, GRID_ROWS - 1));
      const isOffsetRow = clampedRow % 2 === 1;
      const maxCol = isOffsetRow ? GRID_COLS - 1 : GRID_COLS;
      const clampedCol = Math.max(0, Math.min(col, maxCol - 1));
      
      // Find empty spot
      let targetRow = clampedRow;
      let targetCol = clampedCol;
      
      // If spot is occupied, find nearest empty
      if (prevGrid[targetRow]?.[targetCol]) {
        const neighbors = getNeighbors(targetRow, targetCol);
        for (const { row: nr, col: nc } of neighbors) {
          if (nr >= 0 && nr < GRID_ROWS) {
            const nIsOffset = nr % 2 === 1;
            const nMaxCol = nIsOffset ? GRID_COLS - 1 : GRID_COLS;
            if (nc >= 0 && nc < nMaxCol && !prevGrid[nr]?.[nc]) {
              targetRow = nr;
              targetCol = nc;
              break;
            }
          }
        }
      }
      
      // Add bubble to grid (SINGLE entity - the projectile is already gone)
      const newGrid = prevGrid.map(row => [...row]);
      if (!newGrid[targetRow][targetCol]) {
        newGrid[targetRow][targetCol] = {
          color,
          id: `placed-${Date.now()}-${Math.random()}`
        };
      }
      
      // Process matches AFTER projectile is removed and grid is updated
      // Use setTimeout to ensure React has flushed the state updates
      setTimeout(() => {
        processAfterPlacement(targetRow, targetCol, color, newGrid);
        // Reset snap flag after processing is complete
        hasSnappedRef.current = false;
      }, 50);
      
      return newGrid;
    });
    
    // Next bubble - prepare for next shot
    setCurrentBubble(nextBubble);
    setNextBubble(getRandomColor());
  }, [nextBubble, getRandomColor, processAfterPlacement]);
  
  // Calculate trajectory for preview
  // Calculate trajectory for preview - uses SAME logic as real physics
  const calculateTrajectory = useCallback((angle, startX, startY) => {
    const points = [];
    const speed = 15;
    const radius = BUBBLE_SIZE / 2;
    let x = startX;
    let y = startY;
    let vx = Math.cos(angle * Math.PI / 180) * speed;
    let vy = Math.sin(angle * Math.PI / 180) * speed;
    
    const gameWidth = GRID_COLS * BUBBLE_SIZE;
    
    for (let i = 0; i < 50; i++) {
      points.push({ x, y });
      x += vx;
      y += vy;
      
      // Wall bounce - SAME logic as real physics (clamp + absolute direction)
      if (x < radius) {
        x = radius;
        vx = Math.abs(vx); // Always positive (going right)
      } else if (x > gameWidth - radius) {
        x = gameWidth - radius;
        vx = -Math.abs(vx); // Always negative (going left)
      }
      
      // Stop at top or collision
      if (y < radius) break;
      
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
  
  // Bullet animation loop - using ref for velocity to avoid stale closure issues
  const bulletVelRef = useRef(bulletVel);
  useEffect(() => {
    bulletVelRef.current = bulletVel;
  }, [bulletVel]);
  
  useEffect(() => {
    if (!isShooting || !bulletPos || !bulletVel) return;
    
    const gameWidth = GRID_COLS * BUBBLE_SIZE;
    const radius = BUBBLE_SIZE / 2;
    
    const animate = () => {
      // Guardrail: check velocity ref is valid
      const vel = bulletVelRef.current;
      if (!vel || typeof vel.vx !== 'number' || typeof vel.vy !== 'number') {
        // Safety fallback - stop animation
        setShooting(false);
        setBulletPos(null);
        return;
      }
      
      setBulletPos(prev => {
        if (!prev) return null;
        
        let newX = prev.x + vel.vx;
        let newY = prev.y + vel.vy;
        let newVx = vel.vx;
        
        // Wall bounce - clamp position AND reflect velocity in ONE step
        // Left wall
        if (newX < radius) {
          newX = radius;
          newVx = Math.abs(vel.vx); // Always positive (going right)
        } 
        // Right wall
        else if (newX > gameWidth - radius) {
          newX = gameWidth - radius;
          newVx = -Math.abs(vel.vx); // Always negative (going left)
        }
        
        // Update velocity if it changed (only update once per bounce)
        if (newVx !== vel.vx) {
          const updatedVel = { vx: newVx, vy: vel.vy };
          bulletVelRef.current = updatedVel;
          setBulletVel(updatedVel);
        }
        
        // Top collision - attach bubble
        if (newY < radius) {
          const { col } = getGridPos(newX, radius);
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
  }, [isShooting, bulletVel, currentBubble, grid, attachBubble]);
  
  // Next level
  const nextLevel = () => {
    hasSnappedRef.current = false; // Reset snap guard
    setLevel(prev => prev + 1);
    setLevelComplete(false);
    setComboCount(0);
  };
  
  // Reset game
  const resetGame = () => {
    hasSnappedRef.current = false; // Reset snap guard
    setLevel(1);
    setScore(0);
    setGameOver(false);
    setLevelComplete(false);
    setComboCount(0);
    
    setShooting(false);
    setBulletPos(null);
  };
  
  // 🫧 RENDER SOAP BUBBLE - REALISTIC "SOAP BUBBLE" EFFECT
  // Reference: Real soap bubbles with transparency, iridescence, and white highlights
  const renderBubble = (color, x, y, size = BUBBLE_SIZE, shouldVibrate = false, key) => (
    <div
      key={key}
      className={`absolute rounded-full ${shouldVibrate ? 'animate-vibrate' : ''}`}
      style={{
        left: x - size / 2,
        top: y - size / 2,
        width: size,
        height: size,
        // 🫧 SOAP FILM: Almost transparent with soft iridescence
        background: `
          radial-gradient(ellipse 120% 80% at 30% 25%, rgba(255,255,255,0.85) 0%, rgba(255,255,255,0.3) 20%, transparent 50%),
          radial-gradient(ellipse 60% 40% at 75% 80%, rgba(255,255,255,0.15) 0%, transparent 60%),
          radial-gradient(circle at 50% 50%, transparent 30%, rgba(0,220,255,0.08) 50%, rgba(255,0,255,0.06) 65%, rgba(255,255,0,0.05) 80%, transparent 100%),
          linear-gradient(160deg, rgba(0,255,200,0.12) 0%, transparent 40%),
          linear-gradient(200deg, rgba(255,100,255,0.10) 0%, transparent 50%),
          linear-gradient(320deg, rgba(100,200,255,0.08) 0%, transparent 45%),
          radial-gradient(circle at 50% 50%, rgba(255,255,255,0.03) 0%, rgba(200,230,255,0.05) 100%)
        `,
        // Subtle outer glow and soft edge
        boxShadow: `
          inset 0 0 ${size * 0.4}px rgba(255,255,255,0.15),
          inset 0 0 ${size * 0.15}px rgba(255,255,255,0.1),
          0 0 ${size * 0.08}px rgba(255,255,255,0.4),
          0 ${size * 0.03}px ${size * 0.06}px rgba(0,0,0,0.05)
        `,
        // Very thin, subtle border - NOT colored
        border: '1px solid rgba(255,255,255,0.25)',
        // Smooth animation
        transition: 'transform 0.1s ease-out',
      }}
    >
      {/* 🌈 IRIDESCENT FILM - Flowing light effect */}
      <div 
        className="absolute inset-0 rounded-full overflow-hidden"
        style={{
          background: `
            conic-gradient(from 45deg at 60% 40%,
              rgba(0,255,255,0.12) 0deg,
              rgba(0,255,150,0.10) 60deg,
              rgba(255,255,0,0.08) 120deg,
              rgba(255,150,0,0.10) 180deg,
              rgba(255,0,150,0.12) 240deg,
              rgba(150,0,255,0.10) 300deg,
              rgba(0,255,255,0.12) 360deg
            )
          `,
          opacity: 0.7,
          mixBlendMode: 'screen',
        }}
      />
      
      {/* ✨ PRIMARY HIGHLIGHT - Bright white, top-left, oval shape */}
      <div 
        className="absolute"
        style={{
          width: '45%',
          height: '30%',
          top: '8%',
          left: '10%',
          background: 'radial-gradient(ellipse at 50% 50%, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.6) 30%, rgba(255,255,255,0.2) 60%, transparent 100%)',
          borderRadius: '50%',
          transform: 'rotate(-15deg)',
          filter: 'blur(0.5px)',
        }}
      />
      
      {/* ✨ SECONDARY HIGHLIGHT - Smaller, softer */}
      <div 
        className="absolute"
        style={{
          width: '20%',
          height: '12%',
          top: '20%',
          left: '55%',
          background: 'radial-gradient(ellipse at 50% 50%, rgba(255,255,255,0.5) 0%, transparent 100%)',
          borderRadius: '50%',
          transform: 'rotate(20deg)',
        }}
      />
      
      {/* ✨ BOTTOM REFLECTION - Very subtle */}
      <div 
        className="absolute"
        style={{
          width: '25%',
          height: '15%',
          bottom: '12%',
          right: '15%',
          background: 'radial-gradient(ellipse at 50% 50%, rgba(255,255,255,0.25) 0%, transparent 100%)',
          borderRadius: '50%',
        }}
      />
      
      {/* 🎯 COLOR NUCLEUS - 70% diameter with radial gradient fade */}
      {/* Center = saturated color → Edges = transparent (floating in air effect) */}
      <div 
        className="absolute rounded-full"
        style={{
          width: '70%',
          height: '70%',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          // Radial gradient: intense center → soft fade to transparent
          background: `radial-gradient(circle at 50% 50%, 
            ${color.solid}ee 0%, 
            ${color.solid}cc 25%, 
            ${color.solid}99 45%, 
            ${color.solid}55 65%, 
            ${color.solid}22 85%, 
            transparent 100%
          )`,
          // Subtle inner glow for depth
          boxShadow: `
            inset 0 0 ${size * 0.08}px rgba(255,255,255,0.3),
            0 0 ${size * 0.15}px ${color.solid}40
          `,
          // Blend with soap film
          mixBlendMode: 'normal',
        }}
      />
      
      {/* 🌟 INNER EDGE IRIDESCENCE - Subtle color shift at edges */}
      <div 
        className="absolute inset-1 rounded-full"
        style={{
          background: `
            radial-gradient(circle at 50% 50%, 
              transparent 65%,
              rgba(0,255,255,0.06) 75%,
              rgba(255,0,255,0.05) 85%,
              rgba(255,255,0,0.04) 95%,
              transparent 100%
            )
          `,
          pointerEvents: 'none',
        }}
      />
    </div>
  );
  
  // 🎀 RENDER OFFICIAL CANNON - Uses uploaded image
  const renderToyCannon = () => {
    return (
      <div 
        className="relative"
        style={{
          transform: `rotate(${shooterAngle + 90}deg)`,
          transformOrigin: 'center bottom',
        }}
      >
        {/* Official cannon image - 10% bigger */}
        <img 
          src={CANNON_IMAGE_URL}
          alt="Cannone"
          style={{
            width: 70,  /* w-16 (64px) + 10% = ~70px */
            height: 'auto',
            filter: 'drop-shadow(0 4px 8px rgba(0,0,0,0.2))',
            marginTop: -50,
            marginLeft: -12,
          }}
        />
      </div>
    );
  };
  
  const gameWidth = GRID_COLS * BUBBLE_SIZE;
  const gameHeight = GRID_ROWS * BUBBLE_SIZE * 0.866 + 140;
  const shooterX = gameWidth / 2;
  const shooterY = GRID_ROWS * BUBBLE_SIZE * 0.866 + 70;
  
  // Get current difficulty info
  const { colors: numColors } = getDifficultySettings(level);
  
  return (
    <div className="min-h-screen bg-gradient-to-b from-sky-100 via-pink-50 to-purple-100 flex flex-col items-center py-2">
      {/* Header */}
      <div className="w-full max-w-lg px-4 py-2">
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
            {/* Color indicator */}
            <div className="bg-white/80 backdrop-blur-sm rounded-full px-2 py-1 shadow-lg flex items-center gap-0.5">
              {COLORS.slice(0, numColors).map((c, i) => (
                <div key={i} className="w-3 h-3 rounded-full" style={{ backgroundColor: c.solid }} />
              ))}
            </div>
          </div>
          
          <div className="flex items-center gap-1">
            <button
              onClick={() => setShowTrajectory(!showTrajectory)}
              className={`p-2 backdrop-blur-sm rounded-full shadow-lg transition-colors ${showTrajectory ? 'bg-purple-100' : 'bg-white/80'}`}
              title={showTrajectory ? "Nascondi mira" : "Mostra mira"}
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

      {/* Combo indicator */}
      {comboCount >= 4 && (
        <div className="animate-combo-pop mb-2">
          <div className="bg-gradient-to-r from-amber-400 to-orange-500 text-white px-5 py-1.5 rounded-full font-bold text-lg shadow-lg">
            {comboCount}x COMBO! ✨
          </div>
        </div>
      )}

      {/* Game Area */}
      <div 
        ref={gameRef}
        className="relative rounded-3xl shadow-2xl overflow-hidden cursor-crosshair"
        style={{ width: gameWidth, height: gameHeight }}
        onMouseMove={handleMouseMove}
        onClick={handleClick}
      >
        {/* 🌈 LEVEL BACKGROUND - Changes every 5 levels */}
        {currentBackground?.backgroundImageUrl ? (
          <>
            {/* Background image layer (opacity: 1) */}
            <div 
              className="absolute inset-0 bg-cover bg-center"
              style={{ 
                backgroundImage: `url(${process.env.REACT_APP_BACKEND_URL}${currentBackground.backgroundImageUrl})`,
              }}
            />
            {/* Overlay layer (controlled by slider) */}
            <div 
              className="absolute inset-0"
              style={{ 
                backgroundColor: `rgba(255, 255, 255, ${(currentBackground.backgroundOpacity || 30) / 100})`,
                backdropFilter: `blur(${(currentBackground.backgroundOpacity || 30) / 25}px)`,
              }}
            />
          </>
        ) : (
          /* Default background when no level background configured */
          <div className="absolute inset-0 bg-gradient-to-b from-sky-100/60 via-pink-50/40 to-purple-100/60" />
        )}
        
        {/* 🐘 POPPICONNI IMAGE - Fixed, bottom-left, identity element */}
        {/* z-index: 5 = sotto le bolle (z-20), sopra lo sfondo */}
        <div 
          className="absolute pointer-events-none"
          style={{
            left: -20,
            bottom: 0,
            width: 230,  /* 200px + 15% = 230px */
            height: 'auto',
            zIndex: 5,
          }}
        >
          <img 
            src={POPPICONNI_IMAGE_URL}
            alt="Poppiconni"
            className="w-full h-auto"
            style={{ 
              filter: 'drop-shadow(0 6px 12px rgba(0,0,0,0.2))',
            }}
          />
        </div>

        {/* Grid bubbles - z-index: 20 (sopra Poppiconni) */}
        {grid.map((row, rowIdx) => 
          row.map((bubble, colIdx) => {
            if (!bubble) return null;
            const { x, y } = getPixelPos(rowIdx, colIdx);
            return (
              <div key={bubble.id} style={{ position: 'relative', zIndex: 20 }}>
                {renderBubble(bubble.color, x, y, BUBBLE_SIZE, isVibrating, bubble.id)}
              </div>
            );
          })
        )}
        
        {/* Popping bubbles animation */}
        {poppingBubbles.map((bubble) => (
          <div
            key={`pop-${bubble.id}`}
            className="absolute animate-pop pointer-events-none"
            style={{ left: bubble.x, top: bubble.y }}
          >
            {[...Array(10)].map((_, i) => (
              <div
                key={i}
                className="absolute w-2 h-2 rounded-full animate-sparkle"
                style={{
                  left: 0,
                  top: 0,
                  background: bubble.color.solid,
                  boxShadow: `0 0 8px ${bubble.color.solid}`,
                  '--angle': `${i * 36}deg`,
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
            {/* Sparkle when falling */}
            <div className="absolute bottom-0 left-1/2 -translate-x-1/2 text-yellow-400 text-xs animate-pulse">✦</div>
          </div>
        ))}
        
        {/* Trajectory preview - linea tratteggiata morbida */}
        {showTrajectory && isAiming && !isShooting && currentBubble && (
          <>
            {calculateTrajectory(shooterAngle, shooterX, shooterY - 30).map((point, i) => (
              <div
                key={i}
                className="absolute rounded-full"
                style={{
                  left: point.x - 4,
                  top: point.y - 4,
                  width: 8,
                  height: 8,
                  background: `radial-gradient(circle, ${currentBubble.solid}60, ${currentBubble.solid}20)`,
                  opacity: 1 - (i / 50) * 0.9
                }}
              />
            ))}
          </>
        )}
        
        {/* Shooting bubble - z-index alto per essere visibile sopra Poppiconni */}
        {bulletPos && currentBubble && (
          <div style={{ position: 'absolute', zIndex: 30, left: 0, top: 0 }}>
            {renderBubble(currentBubble, bulletPos.x, bulletPos.y, BUBBLE_SIZE, false, 'bullet')}
          </div>
        )}
        
        {/* Shooter area - semi-transparent gradient */}
        <div 
          className="absolute bottom-0 left-0 right-0 h-36 bg-gradient-to-t from-pink-100/70 via-pink-50/40 to-transparent"
        >
          {/* 🎀 TOY CANNON - Central, positioned at bottom */}
          <div 
            className="absolute"
            style={{ 
              left: shooterX - 22, 
              top: 50,  /* Spostato più in basso */
            }}
          >
            {renderToyCannon()}
          </div>
          
          {/* 🎯 BOLLE UI - Layout ORIZZONTALE senza testo */}
          {/* Sinistra = Bolla attiva (più grande) | Destra = Bolla successiva (più piccola) */}
          <div 
            className="absolute flex flex-row items-center gap-3" 
            style={{ right: 15, top: 25 }}
          >
            {/* Bolla ATTIVA - quella che verrà sparata ORA (più grande, dominante) */}
            {currentBubble && !isShooting && (
              <div className="bg-white/70 backdrop-blur-sm rounded-full p-2 shadow-lg ring-2 ring-white/50">
                {renderBubble(currentBubble, 26, 26, 48, false, 'current-active')}
              </div>
            )}
            
            {/* Bolla SUCCESSIVA - la prossima (più piccola, ~85% della prima) */}
            {nextBubble && (
              <div className="bg-white/50 backdrop-blur-sm rounded-full p-1.5 shadow">
                {renderBubble(nextBubble, 20, 20, 40, false, 'next-queue')}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Pause Overlay */}
      {isPaused && !gameOver && !levelComplete && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40 flex items-center justify-center">
          <div className="bg-white rounded-3xl p-8 shadow-2xl text-center max-w-sm mx-4 animate-scale-in">
            <div className="text-4xl mb-3">⏸️</div>
            <h2 className="text-2xl font-bold text-gray-800 mb-2">Pausa</h2>
            <p className="text-gray-600 mb-6">Livello {level} • Punteggio: {score}</p>
            <div className="space-y-3">
              <Button
                onClick={() => setIsPaused(false)}
                className="w-full bg-gradient-to-r from-pink-500 to-purple-500 hover:from-pink-600 hover:to-purple-600 rounded-xl py-5"
              >
                <Play className="w-5 h-5 mr-2" />
                Continua a giocare
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
      
      {/* Game Over Overlay - Neutral, NOT punishing */}
      {gameOver && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40 flex items-center justify-center">
          <div className="bg-white rounded-3xl p-8 shadow-2xl text-center max-w-sm mx-4 animate-scale-in">
            <div className="text-5xl mb-3">🎮</div>
            <h2 className="text-2xl font-bold text-gray-800 mb-2">Fine partita!</h2>
            <p className="text-gray-600 mb-1">Hai raggiunto il livello {level}</p>
            <p className="text-3xl font-bold text-purple-600 mb-6">
              <Star className="w-6 h-6 inline text-amber-500 fill-amber-500 mr-1" />
              {score} punti
            </p>
            <div className="space-y-3">
              <Button
                onClick={resetGame}
                className="w-full bg-gradient-to-r from-pink-500 to-purple-500 hover:from-pink-600 hover:to-purple-600 rounded-xl py-5 text-lg"
              >
                🎈 Gioca ancora!
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
      
      {/* Level Complete Overlay - Celebration! */}
      {levelComplete && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40 flex items-center justify-center">
          <div className="bg-white rounded-3xl p-8 shadow-2xl text-center max-w-sm mx-4 animate-scale-in">
            <div className="text-6xl mb-3 animate-bounce">🎉</div>
            <h2 className="text-3xl font-bold text-gray-800 mb-2">Fantastico!</h2>
            <p className="text-gray-600 mb-1">Livello {level} completato!</p>
            <p className="text-3xl font-bold text-purple-600 mb-6">
              <Star className="w-6 h-6 inline text-amber-500 fill-amber-500 mr-1" />
              {score} punti
            </p>
            {level < 16 && (
              <p className="text-sm text-gray-500 mb-4">
                Prossimo livello: {getDifficultySettings(level + 1).colors} colori! 🌈
              </p>
            )}
            <Button
              onClick={nextLevel}
              className="w-full bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600 rounded-xl py-6 text-xl font-bold shadow-lg"
            >
              Livello {level + 1} → 🚀
            </Button>
          </div>
        </div>
      )}

      <style>{`
        @keyframes vibrate {
          0%, 100% { transform: translate(0, 0); }
          10% { transform: translate(-2px, 1px); }
          20% { transform: translate(2px, -1px); }
          30% { transform: translate(-1px, 2px); }
          40% { transform: translate(1px, -2px); }
          50% { transform: translate(-2px, -1px); }
          60% { transform: translate(2px, 1px); }
          70% { transform: translate(-1px, -2px); }
          80% { transform: translate(1px, 2px); }
          90% { transform: translate(-2px, 1px); }
        }
        .animate-vibrate {
          animation: vibrate 0.08s linear infinite;
        }
        
        @keyframes breathe {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.03); }
        }
        .animate-breathe {
          animation: breathe 3s ease-in-out infinite;
        }
        
        @keyframes pop {
          0% { transform: scale(1); opacity: 1; }
          50% { transform: scale(1.3); }
          100% { transform: scale(0); opacity: 0; }
        }
        .animate-pop {
          animation: pop 0.35s ease-out forwards;
        }
        
        @keyframes sparkle {
          0% { transform: translate(-50%, -50%) rotate(var(--angle)) translateX(0) scale(1); opacity: 1; }
          100% { transform: translate(-50%, -50%) rotate(var(--angle)) translateX(55px) scale(0.5); opacity: 0; }
        }
        .animate-sparkle {
          animation: sparkle 0.45s ease-out forwards;
        }
        
        @keyframes fall {
          0% { transform: translateY(0) rotate(0deg); opacity: 1; }
          100% { transform: translateY(250px) rotate(15deg); opacity: 0; }
        }
        .animate-fall {
          animation: fall 0.7s ease-in forwards;
        }
        
        @keyframes combo-pop {
          0% { transform: scale(0.5); opacity: 0; }
          50% { transform: scale(1.15); }
          100% { transform: scale(1); opacity: 1; }
        }
        .animate-combo-pop {
          animation: combo-pop 0.35s ease-out;
        }
        
        @keyframes scale-in {
          0% { transform: scale(0.9); opacity: 0; }
          100% { transform: scale(1); opacity: 1; }
        }
        .animate-scale-in {
          animation: scale-in 0.3s ease-out;
        }
      `}</style>
    </div>
  );
};

export default BolleMagicheGame;
