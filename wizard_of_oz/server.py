import json
import pickle
from typing import List

import numpy as np
from flask import Flask, jsonify, request, render_template, Response
from flask_socketio import SocketIO, join_room, leave_room, emit, send
import redis
import os
import boto3
from urllib.parse import urlparse

from twilio.rest import Client
import subprocess
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VideoGrant, ChatGrant

from env import RoboTaxiEnv
import logging
import tempfile
import time

# FOR TESTING   
print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
print("NEW GAME")
print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
logging.getLogger('socketio').setLevel(logging.INFO)
logging.getLogger('engineio').setLevel(logging.INFO)


last_key_time = 0


# Flask
app = Flask(__name__, static_url_path='/static', static_folder='static/')
app.config['FLASK_SECRET_KEY'] = os.urandom(24).hex()
socketio = SocketIO(app, cors_allowed_origins="*", ping_timeout=60 * 2, ping_interval=60 * 10)


# Twilio
twilio_account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
twilio_api_key_sid = os.environ.get('TWILIO_API_KEY_SID')
twilio_api_key_secret = os.environ.get('TWILIO_API_KEY_SECRET')

if twilio_account_sid is None:
    raise Exception('Please add the environment variable `export TWILIO_ACCOUNT_SID`')
    
if twilio_api_key_sid is None:
    raise Exception('Please add the environment variable `export TWILIO_API_KEY_SID`')

if twilio_api_key_secret is None:
    raise Exception('Please add the environment variable `export TWILIO_API_KEY_SECRET`')

#twilio_client = Client(twilio_api_key_sid, twilio_api_key_secret, twilio_account_sid)
#twilio_client = Client(twilio_api_key_sid, twilio_api_key_secret)

# S3
if os.path.exists('secret_constants.json'):
    with open("secret_constants.json") as f:
        data = json.load(f)
        AWS_KEY        = data.get("AMAZON_CLIENT_KEY")
        AWS_SECRET_KEY = data.get("AMAZON_SECRET_CLIENT_KEY")
        AWS_REGION     = data.get("AMAZON_REGION")
else:
    AWS_KEY        = os.environ.get("AMAZON_CLIENT_KEY")
    AWS_SECRET_KEY = os.environ.get("AMAZON_SECRET_CLIENT_KEY")
    AWS_REGION     = os.environ.get("AMAZON_REGION")

if AWS_KEY is None or AWS_SECRET_KEY is None or AWS_REGION is None:
    raise Exception('Please add your AWS keys')

s3 = boto3.client('s3', region_name=AWS_REGION,
                  aws_access_key_id=AWS_KEY,
                  aws_secret_access_key=AWS_SECRET_KEY)

# Redis
redis_host = os.environ.get('REDIS_HOST', 'localhost')
redis_port = int(os.environ.get('REDIS_PORT', '6379'))
if redis_host == 'localhost':
    db = redis.Redis(host=redis_host, port=redis_port)
else:
    print(os.environ.get("REDIS_URL"))
    url = urlparse(os.environ.get("REDIS_URL"))
    db = redis.Redis(host=url.hostname, port=url.port, password=url.password, ssl=True, ssl_cert_reqs=None)

#db.flushall()

#s3 = boto3.client('s3')

# session = boto3.Session(
#     aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
#     aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
# )
# s3 = session.resource('s3')
S3_BUCKET = os.environ.get('S3_BUCKET_NAME')
if S3_BUCKET is None:
    raise Exception('Please add your AWS bucket name `export S3_BUCKET_NAME=name`')
#S3_BUCKET = 'interactiverl'


config = {}
with open('config.json') as config_file:
    config = json.load(config_file)


@app.route("/")
def homepage():
    return render_template('index.html')


@app.route("/consent")
def consent():
    return render_template('consent.html')


@app.route("/login")
def login():
    return render_template('login.html')


@app.route("/baseline")
def baseline():
    pid = request.args.get('pid')
    if not pid:
        response = jsonify({'message': 'ERROR: pid, role not specified in request'})
        response.status_code = 400
        return response
    return render_template('baseline.html', pid=pid)


@app.route("/instructions")
def instructions():
    pid = request.args.get('pid')
    if not pid:
        response = jsonify({'message': 'ERROR: pid, role not specified in request'})
        response.status_code = 400
        return response

    role = pid.upper()[0]
    return render_template('instructions.html', role=role, pid=pid)


@app.route("/game")
def game():
    pid = request.args.get('pid')
    if not pid:
        response = jsonify({'message': 'ERROR: pid, role not specified in request'})
        response.status_code = 400
        return response

    role = pid.upper()[0]
    return render_template('game.html', role=role, pid=pid)

@app.route("/replay")
def replay():
    return render_template('replay.html', role='W', pid='00000')

@app.route("/createReplay")
def create_replay():

    files = request.form.items()
    print(files)

    return {"temp" : "temp"}

@socketio.on('connected')
def handle_connection(data):
    print(f"Player connected: {data['pid']}")
    print("\033[91m{}\033[00m".format('IN CONNECTED'))
    pair = data['pid'][1:]

    # Log the connection
    session_obj = {'connected': []}
    ws_room_id = None
    pair_registered = False

    try:
        aws_folder = s3.get_object(Bucket=S3_BUCKET,Key=f'{pair}/')
        pair_registered = True
    except:
        pass

    print(f"PAIR REGISTERED BOOL: {pair_registered}")
    # checks if the pair is already in 
    if pair_registered:
        session_obj = aws_read_json(pair, "session_obj")
        ws_room_id = session_obj['ws_room_id']  # Use the first player who joined's room
        
    else:
        s3.put_object(Bucket=S3_BUCKET, Body = "", Key=f'{pair}/')
        ws_room_id = request.sid  # Use the first player who joined's room
        session_obj['ws_room_id'] = ws_room_id

    session_obj['connected'].append(data['pid'][0])
    aws_write_json(pair, "session_obj", session_obj)

    # Send Twilio token (authorized to connect to pair-specific room)
    token_1 = AccessToken(twilio_account_sid, twilio_api_key_sid, twilio_api_key_secret, identity=data['pid'], ttl=86400)
    token_1.add_grant(VideoGrant(room=pair))

    #token_2 = AccessToken(twilio_account_sid, twilio_api_key_sid, twilio_api_key_secret, identity=f'T{pair}', ttl=86400)
    #token_2.add_grant(VideoGrant(room=pair))
    emit('connect_audio', {'token': token_1.to_jwt(), 'role': data['pid'][0]})
    #emit('connect_audio', {'token': token_2.to_jwt(), 'role': 'T'})

    # Check if both players are connected
    session_obj = aws_read_json(pair, "session_obj")

    if 'T' in session_obj['connected'] and 'W' in session_obj['connected']:
        # They join the same room
        #print("XXXXXXXXXXXXXX")
        #print(f"{ws_room_id=}")
        #print("XXXXXXXXXXXXXX")

        join_room(ws_room_id)

        game_exists = 0

        try:
            aws_folder = s3.get_object(Bucket=S3_BUCKET,Key=f'{pair}/{pair}-game.pickle')
            game_exists = 1
        except:
            pass
  
        # Load game if already existing
        if game_exists:
            print(f"{session_obj['connected']} starts round now")
            env = aws_read_pickle(pair, f'{pair}-game')
            info = aws_read_json(pair, f'{pair}-game-last-info')
            cur_round = aws_read_json(pair, f'{pair}-round')
            cur_episode = aws_read_json(pair, f'{pair}-episode')
            round_score = aws_read_json(pair, f'{pair}-round-score')
        
        else:  # Create new game if not
            # If it doesn't exist then start with practice round
            cur_round = 0
            cur_episode = 0
            round_score = 0

            env = RoboTaxiEnv(config=config['practice']['gameConfig'])
            obs, info = env.reset()

            # Log new game
            logger = Logger(pair=pair)
            logger.record_config(config)
            logger.record(round=cur_round, episode=cur_episode, ts=info['ts'], obs=convert_info_jsonable(obs),
                          info=convert_info_jsonable(info))

            aws_write_json(pair, f'{pair}-round', cur_round)
            aws_write_json(pair, f'{pair}-episode', cur_episode)
            aws_write_json(pair, f'{pair}-round-score', round_score)
            aws_write_json(pair, f'{pair}-game-last-info', convert_info_jsonable(info))
            aws_write_json(pair, f"{pair}-seed", int(pair))  # Set seed for actual game
            aws_write_pickle(pair, f'{pair}-logger', logger)
            aws_write_pickle(pair, f'{pair}-game', env)

        # Send game configuration (used in the UI)
        print(f'cur_round = {cur_round}')
        if cur_round == 0:
            emit('config', config['practice'], room=ws_room_id)
        else:
            print("ERROR: Reconnected (cur_round)")
            emit('config', config['actual'], room=ws_room_id)

        info['round_score'] = round_score
        # Send game info
        print(f'info ts = {info}')
        if info['ts'] == 0:
            emit('update', {'phase': 'COUNTDOWN', 'round': cur_round, 'max_rounds': config['actual']['num_rounds'],
                            'state': convert_info_jsonable(info), 'new_round': True}, room=ws_room_id)
        else:
            print("ERROR: Reconnected (info ts)")
            emit('update', {'phase': 'STEP', 'round': cur_round, 'num_rounds': config['actual']['num_rounds'],
                            'state': convert_info_jsonable(info)}, room=ws_room_id)


@socketio.on('audio_recording')
def handle_audio_recording(data):
    print('handle_audio-recording:', data['pid'])
    pair = data['pid'][1:]
    timestamp = data['timestamp']
    rec_started = data['rec_started']  # True if recording has started, False if stopped
    print("######################")
    print(rec_started)
    print("######################")

    logger = aws_read_pickle(pair, f'{pair}-logger')
    logger.record_audio_meta(rec_started, timestamp)
    aws_write_pickle(pair, f'{pair}-logger', logger)



@socketio.on('step')
def handle_step(data):
    """
    Only the wizard calls this function
    """
    global last_key_time
    print(f'Data: ')
    print(data)

    pid = data['pid']
    pair = data['pid'][1:]
    keypress_hist = data['keypress_hist']
    keysdown = data['keysdown']
    game_rendered_timestamp = data['game_rendered_timestamp']
    ts_end_timestamp = data['ts_end_timestamp']

    game_exists = 0

    try:
        aws_folder = s3.get_object(Bucket=S3_BUCKET,Key=f'{pair}/{pair}-game.pickle')
        game_exists = 1
    except:
        pass


    if game_exists:

        # Get websockets room id
        session_obj = aws_read_json(pair, "session_obj")
        ws_room_id = session_obj['ws_room_id']

        # Get Logger
        logger = aws_read_pickle(pair, f'{pair}-logger')

        # Find last arrow keydown in currently pressed
        arrow_keys = {'ArrowUp': 1, 'ArrowDown': 3, 'ArrowLeft': 4, 'ArrowRight': 2, 'KeyW': 1, 'KeyD': 2, 'KeyS': 3,
                      'KeyA': 4}
        
        action = 0  # Default is Action.NOP.value

        for item in keypress_hist[::-1]:
            if item[1] == 'keydown' and item[0] in arrow_keys:
                action = arrow_keys[item[0]]
                current_time = item[2]
                if current_time == last_key_time:
                    print("**********************************")
                    print("Same key action called!")
                    print("**********************************")
                
                last_key_time = current_time
                break
        
        print("\033[91m{}\033[00m".format('Action action=' + str(action)))

        env = aws_read_pickle(pair, f'{pair}-game')
        cur_round = aws_read_json(pair, f'{pair}-round')
        cur_episode = aws_read_json(pair, f'{pair}-episode')
        round_score = aws_read_json(pair, f'{pair}-round-score')
        session_seed = aws_read_json(pair, f"{pair}-seed")

        # Do one step
        obs, rew, done, info = env.step(action)

        # Log Action, Reward, Next State, Keypress_hist
        logger.record(round=cur_round, episode=cur_episode, ts=env.ts, action=action, reward=rew, done=done,
                      obs=convert_info_jsonable(obs), info=convert_info_jsonable(info), keypress_hist=keypress_hist,
                      keysdown=keysdown, game_rendered_timestamp=game_rendered_timestamp, ts_end_timestamp=ts_end_timestamp)
        round_score += rew

        round_over = info['endRound']
        if round_over:
            cur_round += 1
            cur_episode = 0
        elif done:
            cur_episode += 1

        rounds_left = cur_round <= config['actual']['num_rounds']

        if done and rounds_left:

            if cur_round == 0 and not round_over:
                # Reload a practice game
                emit('config', config['practice'], room=ws_room_id)
                env = RoboTaxiEnv(config=config['practice']['gameConfig'])
                print("test 3")
                obs, info = env.reset()
                logger.record(round=cur_round, episode=cur_episode, ts=info['ts'], obs=convert_info_jsonable(obs),
                              info=convert_info_jsonable(info))

            else:
                # We know have at least finished the practice game so send the actual game config
                emit('config', config['actual'], room=ws_room_id)

                # Create new env with session seed and reset it
                config['actual']['gameConfig']['rng_seed'] = session_seed
                env = RoboTaxiEnv(config['actual']['gameConfig'])
                print("test 4")
                obs, info = env.reset()
                logger.record(round=cur_round, episode=cur_episode, ts=info['ts'], obs=convert_info_jsonable(obs),
                              info=convert_info_jsonable(info))

        # Three cases
        # Round over and rounds left -> Countdown new round
        # Round over and no rounds left -> proceed to feeback
        # Round not over -> proceed as normal
        if round_over and rounds_left:
            info['round_score'] = round_score
            print("test 5")
            emit('update', {'phase': 'COUNTDOWN', 'round': cur_round, 'num_rounds': config['actual']['num_rounds'],
                            'state': convert_info_jsonable(info), 'new_round': True}, room=ws_room_id)
        elif not round_over:
            info['round_score'] = round_score

            # Regular game step
            if not done:
                emit('update', {'phase': 'STEP', 'round': cur_round, 'num_rounds': config['actual']['num_rounds'],
                                'state': convert_info_jsonable(info)},  room=ws_room_id)
            else:  # New episode countdown
                emit('update', {'phase': 'COUNTDOWN', 'round': cur_round, 'num_rounds': config['actual']['num_rounds'],
                                'state': convert_info_jsonable(info), 'new_round': False}, room=ws_room_id)
        elif round_over and not rounds_left:
            info['round_score'] = round_score
            emit('update', {'phase': 'FEEDBACK', 'state': convert_info_jsonable(info)}, room=ws_room_id)
        else:
            raise "Unhandled Case"

        # Store back in redis
        aws_write_pickle(pair, f'{pair}-game', env)
        aws_write_json(pair, f'{pair}-round', cur_round)
        aws_write_json(pair, f'{pair}-game-last-info', convert_info_jsonable(info))  # Stored in case of client disconnect
        aws_write_json(pair, f'{pair}-round-score', round_score)
        aws_write_json(pair, f'{pair}-episode', cur_episode)
        aws_write_pickle(pair, f'{pair}-logger', logger)


        # If round is over, backup log to s3
        if round_over:
            upload_log_to_s3(pid[1:])


@socketio.on('feedback')
def handle_feedback(data):
    print("Logging Feedback")
    pid = data['pid']
    print(f'Data: ')
    print(data)
    pair = pid[1:]
    logger = aws_read_pickle(pair, f'{pair}-logger')
    logger.record_feedback(state=data['state'], path=data['path'])
    aws_write_pickle(pair, f'{pair}-logger', logger)



@app.route('/upload_file', methods=['POST'])
def upload_file():
    filename = request.form['filename']
    if request.method == "POST":
        f = request.files['audio_data']
        #s3.Object(S3_BUCKET, filename).put(Body=f)

        print("##############################")
        print(f"Uploading {filename} to S3")
        print("##############################")

        response = s3.put_object(
            Body=f,
            Bucket=S3_BUCKET,
            Key=filename,
        )
    return "Success"


@app.route('/get_s3_url')
def get_signed_s3_url():
    filename = request.args.get('filename')
    presigned_post = s3.generate_presigned_post(
        Bucket=S3_BUCKET,
        Key=filename,
        Fields={},
        Conditions=[],
        ExpiresIn=3600
    )

    return json.dumps({
        'data': presigned_post,
        'url': 'https://%s.s3.amazonaws.com/%s' % (S3_BUCKET, filename),
        'key': filename
    })

@socketio.on('message')
def handle_message(data):
    print(f"Regular message: {data}")


@socketio.on('json')
def handle_message(json):
    print(f"Regular json: {str(json)}")


@app.route("/survey")
def survey():
    pid = request.args.get('pid')
    if not pid:
        response = jsonify({'message': 'ERROR: pid not specified in request'})
        response.status_code = 400
        return response

    if pid[0] == 'W':
        upload_log_to_s3(pid[1:])

    return render_template('survey.html')


#def redis_write(key, obj):
#    db[key] = json.dumps(obj)
#
#
#def redis_read(key):
#    return json.loads(db[key].decode('utf-8'))

@app.route("/convert_to_video", methods=['POST'])
def convert_to_video():

    files = request.files
    audio_file_name = ''

    images: List[str] = []
    count = 0
    for k in sorted(files.keys()):
        if 'image' in k:
            #images.append(files[k])
            new_file_name = f'image_{count}.png'
            files[k].save(new_file_name)
            images.append(new_file_name)
            count += 1
        else:
            audio_file_name = 'audio.wav'
            files[k].save(audio_file_name)

    if audio_file_name == '':
        return 'No audio uploaded', 400

    start_time = float(request.args.get('start_time'))
    end_time = float(request.args.get('end_time'))
    duration = end_time - start_time

    command = f'ffmpeg -y -i audio.wav -ss {start_time} -t {duration} clipped.wav'
    print(command)
    subprocess.call(command.split(' '))

    FPS_STR = f'{len(images)}/{duration}'

    #command = f'ffmpeg -r {FPS} -i image_%d.png -c:v libx264 -vf fps={FPS} -pix_fmt yuv420p out.mp4'
    command = f'ffmpeg -y -r {FPS_STR} -i image_%d.png -c:v libx264 -vf format=yuv420p out.mp4'
    print(command)
    subprocess.call(command.split(' '))

    print(command)
    #command = f"ffmpeg -y -i out.mp4 -i audio.wav -c:v copy -c:a aac audio_and_frames.mp4"
    #command = f"ffmpeg -y -i out.mp4 -i audio.wav -c copy -map 0:v:0 -map 1:a:0 audio_and_frames.mp4"
    command = f'ffmpeg -y -i out.mp4 -i clipped.wav -vcodec libx264 -acodec libmp3lame audio_and_frames.mp4'
    subprocess.call(command.split(' '))

    subprocess.call(['rm','out.mp4', 'audio.wav', 'clipped.wav'] + images)

    with open('audio_and_frames.mp4', 'rb') as f:
        video = f.read()

    subprocess.call(['rm','audio_and_frames.mp4'])

    return Response(video, mimetype='video/mp4')


def aws_write_json(pair, key, obj,):
    json_object = json.dumps(obj)

    s3.put_object(
     Body=json.dumps(json_object),
     Bucket=S3_BUCKET,
     Key=f'{pair}/{key}.json'
    )

def aws_write_pickle(pair, key, obj):
    pickle_object = pickle.dumps(obj)

    s3.put_object(
     Body=pickle.dumps(pickle_object),
     Bucket=S3_BUCKET,
     Key=f'{pair}/{key}.pickle'
    )


def aws_read_json(pair, key):
    s3.download_file(S3_BUCKET, f'{pair}/{key}.json', f'{key}.json')

   #  open the local file and work with it
    with open(f'{key}.json', 'r') as file:
        return json.loads(json.load(file))
    

def aws_read_pickle(pair, key):
    s3.download_file(S3_BUCKET, f'{pair}/{key}.pickle', f'{key}.pickle')

   #  open the local file and work with it
    with open(f'{key}.pickle', 'rb') as file:
        return pickle.loads(pickle.load(file))
    #return pickle.loads(file_bytes)
        



def convert_info_jsonable(info):
    if isinstance(info, dict):
        for key, val in info.items():
            if isinstance(val, np.ndarray):
                info[key] = val.tolist()
            info['player_location'] = (int(info['player_location'][0]), int(info['player_location'][1]))
    elif isinstance(info, tuple) or isinstance(info, list):
        if isinstance(info, tuple):
            info = list(info)

        for idx, el in enumerate(info):
            if isinstance(el, np.ndarray):
                info[idx] = el.tolist()
            elif isinstance(el, np.integer):
                info[idx] = int(el)
    return info

def upload_log_to_s3(pair):
    logger = aws_read_pickle(pair, f'{pair}-logger')
    json_str_log = json.dumps(logger.dump_dict()).encode('UTF-8')

    # s3_file_obj = s3.Object(S3_BUCKET, f"pair_{pair}_log.json")
    # s3_file_obj.put(Body=(bytes(json_str_log)))

    response = s3.put_object(
        Body=(bytes(json_str_log)),
        Bucket=S3_BUCKET,
        Key=f"pair_{pair}_log.json",
    )

class Logger:
    def __init__(self, pair):
        self.pair = pair
        self.log = {}
        self.audio_log = {}
        self.config = {}
        self.feedback = {}

    def record_config(self, config):
        self.config = config

    def record_feedback(self, state, path):
        self.feedback['state'] = state
        self.feedback['path'] = path

    def record_audio_meta(self, rec_started, timestamp):
        if rec_started:
            self.audio_log['rec_started_ts'] = timestamp
        else:
            self.audio_log['rec_stopped_ts'] = timestamp
        print(self.pair, self.audio_log)

    def record(self, round, episode, ts, obs=None, action=None, reward=None, done=None, info=None, keypress_hist=None, **kwargs):
        """
        Record data for current timestep
        :param round: Round the timestep is in
        :param episode: Episode the timestep is in
        :param ts: Timestep 0 is initial, first action is at timestep 1
        :param obs: The new observation gained from this timestep
        :param action: The action performed during this timestep
        :param reward: The reward gained as a result of the action during this timestep
        :param done: Does this timestep terminate the episode?
        :param info: The new info dict returned as a result of the action performed in the timestep
        :param keypress_hist: Log of wizard keypresses during this timestep
        """
        if f"round-{round}" not in self.log:
            self.log[f"round-{round}"] = {}
        if f"episode-{episode}" not in self.log[f"round-{round}"]:
            self.log[f"round-{round}"][f"episode-{episode}"] = {}
        # if ts > len(self.log[f"round-{round}"][f"episode-{episode}"]) - 1:  # Timestep doesnt exist in log yet
        #     self.log[f"round-{round}"][f"episode-{episode}"].append({})
        if ts not in self.log[f"round-{round}"][f"episode-{episode}"]:  # Timestep doesnt exist in log yet
            self.log[f"round-{round}"][f"episode-{episode}"][ts] = {}

        # print(f"R {round}, e {episode}, ts {ts}: ")

        if obs is not None:
            self.log[f"round-{round}"][f"episode-{episode}"][ts]['obs'] = obs
            # print("obs")
        if action is not None:
            self.log[f"round-{round}"][f"episode-{episode}"][ts]['action'] = action
            # print("action")
        if reward is not None:
            self.log[f"round-{round}"][f"episode-{episode}"][ts]['reward'] = reward
            # print("reward")
        if done is not None:
            self.log[f"round-{round}"][f"episode-{episode}"][ts]['done'] = done
            # print("done")
        if info is not None:
            self.log[f"round-{round}"][f"episode-{episode}"][ts]['info'] = info
            # print("info")
        if keypress_hist is not None:
            self.log[f"round-{round}"][f"episode-{episode}"][ts]['keypress_hist'] = keypress_hist
            # print("keypress_hist")

        # The rest of the arguments
        for key, val in kwargs.items():
            self.log[f"round-{round}"][f"episode-{episode}"][ts][key] = val

    def dump_dict(self):
        return dict(pair=self.pair, log=self.log, audio_log=self.audio_log, config=self.config, feedback=self.feedback)

if __name__ == '__main__':
    print("Starting!")
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, port=port, debug=True)
