// Copyright 2015 by Paulo Augusto Peccin. See license.txt distributed with this file.

jt.ROMLoader = function() {
    var self = this;

    this.connect = function(pCartrigeSocket, pSaveStateSocket) {
        cartridgeSocket = pCartrigeSocket;
        saveStateSocket = pSaveStateSocket;
    };

    this.registerForDnD = function (element) {
        element.addEventListener("dragover", onDragOver, false);
        element.addEventListener("drop", onDrop, false);
    };

    this.registerForFileInputElement = function (element) {
        fileInputElementParent = element;
    };

    this.openFileChooserDialog = function(withAutoPower) {
        if (!fileInputElement) createFileInputElement();
        autoPower = withAutoPower !== false;
        fileInputElement.click();
    };

    this.openURLChooserDialog = function(withAutoPower) {
        autoPower = withAutoPower !== false;
        var url;
        try {
            url = localStorage && localStorage[LOCAL_STOARAGE_LAST_URL_KEY];
        } catch (e) {
            // give up
        }
        url = prompt("Load ROM from URL:", url || "");
        if (!url) return;
        url = url.toString().trim();
        if (!url) return;
        try {
            localStorage[LOCAL_STOARAGE_LAST_URL_KEY] = url;
        } catch (e) {
            // give up
        }
        this.loadFromURL(url);
    };

    this.loadFromFile = function (file) {
        jt.Util.log("Reading ROM file: " + file.name);
        var reader = new FileReader();
        reader.onload = function (event) {
            var content = new Uint8Array(event.target.result);
            loadContent(file.name, content);
        };
        reader.onerror = function (event) {
            showError("File reading error: " + event.target.error.name);
        };

        reader.readAsArrayBuffer(file);
    };

    this.loadFromURL = function (url) {
        jt.Util.log("Reading ROM from URL: " + url);

        var req = new XMLHttpRequest();
        req.withCredentials = true;
        req.open("GET", url, true);
        req.responseType = "arraybuffer";
        req.timeout = 2000;
        req.onload = function () {
            if (req.status === 200) {
                var content = new Uint8Array(req.response);
                loadContent(url, content);
            } else
                showError("URL reading error: " + (req.statusText || req.status));
        };
        req.onerror = function () {
            showError("URL reading error: " + (req.statusText || req.status));
        };
        req.ontimeout = function () {
            showError("URL reading error: " + (req.statusText || req.status));
        };

        req.send();
    };

    var onFileInputChange = function(event) {
        event.returnValue = false;  // IE
        if (event.preventDefault) event.preventDefault();
        if (event.stopPropagation) event.stopPropagation();
        event.target.focus();
        if (!this.files || !this.files.length) return;

        var file = this.files[0];
        // Tries to clear the last selected file so the same rom can be chosen
        try {
            fileInputElement.value = "";
        } catch (e) {
            // Ignore
        }
        self.loadFromFile(file);
        return false;
    };

    var onDragOver = function (event) {
        event.returnValue = false;  // IE
        if (event.preventDefault) event.preventDefault();
        if (event.stopPropagation) event.stopPropagation();

        if (Javatari.CARTRIDGE_CHANGE_DISABLED)
            event.dataTransfer.dropEffect = "none";
        else
            event.dataTransfer.dropEffect = "link";
    };

    var onDrop = function (event) {
        event.returnValue = false;  // IE
        if (event.preventDefault) event.preventDefault();
        if (event.stopPropagation) event.stopPropagation();
        event.target.focus();

        autoPower = event.altKey !== true;

        if (Javatari.CARTRIDGE_CHANGE_DISABLED) return;
        if (!event.dataTransfer) return;

        // First try to get local file
        var files = event.dataTransfer && event.dataTransfer.files;
        if (files && files.length > 0) {
            self.loadFromFile(files[0]);
            return;
        }

        // Then try to get URL
        var url = event.dataTransfer.getData("URL");
        if (url && url.length > 0) {
            self.loadFromURL(url);
        }
    };

    var loadContent = function (name, content) {
        var cart, rom, arrContent;
        // First try reading and creating directly
        try {
            arrContent = new Array(content.length);
            jt.Util.arrayCopy(content, 0, arrContent, 0, arrContent.length);
            // Frist try to load as a SaveState file
            if (saveStateSocket.loadStateFile(arrContent)) {
                jt.Util.log("SaveState file loaded");
                return;
            }
            // Then try to load as a normal, uncompressed ROM
            rom = new jt.ROM(name, arrContent);
            cart = jt.CartridgeDatabase.createCartridgeFromRom(rom);
            if (cartridgeSocket) cartridgeSocket.insert(cart, autoPower);
        } catch(e) {
            if (!e.javatari) {
                jt.Util.log(e.stack);
                throw e;
            }

            // If it fails, try assuming its a compressed content (zip with ROMs)
            try {
                var zip = new JSZip(content);
                var files = zip.file(ZIP_INNER_FILES_PATTERN);
                for (var i = 0; i < files.length; i++) {
                    var file = files[i];
                    jt.Util.log("Trying zip file content: " + file.name);
                    try {
                        var cont = file.asUint8Array();
                        arrContent = new Array(cont.length);
                        jt.Util.arrayCopy(cont, 0, arrContent, 0, arrContent.length);
                        rom = new jt.ROM(file.name, arrContent);
                        cart = jt.CartridgeDatabase.createCartridgeFromRom(rom);
                        if (cartridgeSocket) cartridgeSocket.insert(cart, autoPower);
                        return;
                    } catch (ef) {
                        // Move on and try the next file
                    }
                }
                showError("No valid ROM files inside zip file");
            } catch(ez) {
                // Probably not a zip file. Let the original message show
                showError(e.message);
            }
        }
    };

    var showError = function(message) {
        jt.Util.log("" + message);
        jt.Util.message("Could not load ROM:\n\n" + message);
    };

    var createFileInputElement = function (element) {
        fileInputElement = document.createElement("input");
        fileInputElement.id = "ROMLoaderFileInput";
        fileInputElement.type = "file";
        fileInputElement.accept = INPUT_ELEM_ACCEPT_PROP;
        fileInputElement.style.display = "none";
        fileInputElement.addEventListener("change", onFileInputChange);
        fileInputElementParent.appendChild(fileInputElement);
    };


    var cartridgeSocket;
    var saveStateSocket;

    var fileInputElement;
    var fileInputElementParent;

    var autoPower = true;


    var ZIP_INNER_FILES_PATTERN = /^.*\.(bin|BIN|rom|ROM|a26|A26|jst|JST)$/;
    var INPUT_ELEM_ACCEPT_PROP  = ".bin,.rom,.a26,.zip,.jst";
    var LOCAL_STOARAGE_LAST_URL_KEY = "javatarilasturl";


    Javatari.loadROMFromURL = this.loadFromURL;

};