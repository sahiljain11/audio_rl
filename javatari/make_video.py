import json
import os
import librosa
import argparse
import subprocess


def main(args: dict) -> None:

    dir_list = os.listdir(os.getcwd())

    TRAJ_NAME = f"{args.key}"

    if TRAJ_NAME not in dir_list:
        raise FileNotFoundError(f"Could not find directory: {TRAJ_NAME}")

    print(f"Generating {TRAJ_NAME}...")
    print("=" * 80)

    splitted = TRAJ_NAME.split("_")

    # get the strings for the file names
    WEBM_FILE  = f"{TRAJ_NAME}.webm"
    WAV_FILE   = f"{TRAJ_NAME}.wav"
    JSON_FILE  = f"{TRAJ_NAME}.json"
    ATARI_FILE = f"{splitted[0]}_{splitted[1]}_atari_{splitted[2]}.wav"

    # calculate the number of frames
    with open(os.path.join(os.getcwd(), JSON_FILE)) as f:
        data = json.load(f)

    data = json.loads(data)
    NUM_FRAMES = len(data["time_stamp"])

    # get the number of seconds the wav file lasts so you can calculate FPS
    y, sr = librosa.load(ATARI_FILE, sr=48000)
    SECONDS = librosa.get_duration(y=y, sr=sr)
    FPS = int(round(NUM_FRAMES / SECONDS))

    print(NUM_FRAMES)
    print(SECONDS)
    print(FPS)

    # create a shell script
    f = open(os.path.join(os.getcwd(), f'make_video.sh'), 'w')

    f.write(f'ffmpeg -i {WEBM_FILE} -vn {WAV_FILE}\n')

    # turns all of the images into one video file
    #command = f'ffmpeg -r 24 -start_number 1 -i {TRAJ_NAME}/{TRAJ_NAME}_%01d.png -c:v libx264 -vf "fps={FPS},format=yuv420p" -vf "pad=ceil(iw/2)*2:ceil(ih/2)*2" out.mp4\n'
    command = f'ffmpeg -r {FPS} -start_number 1 -i {TRAJ_NAME}/{TRAJ_NAME}_%01d.png -c:v libx264 -vf "fps={FPS},format=yuv420p" -vf "pad=ceil(iw/2)*2:ceil(ih/2)*2" out.mp4\n'
    f.write(command)

    # combines the user's audio and the atari audio
    f.write(f'ffmpeg -i {WAV_FILE} -i {ATARI_FILE} -filter_complex "[0][1]amerge=inputs=2,pan=stereo|FL<c0+c1|FR<c2+c3[a]" -map "[a]" output.wav\n')

    # adds the audio to the video
    f.write(f"ffmpeg -i out.mp4 -i output.wav -c:v copy -c:a aac {TRAJ_NAME}_final.mp4\n")

    # turn mp4 into mov
    command = f"ffmpeg -i {TRAJ_NAME}_final.mp4 -f mov {TRAJ_NAME}_final.mov\n"
    f.write(command)

    f.write(f"rm {TRAJ_NAME}.wav\n")
    f.write(f"rm out.mp4\n")
    f.write(f"rm output.wav\n")
    f.write(f"rm {TRAJ_NAME}_final.mp4\n")

    f.close()

    # run the shell script
    subprocess.call(['sh', './make_video.sh'])
    os.system("rm ./make_video.sh")



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Turn atari data into a single mp4')
    parser.add_argument('--key', help="Enter the MTurk key user provided. Ex: mspacman_JE5W3X5P3T_1")

    args = parser.parse_args()

    main(args)