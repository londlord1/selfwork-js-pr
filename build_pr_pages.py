#!/usr/bin/env python3
"""Собирает сайт «одна страница на одну ПР» из страниц отдельных задач.

На каждой странице ПР все задания показаны сразу, друг под другом.
Каждое задание встроено через iframe srcdoc, поэтому стили, id и
глобальные переменные заданий не конфликтуют, а работают они вместе
на одной странице.
"""
import argparse
import glob
import html as html_mod
import json
import os
import re

PR_TITLES = {
    3: 'Массивы и операции с ними',
    4: 'Функции',
    5: 'DOM и события',
    6: 'To-Do и localStorage',
    7: 'Валидация форм',
    8: 'Navigator и производительность',
    9: 'События и взаимодействие',
    10: 'Списки и DOM',
    11: 'Окно, сеть и история',
    12: 'Строки и регулярные выражения',
    13: 'Методы массивов',
    14: 'Объекты и деструктуризация',
    15: 'Set, Map и Array',
    16: 'JSON и структуры данных',
    17: 'Инкапсуляция',
    18: 'Расширение браузера',
    19: 'Чат-бот',
    20: 'Форма кредитной карты',
    21: 'API Госуслуг',
    22: 'Основы классов',
    23: 'Наследование и полиморфизм',
    24: 'DOM: рендеринг и события',
    25: 'LocalStorage',
    26: 'React: счётчик',
    27: 'React: списки',
    28: 'React: props и темы',
    29: 'React: таймеры',
    30: 'React: API',
    31: 'React: калькулятор',
    32: 'React: фильтрация',
}

RESIZE_SCRIPT = """<script>
(function () {
  var index = __INDEX__;
  function send() {
    parent.postMessage({ type: 'ph-height', index: index, height: document.documentElement.scrollHeight }, '*');
  }
  window.addEventListener('load', send);
  if (window.ResizeObserver) new ResizeObserver(send).observe(document.documentElement);
  setInterval(send, 1500);
})();
</script>
"""

CSS = """*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',Arial,sans-serif;background:#f0f2f5;color:#222;padding:24px;line-height:1.55}
.wrap{max-width:1000px;margin:0 auto}
.topnav{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:14px;flex-wrap:wrap}
.topnav a{color:#1a73e8;text-decoration:none;font-size:14px}
.topnav a:hover{text-decoration:underline}
.navbtns{display:flex;gap:8px;flex-wrap:wrap}
.navbtns .btn{background:#fff;border:1px solid #cbd5e1;border-radius:8px;padding:8px 14px;font-size:13px;cursor:pointer;color:#0b57d0}
.navbtns .btn:hover{background:#eef6ff}
.navbtns .btn:disabled{opacity:.4;cursor:default}
h1{color:#1a73e8;margin-bottom:4px;font-size:24px}
.pr-tag{display:inline-block;background:#1a73e8;color:#fff;border-radius:12px;padding:2px 12px;font-size:13px;margin-bottom:10px}
.desc{background:#eef6ff;border:1px solid #c9e3ff;border-radius:10px;padding:12px 16px;margin:14px 0;color:#1a56a0;font-size:14px}
.card{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:20px 22px;margin:16px 0;box-shadow:0 2px 6px rgba(0,0,0,0.05)}
.card h2{font-size:17px;color:#333;margin-bottom:10px}
.toc{position:sticky;top:0;z-index:5;background:#f0f2f5;padding:8px 0;display:flex;gap:6px;flex-wrap:wrap;align-items:center;border-bottom:1px solid #e2e8f0;margin-bottom:6px}
.toc b{font-size:13px;color:#475569;margin-right:4px}
.toc a{display:inline-flex;min-width:30px;justify-content:center;background:#fff;border:1px solid #cbd5e1;border-radius:6px;padding:3px 9px;text-decoration:none;font-size:13px;color:#0b57d0}
.toc a:hover{background:#eef6ff;border-color:#93c5fd}
.task{margin:20px 0}
.task-head{display:flex;gap:9px;align-items:center;font-weight:600;color:#334155;margin-bottom:8px;font-size:15px}
.task-num{display:inline-flex;width:26px;height:26px;align-items:center;justify-content:center;background:#1a73e8;color:#fff;border-radius:50%;font-size:13px;flex:none}
.task-frame{width:100%;height:620px;border:1px solid #e2e8f0;border-radius:12px;background:#fff;display:block;transition:height .15s ease}
footer{margin-top:24px;font-size:12px;color:#999;text-align:center}
a{color:#0b57d0}
"""


def clean_task(source, index):
    source = re.sub(r'<div class="topnav">.*?</div>\s*</div>', '', source, flags=re.S)
    source = re.sub(r'<div class="navbtns[^"]*"[^>]*>.*?</div>', '', source, flags=re.S)
    source = re.sub(r'<footer>.*?</footer>', '', source, flags=re.S)
    source = source.replace('</body>', RESIZE_SCRIPT.replace('__INDEX__', str(index)) + '</body>')
    return source


def task_title(source, fallback):
    match = re.search(r'<h1>(.*?)</h1>', source, re.S)
    if not match:
        return fallback
    text = re.sub(r'<[^>]+>', '', match.group(1))
    text = html_mod.unescape(text).strip()
    return re.sub(r'^ПР\d+\s*•\s*Зад\.?\s*\d+\s*•\s*', '', text).strip() or fallback


def build(src_dir, out_dir):
    grouped = {}
    for path in glob.glob(os.path.join(src_dir, 'пр*.html')):
        name = os.path.basename(path)
        match = re.match(r'пр(\d{2})_зад(\d+)_', name)
        if not match:
            continue
        pr, num = int(match.group(1)), int(match.group(2))
        grouped.setdefault(pr, []).append((num, path))

    os.makedirs(out_dir, exist_ok=True)
    prs = sorted(grouped)
    index_cards = []

    apps_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'apps')

    for pr in prs:
        app_path = os.path.join(apps_dir, 'pr%02d.html' % pr)
        if os.path.exists(app_path):
            open(os.path.join(out_dir, 'pr%02d.html' % pr), 'w', encoding='utf-8').write(
                open(app_path, encoding='utf-8').read()
            )
            count = len(sorted(grouped[pr]))
            index_cards.append((pr, 'ПР%02d — %s' % (pr, PR_TITLES.get(pr, '')), count))
            continue

        tasks = []
        for index, (num, path) in enumerate(sorted(grouped[pr])):
            raw = open(path, encoding='utf-8').read()
            tasks.append({
                'title': task_title(raw, 'Задание %d' % num),
                'html': clean_task(raw, index),
            })

        title = 'ПР%02d — %s' % (pr, PR_TITLES.get(pr, ''))
        payload = json.dumps(tasks, ensure_ascii=False).replace('</', '<\\/')

        prev_link = 'pr%02d.html' % (pr - 1) if (pr - 1) in grouped else 'index.html'
        next_link = 'pr%02d.html' % (pr + 1) if (pr + 1) in grouped else 'index.html'

        page = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITLE__</title>
<style>__CSS__</style>
</head>
<body>
<div class="wrap">
<div class="topnav">
  <a href="index.html">« Все практические</a>
  <div class="navbtns">
    <button class="btn" onclick="location.href='__PREV__'">← Пред. ПР</button>
    <button class="btn" onclick="location.href='__NEXT__'">След. ПР →</button>
  </div>
</div>
<span class="pr-tag">ПР__PR__</span>
<h1>__TITLE__</h1>
<div class="desc">Все самостоятельные задания этой практической на одной странице — выполняются вместе. Задания идут по порядку, ниже.</div>
<nav class="toc" id="toc"><b>Задания:</b></nav>
<div id="tasks"></div>
<footer>ПР__PR__ · заданий: __COUNT__ · <a href="index.html">все практические</a></footer>
</div>
<script>
const TASKS = __DATA__;
const container = document.getElementById('tasks');
const toc = document.getElementById('toc');
const frames = [];

TASKS.forEach(function (task, i) {
  const section = document.createElement('section');
  section.className = 'task';
  section.id = 'task-' + (i + 1);

  const head = document.createElement('div');
  head.className = 'task-head';
  const num = document.createElement('span');
  num.className = 'task-num';
  num.textContent = i + 1;
  const title = document.createElement('span');
  title.textContent = task.title;
  head.appendChild(num);
  head.appendChild(title);

  const frame = document.createElement('iframe');
  frame.className = 'task-frame';
  frame.dataset.index = i;
  frame.title = 'Задание ' + (i + 1) + ': ' + task.title;
  frame.src = 'about:blank';

  section.appendChild(head);
  section.appendChild(frame);
  container.appendChild(section);
  frames.push(frame);

  const link = document.createElement('a');
  link.href = '#task-' + (i + 1);
  link.textContent = i + 1;
  link.title = task.title;
  toc.appendChild(link);
});

const observer = new IntersectionObserver(function (entries) {
  entries.forEach(function (entry) {
    if (!entry.isIntersecting) return;
    const frame = entry.target;
    if (frame.dataset.loaded) return;
    frame.dataset.loaded = '1';
    frame.srcdoc = TASKS[Number(frame.dataset.index)].html;
    observer.unobserve(frame);
  });
}, { rootMargin: '600px' });

frames.forEach(function (frame) { observer.observe(frame); });

window.addEventListener('message', function (event) {
  if (!event.data || event.data.type !== 'ph-height') return;
  const frame = frames[event.data.index];
  if (frame) frame.style.height = Math.max(420, event.data.height + 6) + 'px';
});
</script>
</body>
</html>
"""
        page = (page.replace('__TITLE__', html_mod.escape(title))
                    .replace('__CSS__', CSS)
                    .replace('__PREV__', prev_link)
                    .replace('__NEXT__', next_link)
                    .replace('__PR__', '%02d' % pr)
                    .replace('__COUNT__', str(len(tasks)))
                    .replace('__DATA__', payload))

        open(os.path.join(out_dir, 'pr%02d.html' % pr), 'w', encoding='utf-8').write(page)
        index_cards.append((pr, title, len(tasks)))

    cards = []
    for pr, title, count in index_cards:
        cards.append(
            '<a class="card link" href="pr%02d.html"><h2>%s</h2>'
            '<p>%d заданий на одной странице →</p></a>' % (pr, html_mod.escape(title), count)
        )

    index = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Самостоятельные работы — одна страница на ПР</title>
<style>__CSS__
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px;margin-top:14px}
.link{display:block;text-decoration:none;color:inherit;transition:border-color .15s,transform .15s}
.link:hover{border-color:#1a73e8;transform:translateY(-2px)}
.link h2{color:#1a73e8}
.link p{color:#64748b;font-size:14px}
</style>
</head>
<body>
<div class="wrap">
<h1>Самостоятельные работы по JavaScript</h1>
<p class="desc">Одна страница на одну практическую работу: ПР03–ПР32. На странице сразу все задания этой ПР.</p>
<div class="grid">
__CARDS__
</div>
<footer>Всего практических: __TOTAL__ · отдельные страницы по задачам — в репозитории <a href="https://github.com/londlord1/selfwork-js">selfwork-js</a></footer>
</div>
</body>
</html>
"""
    index = index.replace('__CSS__', CSS).replace('__CARDS__', '\n'.join(cards)).replace('__TOTAL__', str(len(index_cards)))
    open(os.path.join(out_dir, 'index.html'), 'w', encoding='utf-8').write(index)
    print('ПР:', len(index_cards), 'заданий:', sum(c[2] for c in index_cards))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--src', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'selfwork-js'))
    parser.add_argument('--out', default=os.path.dirname(os.path.abspath(__file__)))
    args = parser.parse_args()
    build(os.path.abspath(args.src), os.path.abspath(args.out))
