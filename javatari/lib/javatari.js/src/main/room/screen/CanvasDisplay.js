// Copyright 2015 by Paulo Augusto Peccin. See license.txt distributed with this file.

// TODO Implement phosphor and other CRT modes
jt.CanvasDisplay = function(mainElement) {

    function init(self) {
        setupProperties();
        setupMain();
        setupOSD();
        //setupButtonsBar();
        loadImages();
        context = canvas.getContext("2d");
        monitor = new jt.Monitor();
        monitor.connectDisplay(self);
        monitor.addControlInputElements(self.keyControlsInputElements());
    }

    this.connectPeripherals = function(pROMLoader, stateMedia) {
        pROMLoader.registerForDnD(mainElement);
        pROMLoader.registerForFileInputElement(mainElement);
        stateMedia.registerForDownloadElement(mainElement);
        monitor.connectPeripherals(pROMLoader);
    };

    this.connect = function(pVideoSignal, pControlsSocket, pCartridgeSocket) {
        monitor.connect(pVideoSignal, pCartridgeSocket);
        controlsSocket = pControlsSocket;
    };

    this.powerOn = function() {
        mainElement.style.visibility = "visible";
        this.focus();
        drawLogo();
    };

    this.powerOff = function() {
        mainElement.style.visibility = "hidden";
        mainElement.style.display = "none";
    };

    this.refresh = function(image, iWidth, iHeight) {
        signalIsOn = true;
        context.drawImage(image, 0, 0, iWidth, iHeight, 0, 0, canvas.width, canvas.height);
    };

    this.adjustToVideoSignalOff = function() {
        signalIsOn = false;
        drawLogo();
    };

    this.keyControlsInputElements = function() {
        return [mainElement];
    };

    //noinspection JSUnusedLocalSymbols
    this.displayDefaultOpeningScaleX = function(displayWidth, displayHeight) {
        if (isFullscreen) {
            var winW = fsElement.clientWidth;
            var winH = fsElement.clientHeight;
            var scaleX = winW / displayWidth;
            scaleX -= (scaleX % DEFAULT_SCALE_ASPECT_X);		// Round multiple of the default X scale
            var h = scaleX / DEFAULT_SCALE_ASPECT_X * displayHeight;
            while (h > winH + 35) {										// 35 is a little tolerance
                scaleX -= DEFAULT_SCALE_ASPECT_X;				// Decrease one full default X scale
                h = scaleX / DEFAULT_SCALE_ASPECT_X * displayHeight;
            }
            return scaleX | 0;
        } else
            return DEFAULT_OPENING_SCALE_X;
    };

    this.displaySize = function(width, height) {
        setElementsSizes(width, height);
        setCRTFilter();
        if (!signalIsOn) drawLogo();
    };

    this.displayMinimumSize = function(width, height) {
    };

    this.displayCenter = function() {
        this.focus();
    };

    this.getMonitor = function() {
        return monitor;
    };

    this.showOSD = function(message, overlap) {
        //Util.log(message);
        if (osdTimeout) clearTimeout(osdTimeout);
        if (!message) {
            osd.style.transition = "all 0.15s linear";
            osd.style.top = "-29px";
            osd.style.opacity = 0;
            osdShowing = false;
            return;
        }
        if (overlap || !osdShowing) osd.innerHTML = message;
        osd.style.transition = "none";
        osd.style.top = "15px";
        osd.style.opacity = 1;
        osdShowing = true;
        osdTimeout = setTimeout(function() {
            osd.style.transition = "all 0.15s linear";
            osd.style.top = "-29px";
            osd.style.opacity = 0;
            osdShowing = false;
        }, OSD_TIME);
    };

    this.toggleCRTFilter = function() {
        crtFilter = !crtFilter;
        this.showOSD(crtFilter ? "CRT Filter: ON" : "CRT Filter: OFF", true);
        setCRTFilter();
    };

    //noinspection JSUnresolvedFunction
    this.displayToggleFullscreen = function() {
        if (Javatari.SCREEN_FULLSCREEN_DISABLED) return;

        if (!document.fullscreenElement && !document.webkitFullscreenElement && !document.mozFullScreenElement && !document.msFullscreenElement) {
            if (fsElement.requestFullscreen)
                fsElement.requestFullscreen();
            else if (fsElement.webkitRequestFullscreen)
                fsElement.webkitRequestFullscreen();
            else if (fsElement.webkitRequestFullScreen)
                fsElement.webkitRequestFullScreen(Element.ALLOW_KEYBOARD_INPUT);
            else if (fsElement.mozRequestFullScreen)
                fsElement.mozRequestFullScreen();
            else if (fsElement.msRequestFullscreen)
                fsElement.msRequestFullscreen();
            else
                this.showOSD("Fullscreen is not supported by your browser!");
        } else {
            if (document.exitFullscreen) {
                document.exitFullscreen();
            } else if (document.webkitExitFullscreen) {
                document.webkitExitFullscreen();
            } else if (document.mozCancelFullScreen) {
                document.mozCancelFullScreen();
            } else if (document.msExitFullscreen) {
                document.msExitFullscreen();
            }
        }
    };

    this.exit = function() {
        controlsSocket.controlStateChanged(jt.ConsoleControls.POWER_OFF, true);
        monitor.controlActivated(jt.Monitor.Controls.SIZE_DEFAULT);
    };

    this.focus = function() {
        canvas.focus();
    };

    var openSettings = function(page) {
        if (!settings) settings = new jt.Settings();
        settings.show(page);
    };

    var fullScreenChanged = function() {
        var fse = document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement || document.msFullscreenElement;
        isFullscreen = !!fse;
        monitor.controlActivated(jt.Monitor.Controls.SIZE_DEFAULT);
        // Schedule another one to give the browser some time to set full screen properly
        if (isFullscreen)
            setTimeout(function() {
                monitor.controlActivated(jt.Monitor.Controls.SIZE_DEFAULT);
            }, 120);
    };

    var setElementsSizes = function (width, height) {
        canvas.width = width;
        canvas.height = height;
        canvas.style.width = "" + width + "px";
        canvas.style.height = "" + height + "px";
        // Do not change containers sizes while in fullscreen
        if (isFullscreen) return;
        borderElement.style.width = "" + width + "px";
        borderElement.style.height = "" + height + "px";
        width += borderLateral * 2;
        height += borderTop + borderBottom;
        mainElement.style.width = "" + width + "px";
        mainElement.style.height = "" + height + "px";
    };

    var setCRTFilter = function() {
        if (context.imageSmoothingEnabled !== undefined) {
            context.imageSmoothingEnabled = crtFilter;
        } else {
            context.webkitImageSmoothingEnabled = crtFilter;
            context.mozImageSmoothingEnabled = crtFilter;
            context.msImageSmoothingEnabled = crtFilter;
        }
    };

    var drawLogo = function () {
        context.fillStyle = "black";
        context.fillRect(0, 0, canvas.width, canvas.height);
        if (logoImage.isLoaded) {
            var logoWidth = logoImage.width;
            var logoHeight = logoImage.height;
            if (logoHeight > canvas.height * 0.7) {
                var factor = (canvas.height * 0.7) / logoHeight;
                logoHeight = (logoHeight * factor) | 0;
                logoWidth = (logoWidth * factor) | 0;
            }
            context.drawImage(logoImage, ((canvas.width - logoWidth) / 2) | 0, ((canvas.height - logoHeight) / 2) | 0, logoWidth, logoHeight);
        }
    };

    var setupMain = function () {
        mainElement.style.position = "relative";
        mainElement.style.overflow = "hidden";
        mainElement.style.outline = "none";
        mainElement.tabIndex = "-1";               // Make it focusable

        borderElement = document.createElement('div');
        borderElement.style.position = "relative";
        borderElement.style.overflow = "hidden";
        borderElement.style.background = "black";
        borderElement.style.border = "0 solid black";
        borderElement.style.borderWidth = "" + borderTop + "px " + borderLateral + "px " + borderBottom + "px";
        if (Javatari.SCREEN_CONTROL_BAR === 2) {
            borderElement.style.borderImage = "url(" + IMAGE_PATH + "screenborder.png) " +
                borderTop + " " + borderLateral + " " + borderBottom + " repeat stretch";
        }

        fsElement = document.createElement('div');
        fsElement.style.position = "relative";
        fsElement.style.width = "100%";
        fsElement.style.height = "100%";
        fsElement.style.overflow = "hidden";
        fsElement.style.background = "black";

        document.addEventListener("fullscreenchange", fullScreenChanged);
        document.addEventListener("webkitfullscreenchange", fullScreenChanged);
        document.addEventListener("mozfullscreenchange", fullScreenChanged);
        document.addEventListener("msfullscreenchange", fullScreenChanged);

        borderElement.appendChild(fsElement);

        canvas = document.createElement('canvas');
        canvas.style.position = "absolute";
        canvas.style.display = "block";
        canvas.style.left = canvas.style.right = 0;
        canvas.style.top = canvas.style.bottom = 0;
        canvas.style.margin = "auto";
        canvas.tabIndex = "-1";               // Make it focusable
        canvas.style.outline = "none";
        fsElement.appendChild(canvas);

        setElementsSizes(jt.CanvasDisplay.DEFAULT_STARTING_WIDTH, jt.CanvasDisplay.DEFAULT_STARTING_HEIGHT);

        mainElement.appendChild(borderElement);
    };

    var setupButtonsBar = function() {
        buttonsBar = document.createElement('div');
        buttonsBar.style.position = "absolute";
        buttonsBar.style.left = "0";
        buttonsBar.style.right = "0";
        buttonsBar.style.height = "29px";
        if (Javatari.SCREEN_CONTROL_BAR === 2) {
            buttonsBar.style.bottom = "0";
            // No background
        } else if (Javatari.SCREEN_CONTROL_BAR === 1) {
            buttonsBar.style.bottom = "-30px";
            buttonsBar.style.background = "rgba(47, 47, 43, .8)";
            buttonsBar.style.transition = "bottom 0.3s ease-in-out";
            mainElement.addEventListener("mouseover", function() {
                if (buttonsBarHideTimeout) clearTimeout(buttonsBarHideTimeout);
                buttonsBar.style.bottom = "0px";
            });
            mainElement.addEventListener("mouseleave", function() {
                buttonsBarHideTimeout = setTimeout(function() {
                    buttonsBar.style.bottom = "-30px";
                }, 1000);
            });
        } else {
            buttonsBar.style.bottom = "0";
            buttonsBar.style.background = "rgb(44, 44, 40)";
            buttonsBar.style.border = "1px solid black";
        }

        powerButton  = addBarButton(6, -26, 24, 23, -436, -208);
        consoleControlButton(powerButton, jt.ConsoleControls.POWER);
        var fsGap = 23;
        if (!Javatari.SCREEN_FULLSCREEN_DISABLED) {
            fullscreenButton = addBarButton(-53, -26, 24, 22, -387, -209);
            screenControlButton(fullscreenButton, jt.Monitor.Controls.FULLSCREEN);
            fsGap = 0;
        }
        if (!Javatari.SCREEN_RESIZE_DISABLED) {
            scaleDownButton = addBarButton(-92 + fsGap, -26, 18, 22, -342, -209);
            screenControlButton(scaleDownButton, jt.Monitor.Controls.SIZE_MINUS);
            scaleUpButton = addBarButton(-74 + fsGap, -26, 21, 22, -364, -209);
            screenControlButton(scaleUpButton, jt.Monitor.Controls.SIZE_PLUS);
        }

        settingsButton  = addBarButton(-29, -26, 24, 22, -412, -209);
        settingsButton.style.cursor = "pointer";
        settingsButton.addEventListener("mousedown", function (e) {
            if (e.preventDefault) e.preventDefault();
            openSettings();
        });

        logoButton = addBarButton("CENTER", -26, 24, 24, -388, -181);
        logoButton.style.cursor = "pointer";
        logoButton.addEventListener("mousedown", function (e) {
            if (e.preventDefault) e.preventDefault();
            openSettings("ABOUT");
        });

        mainElement.appendChild(buttonsBar);
    };

    var addBarButton = function(x, y, w, h, px, py, noImage) {
        var but = document.createElement('div');
        but.style.position = "absolute";
        if (x === "CENTER") {
            but.style.left = but.style.right = 0;
            but.style.margin = "0 auto";
        } else if (x > 0) but.style.left = "" + x + "px"; else but.style.right = "" + (-w - x) + "px";
        if (y > 0) but.style.top = "" + y + "px"; else but.style.bottom = "" + (-h - y) + "px";
        but.style.width = "" + w + "px";
        but.style.height = "" + h + "px";
        but.style.outline = "none";

        if (!noImage) {
            but.style.backgroundImage = "url(" + IMAGE_PATH + "sprites.png" + ")";
            but.style.backgroundPosition = "" + px + "px " + py + "px";
            but.style.backgroundRepeat = "no-repeat";
        }

        buttonsBar.appendChild(but);

        //but.style.boxSizing = "border-box";
        //but.style.backgroundOrigin = "border-box";
        //but.style.border = "1px solid yellow";

        return but;
    };

    var screenControlButton = function (but, control) {
        but.style.cursor = "pointer";
        but.addEventListener("mousedown", function (e) {
            if (e.preventDefault) e.preventDefault();
            monitor.controlActivated(control);
        });
    };

    var consoleControlButton = function (but, control) {
        but.style.cursor = "pointer";
        but.addEventListener("mousedown", function (e) {
            if (e.preventDefault) e.preventDefault();
            controlsSocket.controlStateChanged(control, true);
        });
    };

    var loadImages = function() {
        logoImage = new Image();
        logoImage.isLoaded = false;
        logoImage.onload = function() {
            logoImage.isLoaded = true;
            drawLogo();
        };
        logoImage.src = IMAGE_PATH + "logo.png";
    };

    var setupOSD = function() {
        osd = document.createElement('div');
        osd.style.position = "absolute";
        osd.style.overflow = "hidden";
        osd.style.top = "-29px";
        osd.style.right = "18px";
        osd.style.height = "29px";
        osd.style.padding = "0 12px";
        osd.style.margin = "0";
        osd.style.font = 'bold 15px/29px sans-serif';
        osd.style.color = "rgb(0, 255, 0)";
        osd.style.background = "rgba(0, 0, 0, 0.4)";
        osd.style.opacity = 0;
        osd.innerHTML = "";
        fsElement.appendChild(osd);
    };

    var setupProperties = function() {
        if (Javatari.SCREEN_CONTROL_BAR === 2) {            // Legacy
            borderTop = 5;
            borderLateral = 5;
            borderBottom = 31;
        } else if (Javatari.SCREEN_CONTROL_BAR === 1) {     // Hover
            borderTop = 1;
            borderLateral = 1;
            borderBottom = 1;
        } else {                                                // Always
            borderTop = 1;
            borderLateral = 1;
            borderBottom = 30;
        }
    };

    var monitor;
    var controlsSocket;
    var settings;

    var borderElement;
    var fsElement;

    var canvas;
    var context;

    var buttonsBar;
    var buttonsBarHideTimeout;

    var osd;
    var osdTimeout;
    var osdShowing = false;

    var signalIsOn = false;
    var crtFilter = false;
    var isFullscreen = false;

    var logoImage;

    var powerButton;
    var logoButton;
    var scaleDownButton;
    var scaleUpButton;
    var fullscreenButton;
    var settingsButton;

    var borderTop;
    var borderLateral;
    var borderBottom;


    var IMAGE_PATH = Javatari.IMAGES_PATH;
    var OSD_TIME = 2500;
    var DEFAULT_SCALE_ASPECT_X = 2;
    var DEFAULT_OPENING_SCALE_X = (Javatari.SCREEN_OPENING_SIZE || 2) * 2;


    init(this);

};

jt.CanvasDisplay.DEFAULT_STARTING_WIDTH = 640;
jt.CanvasDisplay.DEFAULT_STARTING_HEIGHT = 426;
