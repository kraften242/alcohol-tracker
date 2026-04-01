#!/usr/bin/env python3
"""Alcohol Tracker - terminal app for tracking alcohol consumption."""

import curses
import json
import os
from datetime import datetime, date, timedelta

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "drinks.json")

# ── colours ───────────────────────────────────────────────────────────────────
C_GREEN  = 1
C_CYAN   = 2
C_YELLOW = 3
C_RED    = 4
C_SEL    = 5

# ── data helpers ──────────────────────────────────────────────────────────────

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return {"drinks": []}


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def add_drinks(data, name, volume_cl, cost_sek, count=1, drink_date=None):
    entry_date = drink_date or date.today().isoformat()
    for _ in range(count):
        data["drinks"].append({
            "date": entry_date,
            "name": name,
            "volume_cl": float(volume_cl),
            "cost_sek": float(cost_sek),
            "added_at": datetime.now().isoformat(),
        })
    save_data(data)


def remove_entry(data, index_from_end):
    """Remove one drink by its position in the last-10 list (0 = most recent)."""
    pos = len(data["drinks"]) - 1 - index_from_end
    if pos < 0:
        return None
    removed = data["drinks"].pop(pos)
    save_data(data)
    return removed


def today_stats(data):
    today = date.today().isoformat()
    entries = [d for d in data["drinks"] if d["date"] == today]
    vol  = sum(d["volume_cl"] for d in entries)
    cost = sum(d["cost_sek"]  for d in entries)
    return vol, cost


def monthly_cost(data):
    prefix = date.today().strftime("%Y-%m")
    return sum(d["cost_sek"] for d in data["drinks"] if d["date"].startswith(prefix))


def latest_drink(data):
    return data["drinks"][-1] if data["drinks"] else None


def stats_for(data, mode):
    today   = date.today()
    drinks  = data["drinks"]

    if mode == "today":
        filtered = [d for d in drinks if d["date"] == today.isoformat()]
        label    = f"Today  ({today})"

    elif mode == "week":
        # Rolling last 7 days
        cutoff   = (today - timedelta(days=6)).isoformat()
        filtered = [d for d in drinks if d["date"] >= cutoff]
        label    = f"Last 7 days  ({cutoff}  –  {today})"

    else:  # month
        prefix   = today.strftime("%Y-%m")
        filtered = [d for d in drinks if d["date"].startswith(prefix)]
        label    = f"This month  ({today.strftime('%B %Y')})"

    total_vol  = sum(d["volume_cl"] for d in filtered)
    total_cost = sum(d["cost_sek"]  for d in filtered)
    return label, filtered, total_vol, total_cost


# ── curses UI ─────────────────────────────────────────────────────────────────

class App:
    MENU = [
        ("1", "Add drink (today)"),
        ("2", "Add drink (another day)"),
        ("3", "Remove a drink"),
        ("4", "Daily stats"),
        ("5", "Weekly stats"),
        ("6", "Monthly stats"),
        ("q", "Quit"),
    ]

    def __init__(self, stdscr):
        self.scr  = stdscr
        self.data = load_data()
        self._init_colors()
        curses.curs_set(0)
        self.scr.keypad(True)

    def _init_colors(self):
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(C_GREEN,  curses.COLOR_GREEN,  -1)
        curses.init_pair(C_CYAN,   curses.COLOR_CYAN,   -1)
        curses.init_pair(C_YELLOW, curses.COLOR_YELLOW, -1)
        curses.init_pair(C_RED,    curses.COLOR_RED,    -1)
        curses.init_pair(C_SEL,    curses.COLOR_BLACK,  curses.COLOR_WHITE)

    # ── helpers ───────────────────────────────────────────────────────────

    def _prompt(self, win, y, x, label, max_len=40):
        curses.curs_set(1)
        curses.echo()
        win.addstr(y, x, label, curses.color_pair(C_CYAN))
        win.refresh()
        raw = win.getstr(y, x + len(label), max_len)
        curses.noecho()
        curses.curs_set(0)
        return raw.decode("utf-8", errors="replace").strip()

    def _msgbox(self, lines, color=C_GREEN):
        h, w = self.scr.getmaxyx()
        bh   = len(lines) + 4
        bw   = max(len(l) for l in lines) + 6
        win  = curses.newwin(bh, bw, max(0, (h - bh) // 2), max(0, (w - bw) // 2))
        win.box()
        for i, line in enumerate(lines):
            win.addstr(i + 2, 3, line, curses.color_pair(color))
        win.addstr(bh - 1, bw - 11, " any key ", curses.color_pair(C_YELLOW))
        win.refresh()
        win.getch()

    # ── screens ───────────────────────────────────────────────────────────

    def add_drink_screen(self, ask_date=False):
        self.scr.clear()
        title = "Add Drink — another day" if ask_date else "Add Drink — today"
        self.scr.addstr(1, 2, title, curses.color_pair(C_GREEN) | curses.A_BOLD)
        self.scr.addstr(3, 2, "Leave name blank to cancel.", curses.color_pair(C_YELLOW))
        self.scr.refresh()

        drink_date = date.today().isoformat()
        row = 5

        if ask_date:
            date_str = self._prompt(self.scr, row, 2,
                                    f"Date (YYYY-MM-DD) [default {drink_date}]: ", 12)
            if date_str:
                try:
                    datetime.strptime(date_str, "%Y-%m-%d")
                    drink_date = date_str
                except ValueError:
                    self._msgbox(["Invalid date — use YYYY-MM-DD."], C_RED)
                    return
            row += 2

        name = self._prompt(self.scr, row, 2, "Drink name: ")
        if not name:
            return
        row += 1

        vol_str  = self._prompt(self.scr, row, 2, "Volume (cl): ")
        row += 1
        cost_str = self._prompt(self.scr, row, 2, "Cost (SEK):  ")
        row += 1
        count_str = self._prompt(self.scr, row, 2, "How many?   [1]: ", 3)

        try:
            vol   = float(vol_str)
            cost  = float(cost_str)
            count = int(count_str) if count_str else 1
            if count < 1:
                raise ValueError
        except ValueError:
            self._msgbox(["Invalid number entered."], C_RED)
            return

        add_drinks(self.data, name, vol, cost, count, drink_date)
        self._msgbox([
            f"Added {count}x {name}",
            f"  {vol:.1f} cl each   {cost:.2f} SEK each",
            f"  Date: {drink_date}",
        ])

    def remove_drink_screen(self):
        drinks = self.data["drinks"]
        if not drinks:
            self._msgbox(["No drinks to remove."], C_RED)
            return

        last10 = drinks[-10:][::-1]   # most recent first, up to 10

        self.scr.clear()
        h, w = self.scr.getmaxyx()
        self.scr.addstr(1, 2, "Remove a Drink", curses.color_pair(C_GREEN) | curses.A_BOLD)
        self.scr.addstr(3, 2, "#   Date        Drink                  cl    SEK",
                        curses.color_pair(C_YELLOW) | curses.A_BOLD)

        for i, d in enumerate(last10):
            self.scr.addstr(4 + i, 2,
                f"{i+1:<3} {d['date']}  {d['name'][:20]:<20}  "
                f"{d['volume_cl']:<5.1f} {d['cost_sek']:.2f}")

        row = 5 + len(last10)
        try:
            choice_str = self._prompt(self.scr, row, 2,
                                      "Enter number to remove (blank = cancel): ", 3)
            if not choice_str:
                return
            idx = int(choice_str) - 1
            if idx < 0 or idx >= len(last10):
                raise ValueError
        except ValueError:
            self._msgbox(["Invalid choice."], C_RED)
            return

        removed = remove_entry(self.data, idx)
        if removed:
            self._msgbox([
                "Removed:",
                f"  {removed['name']}  {removed['volume_cl']:.1f} cl  {removed['cost_sek']:.2f} SEK",
                f"  Date: {removed['date']}",
            ], C_YELLOW)

    def stats_screen(self, mode):
        label, drinks, total_vol, total_cost = stats_for(self.data, mode)
        self.scr.clear()
        h, w = self.scr.getmaxyx()

        self.scr.addstr(1, 2, label,  curses.color_pair(C_CYAN)  | curses.A_BOLD)
        self.scr.addstr(2, 2,
            f"  {total_vol:.1f} cl total    {total_cost:.2f} SEK total",
            curses.color_pair(C_GREEN) | curses.A_BOLD)
        self.scr.addstr(3, 2, "─" * min(w - 4, 60), curses.color_pair(C_YELLOW))

        cx = {"date": 2, "name": 14, "vol": 36, "cost": 46}
        self.scr.addstr(4, cx["date"], "Date",  curses.color_pair(C_YELLOW) | curses.A_BOLD)
        self.scr.addstr(4, cx["name"], "Drink", curses.color_pair(C_YELLOW) | curses.A_BOLD)
        self.scr.addstr(4, cx["vol"],  "cl",    curses.color_pair(C_YELLOW) | curses.A_BOLD)
        self.scr.addstr(4, cx["cost"], "SEK",   curses.color_pair(C_YELLOW) | curses.A_BOLD)

        max_rows = h - 8
        visible  = drinks[-max_rows:] if len(drinks) > max_rows else drinks
        for i, d in enumerate(visible):
            r = 5 + i
            self.scr.addstr(r, cx["date"], d["date"])
            self.scr.addstr(r, cx["name"], d["name"][:20])
            self.scr.addstr(r, cx["vol"],  f"{d['volume_cl']:.1f}")
            self.scr.addstr(r, cx["cost"], f"{d['cost_sek']:.2f}")

        self.scr.addstr(h - 1, 2, " Press any key to return ", curses.color_pair(C_YELLOW))
        self.scr.refresh()
        self.scr.getch()

    # ── main loop ─────────────────────────────────────────────────────────

    def run(self):
        key_map  = {item[0]: i for i, item in enumerate(self.MENU)}
        selected = 0

        while True:
            self.scr.clear()
            h, w = self.scr.getmaxyx()

            # Header
            title    = "Alcohol Tracker"
            subtitle = date.today().strftime("%A, %d %B %Y")
            self.scr.addstr(1, (w - len(title))   // 2, title,    curses.color_pair(C_GREEN)  | curses.A_BOLD)
            self.scr.addstr(2, (w - len(subtitle)) // 2, subtitle, curses.color_pair(C_CYAN))
            self.scr.addstr(3, 2, "─" * (w - 4), curses.color_pair(C_YELLOW))

            # Inline stats (from original)
            t_vol, t_cost = today_stats(self.data)
            m_cost        = monthly_cost(self.data)
            last          = latest_drink(self.data)
            self.scr.addstr(4, 4, f"Today:  {t_vol:.1f} cl   {t_cost:.2f} SEK",
                            curses.color_pair(C_CYAN))
            self.scr.addstr(5, 4, f"Month:  {m_cost:.2f} SEK",
                            curses.color_pair(C_CYAN))
            if last:
                self.scr.addstr(6, 4,
                    f"Last:   {last['name']} ({last['volume_cl']:.1f} cl, {last['cost_sek']:.2f} SEK)",
                    curses.color_pair(C_CYAN))
            self.scr.addstr(7, 2, "─" * (w - 4), curses.color_pair(C_YELLOW))

            # Menu
            for i, (key, label) in enumerate(self.MENU):
                row  = 9 + i
                text = f"  [{key}]  {label}"
                attr = curses.color_pair(C_SEL) if i == selected else 0
                self.scr.addstr(row, 2, text, attr)

            self.scr.addstr(h - 1, 2,
                "↑↓ navigate   ENTER / number: select   Q: quit",
                curses.color_pair(C_YELLOW))
            self.scr.refresh()

            k      = self.scr.getch()
            action = None

            if k == curses.KEY_UP:
                selected = (selected - 1) % len(self.MENU)
                continue
            elif k == curses.KEY_DOWN:
                selected = (selected + 1) % len(self.MENU)
                continue
            elif k in (curses.KEY_ENTER, 10, 13):
                action = self.MENU[selected][0]
            elif 0 < k < 256:
                ch = chr(k).lower()
                if ch in key_map:
                    selected = key_map[ch]
                    action   = ch

            if   action == "1": self.add_drink_screen(ask_date=False)
            elif action == "2": self.add_drink_screen(ask_date=True)
            elif action == "3": self.remove_drink_screen()
            elif action == "4": self.stats_screen("today")
            elif action == "5": self.stats_screen("week")
            elif action == "6": self.stats_screen("month")
            elif action == "q": break


def main():
    curses.wrapper(lambda scr: App(scr).run())


if __name__ == "__main__":
    main()
