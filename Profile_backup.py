import json
from watson_developer_cloud import ToneAnalyzerV3
from watson_developer_cloud import PersonalityInsightsV2
import threading
from twilio.rest import TwilioRestClient

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
        # with open('person_data.pkl', 'rb') as input:
        #     person2 = pickle.load(input)
        #     self.setMoods(person2.getMoods())
        #     self.setEmotions(person2.getEmotions())
        #     self.setPersonalities(person2.getPersonalities())
        #     self.setNeeds(person2.getMoods())
        #     self.setID(person2.getID())
        #     self.setMessage(person2.getMessage())

    def setMoods(self,moods):
        self.moods=moods
    def setEmotions(self,emotions):
        self.emotions=emotions
    def setPersonalities(self,personalities):
        self.personalities=personalities
    def setNeeds(self,needs):
        self.needs=needs
    def setID(self,ID):
        self.ID=ID
    def setMessage(self,message):
        self.messages=message
    def addMood(self,mood):
        self.moods += [mood]

    def getMoodStat(self,N):
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
        return moodStat

    def getID(self):
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
        return emotionStat

    def getMessages(self):
        result = ""
        for message in self.messages:
            result = result + " " + message
        while len(result.split())<110:
            result = result + " " +result
        return result

    def computePersonalities(self):
        personality = json.dumps(self.personality_insights.profile(
            text=self.getMessages()), indent=2)
        parsed_personality = json.loads(personality)
        for personality in parsed_personality["tree"]["children"][0]["children"][0]["children"]:
            self.personalities[personality["name"]]=personality["percentage"]
        for need in parsed_personality["tree"]["children"][1]["children"][0]["children"]:
            self.needs[need["name"]]=personality["percentage"]
    def addMessage(self,message):
        for word in message.split(" "):
            if word.upper() in self.EMERGENCY_WORDS:
                print "sending help"
                message = self.client.messages.create(body="You might want to check on your children",
                                                      to="+15108134713",  # Replace with your phone number
                                                      from_="+15109013221")  # Replace with your Twilio number
                print "help sent"
                break
        self.messages += [message]
        toneResult = json.dumps(self.tone_analyzer.tone(text=message), indent=2)
        parsed_json = json.loads(toneResult)
        emotion = {}
        for tone in parsed_json["document_tone"]["tone_categories"][0]["tones"]:
            emotion[tone["tone_name"]] = tone["score"]
        self.addEmotions(emotion)

    def addEmotions(self,emotion):
        self.emotions += [emotion]
