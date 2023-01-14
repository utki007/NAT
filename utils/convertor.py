import time
import discord
import math
import datetime
from TagScriptEngine import Interpreter, adapter, block
from discord.ext import commands,tasks

blocks = [
    block.MathBlock(),
    block.RandomBlock(),
    block.RangeBlock(),
]
engine = Interpreter(blocks)
     
async def convert_to_time(query):
    query = query.lower()
    query = query.replace("d", "*86400+",1)
    query = query.replace("h", "*3600+",1)
    query = query.replace("m", "*60+",1)       
    query = query.replace("s", "*1+",1)
    if query.endswith("+"):
        query = f"{query}0"
    return query
    
async def convert_to_numeral(query):
    query = query.lower()
    query = query.replace("k", "e3",100)
    query = query.replace("m", "e6",100)       
    query = query.replace("b", "e9",100)  
    return query

async def calculate(query):
    query = query.replace(",", "")
    engine_input = "{m:" + query + "}"
    start = time.time()
    output = engine.process(engine_input)
    end = time.time()

    output_string = output.body.replace("{m:", "").replace("}", "")
    return int(float(output_string))

async def millify(n):
    n = float(n)
    millnames = ['',' K',' Mil',' Bil']
    millidx = max(0,min(len(millnames)-1,
                        int(math.floor(0 if n == 0 else math.log10(abs(n))/3))))

    # return '{:.1f}{}'.format(n / 10**(3 * millidx), millnames[millidx])
    return f'{round(n / 10**(3 * millidx),1):,}{millnames[millidx]}'

async def convert_to_human_time(seconds):
    
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder , 3600)
    minutes, seconds = divmod(remainder, 60)
        
    human_timer = []
    if int(days)>0:
        if int(days)==1:
            human_timer.append(f"{int(days)} day")
        else:
            human_timer.append(f"{int(days)} days")
    if int(hours)>0:
        if int(hours) == 1:
            human_timer.append(f'{int(hours)} hour')
        else:
            human_timer.append(f'{int(hours)} hours')
    if int(minutes)>0:
        if int(minutes) == 1:
            human_timer.append(f'{int(minutes)} minute')
        else:
            human_timer.append(f'{int(minutes)} minutes')
    if int(seconds)>0:
        if int(seconds) == 1:
            human_timer.append(f'{int(seconds)} second')
        else:
            human_timer.append(f'{int(seconds)} seconds')
    
    if len(human_timer)>1:
        timer = f'{", ".join(i for i in human_timer[:-1])} and {human_timer[-1]}'
    else:
        timer = human_timer[-1]

    return timer.strip()