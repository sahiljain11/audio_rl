# RoboAtari Repository
Code for the Learning from Demonstration (LfD) experiment where the human demonstrator's speech cues are used to train T-REX agents for three different Atari games (Space Invaders, Ms Pacman, Seaquest). This folder contains code for recording the speech of a human teacher (synchronized with their actions) as they demonstrate how to play one of the games.
![Atari on Javascript with Audio Recording](static/atari.png)

## Installation

### S3
In order to save the game data, you will need a S3 bucket for the server to upload game and audio data. Important note: you will need to pay money in order to set this service up. If you are affiliated with a university, typically you can get a free trial with a certain number of limited credits to offset this. Typically, S3 prices are fairly cheap, so unless you're dealing with a large volume of data, you don't need to worry too much.

To authenticate the codebase with your specific AWS Account, you can use AWS's authenticator/role-manager known as IAM. This IAM account will give you access codes (`AMAZON_CLIENT_KEY` and `AMAZON_SECRET_CLIENT_KEY`) for your application to connect to your S3 bucket. To create an IAM user, search for "IAM" in the search navigation bar at the top of the screen and select "Users". There should be a "Create User" button. Click it and give yourself a username.

Afterwards, you'll see a page for "Permission options". Select "Attach policies directly" and search for `AmazonS3FullAccess`. There should be a [+] button right next to where the name is present. Select it to give your IAM user full access to S3. Hit "Next" and then "Create user" to finalize your IAM user creation.

Now that an IAM user is created, you'll need to create an Access Key. Navigate to the "Users" page under IAM again and you should see your newly created IAM user. Click the hyperlink on the username and select "Create access key" in the top right. Select "Other" and the "Next" button, and then hit "Create access key" to finalize the access key. There, two values will be present: the Access Key and the Secret Access Key which will represent the `AMAZON_CLIENT_KEY` and `AMAZON_SECRET_CLIENT_KEY` respectively. **Please write this information down as you will be unable to retrieve these two values again.**

Next, you'll need to create an S3 bucket to hold your data. To create a bucket, search for "S3" in the navigation bar at the top of the screen. Make sure to select a region that is close to your deployment. If you would like to see the list of regions, select the dropdown next to your username in the top right corner of the dashboard. The region you select will become `AMAZON_REGION` later, so be sure to keep track of this value (Ex: us-west-2). After selecting a region, hit "Create bucket". The only two pieces of information you'll need to complete is setting the bucket name and and unchecking all of the boxes under "Block Public Access settings for this bucket". Afterwards, scroll down, hit "Create bucket" and your bucket should be created.

After creating the S3 bucket and IAM credentials, you'll need to modify the Permissions to fit the needs of your security policy of the S3 bucket. If you would like the easiest (and least secure) solution that simply works, add the following to the Bucket Policy and CORS Policy respectively.

#### Bucket Policy
Under the "Permissions" tab of your bucket, scroll down to "Bucket Policy":
```
{
    "Version": "2012-10-17",
    "Id": "<id_automatically_added>",
    "Statement": [
        {
            "Sid": "<sid_automatically_added>",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:*",
            "Resource": "arn:aws:s3:::<bucket_name>"
        }
    ]
}
```
#### CORS Policy
Under the "Permissions" tab of your bucket, scroll down to "Cross-origin resource sharing (CORS)":
```
[
    {
        "AllowedHeaders": [
            "*"
        ],
        "AllowedMethods": [
            "POST",
            "PUT",
            "DELETE",
            "GET"
        ],
        "AllowedOrigins": [
            "*"
        ],
        "ExposeHeaders": []
    }
]
```

### Python Installation

Please make sure you have Python 3.9.19. Simply run the following in a Python virtual environment of your choice (Conda, venv, etc.). An example creation call would be `conda create -n javatari python=3.9.19`. After creating an environment, run the following:

```bash
conda activate javatari
pip install -r requirements.txt
```

### Spin up the server (Linux or Max)

```bash
export ROM=<rom_name (spaceinvaders, mspacman, revenge, enduro, seaquest)>
export S3_BUCKET=<s3_bucket_name>
export AMAZON_CLIENT_KEY=<insert_client_key>
export AMAZON_SECRET_CLIENT_KEY=<insert_secret_client_key>
export AMAZON_REGION=<insert_region>
python new_server.py
```
Navigate to `http://localhost:5000`. **Please note: this software is ONLY supported on Chrome!**

### Spin up the server

```bash
set ROM=<rom_name (spaceinvaders, mspacman, revenge, enduro, seaquest)>
set S3_BUCKET=<s3_bucket_name>
set AMAZON_CLIENT_KEY=<insert_client_key>
set AMAZON_SECRET_CLIENT_KEY=<insert_secret_client_key>
set AMAZON_REGION=<insert_region>
python new_server.py
```
Navigate to `http://localhost:5000`. **Please note: this software is ONLY supported on Chrome!**

### Replay
In order to create playback recordings, you'll need FFmpeg. Installation instructions can be found [here](https://ffmpeg.org/download.html). Once you've done so, spin up the server below:
```bash
python new_server.py
```
From S3, your user's game audio file, recording file, and game state file should all be recorded. Download these files and place them in the root of this directory. The id of the trajectory will be defined as `<traj_id>` going forward.

Navigate to `http://localhost:5000/replay/<traj_id>` (for example, this would be `http://localhost:5000/replay/mspacman_1QQ3LEWANF_1`). Again, **please note: this software is ONLY supported on Chrome!**

This may take some time as the code will go frame-by-frame to download the atari PNG image for each timestamp in a folder with the id of the trajectory. After this has completed, exit out of the server and run the following command:
```bash
python make_video.py --key <traj_id>
```

After the command has completed and used ffmpeg, your final replay video will be created named `<traj_id>_final.mov`.

# Citations
- Code based on the [Atari Grand Challenge Dataset](https://github.com/yobibyte/atarigrandchallenge): *V. Kurin, S. Nowozin, K. Hofmann, L. Beyer, and B. Leibe. The Atari Grand Challenge Dataset. arXiv preprint arXiv:1705.10998, 2017.*
