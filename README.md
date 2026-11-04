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

- AppWorld: `0.2.0.dev0`, установлен из клона, коммит `<git rev-parse HEAD в папке appworld>`
- Python: `<python --version>`
- openai: `<pip show openai>`

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

## Запуск одной задачи

```bash
python agent_2.py <task_id>
```

Пример: `python agent_2.py 0d8a4ee_1`. Результат сохраняется в `runs/single/<task_id>.json`.

## Пакетный запуск

Задачи берутся из `dev_tasks.json` (10 задач из dev, список зафиксирован до настройки). Каждая задача запускается в свежем мире.

```bash
python baseline.py
```

Результаты сохраняются в `runs/baseline/<task_id>.json`. Уже существующие файлы пропускаются; чтобы перезапустить задачу, удалите её файл.

## Оценка

После остановки агента (успешное завершение или лимит) вызывается `world.evaluate()`. Агент не видит ни `ground_truth`, ни код проверок, ни их результаты во время решения. В файл результата записываются:

- `task_id`, `stop` (причина остановки: `completed`, `max_llm_calls`, `max_api_calls`);
- `log` (инструкция, вызовы с аргументами и результатами, токены);
- `success` (`true`, если все проверки evaluator пройдены);
- `failures` (список непройденных проверок с текстом требования и трассой).

Быстрая сводка по пакету:

```bash
python - <<'EOF'
import json, glob
rows = [json.load(open(p)) for p in sorted(glob.glob("runs/baseline/*.json"))]
for r in rows:
    print(r["task_id"], r["stop"], r["success"])
print("успешно:", sum(r["success"] for r in rows), "из", len(rows))
EOF
```

Процент успеха на десяти задачах показывает, что работает и что ломается, и не является оценкой качества агента.
