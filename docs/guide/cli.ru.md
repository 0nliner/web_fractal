# CLI

Команда `wf` ставится вместе с пакетом.

```bash
wf --help
```

## Скаффолдинг

```bash
wf init myproject                       # каркас нового проекта
wf init myproject -p http -p kafka      # сразу с несколькими транспортами

wf add-module orders                    # новый доменный модуль
wf add-module orders --with-controller http
wf add-module orders --app backend      # если пакет называется не "app"
```

`init` раскладывает проект, `add-module` добавляет ограниченный контекст внутрь
существующего. Оба принимают протоколы, которые вы действительно собираетесь
обслуживать, — сгенерированный контроллер сразу под транспорт, а не
HTTP-заглушка, которую придётся переписывать.

## Проверка разводки

```bash
wf validate                             # разводка DI + протокольные контроллеры
wf validate --bundle app.archtool_conf.bundle
```

`validate` собирает инжектор и показывает, что не разрешилось. Стоит держать в
CI: незарегистрированный модуль даёт приложение, которое прекрасно стартует и
падает на первом запросе, — ровно тот отказ, который тесты обычно и пропускают.

```bash
wf graph                                # дерево зависимостей
wf graph --format dot | dot -Tpng -o deps.png
wf graph --format web
```

## Диаграммы из существующего кода

```bash
wf diagram app                          # весь пакет
wf diagram app/orders/models.py -k er
wf diagram app -k class -f mermaid -o docs/classes.md
```

| Опция | Значения |
|---|---|
| `-k, --kind` | `er`, `class`, `both` (по умолчанию) |
| `-f, --format` | `mermaid` (по умолчанию), `cad`, `json` |
| `-o, --out` | писать в файл вместо stdout |

Разбор **статический** (AST): разбираемый пакет не импортируется, поэтому для
картинки не нужны ни его зависимости, ни конфиги, ни живая база.

## Извлечение модуля

```bash
wf extract orders                       # по умолчанию сухой прогон
wf extract orders -p grpc --no-dry-run
```

Подробнее — [Извлечение модуля](extraction.md).
