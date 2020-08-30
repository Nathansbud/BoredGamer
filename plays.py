import site
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from collections import Counter
from math import log

def std(date_string): return datetime.strptime(date_string, "%Y-%m-%d")
def play_plot(days=365):
    plays = site.get_plays(days)
    by_game = {}
    for p in plays:
        if p['name'] in by_game: by_game[p['name']].extend([std(p['date'])]*p['plays'])
        else: by_game[p['name']] = [std(p['date'])]

    fig, ax = plt.subplots()
    plt.title(f"Game Plays, Past {'Year' if -5 <= days - 365 <= 5 else f'{days} Day'+('s' if days != 1 else '')} [Size ∝ Plays]")
    plt.winter()
    plt.xticks(rotation=45)
    plt.yticks(weight='bold')
    plt.xlabel("Date")
    colors = ['red', 'orange', '#FADA5e', 'green', 'blue', 'indigo', 'violet']
    for i, [game, dates] in enumerate(by_game.items()):
        date_count = Counter(dates)
        for date, count in sorted(list(date_count.items()), key=lambda c: c[1])[::-1]:
            ax.plot_date(date, game, ms=5+count, alpha=1 if count == 1 else max(1/(0.8*count), 0.5), color=colors[i % len(colors)])

    for i, ytick in enumerate(ax.get_yticklabels()):
        ytick.set_color(colors[i % len(colors)])

    ax.set_xlim(right=datetime.today())

    gcf = plt.gcf()
    gcf.autofmt_xdate()
    plt.show()

if __name__ == '__main__':
    play_plot()