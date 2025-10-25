#!/usr/bin/env python3
from instagrapi import Client
from pathlib import Path
import os, csv, time

# ===== CONFIG =====
USERNAME = os.getenv("IG_USER", "") #ENTER USERNAME HERE
PASSWORD = os.getenv("IG_PASS", "") #ENTER PASSWORD HERE
SESSIONID = os.getenv("IG_SESSIONID", "").strip()  # optional: browser cookie
STATE_DIR = Path.home() / "ig-followcheck-state"
SETTINGS_PATH = STATE_DIR / "settings.json"
OUTDIR = STATE_DIR / "ig_logs"
# ==================

STATE_DIR.mkdir(parents=True, exist_ok=True)
OUTDIR.mkdir(parents=True, exist_ok=True)
cl = Client()
cl.delay_range = [1, 3]
cl.use_public_requests = False  # avoid GQL + update_headers path

def save():
    cl.dump_settings(SETTINGS_PATH)
    print(f"SAVED: {SETTINGS_PATH}")

def fresh_login():
    print("Fresh login…")
    cl.set_settings({})
    if SESSIONID:
        cl.login_by_sessionid(SESSIONID)
    else:
        cl.login(USERNAME, PASSWORD)
    save()

# try reuse
if SETTINGS_PATH.exists():
    print("Reusing settings...")
    try:
        cl.load_settings(SETTINGS_PATH)
        if SESSIONID:
            cl.login_by_sessionid(SESSIONID)
        else:
            cl.login(USERNAME, PASSWORD)
    except Exception as e:
        print("Old settings invalid:", e)
        SETTINGS_PATH.unlink(missing_ok=True)
        fresh_login()
else:
    print("Settings file not found, creating new one...")
    fresh_login()

save()

# ===== FETCH FOLLOWERS/FOLLOWING =====
# Use the logged-in account id to avoid username->GQL path
try:
    me = cl.account_info().pk
except Exception:
    fresh_login()
    me = cl.account_info().pk

print("Fetching followers…")
followers = cl.user_followers(me)   # dict[pk] -> User
print("Fetching following…")
following = cl.user_following(me)   # dict[pk] -> User

followers_set = set(followers.keys())
following_set = set(following.keys())

not_following_back = following_set - followers_set        # you follow them; they don't follow you
you_dont_follow_back = followers_set - following_set      # they follow you; you don't follow back

ts = time.strftime("%Y%m%d-%H%M%S")

def write_csv(path, data_dict):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pk", "username", "full_name"])
        for pk, user in data_dict.items():
            w.writerow([pk, user.username, user.full_name])

write_csv(OUTDIR / f"followers-{ts}.csv", followers)
write_csv(OUTDIR / f"following-{ts}.csv", following)
write_csv(OUTDIR / f"nonfollowers-{ts}.csv", {pk: following[pk] for pk in not_following_back if pk in following})
write_csv(OUTDIR / f"not-followed-back-by-you-{ts}.csv", {pk: followers[pk] for pk in you_dont_follow_back if pk in followers})

# ===== PRINT LISTS =====
def fmt(u):
    return f"@{u.username}" + (f" ({u.full_name})" if u.full_name else "")

nf_back_list = sorted([fmt(following[pk]) for pk in not_following_back if pk in following], key=str.lower)
ydfb_back_list = sorted([fmt(followers[pk]) for pk in you_dont_follow_back if pk in followers], key=str.lower)

print(f"\nPeople you follow who don't follow you back ({len(nf_back_list)}):")
for s in nf_back_list:
    print("  -", s)

print(f"\nPeople who follow you but you don't follow back ({len(ydfb_back_list)}):")
for s in ydfb_back_list:
    print("  -", s)

print(f"\nResults saved under: {OUTDIR}")
