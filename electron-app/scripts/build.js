#!/usr/bin/env node
/**
 * Build script for Electron application
 * Handles both development and production builds
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const args = process.argv.slice(2);
const isProduction = args.includes('--production') || process.env.NODE_ENV === 'production';

console.log('🔨 Building Electron application...');
console.log(`📦 Mode: ${isProduction ? 'Production' : 'Development'}`);

// Clean dist directory
console.log('🧹 Cleaning dist directory...');
const distPath = path.join(__dirname, '..', 'dist');
if (fs.existsSync(distPath)) {
  fs.rmSync(distPath, { recursive: true, force: true });
}

// Build TypeScript files
console.log('🔧 Compiling TypeScript...');
try {
  execSync('npx tsc', { stdio: 'inherit' });
} catch (error) {
  console.error('❌ TypeScript compilation failed:', error.message);
  process.exit(1);
}

// Build with Vite
console.log('📦 Building with Vite...');
try {
  const viteCommand = isProduction ? 'npx vite build' : 'npx vite build --mode development';
  execSync(viteCommand, { stdio: 'inherit' });
} catch (error) {
  console.error('❌ Vite build failed:', error.message);
  process.exit(1);
}

// Copy Python bridge script
console.log('🐍 Copying Python bridge...');
const pythonSrc = path.join(__dirname, '..', 'src', 'main', 'services', 'python-bridge.py');
const pythonDest = path.join(__dirname, '..', 'dist', 'main', 'services', 'python-bridge.py');
const pythonDestDir = path.dirname(pythonDest);

if (!fs.existsSync(pythonDestDir)) {
  fs.mkdirSync(pythonDestDir, { recursive: true });
}
fs.copyFileSync(pythonSrc, pythonDest);

// Copy assets if they exist
const assetsPath = path.join(__dirname, '..', 'assets');
if (fs.existsSync(assetsPath)) {
  console.log('🎨 Copying assets...');
  const assetsDest = path.join(__dirname, '..', 'dist', 'assets');
  fs.cpSync(assetsPath, assetsDest, { recursive: true });
}

// Create package.json for production
if (isProduction) {
  console.log('📋 Creating production package.json...');
  const originalPackage = require('../package.json');
  const productionPackage = {
    name: originalPackage.name,
    version: originalPackage.version,
    main: 'main/index.js',
    dependencies: originalPackage.dependencies
  };
  
  fs.writeFileSync(
    path.join(distPath, 'package.json'),
    JSON.stringify(productionPackage, null, 2)
  );
}

console.log('✅ Build completed successfully!');

// Run electron-builder if production
if (isProduction && args.includes('--package')) {
  console.log('📦 Packaging application with electron-builder...');
  try {
    execSync('npx electron-builder', { stdio: 'inherit' });
    console.log('✅ Packaging completed!');
  } catch (error) {
    console.error('❌ Packaging failed:', error.message);
    process.exit(1);
  }
}