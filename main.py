#Imports
try:
    import os
    from anipy_api.provider.providers.yugen_provider import YugenProvider
    from anipy_api.provider.providers.gogo_provider import GoGoProvider
    from anipy_api.anime import Anime
    from anipy_api.provider import LanguageTypeEnum
except:
    try:
        import os
        os.system('pip install anipy-api')
        from anipy_api.provider.providers.yugen_provider import YugenProvider
        from anipy_api.provider.providers.gogo_provider import GoGoProvider
        from anipy_api.anime import Anime
        from anipy_api.provider import LanguageTypeEnum
    except:
        print("Error: Couldn't install anipy-api")
        exit(1)

#Functions
def titleGen(index, letter='E'):
    if index in range(9):return f'{letter}0{index+1}' if letter == 'E' else f'{letter}0{index}'
    if index == 9:return f'{letter}10' if letter =="E" else f'{letter}09'
    return f'{letter}{index+1}' if letter == 'E' else f'{letter}{index}'

def removeSymbols(string):
    return ''.join(e for e in string if e.isalnum() or e.isspace())

#Banner
try:
    import bannerchar
    print(bannerchar.bannerWord('ANIME'),end='\r')
    print(bannerchar.bannerWord('PLAYLIST'),end='\r')
    print(bannerchar.bannerWord('CREATOR'),end='\r')
except:
    pass

#Defining Providers
provider = YugenProvider()
ggp = GoGoProvider()

#Inputs
name = input('Enter Anime Name: ')
while True:
    try:
        season = int(input('Season: '))
        break
    except:
        print('Season input (Int: 1, 2, 3, ...)')

ver = None
while ver not in ['d','dub','Dub','D','s','sub','S','Sub','']:
    ver = input("Dub or Sub (d/S):")
ver = True if ver in ['d','dub','Dub','D'] else False

#Initial Search
searhResults=provider.get_search(name)
if not searhResults:
    print(f'No anime with name "{name}" found!')
    exit(0)

#Selection
print("Yugen")
anime=[]
for r in searhResults:anime.append(Anime(provider, r.name, r.identifier, r.languages))
for i in range(len(anime)):print(f"{i}. {anime[i].name} ({anime[i].languages})")
y = int(input('Select: '))
selectedAnime = anime[y]
selectedLanguage=LanguageTypeEnum.DUB if ('DUB' in [x.name for x in selectedAnime.languages]) and ver else LanguageTypeEnum.SUB
episodes = selectedAnime.get_episodes(lang=selectedLanguage)
print('Eps:',episodes)

#Gathering URL's
eps=[]
failed=[]
for e in episodes:
    try:
        eps += [ selectedAnime.get_video(
                    episode=e, 
                    lang=selectedLanguage,
                    preferred_quality=1080 
                    )
                ]
        print('Episode',e, 'done', end='\r')
    except:
        print('Episode',e, 'failed')
        failed += [e]

#Retry for failed episodes
if failed :
    print('failed:',*failed)
    print('Retrying Failed')
    ggsr=ggp.get_search(name)
    gga=[]
    g=None
    for r in ggsr:gga.append(Anime(ggp, r.name, r.identifier, r.languages))
    for i in range(len(gga)):
        if gga[i].name == selectedAnime.name and (selectedLanguage in gga[i].languages):
            g = i
            break
if failed and g is not None:
    ggsa = gga[g]
    ggsl=LanguageTypeEnum.DUB if ('DUB' in [x.name for x in ggsa.languages]) and ver else LanguageTypeEnum.SUB
    ggeps = ggsa.get_episodes(lang=ggsl)
newFail = []
if failed and g is not None:
    for e in failed:
        try:
            eps.insert(e-1, ggsa.get_video(
                        episode=e, 
                        lang=selectedLanguage,
                        preferred_quality=1080
                        )
                    )
            print('Episode',e, 'done', end='\r')
        except:
            newFail+=[e]
            print('Episode',e, 'failed')
if  newFail:
    print("New Fails:",*newFail)
    exit(1)
    
#Setting array of URL
listOut=[i.url for i in eps]
urlArr = listOut
dubORsub = 'DUB' if ver else 'SUB'
if len(urlArr) <3 :exit()
title = removeSymbols(selectedAnime.get_info().name)

#Creating XSPF File
f=open(f'{title} {titleGen(season,"S")} {dubORsub}.xspf','w')
f.write(f'''<?xml version="1.0" encoding="UTF-8"?>\n<playlist xmlns="http://xspf.org/ns/0/" xmlns:vlc="http://www.videolan.org/vlc/playlist/ns/0/" version="1">\n	<title>{title} {titleGen(season,"S")}</title>\n    <trackList>''')
for i in range(len(urlArr)):f.write(f'''\n        <track>\n            <location>{urlArr[i]}</location>\n            <title>{titleGen(season,"S")} {titleGen(i)}</title>\n			<extension application="http://www.videolan.org/vlc/playlist/0">\n				<vlc:id>{i}</vlc:id>\n				<vlc:option>network-caching=1000</vlc:option>\n			</extension>\n        </track>''')
f.write('''\n	</trackList>\n	<extension application="http://www.videolan.org/vlc/playlist/0">''')
for i in range(len(urlArr)):f.write(f'''\n            <vlc:item tid="{i}"/>''')
f.write('''\n	</extension>\n</playlist>\n''')
f.close()
print('Playlist Created!')

#Print Path
print('Open the file with VLC')
print(f'File Path: {os.path.abspath(f.name)}')