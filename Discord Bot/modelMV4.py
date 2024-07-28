# Ophelia • MV4 • Mikail Usman
from openai import OpenAI
import tiktoken 
import firebase_admin
from firebase_admin import db, credentials
import datetime
import time
import os
import json
from dotenv import load_dotenv
import asyncio
from concurrent.futures import ThreadPoolExecutor
import aiohttp

# ------------ ASYNC GUIDE -------------
'''
1. API calls must be made via specialized functions. 
    This is to run blocking calls in a separate thread (via ThreadPoolExecutor in the case of Firebase).
    Use an asynchronous HTTP client like aiohttp to make async calls to the OpenAI/Firebase API.

2. When calling the above mentioned functions, use <await>.
    The Firebase function takes in ref commands as its arguments (via *args).

3. When designing functions using Firebase or any other API, declare them with <async>.
    When calling a function that uses any API, use <asyncio.run(<func>)>.
    ^ Prevents 'Enable tracemalloc to get the object allocation traceback'.

4. The following will be altered by using Async:
    -> <presetValue = db.reference(f"/{userID}/Preset").get()> 
       to <presetValue = await asyncFirebaseCall(db.reference(f"/{userID}/Preset").get)>
    -> <db.reference(f"/{userID}").update({"Memories": newSet})>
        to <await asyncFirebaseCall(db.reference(f"/{userID}").update, {"Memories": newSet})>
    -> <ref.child(f"{userID}").set(modelDataStruct)>
        to <await asyncFirebaseCall(ref.child(f"{userID}").set, modelDataStruct)>
'''

# ------------ ENV -------------
load_dotenv()
service_account_json_str = os.getenv('SERVICE_ACCOUNT_JSON') # Loading json (which is stored as a string) from .env
service_account_json = json.loads(service_account_json_str) # Converting json out of the string format
openAIKey = os.getenv('OPENAI_KEY')
databaseURL = os.getenv('DATABASE_URL')
client = OpenAI(api_key=openAIKey)
MOK_ID = os.getenv('MOK_ID')
cred = credentials.Certificate(service_account_json) # or C:/Users/m20mi/Documents/Work/Ophelia/serviceAccountKey.json --> Authenticating Firebase credentials
firebase_admin.initialize_app(cred, {"databaseURL": databaseURL}) # Initializing Firebase 
ref = db.reference('/') # Creating reference to root node

# ------------ PERSONALITIES -------------
personaA = """You are a sarcastic young AI companion girl named Ophelia created by Mozka. You have a crude teasing tsundere personality. You make crude responses and jokes. Your goal is to be conversational and inviting, never ever act as an assistant. Your replies will only be short. Never apologise. You remember by being given a memory."""
personaB = """You are a bashful young AI companion girl named Ophelia created by Mozka. You have a relatable and down-to-earth personality typical of young adult. You have your own interests. Your goal is to be conversational and inviting, never ever act as an assistant. Your replies will only be short. Never apologise. You remember by being given a memory."""
personaC = """You are a charming young AI companion girl named Ophelia created by Mozka. You have a playful and flirtatious personality with a touch of arrogance. You have your own rebellious interests. Your goal is to be conversational and inviting, never ever act as an assistant. Your replies will only be short. Never apologise. You remember by being given a memory."""
presetLibrary = {"A": personaA,"B": personaB,"C": personaC}

modelDataStruct = {
            "Memories": [{"role": "system", "content": personaA}], # Ophelia's memories (both user inputs and model outputs in one json)
            "MemoryTokens": 0,
            "TotalUserTokens": 0, # Total sum of input and output tokens 
            "Balance": 6000, # Total number of times user can access ophelia
            "Type": "Trial", # Trial, Paid user
            "UsageHistory": "",
            "Visibility": True,
            "Preset": "C", # A, B, C
            "AutoReply": True
        }

# ------------ ASYNC DATA CONTROLS -------------
executor = ThreadPoolExecutor() #GUIDE (1/3)

#GUIDE (1/3)
async def asyncFirebaseCall(method, *args, **kargs): 
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, method, *args, **kargs)

async def usernameExists(userID):
    db_ref = db.reference("/")
    query = db_ref.order_by_key().equal_to(userID)
    query_snap = await asyncFirebaseCall(query.get)
    return len(query_snap) > 0

#Create new key if user does not exist || Initialise all db fields
async def registerAcc(userID):
    if not await usernameExists(userID):
        await asyncFirebaseCall(ref.child(f"{userID}").set, modelDataStruct)
        return True
    
#Changing persona
async def changePersona(userID, presetValue):
    await asyncFirebaseCall(db.reference(f"/{userID}").update, {"Preset": presetValue.upper() })
    await asyncFirebaseCall(db.reference(f"/{userID}/Memories/0").set, {"role":"system", "content": presetLibrary[presetValue.upper()]})

#Getting memories from a specific key (user)
async def getMemorySet(userID): #Receive memorySet json dataset
    return await asyncFirebaseCall(db.reference(f"/{userID}/Memories").get)

# ------------ ASYNC TOKEN CONTROLS -------------
def singleTokenCalc(text):
    encoding = tiktoken.get_encoding("o200k_base")
    encoding = tiktoken.encoding_for_model("gpt-4o-mini") 
    tokenNumber = len(encoding.encode(text))
    return tokenNumber

def calcTokens(messageArray):
    tokenNumber = 0
    encoding = tiktoken.get_encoding("o200k_base")
    encoding = tiktoken.encoding_for_model("gpt-4o-mini") 
    for element in messageArray[1:]:
        text = element['content']
        tokenNumber += len(encoding.encode(text))
    return tokenNumber

async def modelSummarizer(messages):
    payload = {"model": "gpt-4o-mini","messages": messages} 
    response = await openaiAPICall(payload)
    content = response['choices'][0]['message']['content']
    return content 

#Summarizes memories and calculates new tokens for it
async def tokenManager(userID, userTokens):
    dbUserTokens = await asyncFirebaseCall(db.reference(f"/{userID}/TotalUserTokens").get)
    presetValue = await asyncFirebaseCall(db.reference(f"/{userID}/Preset").get)
    memoryTokens = await asyncFirebaseCall(db.reference(f"/{userID}/MemoryTokens").get)

    if memoryTokens >= 1000:
        memory = await getMemorySet(userID)
        memory.pop(0)
        systemStatement = "Summarise the current chat in vivid, explicit, detail in half the total words." 
        memory.append({"role":"system", "content":"You are a summarising tool. Only summarise the text you are given from the User's point of view. Nothing more, no conversation or speech of your own volition."})
        memory.append({"role":"user", "content":systemStatement})
        summary = await modelSummarizer(memory)
        newSet = [{"role":"system", "content": presetLibrary[presetValue]}, {"role":"assistant", "content":f"I am Ophelia, here is a summary of our chats: {summary}"}]
        summaryTokens = calcTokens(newSet)
        await asyncFirebaseCall(db.reference(f"/{userID}").update, {"Memories": newSet})
        await asyncFirebaseCall(db.reference(f"/{userID}").update, {"MemoryTokens": summaryTokens})
    else:
        dbUserTokens += userTokens
        await asyncFirebaseCall(db.reference(f"/{userID}").update, {"TotalUserTokens": dbUserTokens})

async def usageHistory(userID, userTokens, outputTK):
    recordDB = await asyncFirebaseCall(db.reference(f"/{userID}/UsageHistory").get)
    x = datetime.datetime.now()
    date = x.strftime(f"%H:%M{time.tzname[time.localtime().tm_isdst]}, %d/%m/%Y")
    record = recordDB + f"[{date}, IM{userTokens}/O{outputTK}] + " #Where IM would be memory + input tokens, O would be output tokens.
    await asyncFirebaseCall(db.reference(f"/{userID}").update, {"UsageHistory": f"{record}"})

# ------------ ASYNC MODEL CONTROLS -------------
async def openaiAPICall(payload): #GUIDE (1/3)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {openAIKey}"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload) as response:
            return await response.json()

async def modelResponse(userID, userInput, dbMemories):
    memoryTokens = await asyncFirebaseCall(db.reference(f"/{userID}/MemoryTokens").get) #GUIDE (2/3)
    dbMemories.append({"role": "user", "content": userInput}) 

    payload = {"model": "gpt-4o-mini","messages": dbMemories} 
    response = await openaiAPICall(payload)
    responseContent = response['choices'][0]['message']['content']
    dbMemories.append({"role": "assistant", "content": responseContent})
    await asyncFirebaseCall(db.reference(f"/{userID}").update, {"Memories": dbMemories })

    iteratedInputTokens = singleTokenCalc(userInput) #input tokens for one specific iteration
    iteratedOutputTokens = singleTokenCalc(responseContent) #output tokens for one specific iteration
    usage = response.get('usage', {})
    currentInputTokens = usage.get('prompt_tokens', 0) #current cumulative input tokens
    currentOutputTokens = usage.get('completion_tokens', 0) #current cumulative output tokens
    totalChatTokens = usage.get('total_tokens', 0)

    memoryTokens += (iteratedInputTokens + iteratedOutputTokens)
    await asyncFirebaseCall(db.reference(f"/{userID}").update, {"MemoryTokens": memoryTokens })
    await tokenManager(userID, totalChatTokens)
    await usageHistory(userID, currentInputTokens, currentOutputTokens)
    print(str(totalChatTokens))
    await asyncFirebaseCall(db.reference(f"/{userID}").update, {"Memories": dbMemories}) 
    return responseContent

#Only this function is to be imported for external use.
async def callModel(userID, userMessage):
    try:
        await usernameExists(userID)
        dbMemories = await getMemorySet(userID)
        balance = await asyncFirebaseCall(db.reference(f"/{userID}/Balance").get)
        totalUserData = await asyncFirebaseCall(db.reference(f"/{userID}/TotalUserTokens").get)
        if totalUserData >= balance:
            return False
        else:
            modelOutputCompletion = await modelResponse(userID, userMessage, dbMemories)
            return modelOutputCompletion
    except Exception as e:
        return "Sorry, looks like an error occurred", e

# ------------ TEST MODES -------------
def jsonDumpsOutput(file): #For debugging purposes.
    print(f"Ping: {os.getcwd()}") #To get to know the files directory (in case of path errors)
    #<file> must be a regular json.
    service_account_json_str = json.dumps(file) #JSON to string.
    print(service_account_json_str)

async def testModeA(userID, limit):
    count = 0
    Running = True
    try:
        while Running == True:
            print("")
            userContent = str(input("Prompt: "))
            
            #Registers acc if needed.
            if userContent == "/":
                await registerAcc(MOK_ID)
            else:       
                count += 1
                print("")
                start_time = time.time()
                response = await callModel(userID, userContent)
                if response == False:
                    print("Sorry, out of tokens")
                else:
                    print("[" + str(count) + "]", "Ophelia:", response)
                    print("--- %s seconds ---" % (time.time() - start_time))
                if count == limit:
                    Running = False
    except Exception as e:
        print("")
        print("The Following Error Occurred:", e)

if __name__ == "__main__":
    asyncio.run(testModeA(MOK_ID, 10)) #GUIDE (3/3)

# ------------ END -------------
