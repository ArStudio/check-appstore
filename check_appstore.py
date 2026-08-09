import csv
import sys
import time
from pathlib import Path

import requests
import tkinter as tk
from tkinter import filedialog


# ---------------------------------------------------------
# НАСТРОЙКИ
# ---------------------------------------------------------

DEFAULT_COUNTRY = "tr"


# ---------------------------------------------------------
# ВЫБОР СТРАНЫ
# ---------------------------------------------------------

def get_country():
    print("=" * 70)
    print("ПРОВЕРКА ДОСТУПНОСТИ ПРИЛОЖЕНИЙ В APP STORE")
    print("=" * 70)
    print()

    while True:
        country = input(
            "Введите код страны App Store (например: ru, tr, us): "
        ).strip().lower()

        if not country:
            country = DEFAULT_COUNTRY

        # Код страны App Store обычно состоит из 2 букв
        if len(country) == 2 and country.isalpha():
            return country

        print("❌ Некорректный код страны. Используйте две буквы, например: ru")
        print()


# ---------------------------------------------------------
# ВЫБОР CSV-ФАЙЛА
# ---------------------------------------------------------

def select_csv_file():
    root = tk.Tk()
    root.withdraw()

    root.attributes("-topmost", True)

    filename = filedialog.askopenfilename(
        title="Выберите CSV-файл из iMazing",
        filetypes=[
            ("CSV files", "*.csv"),
            ("All files", "*.*"),
        ],
    )

    root.destroy()

    if not filename:
        print()
        print("❌ Файл не выбран.")
        sys.exit(1)

    return filename


# ---------------------------------------------------------
# ЧТЕНИЕ CSV ИЗ iMAZING
# ---------------------------------------------------------

def read_imazing_csv(filename):
    apps = {}

    try:
        with open(
            filename,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as f:

            reader = csv.DictReader(f)

            for row in reader:

                store_id = row.get("Store ID", "").strip()
                name = row.get("Name", "").strip()

                if not store_id or not store_id.isdigit():
                    continue

                # Один Store ID может встречаться несколько раз
                # из-за разных версий приложения.
                if store_id not in apps:
                    apps[store_id] = {
                        "store_id": store_id,
                        "name": name,
                        "bundle_id": row.get(
                            "Bundle ID", ""
                        ).strip(),
                        "developer": row.get(
                            "Developer", ""
                        ).strip(),
                        "original_url": row.get(
                            "App Store URL", ""
                        ).strip(),
                    }

    except FileNotFoundError:
        print()
        print(f"❌ Файл не найден: {filename}")
        sys.exit(1)

    except Exception as e:
        print()
        print(f"❌ Ошибка чтения CSV: {e}")
        sys.exit(1)

    return apps


# ---------------------------------------------------------
# ПРОВЕРКА ОДНОГО ПРИЛОЖЕНИЯ
# ---------------------------------------------------------

def check_app(session, app, country):

    store_id = app["store_id"]

    url = (
        "https://itunes.apple.com/lookup"
        f"?id={store_id}"
        f"&country={country}"
    )

    try:
        response = session.get(
            url,
            timeout=15
        )

        if response.status_code != 200:
            return {
                **app,
                "status": "ERROR",
                "error": f"HTTP {response.status_code}",
            }

        data = response.json()

        # Приложение найдено в нужном storefront
        if data.get("resultCount", 0) > 0:

            result = data["results"][0]

            return {
                **app,
                "status": "AVAILABLE",
                "country_name": result.get(
                    "trackName", ""
                ),
                "country_url": result.get(
                    "trackViewUrl", ""
                ),
                "error": "",
            }

        # Приложение не найдено
        return {
            **app,
            "status": "MISSING",
            "country_name": "",
            "country_url": "",
            "error": "",
        }

    except requests.exceptions.Timeout:

        return {
            **app,
            "status": "ERROR",
            "error": "Timeout",
        }

    except requests.exceptions.RequestException as e:

        return {
            **app,
            "status": "ERROR",
            "error": str(e),
        }

    except Exception as e:

        return {
            **app,
            "status": "ERROR",
            "error": str(e),
        }


# ---------------------------------------------------------
# ОСНОВНАЯ ФУНКЦИЯ
# ---------------------------------------------------------

def main():

    country = get_country()

    print()
    print("Выберите CSV-файл выгрузки из iMazing...")
    print()

    input_file = select_csv_file()

    print()
    print(f"Страна проверки: {country.upper()}")
    print(f"Файл: {input_file}")
    print()

    apps = read_imazing_csv(input_file)

    print(f"Найдено уникальных приложений: {len(apps)}")
    print(f"Проверяем App Store: {country.upper()}")
    print()

    if not apps:
        print("❌ В CSV не найдено приложений с корректным Store ID.")
        return

    results = []

    session = requests.Session()

    session.headers.update({
        "User-Agent": "Mozilla/5.0"
    })

    # -----------------------------------------------------
    # ПОСЛЕДОВАТЕЛЬНАЯ ПРОВЕРКА
    # -----------------------------------------------------

    total = len(apps)

    for index, app in enumerate(
        apps.values(),
        start=1
    ):

        print(
            f"\rПроверено: {index}/{total}",
            end="",
            flush=True
        )

        result = check_app(
            session,
            app,
            country
        )

        results.append(result)

        # Небольшая пауза между запросами
        time.sleep(0.1)

    print()
    print()

    # -----------------------------------------------------
    # СТАТИСТИКА
    # -----------------------------------------------------

    available = [
        x for x in results
        if x["status"] == "AVAILABLE"
    ]

    missing = [
        x for x in results
        if x["status"] == "MISSING"
    ]

    errors = [
        x for x in results
        if x["status"] == "ERROR"
    ]

    # -----------------------------------------------------
    # РЕЗУЛЬТАТ
    # -----------------------------------------------------

    print("=" * 70)
    print("РЕЗУЛЬТАТ")
    print("=" * 70)

    print(
        f"Всего проверено:       {len(results)}"
    )

    print(
        f"Есть в {country.upper()}:          "
        f"{len(available)}"
    )

    print(
        f"Нет в {country.upper()}:           "
        f"{len(missing)}"
    )

    print(
        f"Ошибок проверки:       "
        f"{len(errors)}"
    )

    # -----------------------------------------------------
    # ОТСУТСТВУЮЩИЕ ПРИЛОЖЕНИЯ
    # -----------------------------------------------------

    if missing:

        print()
        print(
            f"НЕТ В {country.upper()}:"
        )
        print()

        for app in sorted(
            missing,
            key=lambda x: x["name"].lower()
        ):

            print(
                f'{app["name"]} '
                f'(Store ID: {app["store_id"]})'
            )

    # -----------------------------------------------------
    # ОШИБКИ
    # -----------------------------------------------------

    if errors:

        print()
        print("НЕ УДАЛОСЬ ПРОВЕРИТЬ:")
        print()

        for app in errors:

            print(
                f'{app["name"]} '
                f'(Store ID: {app["store_id"]}) — '
                f'{app["error"]}'
            )


# ---------------------------------------------------------
# ЗАПУСК
# ---------------------------------------------------------

if __name__ == "__main__":
    main()