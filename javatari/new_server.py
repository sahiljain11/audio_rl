import os
import random
from flask import Flask, render_template, request, jsonify, make_response, redirect, url_for, abort, session
import json
import boto3
import string
from flask_session import Session
from io import BytesIO
import base64

app = Flask(__name__)
app.secret_key = 'afisdosad90akfsdial1239jk'
app.config['SESSION_TYPE'] = 'filesystem'

sess = Session()
sess.init_app(app)

@app.route('/')
def instruct():
  rom = os.environ['ROM']
  if rom == 'spaceinvaders':
    return render_template('instruct_space.html')
  if rom == 'mspacman':
    return render_template('instruct_pac.html')
  if rom == 'revenge':
    return render_template('instruct_rev.html')
  if rom == 'enduro':
    return render_template('instruct_end.html')
  if rom == 'seaquest':
    return render_template('instruct_sea.html')

  return render_template('instruct_space.html')
  #else:
  #  raise Exception("ROM not found")

# both do the same thing. functionally the same, but I needed another for a href call in JS
@app.route('/start')
def start():
  rom = os.environ['ROM']
  if rom == 'spaceinvaders':
    return render_template('instruct_space.html')
  if rom == 'mspacman':
    return render_template('instruct_pac.html')
  if rom == 'revenge':
    return render_template('instruct_rev.html')
  if rom == 'enduro':
    return render_template('instruct_end.html')
  if rom == 'seaquest':
    return render_template('instruct_sea.html')

  return render_template('instruct_space.html')
  #else:
  #  raise Exception("ROM not found")

@app.route('/trial')
def trial():
  rom = os.environ['ROM']
  return render_template('trial.html', rom=rom, ai_score=0)

@app.route('/after_trial')
def after_trial():
  rom = os.environ['ROM']
  if rom == "enduro":
    return render_template('instruct2_enduro.html')

  return render_template('instruct2.html')

@app.route('/last')
def last():
  rom = os.environ['ROM']
  key = session.get("key")
  if key == None:
    return render_template('last.html', key="<no_code_given>")
  return render_template('last.html', key=key)

@app.route('/game')
def game():
  #rom = 'spaceinvaders'
  rom = os.environ['ROM']
  #rom = 'revenge'
  #rom = "mspacman"
  session["key"] = ran_gen(10, "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890")
  key = session["key"]
  return render_template('index.html', rom=rom, ai_score=0, key=key)


def ran_gen(size, chars=string.ascii_uppercase + string.digits):
  return ''.join(random.choice(chars) for x in range(size))

#@app.route('/key')
#def key():
#  # rom = random.choice(['qbert', 'spaceinvaders', 'mspacman', 'pinball', 'revenge'])
#  return jsonify({"key": ran_gen(10, "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890")})

# @app.route('/<rom>')
# def index_rom(rom):
#   if(rom not in ['qbert', 'spaceinvaders', 'mspacman', 'pinball', 'revenge']):
#     return redirect('/')
#   return render_template('index.html', rom=rom, ai_score=0)

@app.route("/mic")
def blank():
  return render_template('blank.html')

@app.route('/sign_s3/')
def sign_s3():
    S3_BUCKET = os.environ.get('S3_BUCKET')
    #S3_BUCKET = 'atari11'
    file_name = request.args.get('file_name')
    file_type = request.args.get('file_type')

    AWS_REGION = os.environ.get("AMAZON_REGION")
    AWS_KEY = os.environ.get("AMAZON_CLIENT_KEY")
    AWS_SECRET_KEY = os.environ.get("AMAZON_SECRET_CLIENT_KEY")

    s3 = boto3.client('s3', region_name=AWS_REGION,
                  aws_access_key_id=AWS_KEY,
                  aws_secret_access_key=AWS_SECRET_KEY)

    presigned_post = s3.generate_presigned_post(
        Bucket=S3_BUCKET,
        Key=file_name,
        Fields={},
        Conditions=[],
        ExpiresIn=3600
    )

    return json.dumps({
        'data': presigned_post,
        'url': 'https://%s.s3.amazonaws.com/%s' % (S3_BUCKET, file_name),
        'key': file_name
    })

@app.route("/api/save", methods=["POST"])
def api_save():
  # save information on S3
  store = request.get_json()
  return "finished"

### replay stuff
@app.route('/replay/<traj_id>')
def replay(traj_id):
  if session.get('new_time') == None or session.get('old_time') == None:
    session["new_time"] = 1
    session["old_time"] = 1
  path = os.path.abspath(os.getcwd()) + "/" + traj_id
  os.mkdir(path)
  return render_template('replay.html', replay=True, traj_id=traj_id,
                         seconds=session["new_time"], old_time=session["old_time"])

### adjusted replay stuff
@app.route('/update_replay', methods=["POST"])
def replay_again():
  req_data = request.get_json(force=True)
  session["new_time"] = req_data["seconds"]
  session["old_time"] = req_data["old_time"]
  return jsonify({"done" : "yay"})

@app.route('/api/trajectory/<trajectory_id>')
def get_trajectory(trajectory_id):
  rom = os.environ['ROM']
  path = os.path.abspath(os.getcwd()) + "/" + trajectory_id + ".json"
  print(path)

  with open(path) as f:
    data = json.load(f)

  data = json.loads(data)
  #return jsonify(**{'trajectory':json.loads(traj.actions), 'init_state':json.loads(traj.init_state), 'seqid':traj.id})
  #return jsonify(**{'trajectory': data[0]["trajectory\""], 'init_state': data[0]["init_state"]})
  return jsonify(data)

@app.route('/api/save_trajectory', methods=['POST'])
def save_trajectory():
  return 'sequence saved', 200

@app.route('/api/save_frame', methods=['POST'])
def save_frame():
  from PIL import Image
  resp = request.get_json()
  
  data = resp['screenshot'].split(',')[1]
  w = resp['width']
  h = resp['height']
  key = resp['key']
  count = resp['count']
  im = Image.open(BytesIO(base64.b64decode(data)))
  im = im.crop((0,0,w,h))

  path = os.path.join(os.getcwd(), f'{key}/{key}_{count}.png')
  im.save(path)
  return 'screenshot saved', 200



if __name__ == "__main__":

  if os.environ['ROM'] is None:
    raise Exception('Please specify the ROM: export ROM=<spaceinvaders, mspacman, revenge, enduro, seaquest>')
  
  if os.environ['S3_BUCKET'] is None:
    raise Exception('Please specify the S3 bucket: export S3_BUCKET=<insert_bucket_name>')
  
  if os.environ.get("AMAZON_CLIENT_KEY") is None:
    raise Exception('Please specify the AWS Key: export AMAZON_CLIENT_KEY=<insert_client_key>')

  if os.environ.get("AMAZON_SECRET_CLIENT_KEY") is None:
    raise Exception('Please specify the AWS Key: export AMAZON_SECRET_CLIENT_KEY=<insert_secret_client_key>')

  if os.environ.get("AMAZON_REGION") is None:
    raise Exception('Please specify the AWS Region: export AMAZON_REGION=<insert_region>')

  rom = os.environ['ROM']

  print('Reminder: This application only works on Chrome!')
  app.run()