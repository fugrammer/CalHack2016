from __future__ import unicode_literals

from os.path import join, dirname
from watson_developer_cloud import SpeechToTextV1
from sys import byteorder
from array import array
from struct import pack
import pyaudio
import wave
from Profile import *
import threading
import pylab
import time
import cv2
from rapidconnect import RapidConnect
import requests
import cPickle as pickle
from rapidconnect import RapidConnect
from watson_developer_cloud import RetrieveAndRankV1
import unirest
from watson_developer_cloud import TextToSpeechV1
import sys
import subprocess
from flask import Flask, render_template, Response

rapid = RapidConnect('Calhack', '69626f7d-c0d1-40bf-b52a-6b4d6f461f48')

MOODWHITELIST=["sadness","neutral","happiness","fear","anger"]
PERSONALITYWHITELIST = []
NEEDBLACKLIST = ["Liberty","Ideal"]
EMOTIONBLACKLIST = ["neutral"]
THRESHOLD = 2000
CHUNK_SIZE = 1024
FORMAT = pyaudio.paInt16
RATE = 44100
import winsound

_url = 'https://api.projectoxford.ai/emotion/v1.0/recognize'
_key = "666bd7f2bb84487e880da9565f3394d6" #Here you have to paste your primary key
_maxNumRetries = 2

speech_to_text = SpeechToTextV1(
    username='4ac3e445-4ff7-4dc5-bf72-990f241a818c',
    password='stnkTzth6yWk',
    x_watson_learning_opt_out=False
)

retrieve_and_rank = RetrieveAndRankV1(
    username='d8be8167-8a0a-4896-bb7f-bcb7b97b9a10',
    password='0CsTTPu5sdpE')

text_to_speech = TextToSpeechV1(
    username='453f62f9-1044-4498-b6f8-c6eaf963f695',
    password='tD8lQpgge2rA',
    x_watson_learning_opt_out=True)

def is_silent(snd_data):
    "Returns 'True' if below the 'silent' threshold"
    return max(snd_data) < THRESHOLD

def normalize(snd_data):
    "Average the volume out"
    MAXIMUM = 16384
    times = float(MAXIMUM)/max(abs(i) for i in snd_data)
    r = array('h')
    for i in snd_data:
        r.append(int(i*times))
    return r

def trim(snd_data):
    "Trim the blank spots at the start and end"
    def _trim(snd_data):
        snd_started = False
        r = array('h')

        for i in snd_data:
            if not snd_started and abs(i)>THRESHOLD:
                snd_started = True
                r.append(i)

            elif snd_started:
                r.append(i)
        return r

    # Trim to the left
    snd_data = _trim(snd_data)
    # Trim to the right
    snd_data.reverse()
    snd_data = _trim(snd_data)
    snd_data.reverse()
    return snd_data

def add_silence(snd_data, seconds):
    "Add silence to the start and end of 'snd_data' of length 'seconds' (float)"
    r = array('h', [0 for i in xrange(int(seconds*RATE))])
    r.extend(snd_data)
    r.extend([0 for i in xrange(int(seconds*RATE))])
    return r

def record():
    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT, channels=1, rate=RATE,
        input=True, output=True,
        frames_per_buffer=CHUNK_SIZE)
    num_silent = 0
    count = 0
    snd_started = False
    r = array('h')
    while 1:
        # little endian, signed short
        snd_data = array('h', stream.read(CHUNK_SIZE))
        if byteorder == 'big':
            snd_data.byteswap()
        r.extend(snd_data)

        silent = is_silent(snd_data)

        if silent and snd_started:
            num_silent += 1
        elif not silent and not snd_started:
            snd_started = True
        if snd_started and num_silent > 100:
            break
        if snd_started:
            count += 1
        if count>400:
            break

    sample_width = p.get_sample_size(FORMAT)
    stream.stop_stream()
    stream.close()
    p.terminate()

    r = normalize(r)
    r = trim(r)
    r = add_silence(r, 0.5)
    return sample_width, r

def processRequest(json, data, headers, params):
    """
    Helper function to process the request to Project Oxford

    Parameters:
    json: Used when processing images from its URL. See API Documentation
    data: Used when processing image read from disk. See API Documentation
    headers: Used to pass the key information and the data type request
    """

    retries = 0
    result = None

    while True:

        response = requests.request('post', _url, json=json, data=data, headers=headers, params=params)

        if response.status_code == 429:

            print("Message: %s" % (response.json()['error']['message']))

            if retries <= _maxNumRetries:
                time.sleep(1)
                retries += 1
                continue
            else:
                print('Error: failed after retrying!')
                break

        elif response.status_code == 200 or response.status_code == 201:

            if 'content-length' in response.headers and int(response.headers['content-length']) == 0:
                result = None
            elif 'content-type' in response.headers and isinstance(response.headers['content-type'], str):
                if 'application/json' in response.headers['content-type'].lower():
                    result = response.json() if response.content else None
                elif 'image' in response.headers['content-type'].lower():
                    result = response.content
        else:
            print("Error code: %d" % (response.status_code))
            print("Message: %s" % (response.json()['error']['message']))

        break

    return result

def record_to_file(path):
    "Records from the microphone and outputs the resulting data to 'path'"
    sample_width, data = record()
    data = pack('<' + ('h'*len(data)), *data)
    wf = wave.open(path, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(sample_width)
    wf.setframerate(RATE)
    wf.writeframes(data)
    wf.close()

def audioWorker(id,stop):
    global person1
    counter = 0
    #print("please speak a word into the microphone")
    while True:
        try:
            print "Recording"
            record_to_file('demo.wav')
            print "Done recording"
            with open(join(dirname(__file__), 'demo.wav'), 'rb') as audio_file:
                message = (json.dumps(speech_to_text.recognize(
                    audio_file, content_type='audio/wav', timestamps=True, word_confidence=True), indent=2))
            parsed_message = json.loads(message)
            message = parsed_message["results"][0]["alternatives"][0]["transcript"]
            message = message.strip()
            print "Message: ",message
            person1.addMessage(message)
            person1.computePersonalities()
            time.sleep(1)
        except:
            pass
            # print("Unexpected audioWorker error:", sys.exc_info()[0])
        if stop():
            break


def displayStats(id,stop):
    global person1
    while True:
        try:
            ### Current personalities graph
            personalities = person1.getPersonalities()
            pylab.figure(0, figsize=(6, 6))
            pylab.ion()
            pylab.clf()
            pylab.title("Personalities", bbox={'facecolor': '0.8', 'pad': 5})
            sum = 0
            labels = []
            fracs = []
            explode = []
            for need in personalities:
                sum += personalities[need]
                labels += [need]
            for need in labels:
                fracs += [personalities[need] / sum * 100]
                if personalities[need]==max(personalities):
                    explode+=[0.5]
                else:
                    explode += [0]
            # fracs = [15, 30, 45, 10]
            explode = tuple(explode)
            pylab.pie(fracs, explode=explode, labels=labels,
                      autopct='%1.1f%%', shadow=True, startangle=90)

            ### Current Needs graph ###
            needs = person1.getNeeds()
            pylab.figure(1, figsize=(6, 6))
            pylab.ion()
            pylab.clf()
            pylab.title("Needs", bbox={'facecolor': '0.8', 'pad': 5})
            sum = 0
            labels = []
            fracs = []
            explode = []
            for need in needs:
                if not need in NEEDBLACKLIST:
                    sum += needs[need]
                    labels += [need]
            # labels = 'Frogs', 'Hogs', 'Dogs', 'Logs'
            for need in labels:
                fracs += [needs[need] / sum * 100]
                if needs[need]==max(needs):
                    explode += [0.1]
                else:
                    explode += [0]
            explode = tuple(explode)
            pylab.pie(fracs, explode=explode, labels=labels,
                autopct='%1.1f%%', shadow=True, startangle=90,)

            ### Summary Emotional Graph ###
            moods = person1.getMoodsStat(200)
            pylab.figure(3, figsize=(6, 6))
            pylab.ion()
            pylab.clf()
            pylab.title("Emotion Summary for past 24 hours", bbox={'facecolor': '0.8', 'pad': 5})
            sum = 0
            labels = []
            fracs = []
            explode = []
            for mood in moods:
                if not mood in EMOTIONBLACKLIST:
                    sum += moods[mood]
                    labels += [mood]
            for mood in labels:
                fracs += [moods[mood] / sum * 100]
                if moods[mood] == max(moods):
                    explode += [0.1]
                else:
                    explode += [0]
            explode = tuple(explode)
            pylab.pie(fracs, explode=explode, labels=labels,
                      autopct='%1.1f%%', shadow=True, startangle=90, )

            ### Historical Emotional Graph ###
            moods = person1.getMoods()
            histories = {}
            for history in moods:
                for mood in history:
                    if not mood in EMOTIONBLACKLIST:
                        if mood in histories:
                            histories [mood] = histories [mood] + [history[mood]]
                        else:
                            histories [mood] = [history [mood]]
            pylab.figure(2, figsize=(6, 6))
            pylab.ion()
            pylab.clf()
            pylab.title("Emotion", bbox={'facecolor': '0.8', 'pad': 5})
            for mood in histories:
                pylab.plot(histories[mood],label=mood)
            pylab.ylabel('Level')
            pylab.xlabel("Time")
            pylab.legend(loc='upper left')
            pylab.show()
            pylab.pause(1)

            if stop():
                break
        except:
            pass

def getEmotion(id,stop):
    global person1
    while True:
        try:
            pathToFileInDisk = r'2.jpg'
            lock2.acquire()
            with open(pathToFileInDisk, 'rb') as f:
                data = f.read()
            lock2.release()
            headers = dict()
            headers['Ocp-Apim-Subscription-Key'] = _key
            headers['Content-Type'] = 'application/octet-stream'
            json = None
            params = None
            result = processRequest(json, data, headers, params)
            outcome={}
            for emotion in result[0]['scores']:
                if emotion in MOODWHITELIST:
                    outcome[emotion]=result[0]['scores'][emotion]
            if outcome["anger"]>0.7:
                print "anger detected"
                result = rapid.call('Twilio', 'sendSms', {
                    'accountSid': 'ACac8c7fa67c6225368680cefe0adad93a',
                    'accountToken': '4184dca455364439190864fe90b36c0a',
                    'from': '+15109013221',
                    'to': '+15108134713',
                    'applicationSid': '',
                    'statusCallback': '',
                    'messagingServiceSid': 'MG92a2e26fc2534bd0b48742c25794c464',
                    'body': 'Your child seems to be in a bad mood. You might want to check on him',
                    'maxPrice': '',
                    'provideFeedback': ''
                });
            if outcome["sadness"]>0.7:
                print "sadness detected"
                result = rapid.call('Twilio', 'sendSms', {
                    'accountSid': 'ACac8c7fa67c6225368680cefe0adad93a',
                    'accountToken': '4184dca455364439190864fe90b36c0a',
                    'from': '+15109013221',
                    'to': '+15108134713',
                    'applicationSid': '',
                    'statusCallback': '',
                    'messagingServiceSid': 'MG92a2e26fc2534bd0b48742c25794c464',
                    'body': 'Your child seems to be down. You might want to check on him',
                    'maxPrice': '',
                    'provideFeedback': ''
                });
            if outcome["fear"]>0.7:
                print "fear detected"
                result = rapid.call('Twilio', 'sendSms', {
                    'accountSid': 'ACac8c7fa67c6225368680cefe0adad93a',
                    'accountToken': '4184dca455364439190864fe90b36c0a',
                    'from': '+15109013221',
                    'to': '+15108134713',
                    'applicationSid': '',
                    'statusCallback': '',
                    'messagingServiceSid': 'MG92a2e26fc2534bd0b48742c25794c464',
                    'body': 'Your child seems to be frightful. You might want to check on him',
                    'maxPrice': '',
                    'provideFeedback': ''
                });

            person1.addMood(outcome)
        except:
            pass
        time.sleep(5)
        if stop():
            break

def camera(id,stop):
    global lock2
    global inbyte
    cap = cv2.VideoCapture(1)
    while True:
        ret, frame = cap.read()
        # Our operations on the frame come here
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)
        # Display the resulting frame
        cv2.imshow('frame', gray)
        lock2.acquire()
        cv2.imwrite('2.jpg', frame)
        ret, jpeg = cv2.imencode('.jpg', frame)
        inbyte = jpeg.tobytes()
        #cv2.imwrite('../livestream/static/2.jpg', frame)
        lock2.release()
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        if stop():
            break

    cap.release()
    cv2.destroyAllWindows()

def main():
    global inbyte
    inbyte = None

    # responce = raw_input("Load data? Y/N")
    responce = "Y"
    if responce.upper() == "Y":
        try:
            with open('moods.pkl', 'rb') as input:
                moods = pickle.load(input)
            person1.setMoods(moods)
            with open('messages.pkl', 'rb') as input:
                message = pickle.load(input)
            person1.setMessage()
        except:
            pass
    stop_threads = False
    threads = []
    p = threading.Thread(target=displayStats, args=(id, lambda: stop_threads))
    p.start()
    i = threading.Timer(5, getEmotion, args=(id, lambda: stop_threads))
    i.start()
    c = threading.Thread(target=camera, args=(id, lambda: stop_threads))
    c.start()
    t = threading.Thread(target=audioWorker, args=(id, lambda: stop_threads))
    t.start()

    threads.append(t)
    threads.append(p)
    threads.append(i)
    threads.append(c)

    while True:
        try:
            app.run(host='192.168.161.1', debug=True,use_reloader=False)
        except:
            continue
        option = raw_input("1. End application\n2. Save person data")
        if option == "1":
            break
        elif option == "2":
            with open('moods.pkl', 'wb') as output:
                moods = person1.getMoods()
                pickle.dump(moods, output, pickle.HIGHEST_PROTOCOL)
            with open('messages.pkl', 'wb') as output:
                message = person1.getMessage()
                pickle.dump(message, output, pickle.HIGHEST_PROTOCOL)
    stop_threads = True
    for worker in threads:
        worker.join()
    print ("Application Exited")

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

def gen():
    global inbyte
    while True:
        #frame = camera.get_frame()
        yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + inbyte + b'\r\n\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    person1 = Profile(5)
    lock2 = threading.Lock()
    main()

