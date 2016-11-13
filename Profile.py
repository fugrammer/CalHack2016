import json
from watson_developer_cloud import ToneAnalyzerV3
from watson_developer_cloud import PersonalityInsightsV2
import threading
from twilio.rest import TwilioRestClient
from rapidconnect import RapidConnect

rapid = RapidConnect('Calhack', '69626f7d-c0d1-40bf-b52a-6b4d6f461f48')

class Profile:

    def __init__(self, ID):

        self.EMERGENCY_WORDS = ["HELP", "FIRE"]
        self.lock = threading.Lock()
        self.personality_insights = PersonalityInsightsV2(
            username='5c93fdbf-78bb-48ae-b582-4d5bb599d8d8',
            password='WaQNMevaaSRp')

        self.tone_analyzer = ToneAnalyzerV3(
            username='f96a788e-de09-466d-b23b-9f5668a88d7f',
            password='iClOKF18wGte',
            version='2016-02-11')

        self.account_sid = "ACac8c7fa67c6225368680cefe0adad93a"  # Your Account SID from www.twilio.com/console
        self.auth_token = "4184dca455364439190864fe90b36c0a"  # Your Auth Token from www.twilio.com/console

        self.client = TwilioRestClient(self.account_sid, self.auth_token)
        self.ID = ID
        self.messages=[]
        self.emotions=[]
        self.moods = []
        self.personalities={}
        self.needs={}

    def setMoods(self,moods):
        self.lock.acquire()
        self.moods=moods
        self.lock.release()
    def setEmotions(self,emotions):
        self.lock.acquire()
        self.emotions=emotions
        self.lock.release()
    def setPersonalities(self,personalities):
        self.lock.acquire()
        self.personalities=personalities
        self.lock.release()
    def setNeeds(self,needs):
        self.lock.acquire()
        self.needs=needs
        self.lock.release()
    def setID(self,ID):
        self.lock.acquire()
        self.ID=ID
        self.lock.release()
    def setMessage(self,message):
        self.lock.acquire()
        self.messages=message
        self.lock.release()
    def addMood(self,mood):
        self.lock.acquire()
        self.moods += [mood]
        self.lock.release()

    def getMoodStat(self,N):
        self.lock.acquire()
        if N>len(self.moods):
            N=len(self.moods)
        moodStat = {}
        for moods in self.moods[-N:]:
            for mood in moods:
                if mood in moodStat:
                    moodStat[mood] = moodStat[mood] + moods[mood]
                else:
                    moodStat[mood] = moods[mood]
        for mood in moodStat:
            moodStat[mood] = moodStat[mood]/N
        self.lock.release()
        return moodStat

    def getID(self):
        self.lock.acquire()
        return self.ID

    def getPersonalities(self):
        return self.personalities

    def getMessage(self):
        return self.messages

    def getNeeds(self):
        return self.needs

    def getMoods(self):
        return self.moods

    def getEmotions(self):
        return self.emotions

    def getEmotionsStat(self,N):
        self.lock.acquire()
        if N>len(self.emotions):
            N=len(self.emotions)
        emotionStat = {}
        for emotions in self.emotions[-N:]:
            for emotion in emotions:
                if emotion in emotionStat:
                    emotionStat[emotion] = emotionStat[emotion] + emotions[emotion]
                else:
                    emotionStat[emotion] = emotions[emotion]
        for emotion in emotionStat:
            emotionStat[emotion] = emotionStat[emotion]/N
        self.lock.release()
        return emotionStat

    def getMoodsStat(self,N):
        self.lock.acquire()
        if N > len(self.moods):
            N = len(self.moods)
        moodStat = {}
        for moods in self.moods[-N:]:
            for mood in moods:
                if mood in moodStat:
                    moodStat[mood] = moodStat[mood] + moods[mood]
                else:
                    moodStat[mood] = moods[mood]
        for mood in moodStat:
            moodStat[mood] = moodStat[mood] / N
        self.lock.release()
        return moodStat

    def getMessages(self):
        self.lock.acquire()
        result = ""
        for message in self.messages:
            result = result + " " + message
        while len(result.split())<110:
            result = result + " " +result
        self.lock.release()
        return result

    def computePersonalities(self):

        personality = json.dumps(self.personality_in sights.profile(
            text=self.getMessages()), indent=2)

        parsed_personality = json.loads(personality)
        self.lock.acquire()
        for personality in parsed_personality["tree"]["children"][0]["children"][0]["children"]:
            self.personalities[personality["name"]]=personality["percentage"]
        for need in parsed_personality["tree"]["children"][1]["children"][0]["children"]:
            self.needs[need["name"]]=personality["percentage"]
        self.lock.release()

    def addMessage(self,message):
        self.lock.acquire()
        try:
            for word in message.split(" "):
                if word.upper() in self.EMERGENCY_WORDS:
                    print "sending help"
                    result = rapid.call('Twilio', 'sendSms', {
                        'accountSid': 'ACac8c7fa67c6225368680cefe0adad93a',
                        'accountToken': '4184dca455364439190864fe90b36c0a',
                        'from': '+15109013221',
                        'to': '+15108134713',
                        'applicationSid': '',
                        'statusCallback': '',
                        'messagingServiceSid': 'MG92a2e26fc2534bd0b48742c25794c464',
                        'body': 'Your child seems to be in danger.',
                        'maxPrice':'',
                        'provideFeedback': ''
                    });
                    # message = self.client.messages.create(body="Your child seems to be in danger.",
                    #                                       to="+15108134713",  # Replace with your phone number
                    #                                       from_="+15109013221")  # Replace with your Twilio number
                    break
        except:
            pass
        self.messages += [message]
        toneResult = json.dumps(self.tone_analyzer.tone(text=message), indent=2)
        parsed_json = json.loads(toneResult)
        emotion = {}
        for tone in parsed_json["document_tone"]["tone_categories"][0]["tones"]:
            emotion[tone["tone_name"]] = tone["score"]
        self.lock.release()
        self.addEmotions(emotion)

    def addEmotions(self,emotion):
        self.lock.acquire()
        self.emotions += [emotion]
        self.lock.release()

