#Debug
debugFlag = bool(0)

try:
    from anipy_api.provider.providers.yugen_provider import YugenProvider
    from anipy_api.provider.providers.gogo_provider import GoGoProvider
    from anipy_api.anime import Anime
    from anipy_api.provider import LanguageTypeEnum
except:
    try:
        os.system('pip install anipy-api')
        from anipy_api.provider.providers.yugen_provider import YugenProvider
        from anipy_api.provider.providers.gogo_provider import GoGoProvider
        from anipy_api.anime import Anime
        from anipy_api.provider import LanguageTypeEnum
    except:
        print("Error: Couldn't install anipy-api")
        exit(1)
        
import os
import concurrent.futures

def titleGen(index, letter='E'):
    if index in range(9): return f'{letter}0{index+1}' if letter == 'E' else f'{letter}0{index}'
    if index == 9: return f'{letter}10' if letter == "E" else f'{letter}09'
    return f'{letter}{index+1}' if letter == 'E' else f'{letter}{index}'

def removeSymbols(string):
    return ''.join(e for e in string if e.isalnum() or e.isspace())

def fetch_episode(selectedAnime, e, selectedLanguage):
    try:
        video = selectedAnime.get_video(
            episode=e,
            lang=selectedLanguage,
            preferred_quality=1080
        )
        print(f'Episode {e} done')
        return e, video
    except Exception as exc:
        print(f'Episode {e} failed: {exc}')
        return e, None

def inputs():
    name = input('Enter Anime Name: ')
    while True:
        try:season = int(input('Season: '));break
        except:print('Season input (Int: 1, 2, 3, ...)')
    ver = None
    while ver not in ['d','dub','Dub','D','s','sub','S','Sub','']:ver = input("Dub or Sub (d/S):")
    ver = True if ver in ['d','dub','Dub','D'] else False
    return [name,season,ver]

# Banner
try:
    import bannerchar
    print(bannerchar.bannerWord('ANIME'), end='\r')
    print(bannerchar.bannerWord('PLAYLIST'), end='\r')
    print(bannerchar.bannerWord('CREATOR'), end='\r')
except ImportError:
    pass

# Defining Providers
provider = YugenProvider()
ggp = GoGoProvider()

# Inputs
if not debugFlag: name,season,ver = inputs()
else: name,season,ver = "smartphone", 1, True


# Initial Search
searchResults = provider.get_search(name)
if not searchResults:
    print(f'No anime with name "{name}" found!')
    exit(0)

# Selection
print("Yugen")
anime = []
for r in searchResults:
    anime.append(Anime(provider, r.name, r.identifier, r.languages))
if not debugFlag:
    for i in range(len(anime)):
        print(f"{i}. {anime[i].name} ({anime[i].languages})")
    y = int(input('Select: '))
else: y=0
selectedAnime = anime[y]
selectedLanguage = LanguageTypeEnum.DUB if ('DUB' in [x.name for x in selectedAnime.languages]) and ver else LanguageTypeEnum.SUB
episodes = selectedAnime.get_episodes(lang=selectedLanguage)
print('Eps:', episodes)

# Gathering URLs
eps = {}
failed = []
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    future_to_episode = {executor.submit(fetch_episode, selectedAnime, e, selectedLanguage): e for e in episodes}
    for future in concurrent.futures.as_completed(future_to_episode):
        episode = future_to_episode[future]
        try:
            ep_num, result = future.result()
            if result:
                eps[ep_num] = result
            else:
                failed.append(ep_num)
        except Exception as exc:
            print(f'Episode {episode} generated an exception: {exc}')
            failed.append(episode)

# Retry for failed episodes
if failed:
    print('Failed:', *failed)
    print('Retrying Failed')
    ggsr = ggp.get_search(name)
    gga = []
    g = None
    for r in ggsr:
        gga.append(Anime(ggp, r.name, r.identifier, r.languages))
    for i in range(len(gga)):
        if gga[i].name == selectedAnime.name and (selectedLanguage in gga[i].languages):
            g = i
            break

newFail = []
if failed and g is not None:
    ggsa = gga[g]
    ggsl = LanguageTypeEnum.DUB if ('DUB' in [x.name for x in ggsa.languages]) and ver else LanguageTypeEnum.SUB
    ggeps = ggsa.get_episodes(lang=ggsl)

if failed and g is not None:
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_episode = {executor.submit(fetch_episode, ggsa, e, selectedLanguage): e for e in failed}
        for future in concurrent.futures.as_completed(future_to_episode):
            episode = future_to_episode[future]
            try:
                ep_num, result = future.result()
                if result:
                    eps[ep_num] = result
                else:
                    newFail.append(ep_num)
            except Exception as exc:
                print(f'Episode {episode} generated an exception: {exc}')
                newFail.append(episode)

if newFail:
    print("New Fails:", *newFail)
    exit(1)

# Setting array of URL
urlArr = [eps[e].url for e in sorted(eps.keys())]
dubORsub = 'DUB' if ver else 'SUB'
if len(urlArr) < 3:
    exit()
title = removeSymbols(selectedAnime.get_info().name)

# Creating XSPF File
file_path = f'{title} {titleGen(season, "S")} {dubORsub}.xspf'
with open(file_path, 'w') as f:
    f.write(f'''<?xml version="1.0" encoding="UTF-8"?>\n<playlist xmlns="http://xspf.org/ns/0/" xmlns:vlc="http://www.videolan.org/vlc/playlist/ns/0/" version="1">\n\t<title>{title} {titleGen(season, "S")}</title>\n    <trackList>''')
    for i, url in enumerate(urlArr):
        f.write(f'''\n        <track>\n            <location>{url}</location>\n            <title>{titleGen(season, "S")} {titleGen(i)}</title>\n\t\t\t<extension application="http://www.videolan.org/vlc/playlist/0">\n\t\t\t\t<vlc:id>{i}</vlc:id>\n\t\t\t\t<vlc:option>network-caching=1000</vlc:option>\n\t\t\t</extension>\n        </track>''')
    f.write('''\n\t</trackList>\n\t<extension application="http://www.videolan.org/vlc/playlist/0">''')
    for i in range(len(urlArr)):
        f.write(f'''\n            <vlc:item tid="{i}"/>''')
    f.write('''\n\t</extension>\n</playlist>\n''')

print('Playlist Created!')

# Print Path
print('Open the file with VLC')
print(f'File Path: {os.path.abspath(file_path)}')