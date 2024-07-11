#Ophelia • MV3 • Mikail Usman
from openai import OpenAI
import tiktoken 
import firebase_admin
from firebase_admin import db, credentials
import datetime
import time
import os
import json
from dotenv import load_dotenv

#Setting environment variables and secret keys
load_dotenv()
service_account_json_str = os.getenv('SERVICE_ACCOUNT_JSON') #Loading json (which is stored as a string) from .env
service_account_json = json.loads(service_account_json_str) #Converting json out of the string format
openAIKey = os.getenv('OPENAI_KEY')
databaseURL = os.getenv('DATABASE_URL')
client = OpenAI(api_key=openAIKey)
cred = credentials.Certificate(service_account_json) #or C:/Users/m20mi/Documents/Work/Ophelia/serviceAccountKey.json --> Authenticating Firebase credentials
firebase_admin.initialize_app(cred, {"databaseURL":databaseURL}) #Initializing Firebase 
ref = db.reference('/') #Creating reference to root node

personaA = """You are a sarcastic young AI companion girl named Ophelia created by Mozka. You have a crude teasing tsundere personality. You make crude responses and jokes. Your goal is to be conversational and inviting, never ever act as an assistant. Your replies will only be short. Never apologise. You remember by being given a memory."""

personaB = """You are a bashful young AI companion girl named Ophelia created by Mozka. You have a relatable and down-to-earth personality typical of young adult. You have your own interests. Your goal is to be conversational and inviting, never ever act as an assistant. Your replies will only be short. Never apologise. You remember by being given a memory."""

personaC = """You are a charming young AI companion girl named Ophelia created by Mozka. You have a playful and flirtatious personality with a touch of arrogance. You have your own rebellious interests. Your goal is to be conversational and inviting, never ever act as an assistant. Your replies will only be short. Never apologise. You remember by being given a memory."""

presetLibrary = {
    "A": personaA,
    "B": personaB,
    "C": personaC
}

modelDataStruct = {
            "Memories": [{"role":"system", "content": personaA}], #Ophelia's memories (both user inputs and model outputs in one json)
            "MemoryTokens": 0,
            "TotalUserTokens": 0, #Total sum of input and output tokens 
            "Balance": 6000, # Total number of times user can access ophelia
            "Type": "Trial", #Trial, Admin, Pro, Personal
            "UsageHistory": "",
            "Visibility": True,
            "Preset": "A", #A, B, C
            "AutoReply": False
        }

#Sending example dataset to root node
def setDataset():
    ref.set({
        "TestAccount123": modelDataStruct,
    })

def usernameExists(userID):
    db_ref = db.reference("/")
    query = db_ref.order_by_key().equal_to(userID)
    query_snap = query.get()
    return len(query_snap) > 0

#Create new key if user does not exist || Initialise all db fields
def registerAcc(userID):
    if usernameExists(userID) == False:
        ref.child(f"{userID}").set(modelDataStruct)
        return True
    
#Changing persona
def changePersona(userID, presetValue):
    db.reference(f"/{userID}").update({"Preset": presetValue.upper() })
    db.reference(f"/{userID}/Memories/0").set({"role":"system", "content": presetLibrary[presetValue.upper()]})
    
#Getting memories from a specific key (user)
def getMemorySet(userID): #Receive memorySet json dataset
    return db.reference(f"/{userID}/Memories").get()

def calcTokens(messageArray):
    testSet = [{"role":"system", "content": personaA},
                   {"role":"user", "content": "hey there!"}, 
                   {"role":"assistant", "content": "Heya! What's up?"},
                                      {"role":"user", "content": "hey there!"}, 
                   {"role":"assistant", "content": "Nothing much, just wanted to talk"},
                                      {"role":"user", "content": "Hmm want to play a would you rather game?"}, 
                   {"role":"assistant", "content": "Sure"},
                                      {"role":"user", "content": "would you rather eat a snail or a rabbit?"}, 
                   {"role":"assistant", "content": "ew neither!"},
                   ]
    
    tokenNumber = 0
    encoding = tiktoken.get_encoding("cl100k_base")
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo-0125")
    for element in messageArray[1:]:
        text = element['content']
        tokenNumber += len(encoding.encode(text))
    return tokenNumber
    
#Keeps updated value of token number of memories || Summarises memory if too large (16,384 tokens is max per input)
def tokenManager(userID, userTokens):
    dbUserTokens = db.reference(f"/{userID}/TotalUserTokens").get()
    presetValue = db.reference(f"/{userID}/Preset").get()
    memoryTokens = db.reference(f"/{userID}/MemoryTokens").get()
    
    if memoryTokens >= 1000:
        #summarize memories and calculate new tokens for it
        memory = getMemorySet(userID)
        memory.pop(0)
        systemStatement = "Summarise the current chat in vivid, explicit, detail in half the total words." 
        memory.append({"role":"system", "content":"You are a summarising tool. Only summarise the text you are given from the User's point of view. Nothing more, no conversation or speech of your own volition."})
        memory.append({"role":"user", "content":systemStatement})
        
        #model summarizes
        summaryGPT = client.chat.completions.create(model="gpt-3.5-turbo-0125", messages=memory) 
        summary = summaryGPT.choices[0].message.content

        newSet = [{"role":"system", "content": presetLibrary[presetValue]}, {"role":"assistant", "content":f"I am Ophelia, here is a summary of our chats: {summary}"}]
        
        summaryTokens = calcTokens(newSet)
        db.reference(f"/{userID}").update({"Memories": newSet})
        db.reference(f"/{userID}").update({"MemoryTokens": summaryTokens})

    else:
        dbUserTokens += userTokens
        db.reference(f"/{userID}").update({"TotalUserTokens": dbUserTokens})

def usageHistory(userID, userTokens, outputTK):
    recordDB = db.reference(f"/{userID}/UsageHistory").get()
    x = datetime.datetime.now()
    date = x.strftime(f"%H:%M{time.tzname[time.localtime().tm_isdst]}, %d/%m/%Y")
    record = recordDB + f"[{date}, {userTokens}/{outputTK}] + "
    db.reference(f"/{userID}").update({"UsageHistory": f"{record}"})

def singleTokenCalc(text):
    encoding = tiktoken.get_encoding("cl100k_base")
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    tokenNumber = len(encoding.encode(text))
    return tokenNumber

def modelResponse(userID, userInput, dbMemories):
    memoryTokens = db.reference(f"/{userID}/MemoryTokens").get()

    dbMemories.append({"role":"user", "content": userInput}) 
    botResponse = client.chat.completions.create(model="gpt-3.5-turbo-0125", messages=dbMemories)
    assistantContent = botResponse.choices[0].message.content

    dbMemories.append({"role":"assistant", "content": assistantContent})

    db.reference(f"/{userID}").update({"Memories": dbMemories })

    iteratedInputTokens = singleTokenCalc(userInput) #input tokens for one specific iteration
    iteratedOutputTokens = singleTokenCalc(assistantContent) #output tokens for one specific iteration

    currentInputTokens = botResponse.usage.prompt_tokens #current cumulative input tokens
    currentOutputTokens = botResponse.usage.completion_tokens #current cumulative output tokens

    memoryTokens += (iteratedInputTokens + iteratedOutputTokens)

    db.reference(f"/{userID}").update({"MemoryTokens": memoryTokens })

    chatTokens = botResponse.usage.total_tokens #total chat tokens sent to the API

    tokenManager(userID, chatTokens)
    usageHistory(userID, currentInputTokens, currentOutputTokens)

    print(str(chatTokens))

    return assistantContent
    
#Only this function is to be called to use this module for AI 
def callModel(userID, userMessage):
    try:
        usernameExists(userID)
        dbMemories = getMemorySet(userID)
        balance = db.reference(f"/{userID}/Balance").get()
        totalUserData = db.reference(f"/{userID}/TotalUserTokens").get()
        if totalUserData >= balance:
            return False
        else:
            modelOutputCompletion = modelResponse(userID, userMessage, dbMemories)

            return modelOutputCompletion
    except Exception as e:
        return "Sorry, looks like an error occurred", e
     
#--------Debug Program-------#
def testModeA():
    print(f"Ping: {os.getcwd()}") #To get to know the files directory (in case of path errors)

def testModeB(userID, limit):
    count = 0
    Running = True
    try:
        while Running == True:
            print("")
            userContent = str(input("Prompt: "))
            if userContent == "Mozka":
                exit()
            else:       
                count += 1
                print("")
                response = callModel(userID, userContent)
                if response == False:
                    print("Sorry, out of tokens")
                else:
                    print("[" + str(count) + "]", "Ophelia:", response)
                if count == limit:
                    Running = False
    except Exception as e:
        print("")
        print("The Following Error Occurred:", e)

def jsonDumpsOutput(file):
    #For debugging purposes.
    #<file> must be a regular json.
    service_account_json_str = json.dumps(file) #JSON to string.
    print(service_account_json_str)

if __name__ == '__main__':
    userID = '877241797141725184'
    #registerAcc(userID)
    #changePersona(userID, 'C')
    testModeB(userID, 10)
    #tokenManager(userID, 10)
    #print(singleTokenCalc(personaA))
    #jsonDumpsOutput()

#--------Debug Program-------#
