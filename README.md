Агент решает задачи бенчмарка AppWorld: читает инструкцию, сам выбирает приложения и функции, вызывает их через function calling и завершает задачу. LLM: бесплатный Gemini API через OpenAI-совместимый endpoint.

AppWorld 0.2.0.dev0, установлен из клона `https://github.com/StonyBrookNLP/appworld`

## Установка

1. Установить AppWorld из клона и скачать данные (см. официальную инструкцию AppWorld).

2. Клонировать этот репозиторий и установить зависимости агента в то же окружение:

   ```bash
   git clone https://github.com/GDK1995/appworld-agent.git
   cd ~/appworld-agent
   pip install -r requirements.txt
   ```

3. Указать путь к папке AppWorld, где лежит `data/`:

   ```bash
   export APPWORLD_ROOT=~/appworld
   `

## Версии

- AppWorld: `0.2.0.dev0`
- Python: `Python 3.11.17`
- openai: `openai 3.37.0`

## Конфиг модели

Настройки лежат в `config.yaml`:

```yaml
model: <gemini-3.5-flash-lite>
base_url: https://generativelanguage.googleapis.com/v1beta/openai/
temperature: 0
max_llm_calls: 30
max_api_calls: 100
sleep_between_calls: 4
```

## Запуск одной задачи baseline

```bash
python agent_2.py <task_id>
```

Пример: `python agent_2.py 0d8a4ee_1`. Результат сохраняется в `runs/single/<task_id>.json`.

## Запуск одной задачи agent

```bash
python agent_3.py <task_id>
```

Пример: `python agent_3.py 0d8a4ee_1`. Результат сохраняется в `runs/single_B/<task_id>.json`.

## Пакетный запуск baseline

Задачи берутся из зафиксированного списка до настройки. Каждая задача запускается в свежем мире.

```bash
python baseline.py
```

Результаты сохраняются в `runs/baseline/<task_id>.json`.

## Пакетный запуск agent

Задачи берутся из зафиксированного списка до настройки. Каждая задача запускается в свежем мире.

```bash
python dev_B.py
```

Результаты сохраняются в `runs/dev_experiment/<task_id>.json`.

## Оценка

После остановки агента (успешное завершение или лимит) вызывается `world.evaluate()`. Агент не видит ни `ground_truth`, ни код проверок, ни их результаты во время решения. В файл результата записываются:

- `task_id`, `stop` (причина остановки: `completed`, `max_llm_calls`, `max_api_calls`);
- `log` (инструкция, вызовы с аргументами и результатами, токены);
- `success` (`true`, если все проверки evaluator пройдены);
- `failures` (список непройденных проверок с текстом требования и трассой).

Быстрая сводка по baseline:

```bash
python - <<'EOF'
import json, glob
rows = [json.load(open(p)) for p in sorted(glob.glob("runs/baseline/*.json"))]
for r in rows:
    print(r["task_id"], r["stop"], r["success"])
print("успешно:", sum(r["success"] for r in rows), "из", len(rows))
EOF
```

Быстрая сводка по agent:

```bash
python - <<'EOF'
import json, glob
rows = [json.load(open(p)) for p in sorted(glob.glob("runs/dev_experiment/*.json"))]
for r in rows:
    print(r["task_id"], r["stop"], r["success"])
print("успешно:", sum(r["success"] for r in rows), "из", len(rows))
EOF
```

### 1. `530b157_1`: Kristin paid for my grocery recently as my payment cards were not working at the time. Send them the owed money with a description note \"Groceries\" as per my phone text conversation, and then send them a phone text message, \"It is done.\".

- **Задача:** отправить Кристин в Venmo сумму за продукты с заметкой «Groceries» (сумма указана в переписке в телефоне) и написать ей «It is done.».
- **Результат:** `stop = completed`, `success = false`; evaluator: `amount: 25.0 == 54` и `answers match` (ожидалось `null`).
- **Первый ошибочный шаг:** шаг 13. Вызов `phone__search_text_messages` с `phone_number` Кристин и без `page_limit` (по умолчанию 5) вернул ровно 5 сообщений, то есть полную страницу. Следующую страницу (`page_index=1`) агент не запросил. Суммы 54 в просмотренных сообщениях нет.
- **Последствия:** на шаге 15 агент взял $25 из сообщения «I owe you $25 from the last time» (это старый долг) и создал транзакцию. Платёж с неверной суммой уже выполнен в мире и не откатывается. После него отправлено «It is done.». На шаге 17 в `complete_task` передан `answer` с пересказом действий, хотя задача не вопрос.
- **Гипотеза исправления:** если после ответа с ровно `page_limit` записей добавлять в результат пометку «страница полная, могут быть ещё записи: запроси следующий `page_index`», агент прочитает переписку целиком и найдёт сумму. Предполагается, что сообщение с 54 лежит на следующих страницах; в логе его нет.


### 2. `6c2c621_3`: Export all my Simple Note notes to \"~/backups/simple_notes/\" directory in my file system. The files should be named according to the note title, replacing white space with \"_\", and the extension should be \".md\".

- **Задача:** экспортировать все заметки Simple Note в `~/backups/simple_notes/` как `.md`, имя файла по заголовку с заменой пробелов на `_`.
- **Результат:** `stop = completed`, `success = false`; evaluator: пути и содержимое файлов (3 проверки) и `answers match`.
- **Первый ошибочный шаг:** шаг 25. Создан файл с путём `...([x]_=_done,_[_]=_not_done)).md` вместо `...[_]_=_not_done...` (потерян `_`); в `Food_Recipes.md` последовательности `\xB0`, `\xE9` заменены на `\u00b0`, `\u00e9`.
- **Последствия:** 36 из 38 файлов верны, но строгая проверка путей и содержимого не пройдена. На шаге 26 в `complete_task` передан `answer` (документация не читалась).
- **Гипотеза исправления:** (1) добавить правило в промпте «копируй значения из ответов функций символ в символ, включая пробелы и escape-последовательности, ничего не нормализуй»; (2) запрет вызова функции без прочитанной документации.

### 3. `0d8a4ee_3`: Send the following phone message to my roommates and friends, who do not have a venmo account, \"Make an account on venmo please.\".

- **Задача:** отправить сообщение «Make an account on venmo please.» соседям и друзьям, у которых нет аккаунта в Venmo.
- **Результат:** `stop = completed`, `success = false`; evaluator: получатели сообщений `[62]`, ожидались `[62, 68, 78]`.
- **Первый ошибочный шаг:** шаг 14. В контактах (шаг 12) 3 соседа и 6 друзей, но в Venmo агент проверил только соседей (три `venmo__search_users`: Jose Harrison, Lindsey Simpson, Paul Miller). Друзья (Cheryl, Cody, Cory, Grant, Travis, William) не проверены.
- **Последствия:** на шаге 16 сообщение отправлено только Lindsey Simpson. На шаге 17 агент написал «successfully sent» и перечислил только соседей, затем завершил задачу (шаг 20) без проверки второй части условия.
- **Гипотеза исправления:** перед завершением перечитать инструкцию и сверить каждую её часть с выполненными действиями.

