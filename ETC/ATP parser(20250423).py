import re
import json

with open("atp_text.txt", "r", encoding="utf-8") as file:
    lines = [line.strip() for line in file if line.strip()]

tournaments = []
i = 0

while i < len(lines):
    line = lines[i]

    # 대회명 찾기
    if re.match(r"^tournament-badge-\d+", line):
        tournament = lines[i + 1]
        location_line = lines[i + 2]
        surface = lines[i + 5] if i + 5 < len(lines) else ""
        environment = lines[i + 6] if i + 6 < len(lines) else ""

        # 도시, 국가, 날짜 추출
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
            "Environment": environment
        })

        i += 7  # 다음 대회로 이동
    else:
        i += 1

# 저장
with open("atp_tournaments_2025.json", "w", encoding="utf-8") as f:
    json.dump(tournaments, f, indent=2, ensure_ascii=False)

print("✅ 저장 완료: atp_tournaments_2025.json")
