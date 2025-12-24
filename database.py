from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extensions import register_adapter, AsIs

from config import Config

BASE_DIR = Path(__file__).resolve().parent.parent
DUMPS_DIR = Path("dumps")
register_adapter(np.int64, AsIs)


def df(cars) -> pd.DataFrame:
    dataframe = pd.DataFrame([asdict(car) for car in cars])
    dataframe = dataframe.replace({np.nan: None})
    return dataframe


def get_connection():
    connection = psycopg2.connect(
        port=Config.DB_PORT,
        host=Config.DB_HOST,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        dbname=Config.DB_NAME,
    )
    print(
        f"Successful connection to host={Config.DB_HOST}"
    )
    return connection


def insert_dataframe(cars):
    data = df(cars)

    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS cars(
            url varchar(255) NOT NULL,
            title varchar(255) NOT NULL,
            price_usd int NOT NULL,
            odometer int NOT NULL,
            username varchar(255) NOT NULL,
            phone_number bigint,
            image_url text NOT NULL,
            images_count int,
            car_number varchar(255),
            car_vin varchar(255),
            datetime_found date NOT NULL
            )"""
        )
        conn.commit()

        for i in range(0, len(data)):
            values = (
                data["url"][i],
                data["title"][i],
                data["price_usd"][i],
                data["odometer"][i],
                data["username"][i],
                data["phone_number"][i],
                data["image_url"][i],
                data["images_count"][i],
                data["car_number"][i],
                data["car_vin"][i],
                data["datetime_found"][i],
            )
            cursor.execute(
                "INSERT INTO cars ("
                "url, title, price_usd, odometer, username, phone_number, image_url,"
                "images_count, car_number, car_vin, datetime_found) VALUES "
                "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                values,
            )

        conn.commit()
        print(f"Records created successfully")
