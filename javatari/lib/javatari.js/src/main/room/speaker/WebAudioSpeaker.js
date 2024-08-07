// Copyright 2015 by Paulo Augusto Peccin. See license.txt distributed with this file.

jt.WebAudioSpeaker = function() {

    this.connect = function(pAudioSignal) {
        audioSignal = pAudioSignal;
        audioSignal.connectMonitor(this);
    };

    this.powerOn = function() {
        createAudioContext();
        if (!audioContext) return;

        processor = audioContext.createScriptProcessor(Javatari.AUDIO_BUFFER_SIZE, 0, 1);
        processor.onaudioprocess = onAudioProcess;
        this.play();
    };

    this.powerOff = function() {
        this.mute();
        audioContext = undefined;
    };

    this.play = function () {
        if (processor) processor.connect(audioContext.destination);
    };

    this.mute = function () {
        if (processor) processor.disconnect();
    };

    var createAudioContext = function() {
        try {
            var constr = (window.AudioContext || window.webkitAudioContext || window.WebkitAudioContext);
            if (!constr) throw new Error("WebAudio API not supported by the browser");
            audioContext = new constr();
            resamplingFactor = jt.TiaAudioSignal.SAMPLE_RATE / audioContext.sampleRate;
            jt.Util.log("Speaker AudioContext created. Sample rate: " + audioContext.sampleRate);
            //jt.Util.log("Audio resampling factor: " + (1/resamplingFactor));
        } catch(e) {
            jt.Util.log("Could not create AudioContext. Audio disabled.\n" + e.message);
        }
    };

    var onAudioProcess = function(event) {
        if (!audioSignal) return;

        // Assumes there is only one channel
        var outputBuffer = event.outputBuffer.getChannelData(0);
        // TODO Be aware of fractional samples to avoid +1 here
        var input = audioSignal.retrieveSamples(((outputBuffer.length * resamplingFactor) | 0) + 1);
        jt.Util.arrayCopyCircularSourceWithStep(
            input.buffer, input.start, input.bufferSize, resamplingFactor,
            outputBuffer, 0, outputBuffer.length
        );
    };


    var audioSignal;
    var resamplingFactor;

    var audioContext;
    var processor;

};
