set shell := ["bash", "-euo", "pipefail", "-c"]

_default:
    @just --list

# Установить зависимости из package-lock.json.
sync:
    npm ci

# Запустить клиент для разработки.
run:
    npm run dev

# Проверить форматирование, типы и сборку.
check:
    npm run format:check
    npm run build

# Собрать статический клиент.
build:
    npm run build

# Локально открыть собранный клиент.
preview:
    npm run preview
