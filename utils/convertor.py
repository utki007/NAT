import re
import math
from TagScriptEngine import Interpreter, block
from discord.ext import commands

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
    output = engine.process(engine_input)

    output_string = output.body.replace("{m:", "").replace("}", "")
    return round((float(output_string)),2)

async def millify(n):
    n = float(n)
    millnames = ['',' K',' Mil',' Bil']
    millidx = max(0,min(len(millnames)-1,
                        int(math.floor(0 if n == 0 else math.log10(abs(n))/3))))

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

def dict_to_tree(data, indent=0):
    tree = ""
    for i, (key, value) in enumerate(data.items()):
        tree += "\n" + "│  "*indent
        if isinstance(value, (dict, list)):
            tree += f"├─{key}:"
            if isinstance(value, dict):
                tree += dict_to_tree(value, indent=indent+1)
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    tree += "\n" + "│  "*(indent+1) + f"├─{key}[{index}]:"
                    if isinstance(item, (dict, list)):
                        tree += dict_to_tree(item, indent=indent+2)
                    else:
                        tree += "\n" + "│  "*(indent+2) + str(item)
        else:
            if i == len(data)-1:
                tree += f"└─{key}: {value}"
            else:
                tree += f"├─{key}: {value}"
    return tree

time_regex = re.compile("(?:(\d{1,5})(h|s|m|d))+?")
time_dict = {"h": 3600, "s": 1, "m": 60, "d": 86400, "w": 604800, "y": 31536000}


class TimeConverter(commands.Converter):
    async def convert(self, ctx, argument):
        matches = time_regex.findall(argument.lower())
        time = 0
        for v, k in matches:
            try:
                time += time_dict[k]*float(v)
            except KeyError:
                raise commands.BadArgument("{} is an invalid time-key! h/m/s/d are valid!".format(k))
            except ValueError:
                raise commands.BadArgument("{} is not a number!".format(v))
        return time

class DMCConverter(commands.Converter):
    async def convert(self, ctx, value: str):

        value = value.lower()
        value = value.replace("⏣", "").replace(",", "").replace("k", "e3").replace("m", "e6").replace(" mil", "e6").replace("mil", "e6").replace("b", "e9")
        if 'e' not in value:
            return int(value)
        value = value.split("e")

        if len(value) > 2: 
            raise Exception(f"Invalid number format try using 1e3 or 1k: {value}")

        price = value[0]
        try:
            multi = int(value[1])
            price = float(price) * (10 ** multi)
        except ValueError:
            return None

        return int(price)