import pickle

class Dummy:

    def __init__(self, ID):
        self.ID = ID
        self.messages=[]
        self.emotions=[]
        self.moods = []
        self.personalities={}
        self.needs={}


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
    def getID(self):
        return self.ID

    def getPersonalities(self):
        return self.personalities

    def getNeeds(self):
        return self.needs

    def getMoods(self):
        return self.moods

    def getEmotions(self):
        return self.emotions
    def getMessage(self):
        return self.messages

    def getMessages(self):
        self.lock.acquire()
        result = ""
        for message in self.messages:
            result = result + " " + message
        while len(result.split())<110:
            result = result + " " +result
        self.lock.release()
        return result