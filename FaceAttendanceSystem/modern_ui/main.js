const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn, execSync } = require('child_process');
const http = require('http');
const fs = require('fs');

let mainWindow;
let splashWindow;
let pythonProcess;

// ──────────────────────────────────────────────
// Splash / Loading Screen
// ──────────────────────────────────────────────
function createSplashWindow() {
  splashWindow = new BrowserWindow({
    width: 460,
    height: 420,
    frame: false,
    transparent: true,
    resizable: false,
    alwaysOnTop: true,
    skipTaskbar: false,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  splashWindow.loadFile(path.join(__dirname, 'loading.html'));
  splashWindow.center();
}

function sendSplashStatus(status, message, percent) {
  if (splashWindow && !splashWindow.isDestroyed()) {
    splashWindow.webContents.send('loading-status', { status, message, percent });
  }
}

// ──────────────────────────────────────────────
// Main Application Window
// ──────────────────────────────────────────────
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    show: false, // Don't show until ready
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    },
    titleBarStyle: 'hidden',
    titleBarOverlay: {
      color: '#ffffff',
      symbolColor: '#000000',
    }
  });

  mainWindow.loadFile(path.join(__dirname, 'index.html'));

  mainWindow.once('ready-to-show', () => {
    // Close splash and show main window
    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.close();
      splashWindow = null;
    }
    mainWindow.show();
    mainWindow.focus();
  });
}

// ──────────────────────────────────────────────
// Python Backend Management
// ──────────────────────────────────────────────
function findPython() {
  // Try system Python first (where packages are installed)
  const systemPython = 'C:\\Users\\manda\\AppData\\Local\\Programs\\Python\\Python314\\python.exe';
  if (fs.existsSync(systemPython)) {
    console.log('Using system Python:', systemPython);
    return systemPython;
  }
  
  // Fallback: try 'python' from PATH
  try {
    const pythonPath = execSync('where python', { encoding: 'utf-8' }).split('\n')[0].trim();
    console.log('Using PATH Python:', pythonPath);
    return pythonPath;
  } catch (e) {
    console.log('Falling back to python command');
    return 'python';
  }
}

function getPaths() {
  let pythonExe, cwd, apiPath;

  if (app.isPackaged) {
    // Installed via setup.exe — backend is at {app}/backend/
    const appDir = path.dirname(app.getPath('exe'));
    const backendPath = path.join(appDir, 'backend');
    pythonExe = path.join(backendPath, 'Python314', 'python.exe');
    cwd = path.join(backendPath, 'app');
    apiPath = path.join(cwd, 'api.py');

    // Fallback: check resources path (electron-builder default)
    if (!fs.existsSync(pythonExe)) {
      const altBackend = path.join(process.resourcesPath, '..', 'backend');
      if (fs.existsSync(path.join(altBackend, 'Python314', 'python.exe'))) {
        pythonExe = path.join(altBackend, 'Python314', 'python.exe');
        cwd = path.join(altBackend, 'app');
        apiPath = path.join(cwd, 'api.py');
      }
    }

    console.log('Running packaged mode.');
    console.log('  Python:', pythonExe);
    console.log('  CWD:', cwd);
    console.log('  API:', apiPath);
    console.log('  Python exists:', fs.existsSync(pythonExe));
    console.log('  API exists:', fs.existsSync(apiPath));
  } else {
    // Development mode
    pythonExe = findPython();
    cwd = path.join(__dirname, '..');
    apiPath = path.join(cwd, 'api.py');
    console.log('Running dev mode. Python:', pythonExe, 'API:', apiPath);
  }

  return { pythonExe, cwd, apiPath };
}

function startPythonBackend() {
  return new Promise((resolve) => {
    const { pythonExe, cwd, apiPath } = getPaths();

    // Validate paths exist
    if (!fs.existsSync(pythonExe)) {
      console.error('Python executable not found at:', pythonExe);
      sendSplashStatus('error', `Python not found at: ${pythonExe}`, 100);
      resolve(false);
      return;
    }

    if (!fs.existsSync(apiPath)) {
      console.error('API script not found at:', apiPath);
      sendSplashStatus('error', `API script not found at: ${apiPath}`, 100);
      resolve(false);
      return;
    }

    sendSplashStatus('progress', 'Starting Python AI Engine', 10);

    // Kill any existing process
    if (pythonProcess) {
      try { pythonProcess.kill(); } catch (e) {}
    }

    pythonProcess = spawn(pythonExe, [apiPath], { 
      cwd: cwd,
      env: { ...process.env, PYTHONUNBUFFERED: '1' }
    });

    pythonProcess.stdout.on('data', (data) => {
      console.log(`Python: ${data}`);
    });

    pythonProcess.stderr.on('data', (data) => {
      const msg = data.toString();
      console.error(`Python: ${msg}`);
      // Flask prints "Running on http://..." to stderr
      if (msg.includes('Running on')) {
        sendSplashStatus('progress', 'Server started, verifying', 70);
      }
    });

    pythonProcess.on('error', (err) => {
      console.error('Failed to start Python process:', err);
      sendSplashStatus('error', `Failed to start Python: ${err.message}`, 100);
      resolve(false);
    });

    pythonProcess.on('exit', (code) => {
      console.error('Python process exited with code:', code);
      if (code !== null && code !== 0) {
        sendSplashStatus('error', `Python exited with code ${code}. Check logs.`, 100);
      }
    });

    // Now wait for the API to become available
    sendSplashStatus('progress', 'Starting Services', 25);
    
    let attempts = 0;
    const maxAttempts = 60; // 60 seconds timeout
    
    const progressStages = [
      { at: 5,  msg: 'Initializing Secure Modules', pct: 30 },
      { at: 12, msg: 'Calibrating AI Engine', pct: 50 },
      { at: 25, msg: 'Synchronizing Workspace', pct: 70 },
      { at: 40, msg: 'Finalizing Startup', pct: 90 },
    ];

    const check = () => {
      attempts++;
      
      // Update progress messages based on attempt count
      const stage = progressStages.filter(s => s.at <= attempts).pop();
      if (stage) {
        sendSplashStatus('progress', stage.msg, stage.pct);
      }

      const req = http.get('http://127.0.0.1:5000/api/health', (res) => {
        console.log('API is ready! Status:', res.statusCode);
        sendSplashStatus('ready', 'Ready! Launching application...', 100);
        setTimeout(() => resolve(true), 500); // Small delay for visual
      });
      
      req.on('error', () => {
        if (attempts >= maxAttempts) {
          console.error('Python API failed to start after', maxAttempts, 'attempts.');
          sendSplashStatus('error', 'API server did not respond within 60 seconds. The backend may have crashed.', 100);
          resolve(false);
        } else {
          setTimeout(check, 1000);
        }
      });
      
      req.setTimeout(2000, () => {
        req.destroy();
      });
    };
    
    // Give Python 2 seconds head start before first check
    setTimeout(check, 2000);
  });
}

// ──────────────────────────────────────────────
// App Lifecycle
// ──────────────────────────────────────────────
app.whenReady().then(async () => {
  // Show splash screen immediately
  createSplashWindow();

  // Start the backend and wait
  const success = await startPythonBackend();

  if (success) {
    createWindow();
  }
  // If failed, splash screen shows the error with retry button

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) {
      createSplashWindow();
      startPythonBackend().then((ok) => { if (ok) createWindow(); });
    }
  });
});

// Handle retry from splash screen
ipcMain.on('retry-backend', async () => {
  console.log('Retrying backend startup...');
  const success = await startPythonBackend();
  if (success) {
    createWindow();
  }
});

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit();
});

app.on('will-quit', () => {
  if (pythonProcess) {
    pythonProcess.kill();
  }
});
