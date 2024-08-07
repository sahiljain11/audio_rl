import os
import json
import librosa

#keys = ['mspacman_JE5W3X5P3T',
#        'spaceinvaders_<key>',
#        'enduro_<key>',
#        'seaquest_<key>',
#        'mspacman_<key>']
keys = ['mspacman_JE5W3X5P3T',
        'spaceinvaders_X549THSLUZ',
        'revenge_JPR7OWTO4Y',
        "enduro_45APTZRP7R",
        "seaquest_5E9XSWHWEA"]

complete = {}

for KEY in keys:
    ROM = KEY.split('_')[0]

    traj_num = 1
    json_name = f"{KEY}_{traj_num}"
    json_path = os.path.join(os.getcwd(), f"{json_name}.json")
    wav_file  = os.path.join(os.getcwd(), f"{json_name}.wav")
    ann_file  = os.path.join(os.getcwd(), f"{json_name}_annotations.json")

    while os.path.exists(json_path):
        print(json_name)

        traj_data = {}
        f = open(json_path, "r")
        json_data = json.loads(json.load(f))

        y, sr = librosa.load(wav_file, sr=48000)
        SECONDS = librosa.get_duration(y=y, sr=sr)
        ann = open(ann_file, "r")
        ann_data = json.load(ann)

        trajectory = json_data["trajectory"]
        keys = trajectory.keys()
        n = len(keys)
        for timestep in keys:
            i = int(timestep)
            temp = {}

            data = trajectory[timestep]
            if abs(data['reward']) > 200:
                data['reward'] = 0
                data['score'] = 0

            # find the reward for the particular frame
            temp['reward'] = data['reward']
            temp['frame_num'] = i

            # determine if a particular frame had audio playing
            temp['confidence'] = 0.0
            temp['audio'] = None
            for j in ann_data.keys():
                j = ann_data[j]
                start = n * (j[0] / SECONDS)
                end   = n * (j[1] / SECONDS)
                word  = j[2]
                conf  = j[3]

                if i >= start and i < end:
                    temp['confidence'] = conf
                    temp['audio'] = word

            traj_data[i] = temp

        complete[json_name] = traj_data

        traj_num += 1
        json_name = f"{KEY}_{traj_num}"
        json_path = os.path.join(os.getcwd(), f"{json_name}.json")
        wav_file  = os.path.join(os.getcwd(), f"{json_name}.wav")
        ann_file  = os.path.join(os.getcwd(), f"{json_name}_annotations.json")
    

try:
    os.remove(f'complete.json')
except:
    pass

with open(f'complete.json', 'w') as f:
    json.dump(complete, f)