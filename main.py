import csv
import json
import logging
import sys
import time
from dataclasses import dataclass, fields, astuple, asdict
import datetime
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from database import insert_dataframe, DUMPS_DIR

BASE_URL = "https://auto.ria.com/uk/"
HOME_URL = urljoin(BASE_URL, "search/?indexName=auto")

_driver: WebDriver | None = None


def get_driver() -> WebDriver:
    return _driver


def set_driver(new_driver: WebDriver) -> None:
    global _driver
    _driver = new_driver


@dataclass
class Product:
    url: str
    title: str
    price_usd: int
    odometer: int
    username: str
    phone_number: int
    image_url: str
    images_count: int
    car_number: str
    car_vin: str
    datetime_found: datetime


CAR_FIELDS = [field.name for field in fields(Product)]


logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)8s]:  %(message)s",
    handlers=[
        logging.FileHandler("parser.log"),
        logging.StreamHandler(sys.stdout),
    ],
)


def parse_hidden_phone_number_person(car_soup: Tag) -> str:
    absolute_url = urljoin(BASE_URL, car_soup["href"])
    driver = get_driver()
    driver.get(absolute_url)
    wait = WebDriverWait(driver, 10)
    result = ""
    try:
        cookie_btn = driver.find_element(By.CSS_SELECTOR, "button.js-cookie-agree")
        cookie_btn.click()

    except Exception:
        pass

    try:
        button = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "#sellerInfo .button-main.mt-12 button")
            )
        )
        button.click()
        phone = wait.until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    ".py-24.px-24.popup-body .common-text.ws-pre-wrap.action",
                )
            )
        )
        driver.save_screenshot("screen1.png")
        result += "38" + "".join(
            phone.text.replace("(", "").replace(")", "").split(" ")
        )
    except Exception as ex:
        print(ex)
        result = None
        pass
    finally:
        return result


def parse_single_car(product: Tag) -> Optional[Product]:
    open_detail = requests.get(urljoin(BASE_URL, product["href"])).content
    detail_soup = BeautifulSoup(open_detail, "html.parser")
    if product.select_one(".common-text.ellipsis-1.body").text.strip() == "Без пробігу":
        return None
    else:
        nickname = detail_soup.select_one(
            "#sellerInfoUserName .common-text.ws-pre-wrap.titleM"
        )
        car_num = detail_soup.select_one(".car-number.ua .common-text.ws-pre-wrap.body")
        image_count_person = detail_soup.select_one(".common-badge.alpha.medium")
        car_vin = detail_soup.select_one(
            "#badgesVinGrid .common-text.ws-pre-wrap.badge"
        )
        phone_number = parse_hidden_phone_number_person(product)

        print(
            dict(
                url=urljoin(BASE_URL, product["href"]),
                title=product.select_one(
                    ".common-text.size-16-20.titleS.fw-bold.mb-4"
                ).text.strip(),
                price_usd="".join(
                    [
                        i if i.isdigit() else ""
                        for i in product.select_one(".common-text.titleM.c-green").text
                    ]
                ),
                odometer=int(
                    "".join(
                        product.select_one(".common-text.ellipsis-1.body")
                        .text.strip()
                        .replace("тис. км", "000")
                        .split()
                    )
                ),
                username=nickname.text.strip() if nickname else "sold",
                phone_number=phone_number,
                image_url=str(product.select_one(".picture img")["src"]),
                images_count=(
                    int(image_count_person.text.split()[-1])
                    if image_count_person
                    else None
                ),
                car_number=car_num.text.strip() if car_num else None,
                car_vin=car_vin.text if car_vin else None,
                datetime_found="".join(
                    str(datetime.datetime.now().strftime("%Y-%m-%d"))
                ),
            )
        )

        return Product(
            url=urljoin(BASE_URL, product["href"]),
            title=product.select_one(
                ".common-text.size-16-20.titleS.fw-bold.mb-4"
            ).text.strip(),
            price_usd=int(
                "".join(
                    [
                        i if i.isdigit() else ""
                        for i in product.select_one(".common-text.titleM.c-green").text
                    ]
                )
            ),
            odometer=int(
                "".join(
                    product.select_one(".common-text.ellipsis-1.body")
                    .text.strip()
                    .replace("тис. км", "000")
                    .split()
                )
            ),
            username=nickname.text.strip() if nickname else "sold",
            phone_number=int(phone_number) if phone_number else None,
            image_url=str(product.select_one(".picture img")["src"]),
            images_count=(
                int(image_count_person.text.split()[-1])
                if image_count_person else None
            ),
            car_number=car_num.text.strip() if car_num else None,
            car_vin=car_vin.text if car_vin else None,
            datetime_found=str(datetime.datetime.now().strftime("%Y-%m-%d")),
        )


def parse_car_pages():
    logging.info("Start parsing autoria")
    text = requests.get(urljoin(HOME_URL, "&page=0")).content
    soup = BeautifulSoup(text, "html.parser")
    all_cars = get_page_cars(soup)
    # num_pages = int("".join(soup.select(".item .link.page-link")[-1].text.split()))
    # IF ALL PAGES ADD TO RANGE AS A SECOND ARGUMENT INSTEAD "1 + 1"
    for num in range(1, 1 + 1):
        logging.info(f"Start parsing page: # {num}")
        new_text = requests.get(
            f"https://auto.ria.com/uk/search/?indexName=auto&page={num}"
        ).content
        start_time = time.time()
        new_soup = BeautifulSoup(new_text, "html.parser")
        all_cars.extend(get_page_cars(new_soup))
        end_time = time.time()
        print("EXECUTION TIME: ", end_time - start_time)
        print("PAGE NUMBER::::::::;;", num)
    return all_cars


def get_page_cars(page_soup):
    cars = page_soup.select(".link.product-card.horizontal")
    car = [
        parsed
        for parsed in (parse_single_car(car) for car in cars)
        if parsed is not None
    ]
    return car


def write_cars_to_files(cars: list):
    DUMPS_DIR.mkdir(parents=True, exist_ok=True)

    today_str = datetime.date.today().isoformat()

    csv_path = DUMPS_DIR / f"{today_str}.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CAR_FIELDS)
        writer.writerows([astuple(car) for car in cars])

    json_path = DUMPS_DIR / f"{today_str}.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump([asdict(car) for car in cars], f, ensure_ascii=False, indent=4)

    print(f"Files written to {DUMPS_DIR.resolve()}")


def main():
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    with webdriver.Remote(
        command_executor="http://selenium:4444/wd/hub",
        options=options
    ) as driver:
        set_driver(driver)
        cars = parse_car_pages()
        write_cars_to_files(cars)
        insert_dataframe(cars)
