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
import pickle
import sys
import Dummy

MOODWHITELIST=["sadness","neutral","happiness","fear","anger"]
PERSONALITYWHITELIST = []
NEEDWHITELIST = []
THRESHOLD = 500
CHUNK_SIZE = 1024
FORMAT = pyaudio.paInt16
RATE = 44100

_url = 'https://api.projectoxford.ai/emotion/v1.0/recognize'
_key = "666bd7f2bb84487e880da9565f3394d6" #Here you have to paste your primary key
_maxNumRetries = 10

speech_to_text = SpeechToTextV1(
    username='4ac3e445-4ff7-4dc5-bf72-990f241a818c',
    password='stnkTzth6yWk',
    x_watson_learning_opt_out=False
)

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
        if count>500:
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
            record_to_file('demo.wav')
            with open(join(dirname(__file__), 'demo.wav'), 'rb') as audio_file:
                message = (json.dumps(speech_to_text.recognize(
                    audio_file, content_type='audio/wav', timestamps=True, word_confidence=True), indent=2))
            parsed_message = json.loads(message)
            message = parsed_message["results"][0]["alternatives"][0]["transcript"]
            person1.addMessage(message)
            person1.computePersonalities()
            time.sleep(1)
        except:
            print "no message detected"
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
                sum += needs[need]
                labels += [need]
            # labels = 'Frogs', 'Hogs', 'Dogs', 'Logs'
            for need in labels:
                fracs += [needs[need] / sum * 100]
                explode += [0]
            explode = tuple(explode)
            pylab.pie(fracs, explode=explode, labels=labels,
                autopct='%1.1f%%', shadow=True, startangle=90)

            ### Historical Emotional Graph ###
            moods = person1.getMoods()
            histories = {}
            for history in moods:
                for mood in history:
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


rapid = RapidConnect('carebear2', 'ff5243a0-4c31-4e7a-a328-0b536a5c722d')

def getEmotion(id,stop):
    global rapid
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
            person1.addMood(outcome)
        except:
            print "Emotion error",sys.exc_info()[0]
        time.sleep(5)
        if stop():
            break

def camera(id,stop):
    global lock2
    cap = cv2.VideoCapture(0)
    while True:
        ret, frame = cap.read()
        # Our operations on the frame come here
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)
        # Display the resulting frame
        cv2.imshow('frame', gray)
        lock2.acquire()
        cv2.imwrite('2.jpg', frame)
        lock2.release()
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        if stop():
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    lock2 = threading.Lock()
    person1 = Profile(5)
    stop_threads = False
    message = ""
    counter = 0
    threads = []
    c = threading.Thread(target=camera,args=(id,lambda: stop_threads))
    c.start()
    t = threading.Thread(target=audioWorker,args=(id,lambda: stop_threads))
    t.start()
    p = threading.Thread(target=displayStats,args=(id,lambda: stop_threads))
    p.start()
    i = threading.Timer(5,getEmotion,args=(id,lambda: stop_threads))
    i.start()
    threads.append(t)
    threads.append(p)
    threads.append(i)
    threads.append(c)
    while True:
        option = raw_input("1. End application\n2. Save person data\n3. Load person data")
        if option=="1":
            break
        elif option == "2":
            with open('person_data.pkl', 'wb') as output:
                pickle.dump(person1, output, pickle.HIGHEST_PROTOCOL)

    stop_threads = True
    for worker in threads:
        worker.join()
    print ("Application Exited")