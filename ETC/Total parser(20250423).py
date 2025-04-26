import re
import json

# 월 이름 매핑 (Full name과 축약형 모두 처리)
month_map = {
    'January': '01', 'Jan': '01',
    'February': '02', 'Feb': '02',
    'March': '03', 'Mar': '03',
    'April': '04', 'Apr': '04',
    'May': '05',
    'June': '06', 'Jun': '06',
    'July': '07', 'Jul': '07',
    'August': '08', 'Aug': '08',
    'September': '09', 'Sep': '09',
    'October': '10', 'Oct': '10',
    'November': '11', 'Nov': '11',
    'December': '12', 'Dec': '12'
}

def parse_period(period):
    period = period.strip()
    if not period:
        return None, None

    match1 = re.match(r'(\d{1,2})\s*-\s*(\d{1,2})\s+([A-Za-z]+),\s*(\d{4})', period)
    match2 = re.match(r'(\d{1,2})\s+([A-Za-z]+)\s*-\s*(\d{1,2})\s+([A-Za-z]+),\s*(\d{4})', period)
    match3 = re.match(r'([A-Za-z]+)\s*(\d{1,2})\s*-\s*([A-Za-z]+)\s*(\d{1,2}),\s*(\d{4})', period)

    if match1:
        day_start, day_end, month, year = match1.groups()
        month_num = month_map.get(month)
        if not month_num:
            return None, None
        start_date = f"{year}-{month_num}-{int(day_start):02d}"
        end_date = f"{year}-{month_num}-{int(day_end):02d}"
        return start_date, end_date

    elif match2:
        day_start, month_start, day_end, month_end, year = match2.groups()
        start_month_num = month_map.get(month_start)
        end_month_num = month_map.get(month_end)
        if not start_month_num or not end_month_num:
            return None, None
        start_date = f"{year}-{start_month_num}-{int(day_start):02d}"
        end_date = f"{year}-{end_month_num}-{int(day_end):02d}"
        return start_date, end_date

    elif match3:
        month_start, day_start, month_end, day_end, year = match3.groups()
        start_month_num = month_map.get(month_start)
        end_month_num = month_map.get(month_end)
        if not start_month_num or not end_month_num:
            return None, None
        start_date = f"{year}-{start_month_num}-{int(day_start):02d}"
        end_date = f"{year}-{end_month_num}-{int(day_end):02d}"
        return start_date, end_date

    return None, None

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

# StartDate, EndDate 추가
for tournament in combined_data:
    start, end = parse_period(tournament.get('Period', ''))
    tournament['StartDate'] = start
    tournament['EndDate'] = end

with open("combined_tennis_tournaments_2025.json", "w", encoding="utf-8") as f:
    json.dump(combined_data, f, indent=2, ensure_ascii=False)

print("✅ 저장 완료: combined_tennis_tournaments_2025.json")