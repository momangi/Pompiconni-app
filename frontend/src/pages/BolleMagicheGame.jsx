import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Pause, Play, Volume2, VolumeX, RotateCcw, Star, Eye, EyeOff } from 'lucide-react';
import { Button } from '../components/ui/button';
import { getLevelBackgrounds } from '../services/api';
import { useGameAudio } from '../hooks/useGameAudio';

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

// ============================================
// 📐 CANNON CONFIG - Centralized parameters
// All cannon-related values in ONE place for easy fine-tuning
// ============================================
const CANNON_CONFIG = {
  // Dimensions
  width: 70,
  height: 100,
  
  // Pivot point (% from top-left of cannon image) - where the cannon rotates
  pivotOriginX: 0.5,  // Center horizontally
  pivotOriginY: 0.85, // 85% from top = near base
  
  // Barrel length in pixels (distance from pivot to muzzle tip)
  // CALIBRATED: Must match visual cannon tip exactly
  barrelLengthPx: 85,
  
  // Micro-offset for pixel-perfect muzzle alignment (optional fine-tuning)
  muzzleOffsetX: 0,
  muzzleOffsetY: -3, // Slightly upward to match visual tip
  
  // Angle limits (degrees from vertical -90°)
  // -165° to -15° means ±75° from straight up
  angleMin: -165,
  angleMax: -15,
  
  // Position in game area (shooter area coordinates)
  positionTop: 25, // px from top of shooter area
  
  // Trajectory dot styling
  trajectoryDotRadius: 4,     // Reduced to 4px
  trajectoryDotSpacing: 0.85, // Tighter spacing
};

// ⏱️ DIFFICOLTÀ KIDS-FRIENDLY (tempi molto lunghi per livelli semplici)
const getDifficultySettings = (level) => {
  if (level <= 3) return { dropInterval: 35000, colors: 3 }; // 35s, 3 colori - MOLTO facile
  if (level <= 6) return { dropInterval: 28000, colors: 4 }; // 28s, 4 colori - facile
  if (level <= 9) return { dropInterval: 22000, colors: 5 }; // 22s, 5 colori
  if (level <= 12) return { dropInterval: 18000, colors: 6 }; // 18s, 6 colori
  if (level <= 15) return { dropInterval: 14000, colors: 7 }; // 14s, 7 colori
  return { dropInterval: 10000, colors: 8 }; // 10s minimo, 8 colori (ARCOBALENO)
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
  
  // 🎧 AUDIO SYSTEM - Centralized game audio
  const { 
    isMuted, 
    toggleMute, 
    initAudio, 
    playShoot, 
    playPop, 
    playBounce, 
    playMiss 
  } = useGameAudio();
  
  // UI state
  const [score, setScore] = useState(0);
  const [level, setLevel] = useState(1);
  const [isPaused, setIsPaused] = useState(false);
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
  const cannonRef = useRef(null);
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
    
    // 🎵 Play pop sound with combo multiplier
    const comboMultiplier = bubblesToPop.length > 3 ? bubblesToPop.length / 3 : 1;
    playPop(comboMultiplier);
    
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
  }, [playPop]);
  
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
      // 🎵 Play miss sound (no match found)
      playMiss();
      setGrid(gridState);
      checkLevelComplete(gridState);
    }
  }, [findConnected, popBubbles, findFloating, checkLevelComplete, playMiss]);
  
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
  
  // ============================================
  // 🎯 UNIFIED TRAJECTORY CALCULATION
  // Same logic for preview AND real shot
  // ============================================
  const calculateTrajectory = useCallback((angle, muzzleX, muzzleY) => {
    const points = [];
    const speed = 15;
    const radius = BUBBLE_SIZE / 2;
    
    // Start exactly at muzzle point
    let x = muzzleX;
    let y = muzzleY;
    
    // Velocity based on angle (angle in degrees, -90 = straight up)
    let vx = Math.cos(angle * Math.PI / 180) * speed;
    let vy = Math.sin(angle * Math.PI / 180) * speed;
    
    const gameW = GRID_COLS * BUBBLE_SIZE;
    
    // Apply spacing factor from config
    const spacingFactor = CANNON_CONFIG.trajectoryDotSpacing;
    
    for (let i = 0; i < 60; i++) {
      points.push({ x, y });
      x += vx * spacingFactor;
      y += vy * spacingFactor;
      
      // Wall bounce with clamp (same as real physics)
      if (x < radius) {
        x = radius;
        vx = Math.abs(vx);
      } else if (x > gameW - radius) {
        x = gameW - radius;
        vx = -Math.abs(vx);
      }
      
      // Stop at top
      if (y < radius) break;
      
      // Stop at grid collision
      const { row, col } = getGridPos(x, y);
      if (row >= 0 && row < GRID_ROWS && grid[row]?.[col]) {
        break;
      }
    }
    
    return points;
  }, [grid]);
  
  // ============================================
  // 🔫 GAME AREA DIMENSIONS (for layout/render)
  // ============================================
  const gameWidth = GRID_COLS * BUBBLE_SIZE;
  const gameHeight = GRID_ROWS * BUBBLE_SIZE * 0.866 + 140;
  const shooterX = gameWidth / 2;
  const shooterY = GRID_ROWS * BUBBLE_SIZE * 0.866 + 70;
  
  // ============================================
  // 🎯 MUZZLE POINT CALCULATION - SINGLE SOURCE OF TRUTH
  // DOM-BASED ONLY: Uses getBoundingClientRect()
  // Used by BOTH trajectory preview AND bullet spawn
  // NO hardcoded offsets or alternative formulas allowed
  // ============================================
  const getMuzzlePoint = useCallback((angle) => {
    const gameArea = gameRef.current;
    const cannonEl = cannonRef.current;
    
    // Fallback if refs not ready (should not happen during gameplay)
    if (!gameArea || !cannonEl) {
      console.warn('⚠️ getMuzzlePoint: refs not ready, using fallback');
      const fallbackPivotX = gameWidth / 2;
      const fallbackPivotY = gameHeight - 140 + CANNON_CONFIG.positionTop + (CANNON_CONFIG.height * CANNON_CONFIG.pivotOriginY);
      const angleRad = (angle * Math.PI) / 180;
      return {
        x: fallbackPivotX + Math.cos(angleRad) * CANNON_CONFIG.barrelLengthPx,
        y: fallbackPivotY + Math.sin(angleRad) * CANNON_CONFIG.barrelLengthPx,
      };
    }
    
    // ====== DOM-BASED CALCULATION ======
    const gameRect = gameArea.getBoundingClientRect();
    const cannonRect = cannonEl.getBoundingClientRect();
    
    // Calculate pivot in game area coordinates
    const pivotX = (cannonRect.left - gameRect.left) + (cannonRect.width * CANNON_CONFIG.pivotOriginX);
    const pivotY = (cannonRect.top - gameRect.top) + (cannonRect.height * CANNON_CONFIG.pivotOriginY);
    
    // Calculate muzzle from pivot using angle and barrel length
    const angleRad = (angle * Math.PI) / 180;
    const muzzleX = pivotX + Math.cos(angleRad) * CANNON_CONFIG.barrelLengthPx + CANNON_CONFIG.muzzleOffsetX;
    const muzzleY = pivotY + Math.sin(angleRad) * CANNON_CONFIG.barrelLengthPx + CANNON_CONFIG.muzzleOffsetY;
    
    return { x: muzzleX, y: muzzleY };
  }, [gameWidth, gameHeight]);
  
  // ============================================
  // 🎯 PIVOT POINT FOR AIMING (DOM-based)
  // Used for mouse angle calculation
  // ============================================
  const getPivotPoint = useCallback(() => {
    const gameArea = gameRef.current;
    const cannonEl = cannonRef.current;
    
    if (!gameArea || !cannonEl) {
      // Fallback
      return {
        x: gameWidth / 2,
        y: gameHeight - 140 + CANNON_CONFIG.positionTop + (CANNON_CONFIG.height * CANNON_CONFIG.pivotOriginY)
      };
    }
    
    const gameRect = gameArea.getBoundingClientRect();
    const cannonRect = cannonEl.getBoundingClientRect();
    
    return {
      x: (cannonRect.left - gameRect.left) + (cannonRect.width * CANNON_CONFIG.pivotOriginX),
      y: (cannonRect.top - gameRect.top) + (cannonRect.height * CANNON_CONFIG.pivotOriginY)
    };
  }, [gameWidth, gameHeight]);
  
  // Handle mouse move for aiming (with angle clamping ±75° from vertical)
  const handleMouseMove = useCallback((e) => {
    if (isShooting || isPaused || gameOver || levelComplete) return;
    
    const rect = gameRef.current?.getBoundingClientRect();
    if (!rect) return;
    
    // Get pivot point from DOM
    const pivot = getPivotPoint();
    
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    
    const dx = mouseX - pivot.x;
    const dy = mouseY - pivot.y;
    
    let angle = Math.atan2(dy, dx) * 180 / Math.PI;
    
    // Clamp angle using CANNON_CONFIG
    angle = Math.max(CANNON_CONFIG.angleMin, Math.min(CANNON_CONFIG.angleMax, angle));
    
    setShooterAngle(angle);
    setIsAiming(true);
  }, [isShooting, isPaused, gameOver, levelComplete, getPivotPoint]);
  
  // Handle click to shoot - spawns bullet at MUZZLE POINT (pixel-perfect with cannon tip)
  const handleClick = useCallback(() => {
    if (isShooting || isPaused || !currentBubble || gameOver || levelComplete) return;
    
    // 🎧 Initialize audio on first interaction (autoplay policy)
    initAudio();
    
    // 🎵 Play shoot sound
    playShoot();
    
    // Use unified getMuzzlePoint (same function as trajectory preview)
    const muzzle = getMuzzlePoint(shooterAngle);
    
    // ============================================
    // 🛡️ DEV GUARDRAIL: Verify muzzle alignment
    // Only runs in development mode
    // ============================================
    if (process.env.NODE_ENV === 'development') {
      // Re-calculate to verify (should be identical)
      const verifyMuzzle = getMuzzlePoint(shooterAngle);
      const distance = Math.sqrt(
        Math.pow(muzzle.x - verifyMuzzle.x, 2) + 
        Math.pow(muzzle.y - verifyMuzzle.y, 2)
      );
      if (distance > 1) {
        console.warn(
          '⚠️ MUZZLE MISALIGNMENT DETECTED!',
          '\n  Preview:', verifyMuzzle,
          '\n  Shot:', muzzle,
          '\n  Distance:', distance.toFixed(2), 'px'
        );
      }
    }
    
    const speed = 18;
    const vx = Math.cos(shooterAngle * Math.PI / 180) * speed;
    const vy = Math.sin(shooterAngle * Math.PI / 180) * speed;
    
    // Spawn bullet at muzzle point
    setBulletPos({ x: muzzle.x, y: muzzle.y });
    setBulletVel({ vx, vy });
    setShooting(true);
    
  }, [isShooting, isPaused, currentBubble, shooterAngle, gameOver, levelComplete, getMuzzlePoint, initAudio, playShoot]);
  
  // Bullet animation loop - using ref for velocity to avoid stale closure issues
  const bulletVelRef = useRef(bulletVel);
  useEffect(() => {
    bulletVelRef.current = bulletVel;
  }, [bulletVel]);
  
  useEffect(() => {
    if (!isShooting || !bulletPos || !bulletVel) return;
    
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
          // 🎵 Play bounce sound
          playBounce();
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
  }, [isShooting, bulletVel, currentBubble, grid, attachBubble, playBounce]);
  
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
  
  // Clamp angle to prevent extreme rotations (using CANNON_CONFIG)
  const clampedAngle = Math.max(
    CANNON_CONFIG.angleMin + 90, 
    Math.min(CANNON_CONFIG.angleMax + 90, shooterAngle + 90)
  );
  
  // 🎀 RENDER CANNON with fixed pivot rotation
  const renderToyCannon = () => {
    return (
      <div 
        ref={cannonRef}
        className="relative"
        style={{
          width: CANNON_CONFIG.width,
          height: CANNON_CONFIG.height,
          // PIVOT-BASED ROTATION: transform-origin at base
          transformOrigin: `50% ${CANNON_CONFIG.pivotOriginY * 100}%`,
          transform: `rotate(${clampedAngle}deg)`,
        }}
      >
        {/* Official cannon image */}
        <img 
          src={CANNON_IMAGE_URL}
          alt="Cannone"
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'contain',
            filter: 'drop-shadow(0 4px 8px rgba(0,0,0,0.2))',
          }}
        />
      </div>
    );
  };
  
  // Get current difficulty info
  const { colors: numColors } = getDifficultySettings(level);
  
  // ============================================
  // 📐 RESPONSIVE GAME SIZING
  // Single source of truth for game dimensions
  // ============================================
  // Base dimensions (used for internal calculations)
  const baseWidth = gameWidth;   // 484px (GRID_COLS * BUBBLE_SIZE)
  const baseHeight = gameHeight; // ~597px
  const aspectRatio = baseWidth / baseHeight;
  
  return (
    <div className="min-h-screen bg-gradient-to-b from-sky-100 via-pink-50 to-purple-100 flex flex-col items-center justify-center py-2 px-2">
      {/* 
        ============================================
        📐 RESPONSIVE GAME WRAPPER
        ============================================
        - Mobile: width = min(92vw, 480px), centered
        - Tablet: width = min(75vw, 520px)
        - Desktop: width = min(45vw, 600px)
        - Large Desktop: width = min(38vw, 640px)
        - max-height: 88vh to prevent overflow
        - aspect-ratio preserved
      */}
      <div 
        className="flex flex-col items-center w-full"
        style={{
          maxWidth: 'min(92vw, 480px)', // Mobile default
          maxHeight: '88vh',
        }}
      >
        <style>{`
          @media (min-width: 768px) {
            .game-wrapper {
              max-width: min(75vw, 520px) !important;
            }
          }
          @media (min-width: 1024px) {
            .game-wrapper {
              max-width: min(45vw, 600px) !important;
            }
          }
          @media (min-width: 1440px) {
            .game-wrapper {
              max-width: min(38vw, 680px) !important;
            }
          }
        `}</style>
        
        {/* Header - scales with game */}
        <div className="w-full px-2 py-2 game-wrapper" style={{ maxWidth: 'inherit' }}>
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
              onClick={toggleMute}
              className="p-2 bg-white/80 backdrop-blur-sm rounded-full shadow-lg hover:bg-white transition-colors"
              title={isMuted ? "Attiva audio" : "Disattiva audio"}
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

      {/* 
        ============================================
        🎮 GAME AREA - Responsive Container
        ============================================
        Uses aspect-ratio to maintain proportions while scaling.
        Width is controlled by parent wrapper (game-wrapper class).
        Internal elements use relative positioning.
      */}
      <div 
        ref={gameRef}
        className="relative rounded-3xl shadow-2xl overflow-hidden cursor-crosshair game-wrapper w-full"
        style={{ 
          aspectRatio: `${baseWidth} / ${baseHeight}`,
          maxWidth: 'inherit',
          maxHeight: '78vh',
        }}
        onMouseMove={handleMouseMove}
        onClick={handleClick}
      >
        {/* Internal scaling container - maintains pixel-based layout */}
        <div 
          className="absolute inset-0"
          style={{
            width: gameWidth,
            height: gameHeight,
            transform: 'scale(var(--game-scale, 1))',
            transformOrigin: 'top left',
          }}
        >
        {/* 🌈 LEVEL BACKGROUND - Changes every 5 levels */}
        {/* FULL AREA coverage: behind everything (z-index: 0), no tiling */}
        {currentBackground?.backgroundImageUrl ? (
          <>
            {/* Background image layer - covers ENTIRE game area */}
            <div 
              className="absolute"
              style={{ 
                inset: 0,
                width: '100%',
                height: '100%',
                backgroundImage: `url(${process.env.REACT_APP_BACKEND_URL}${currentBackground.backgroundImageUrl})`,
                backgroundSize: 'cover',
                backgroundPosition: 'center',
                backgroundRepeat: 'no-repeat',
                zIndex: 0,
              }}
            />
            {/* Overlay layer (controlled by admin slider) */}
            <div 
              className="absolute"
              style={{ 
                inset: 0,
                width: '100%',
                height: '100%',
                backgroundColor: `rgba(255, 255, 255, ${(currentBackground.backgroundOpacity || 30) / 100})`,
                backdropFilter: `blur(${(currentBackground.backgroundOpacity || 30) / 25}px)`,
                zIndex: 1,
              }}
            />
          </>
        ) : (
          /* Default background when no level background configured */
          <div 
            className="absolute bg-gradient-to-b from-sky-100/60 via-pink-50/40 to-purple-100/60" 
            style={{ inset: 0, width: '100%', height: '100%', zIndex: 0 }}
          />
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
        
        {/* Trajectory preview - starts EXACTLY from cannon muzzle */}
        {showTrajectory && isAiming && !isShooting && currentBubble && (() => {
          // Use unified getMuzzlePoint (same function as handleClick)
          const muzzle = getMuzzlePoint(shooterAngle);
          const dotRadius = CANNON_CONFIG.trajectoryDotRadius;
          
          return calculateTrajectory(shooterAngle, muzzle.x, muzzle.y).map((point, i) => (
            <div
              key={i}
              className="absolute rounded-full pointer-events-none"
              style={{
                left: point.x - dotRadius,
                top: point.y - dotRadius,
                width: dotRadius * 2,
                height: dotRadius * 2,
                background: `radial-gradient(circle, ${currentBubble.solid}70, ${currentBubble.solid}30)`,
                opacity: 1 - (i / 60) * 0.85,
                zIndex: 25,
              }}
            />
          ));
        })()}
        
        {/* Shooting bubble - z-index alto per essere visibile sopra Poppiconni */}
        {bulletPos && currentBubble && (
          <div style={{ position: 'absolute', zIndex: 30, left: 0, top: 0 }}>
            {renderBubble(currentBubble, bulletPos.x, bulletPos.y, BUBBLE_SIZE, false, 'bullet')}
          </div>
        )}
        
        {/* Shooter area - semi-transparent gradient */}
        <div 
          className="absolute bottom-0 left-0 right-0 h-36 bg-gradient-to-t from-pink-100/70 via-pink-50/40 to-transparent"
          style={{ zIndex: 15 }}
        >
          {/* 🎀 CANNON with FIXED PIVOT at base */}
          {/* Position: pivot point at shooterX, positionTop from top of shooter area */}
          <div 
            className="absolute"
            style={{ 
              left: shooterX - (CANNON_CONFIG.width / 2), // Center cannon
              top: CANNON_CONFIG.positionTop,
              zIndex: 20,
            }}
          >
            {renderToyCannon()}
          </div>
        </div>
        
        {/* 🎯 BOLLE UI - Layout ORIZZONTALE senza testo */}
        {/* Abbassato di 25px, gap aumentato a 15px */}
        <div 
          className="absolute flex flex-row items-center" 
          style={{ right: 35, bottom: 55, gap: '15px', zIndex: 25 }}
        >
          {/* Bolla ATTIVA - quella che verrà sparata ORA */}
          {currentBubble && !isShooting && (
            <div className="bg-white/70 backdrop-blur-sm rounded-full p-1.5 shadow-lg ring-2 ring-white/50">
              {renderBubble(currentBubble, 22, 22, 40, false, 'current-active')}
            </div>
          )}
          
          {/* Bolla SUCCESSIVA - la prossima (più piccola) */}
          {nextBubble && (
            <div className="bg-white/50 backdrop-blur-sm rounded-full p-1 shadow">
              {renderBubble(nextBubble, 17, 17, 32, false, 'next-queue')}
            </div>
          )}
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
