// Copyright 2015 by Paulo Augusto Peccin. See license.txt distributed with this file.

jt.TiaAudioSignal = function() {

    this.connectMonitor = function(pMonitor) {
        monitor = pMonitor;
    };

    this.cartridgeInserted = function(pCartridge) {
        if (pCartridge && pCartridge.needsAudioClock()) cartridgeNeedsAudioClock = pCartridge;
        else cartridgeNeedsAudioClock = null;
    };

    this.getChannel0 = function() {
        return channel0;
    };

    this.getChannel1 = function() {
        return channel1;
    };

    this.audioClockPulse = function() {
        if (frameSamples < samplesPerFrame)
            generateNextSamples(1);
    };

    this.signalOn = function() {
        signalOn = true;
    };

    this.signalOff = function() {
        signalOn = false;
        channel0.setVolume(0);
        channel1.setVolume(0);
    };

    this.setFps = function(fps) {
        // Normal amount is 2 sample per scanline = 31440, 524 for NTSC(60Hz) and 624 for PAL(50hz)
        // Calculate total samples per frame based on fps
        samplesPerFrame = Math.round(jt.TiaAudioSignal.SAMPLE_RATE / fps);
        if (samplesPerFrame > MAX_SAMPLES) samplesPerFrame = MAX_SAMPLES;
    };

    this.finishFrame = function() {
        var missingSamples = samplesPerFrame - frameSamples;
        if (missingSamples > 0) generateNextSamples(missingSamples);
        frameSamples = 0;
    };

    // TODO Verify choppiness in DPC audio
    this.retrieveSamples = function(quant) {
        //Util.log(">>> Samples generated: " + (nextSampleToGenerate - nextSampleToRetrieve));

        //if (nextSampleToGenerate === nextSampleToRetrieve)
        //    console.log("MATCH: " + nextSampleToGenerate );

        //if (nextSampleToGenerate < nextSampleToRetrieve)
        //    console.log("WRAP: " + nextSampleToGenerate );

        var missing = nextSampleToGenerate >= nextSampleToRetrieve
            ? quant - (nextSampleToGenerate - nextSampleToRetrieve)
            : quant - (MAX_SAMPLES - nextSampleToRetrieve + nextSampleToGenerate);

        if (missing > 0) {
            generateNextSamples(missing, true);
            //Util.log(">>> Extra samples generated: " + missing);
        } else {
            //Util.log(">>> No missing samples");
        }

        var end = nextSampleToRetrieve + quant;
        if (end >= MAX_SAMPLES) end -= MAX_SAMPLES;

        var result = retrieveResult;

        result.start = nextSampleToRetrieve;

        nextSampleToRetrieve = end;

        return result;
    };

    var generateNextSamples = function(quant, extra) {
        var mixedSample;
        for (var i = quant; i > 0; i--) {

            if (cartridgeNeedsAudioClock) cartridgeNeedsAudioClock.audioClockPulse();

            if (signalOn) {
                mixedSample = channel0.nextSample() - channel1.nextSample();
                // Add a little damper effect to round the edges of the square wave
                if (mixedSample !== lastSample) {
                    mixedSample = (mixedSample * 9 + lastSample) / 10;
                    lastSample = mixedSample;
                }
            } else {
                mixedSample = 0;
            }

            samples[nextSampleToGenerate] = mixedSample * MAX_AMPLITUDE;

            nextSampleToGenerate++;
            if (nextSampleToGenerate >= MAX_SAMPLES)
                nextSampleToGenerate = 0;
        }
        if (!extra) frameSamples += quant;
    };


    var monitor;

    var cartridgeNeedsAudioClock;

    var signalOn = false;
    var channel0 = new jt.TiaAudioChannel();
    var channel1 = new jt.TiaAudioChannel();

    var nextSampleToGenerate = 0;
    var nextSampleToRetrieve = 0;

    var samplesPerFrame =  jt.TiaAudioSignal.SAMPLE_RATE / jt.VideoStandard.NTSC.fps;
    var frameSamples = 0;

    var lastSample = 0;

    var MAX_SAMPLES = 10 * Javatari.AUDIO_BUFFER_SIZE;
    var MAX_AMPLITUDE = 0.4;

    var samples = jt.Util.arrayFill(new Array(MAX_SAMPLES), 0);

    var retrieveResult = {
        buffer: samples,
        bufferSize: MAX_SAMPLES,
        start: 0
    };

};

jt.TiaAudioSignal.SAMPLE_RATE = 31440;
