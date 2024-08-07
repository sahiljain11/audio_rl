import json
import librosa
import os

from google.cloud import speech_v1 as speech

def speech_to_text(config, speech_file, file_name):
    client = speech.SpeechClient()

    audio = speech.RecognitionAudio(uri=f"{speech_file}.wav")
    config = speech.RecognitionConfig(
        enable_word_time_offsets=True,
        language_code="en-US",
    )
    operation = client.long_running_recognize(config=config, audio=audio)
    response = operation.result(timeout=900)
    print_sentences(response, file_name)


def print_sentences(response, file_name):
    annotations = {}
    count = 0
    for result in response.results:
        best_alternative = result.alternatives[0]
        transcript = best_alternative.transcript
        confidence = best_alternative.confidence
        #print("-" * 80)
        #print(f"Transcript: {transcript}")
        #print(f"Confidence: {confidence:.0%}")

        for word in best_alternative.words:
            start_s = word.start_time.total_seconds()
            end_s = word.end_time.total_seconds()
            word = word.word
            annotations[count] = [start_s, end_s, word, confidence]
            count += 1
            print(f"{start_s:>7.3f} | {end_s:>7.3f} | {word}")

    print(f'Writing {file_name}_annotations.json...')
    try:
        os.remove(f'{file_name}_annotations.json')
    except:
        pass

    with open(f'{file_name}_annotations.json', 'w') as f:
        json.dump(annotations, f)

#def print_word_offsets(alternative):
#    for word in alternative.words:
#        start_s = word.start_time.total_seconds()
#        end_s = word.end_time.total_seconds()
#        word = word.word
#        print(f"{start_s:>7.3f} | {end_s:>7.3f} | {word}")

for i in range(1, 5):
    #file_name = f"revenge_JPR7OWTO4Y_{i}"
    #file_name = f"spaceinvaders_X549THSLUZ_{i}"
    #file_name = f"mspacman_JE5W3X5P3T_{i}"
    #file_name = f"enduro_45APTZRP7R_{i}"
    file_name = f"seaquest_5E9XSWHWEA_{i}"
    config = dict(language_code="en-US")
    audio = f"gs://roboatari/{file_name}"
    speech_to_text(config, audio, file_name)
