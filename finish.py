"""Space health check."""

import csv
import math
import os
import time
from datetime import datetime

import streamlit as st

st.set_page_config(page_title="Space Health", page_icon="🚀", layout="wide")
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');
html,body,p,label,h1,h2,h3,td,th,button,input,[data-testid="stMarkdownContainer"]{
  font-family:'Press Start 2P',monospace!important;font-size:11px;line-height:1.9}
body,[data-testid="stAppViewContainer"]{background:#050a12;color:#e0fbfc}
h1{font-size:18px;color:#ffd23f;text-shadow:4px 4px 0 #003f4d}
h2,h3{font-size:12px;color:#00d4ff}
label{color:#00d4ff;font-size:9px}
[data-baseweb="select"]>div{border-radius:0;background:#0b1a2b;
  border:3px solid #00d4ff;box-shadow:4px 4px 0 #003f4d}
[data-baseweb="input"]{border:none;box-shadow:none;background:transparent;padding:2px 8px}
[data-baseweb="input"] input,.pixel-input{font-family:'Press Start 2P',monospace!important;
  font-size:12px;color:#212529;background:#ffffff;border:none;outline:none;padding:12px 16px;
  margin:8px 0;box-shadow:0 -4px 0 0 #000,0 4px 0 0 #000,-4px 0 0 0 #000,4px 0 0 0 #000,
  inset -4px -4px 0 0 #adafbc}
[data-baseweb="input"]>*:focus-within input,.pixel-input:focus{background:#fffbe6;
  box-shadow:0 -4px 0 0 #000,0 4px 0 0 #000,-4px 0 0 0 #000,4px 0 0 0 #000,
  inset -4px -4px 0 0 #e59400}
button[kind="primary"]{border-radius:0;background:#00d4ff;color:#04121c;
  border:3px solid #04121c;box-shadow:5px 5px 0 #003f4d}
[data-testid="stMetric"]{background:#0b1a2b;border:3px solid #00d4ff;
  box-shadow:6px 6px 0 #003f4d;padding:12px}
[data-testid="stImage"] img{image-rendering:pixelated}
.bub{background:#0b1a2b;border:4px solid #00d4ff;box-shadow:6px 6px 0 #003f4d;
  padding:14px 18px;margin-left:10px;min-height:70px}
.who{color:#ffd23f;font-size:9px;margin-bottom:8px}
.pt{border-collapse:collapse;width:100%;margin:6px 0}
.pt th,.pt td{border:2px solid #00d4ff;padding:6px 8px;font-size:10px;text-align:left}
.pt th{color:#ffd23f;background:#0b1a2b}
.pt .bar{display:inline-block;height:10px;min-width:2px;background:#00d4ff;
  margin-right:6px;vertical-align:middle}
</style>""", unsafe_allow_html=True)

LOG = "health_log.csv"
WHO = {"crew": ("CREW", "🧑‍🚀", ["crew.png", "astronaut.png", "CREW_closed.png"]),
       "rover": ("ROVER", "🚙", ["rover.png", "robot.png"])}

SYS = ["bone", "spine", "muscle", "eye", "gut", "blood", "mind"]
LAB = dict(zip(SYS, ["Bone", "Spine", "Muscle", "Eyes", "Stomach", "Blood", "Mind"]))
FACT = ["grav", "rad", "sleep", "move", "mind", "food"]
FIELDS = ["time", "name", "place", "days", "weight", "sleep", "move", "total"] + SYS

PLACE = {"Earth": (1, .6), "Mars": (.38, 1.8), "Jupiter": (1, 5),
         "Saturn": (1, 3), "Deep space": (0, 1.8)}
HABITS = ["exercise", "meditate", "call home", "music", "sleep 8 h"]

BASE = dict(zip(SYS, [[12, 2, 2, 6, 1, 3], [8, 1, 3, 3, 2, 2], [15, 2, 3, 8, 2, 4],
                      [3, 4, 2, 0, 2, 2], [8, 3, 3, 1, 4, 5], [8, 3, 3, 4, 3, 4],
                      [2, 2, 10, 3, 8, 2]]))

K1, K2 = 55, 140
SLOT = ["08:00", "13:00", "18:00", "22:00"]

SUPP = {
    "bone": [("D3", "1000 IU", "08:00", "food"), ("Calcium", "500 mg", "18:00", "not with iron")],
    "spine": [("D3", "1000 IU", "08:00", "food"), ("Magnesium", "200 mg", "22:00", "bed")],
    "muscle": [("Protein", "20 g", "13:00", "post-workout"), ("Creatine", "3 g", "13:00", "water")],
    "eye": [("Lutein", "10 mg", "13:00", "meal"), ("Omega-3", "1 g", "18:00", "meal")],
    "gut": [("Probiotic", "1 cap", "08:00", "empty"), ("Fibre", "5 g", "22:00", "water")],
    "blood": [("Omega-3", "1 g", "18:00", "meal"), ("Iron", "18 mg", "08:00", "vit C")],
    "mind": [("Magnesium", "300 mg", "22:00", "bed"), ("B-complex", "1 tab", "08:00", "food")],
    "rad": [("Vit C", "500 mg", "13:00", "food"), ("NAC", "600 mg", "18:00", "water")],
}

BAD = [("Calcium", "Iron"), ("Calcium", "Magnesium")]

TODO = {
    "bone": "Load 6 days a week, DEXA every 60 days.",
    "spine": "10 min decompression daily, log spine length.",
    "muscle": "Lift 5 days a week, 1.6 g protein/kg.",
    "eye": "20-20-20 rule, eye check every 30 days.",
    "gut": "Fixed meals, 25 g fibre, report reflux.",
    "blood": "LBNP 2 h, 30 min cardio, 2.5 L water.",
    "mind": "Fixed sleep window, call home daily.",
}


def save(row):
    new = not os.path.exists(LOG)
    with open(LOG, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)


def tbl(rows):
    if not rows:
        return
    head = "".join("<th>" + str(k) + "</th>" for k in rows[0])
    body = "".join("<tr>" + "".join("<td>" + str(v) + "</td>" for v in r.values()) + "</tr>"
                   for r in rows)
    st.markdown("<table class='pt'><tr>" + head + "</tr>" + body + "</table>",
                unsafe_allow_html=True)


def bars(tab):
    keys = [k for k in tab[0] if k != "Check"]
    top = max(1, max(r[k] for r in tab for k in keys))
    head = "<tr><th>System</th>" + "".join("<th>" + str(r["Check"]) + "</th>"
                                            for r in tab) + "</tr>"
    body = ""
    for k in keys:
        body += "<tr><td>" + k + "</td>"
        for r in tab:
            w = max(2, round(r[k] / top * 70))
            body += ("<td><i class='bar' style='width:" + str(w) + "px'></i>"
                     + str(r[k]) + "</td>")
        body += "</tr>"
    st.markdown("<table class='pt'>" + head + body + "</table>", unsafe_allow_html=True)


def bmi(h, w):
    return w / (h / 100) ** 2


def food(b):
    return 1 if b < 18.5 else .15 if b < 25 else .5 if b < 30 else .9


def mood(mv, sl, hb):
    return int(max(1, min(5, round(1 + len(hb) + mv - max(0, 7 - sl)))))


def score(p):
    g, rd = PLACE[p["place"]]
    days = max(1, p["days"])
    d = days / 30
    sev = {"grav": 1 - g, "rad": min(1, rd / 2),
           "sleep": min(1, max(0, 7 - p["sleep"]) / 4), "move": 1 - p["move"],
           "mind": (5 - p["mood"]) / 4, "food": food(bmi(p["h"], p["w"]))}

    pts = {s: sum(b * sev[f] for b, f in zip(BASE[s], FACT)) * d for s in SYS}
    ill = {s: round(100 * (1 - math.exp(-pts[s] / K1)), 1) for s in SYS}
    tab = [{"System": LAB[s],
            **{f: round(b * sev[f] * d, 1) for b, f in zip(BASE[s], FACT)},
            "Illness %": ill[s]} for s in SYS]

    r = {"p": p, "rd": rd, "day": days, "ill": ill, "tab": tab,
         "all": round(100 * (1 - math.exp(-sum(pts.values()) / K2)), 1),
         "canc": round(rd * days / 1000 * 5, 2), "mood": p["mood"],
         "bmi": round(bmi(p["h"], p["w"]), 1), "rad": rd * days}
    r["supp"], r["warn"] = supps(r, p["th"])
    r["plan"] = plan(p, r)
    return r


def supps(r, th):
    pick = [x for s in SYS if r["ill"][s] >= th for x in SUPP[s]]
    if r["rad"] >= 50:
        pick += SUPP["rad"]
    if r["mood"] <= 2:
        pick += SUPP["mind"]

    out = []
    for n, dose, when, how in pick:
        if n not in [o["pills"] for o in out]:
            out.append({"pills": n, "dose": dose, "when": when, "how": how})
    if not out:
        return [], []

    cap = 2 if len(out) <= 2 else 1 if len(out) <= 4 else 3
    slots = {k: [] for k in SLOT}
    for o in out:
        k = o["when"]
        if len(slots[k]) >= cap:
            k = min(SLOT, key=lambda x: len(slots[x]))
        o["when"] = k
        slots[k].append(o)

    warn = [k + ": " + ", ".join(o["pills"] for o in slots[k]) + " - 10-15 min apart."
            for k in SLOT if len(slots[k]) > 1]
    for k in SLOT:
        ns = [o["pills"] for o in slots[k]]
        warn += [k + ": " + a + " and " + b + " block each other, 2 h apart."
                 for a, b in BAD if a in ns and b in ns]
    if len(out) > 2:
        warn.append("More than 2: one per slot, iron away from calcium.")

    rows = [{"Time": k, "Supplement": o["pills"], "Dose": o["dose"], "How": o["how"]}
            for k in SLOT for o in slots[k]]
    return rows, warn


def plan(p, r):
    day = [("06:30", "Wake, water, stretch"), ("07:00", "Breakfast, protein + carbs"),
           ("08:00", "Resistance 45 min" if p["move"] else "Start resistance, 20 min"),
           ("10:00", "Water, eye rest"), ("12:30", "Lunch, fibre + veg")]
    if r["mood"] <= 3:
        day.append(("14:00", "Mindfulness + call home"))
    if r["rad"] >= 50:
        day.append(("15:00", "Antioxidant + rest"))
    day += [("17:00", "Cardio 30 min"), ("18:30", "Dinner, iron + vit C"),
            ("21:30", "Lights down, sleep 7-8 h")]
    return [{"Time": t, "Action": a} for t, a in day]


def show(r, title):
    p = r["p"]
    hit = [s for s in SYS if r["ill"][s] >= p["th"]]
    msg = "Overall risk " + str(r["all"]) + "%. "
    msg += "Watch: " + ", ".join(LAB[s] for s in hit[:3]) + "." if hit else \
        "All systems are below your threshold."
    say(st.empty(), "rover", msg + " Cancer risk +" + str(r["canc"]) + "%.")

    st.subheader(title)
    a, b, c, d = st.columns(4)
    a.metric("Overall", f'{r["all"]}%')
    b.metric("Cancer", f'{r["canc"]}%')
    c.metric("Mood", f'{r["mood"]}/5')
    d.metric("BMI", r["bmi"])
    st.caption(f'{p["place"]} | day {r["day"]} | {r["rd"]} mSv/day | {r["rad"]:.0f} mSv')

    st.write("**Risk matrix and illness %**")
    tbl(r["tab"])

    if r["supp"]:
        st.write("**Supplements**")
        tbl(r["supp"])
        for w in r["warn"]:
            st.info(w)
    else:
        st.success("No supplement needed.")

    st.write("**Routine**")
    tbl(r["plan"])

    if hit:
        st.write("**What to do**")
        for s in hit:
            st.markdown(f'- **{LAB[s]}** ({r["ill"][s]}%): {TODO[s]}')
    else:
        st.success("All below the threshold.")


def log(r):
    p = r["p"]
    row = {"time": datetime.now().strftime("%d.%m %H:%M"), "name": p["name"],
           "place": p["place"], "days": r["day"], "weight": p["w"],
           "sleep": p["sleep"], "move": int(p["move"]), "total": r["all"]}
    row.update(r["ill"])
    save(row)


def say(box, who, t):
    name, emo, files = WHO[who]
    with box.container():
        a, b = st.columns([1, 5])
        f = next((x for x in files if os.path.exists(x)), None)
        if f:
            a.image(f, width=110)
        else:
            a.markdown("<div style='font-size:60px'>" + emo + "</div>",
                       unsafe_allow_html=True)
        b.markdown("<div class='bub'><div class='who'>&#9654; " + name + "</div>"
                   + t + "</div>", unsafe_allow_html=True)


def intro(lines):
    box = st.empty()
    for m in lines:
        for i in range(0, len(m) + 1, 4):
            say(box, "crew", m[:i])
            time.sleep(.02)
        say(box, "crew", m)
        time.sleep(1.2)


st.title("Space Health Monitor")

if "intro" not in st.session_state:
    intro(["Hello, welcome to Space Health Monitor.",
           "Sick or hurt in space is very dangerous - no hospitals up here.",
           "So by tracking your health I keep the crew healthy on long missions.",
           "Fill the form and the ROVER will analyse your scan."])
    st.session_state["intro"] = True

if "checks" not in st.session_state:
    st.session_state["checks"] = []

st.subheader("____ HEALTH STATUS ____")

say(st.empty(), "crew", "Crew, give me your numbers before we launch.")

with st.form("first"):
    a, b, c = st.columns(3)
    name = a.text_input("Name", key="name")
    age = b.number_input("Age", 1, 120, 30, key="age")
    h = c.number_input("Height cm", 100, 250, 170, key="h")
    w = a.number_input("Weight kg", 30.0, 200.0, 70.0, 0.5, key="w")
    place = b.selectbox("Destination", list(PLACE), key="place")
    days = c.number_input("Days in space", 1, 1000, 30, key="days")
    move = a.radio("Exercise", ["No", "Yes"], index=1, horizontal=True, key="move") == "Yes"
    sleep = b.slider("Sleep hours", 3.0, 12.0, 7.0, 0.5, key="sleep")
    habits = c.multiselect("Habits", HABITS, default=["exercise", "sleep 8 h"], key="habits")
    th = st.slider("Alert threshold %", 5, 40, 10, key="th")
    go1 = st.form_submit_button("Run check", type="primary")

if age < 18 or age > 100:
    st.error("You can't fly at this age")
if h < 157 or h > 190:
    st.warning("Height outside the NASA range (157-190 cm)")

if go1:
    p = {"name": name, "age": age, "h": h, "w": w, "place": place, "days": int(days),
         "move": move, "sleep": float(sleep), "habits": habits, "th": th,
         "mood": mood(move, sleep, habits)}
    r = score(p)
    st.session_state["base"] = p
    st.session_state["r1"] = r
    st.session_state["last"] = r
    st.session_state["checks"] = [{"tag": "Check 1", "ill": r["ill"]}]
    log(r)

if st.session_state.get("r1"):
    show(st.session_state["r1"], "Check 1 - start")

if st.session_state.get("base"):
    st.divider()
    st.subheader("Second check")
    say(st.empty(), "crew", "Second check. Tell me what changed since day 0.")
    base = st.session_state["base"]
    with st.form("second"):
        a, b, c = st.columns(3)
        gap = a.number_input("Days since last check", 1, 500, 30, key="fu_gap")
        sleep2 = b.slider("Sleep now", 3.0, 12.0, float(base["sleep"]), 0.5, key="fu_sleep")
        w2 = c.number_input("Weight now", 30.0, 200.0, float(base["w"]), 0.5, key="fu_w")
        move2 = a.radio("Exercise now", ["No", "Yes"], index=1 if base["move"] else 0,
                        horizontal=True, key="fu_move") == "Yes"
        habits2 = b.multiselect("Habits now", HABITS, default=base["habits"], key="fu_habits")
        th2 = c.slider("Threshold %", 5, 40, int(base["th"]), key="fu_th")
        go2 = st.form_submit_button("Run second check", type="primary")

    if go2:
        p2 = dict(base)
        p2.update({"days": base["days"] + int(gap), "sleep": float(sleep2), "w": float(w2),
                   "move": move2, "habits": habits2, "th": th2,
                   "mood": mood(move2, sleep2, habits2)})
        r2 = score(p2)
        st.session_state["prev"] = st.session_state["checks"][-1]
        st.session_state["base"] = p2
        st.session_state["last"] = r2
        st.session_state["checks"].append(
            {"tag": "Check " + str(len(st.session_state["checks"]) + 1), "ill": r2["ill"]})
        log(r2)

if len(st.session_state["checks"]) > 1:
    r2, old = st.session_state["last"], st.session_state["prev"]
    show(r2, "Check " + str(len(st.session_state["checks"])) + " - after the change")

    st.subheader("What changed")
    same = [s for s in SYS if abs(r2["ill"][s] - old["ill"][s]) <= .05]
    say(st.empty(), "rover", "Compared with the last scan: " + str(len(SYS) - len(same))
        + " of 7 systems changed, overall now " + str(r2["all"]) + "%.")
    diff = []
    for s in SYS:
        d = round(r2["ill"][s] - old["ill"][s], 1)
        diff.append({"System": LAB[s], "Before": old["ill"][s], "Now": r2["ill"][s],
                     "Change": d,
                     "Trend": "worse" if d > .05 else "better" if d < -.05 else "same"})
    tbl(diff)

if st.session_state["checks"]:
    st.divider()
    st.subheader("Growth of the risk")
    ch = st.session_state["checks"]
    p3 = dict(st.session_state["base"])
    p3["days"] = st.session_state["last"]["day"] + 30
    nxt = score(p3)

    tab = [{"Check": c["tag"], **{LAB[s]: c["ill"][s] for s in SYS}} for c in ch]
    tab.append({"Check": "Predict +30 d", **{LAB[s]: nxt["ill"][s] for s in SYS}})

    bars(tab)
    st.caption("Illness % per system, bars scaled to the tallest value. "
               "Last column is +30 days with the same routine.")

rows = sum(1 for _ in open(LOG, encoding="utf-8-sig")) - 1 if os.path.exists(LOG) else 0
st.caption("Saved in " + LOG + " - " + str(rows) + " row(s).")

