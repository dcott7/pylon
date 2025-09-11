from bs4 import BeautifulSoup
import json
import requests
import time


OUT_FILE = "./data/formations.json"
BASE_URL = "https://www.madden-school.com"


def get_playbook_endpoints(endpoint: str = "/playbooks"):
    res = requests.get(BASE_URL + endpoint)
    soup = BeautifulSoup(res.text, "html.parser")
    divs = soup.find_all("div", class_="w-60 m-1 border text-white text-center")
    for div in divs:
        a_tag = div.find("a")
        if a_tag:
            yield a_tag["href"]


def get_formation_endpoints(playbook_endpoint: str):
    res = requests.get(BASE_URL + playbook_endpoint)
    soup = BeautifulSoup(res.text, "html.parser")
    divs = soup.find_all("div", class_="w-full sm:w-1/2 lg:w-1/3 px-2 mb-4")
    for div in divs:
        a_tag = div.find("a")
        if a_tag:
            yield a_tag["href"]


def get_play_names(play_endpoint: str):
    res = requests.get(BASE_URL + play_endpoint)
    soup = BeautifulSoup(res.text, "html.parser")
    play_divs = soup.find_all("div", class_="py-2 text-center w-full h-10 block font-bold text-sm text-white hover:text-[16px] hover:text-white")
    for div in play_divs:
        yield div.get_text(strip=True)


def main():
    data = []
    for pb in get_playbook_endpoints():
        for formation in get_formation_endpoints(pb):
            sections = formation.split("/")
            team_entry = sections[2]
            side_entry = sections[3]
            formation_entry = sections[4]
            subformation_entry = sections[5]
            plays_entry = list(get_play_names(formation))
            data.append({
                "team": team_entry,
                "side": side_entry,
                "formation": formation_entry,
                "subformation": subformation_entry,
                "plays": plays_entry
            })
    
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    

if __name__ == "__main__":
    main()