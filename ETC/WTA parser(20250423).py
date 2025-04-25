import re
import json

# ------------ ATP 처리 ------------ #
def parse_atp(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        lines = [line.strip() for line in file if line.strip()]
    
    tournaments = []
    i = 0

    while i < len(lines):
        line = lines[i]
        if re.match(r"^tournament-badge-\d+", line):
            tournament = lines[i + 1]
            location_line = lines[i + 2]
            surface = lines[i + 5] if i + 5 < len(lines) else ""
            environment = lines[i + 6] if i + 6 < len(lines) else ""

            loc_match = re.match(r"^(.*?), (.*?) \| (.+)$", location_line)
            if loc_match:
                city, country, period = loc_match.groups()
            else:
                city = country = period = ""

            tournaments.append({
                "Tournament": tournament,
                "City": city,
                "Country": country,
                "Period": period,
                "Surface": surface,
                "Environment": environment,
                "Tour": "ATP"
            })
            i += 7
        else:
            i += 1
    return tournaments

# ------------ WTA 처리 ------------ #
def parse_wta(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        lines = [line.strip() for line in file.readlines() if line.strip()]

    tournaments = []
    i = 0

    date_pattern = re.compile(r"^[A-Za-z]{3} \d{1,2} - [A-Za-z]{3} \d{1,2}, 2025$")
    wta_levels = {"Grand Slam", "Finals", "WTA 1000", "WTA 500", "WTA 250", "WTA 125"}

    while i < len(lines):
        line = lines[i]
        if date_pattern.match(line):
            period = line
            surface = lines[i + 1]
            level = lines[i + 2] if lines[i + 2] in wta_levels else ""
            tournament = lines[i + 3]
            location = lines[i + 4]
            city_country = location.split(",")
            city = city_country[0].strip().upper()
            country = city_country[1].strip().upper() if len(city_country) > 1 else ""

            entry = {
                "Tournament": tournament,
                "City": city,
                "Country": country,
                "Period": period,
                "Surface": surface,
                "Level": level,
                "Tour": "WTA"
            }

            tournaments.append(entry)
            i += 5 if level else 4
        else:
            i += 1
    return tournaments

# ------------ 통합 및 저장 ------------ #
atp_data = parse_atp("atp_text.txt")
wta_data = parse_wta("wta_schedule_2025.txt")

combined_data = atp_data + wta_data

with open("combined_tennis_tournaments_2025.json", "w", encoding="utf-8") as f:
    json.dump(combined_data, f, indent=2, ensure_ascii=False)

print("✅ 저장 완료: combined_tennis_tournaments_2025.json")
