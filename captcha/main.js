const {app, BrowserWindow, Menu, Tray} = require('electron');

const captcha = require('./public/js/captcha');
const remote = require('electron').remote;
captcha.registerScheme();

let tray = null;
let mainWindow;
let trayIcon = __dirname + "/icon.png";

const isMac = process.platform === 'darwin'

function createTray() {
    tray = new Tray(trayIcon);
    const contextMenu = Menu.buildFromTemplate([
        {
            label: 'Show App',
            click: function () {
                if (mainWindow) mainWindow.show();
            }
        },
        {
            label: 'Quit',
            click: function () {
                app.isQuiting = true;
                if (mainWindow) {
                    mainWindow.close()
                } else {
                    app.quit()
                }
            }
        }
    ]);

    tray.setToolTip('Tidal Recaptcha');
    if (isMac) {
        app.dock.setIcon(trayIcon);
    }
    tray.setContextMenu(contextMenu);

    tray.on('click', function (e) {
        if (mainWindow) {
            if (mainWindow.isVisible()) {
                mainWindow.hide()
            } else {
                mainWindow.show()
            }
        }
    });
}

function createWindow() {
    // Create browser window
    mainWindow = new BrowserWindow({
        width: 350,
        height: 650,
        icon: trayIcon,
        webPreferences: {
            contextIsolation: true,
            enableRemoteModule: true
        }
    });

    mainWindow.setMenu(null);

    let template = [
        isMac ? {
            label: 'Tidal reCAPTCHA',
            submenu: [
                {label: "About Tidal reCAPTCHA", role: 'about'},
                {type: 'separator'},
                {
                    label: "Quit", accelerator: "Command+Q", click: function () {
                        app.quit();
                    }
                }
            ]
        } : {
            label: 'Tidal reCAPTCHA',
            submenu: [
                {label: 'Close', role: 'quit'}
                ]
        },
        {
            label: 'View',
            submenu: [
                {label: 'Reload', role: 'reload'},
                {label: 'Force Reload', role: 'forceReload'},
                {label: 'Toggle Developer Tools', role: 'toggleDevTools'},
                {type: 'separator'},
                {label: 'Actual Size', role: 'resetZoom'},
                {label: 'Zoom in', role: 'zoomIn'},
                {label: 'Zoom out', role: 'zoomOut'},
                {type: 'separator'},
                {label: 'Toogle Full Screen', role: 'togglefullscreen'}
            ]
        },
        {
            label: "Edit",
            submenu: [
                {label: "Undo", accelerator: "CmdOrCtrl+Z", selector: "undo:"},
                {label: "Redo", accelerator: "Shift+CmdOrCtrl+Z", selector: "redo:"},
                {type: "separator"},
                {label: "Cut", accelerator: "CmdOrCtrl+X", selector: "cut:"},
                {label: "Copy", accelerator: "CmdOrCtrl+C", selector: "copy:"},
                {label: "Paste", accelerator: "CmdOrCtrl+V", selector: "paste:"},
                {label: "Select All", accelerator: "CmdOrCtrl+A", selector: "selectAll:"}
            ]
        }
    ];

    Menu.setApplicationMenu(Menu.buildFromTemplate(template));

    mainWindow.loadFile('public/html/index.html');

    // mainWindow.openDevTools();
}

// This method will be called when Electron has finished
// initialization and is ready to create browser windows.
app.on('ready', function () {
    createTray();
    createWindow();
    captcha.registerProtocol();
});

// Quit when all windows are closed, except on macOS. There, it's common
// for applications and their menu bar to stay active until the user quits
// explicitly with Cmd + Q.
app.on('window-all-closed', () => {
    app.quit()
});
