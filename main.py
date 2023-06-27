import sqlite3

import japanize_matplotlib
import matplotlib.pyplot as plt
import openai
import pandas as pd
import seaborn as sns
import streamlit as st
from faker import Faker
from faker.providers import BaseProvider

table_definition = """
CREATE TABLE users (
  id INTEGER,
  age INTEGER NOT NULL,
  name TEXT NOT NULL,
  sex VARCHAR(10) NOT NULL,
  job VARCHAR(50) NOT NULL,
  team VARCHAR(50) NOT NULL,
  country VARCHAR(50) NOT NULL,
  grade VARCHAR(50) NOT NULL,
  PRIMARY KEY (id)
);
"""

fake = Faker("ja_JP")


class MyProvider(BaseProvider):
    def job(self, team):
        print(team)
        if team == "開発部":
            return self.random_element(
                [
                    "エンジニア",
                    "デザイナー",
                    "PdM",
                ]
            )
        elif team == "営業部":
            return self.random_element(
                [
                    "営業",
                ]
            )
        elif team == "人事部":
            return self.random_element(
                [
                    "人事",
                ]
            )

        return "その他"

    def sex(self):
        return self.random_element(
            [
                "男性",
                "女性",
            ]
        )

    def age(self):
        return self.random_int(min=20, max=65)

    def country(self):
        return self.random_element(
            [
                "日本",
                "アメリカ",
                "カナダ",
                "イギリス",
            ]
        )

    def team(self):
        return self.random_element(
            [
                "開発部",
                "営業部",
                "人事部",
            ]
        )

    def grade(self):
        return self.random_element(
            [
                "G1",
                "G2",
                "G3",
                "G4",
                "G5",
                "G6",
                "G7",
            ]
        )


fake.add_provider(MyProvider)


def create_table(conn):
    c = conn.cursor()
    create_query = table_definition
    c.execute(create_query)


def insert_data(conn):
    c = conn.cursor()
    for i in range(100):
        age = fake.age()
        name = fake.name()
        sex = fake.sex()
        team = fake.team()
        job = fake.job(team)
        country = fake.country()
        grade = fake.grade()

        # Insert query
        insert_query = f"""
        INSERT INTO users (age, name, sex, job, team, country, grade)
        VALUES ({age}, '{name}', '{sex}', '{job}', '{team}', '{country}', '{grade}')
        """
        print(insert_query)
        c.execute(insert_query)

    conn.commit()


def init_dataframe(conn, query, multi_index=False):

    c = conn.cursor()
    c.execute(query)

    results = c.fetchall()

    columns = []
    for v in c.description:
        columns.append(v[0])

    df = pd.DataFrame(data=results, columns=columns)

    return df


@st.cache_resource
def load_data():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    create_table(conn)
    insert_data(conn)
    df = init_dataframe(conn, "SELECT * FROM users")
    print(df)
    return conn, df


conn, df = load_data()

if "conn" not in st.session_state:
    st.session_state["conn"] = conn

st.write("Default data")
st.dataframe(df)


def on_change():
    instruction = st.session_state.instruction
    if instruction == "":
        return

    sql = generate_sql(instruction)
    st.session_state.query = sql

    conn = st.session_state["conn"]

    df = init_dataframe(conn, sql)
    st.session_state["aggregated_df"] = df


st.text_area(key="instruction", label="instruction", on_change=on_change)
st.text_area(key="query", label="SQL (Debug)")

if "aggregated_df" in st.session_state:
    aggregated_df = st.session_state["aggregated_df"]
    st.dataframe(aggregated_df)
    # st.bar_chart(aggregated_df)

    index_names = aggregated_df.index.names
    columns = aggregated_df.columns
    x = columns[0]
    hue = None
    if len(columns) > 2:
        hue = columns[1]

    y = columns[1]
    if len(columns) > 2:
        y = columns[2]

    fig = plt.figure(figsize=(15, 10))

    sns.barplot(
        data=aggregated_df,
        x=x,
        y=y,
        hue=hue,
    )
    st.pyplot(fig)


def generate_sql(instruction):
    content = f"""
    There is a table defined by the following CREATE statement in sqlite3.

    {table_definition}

    Each column corresponds to the following.

    id: ID
    age: 年齢
    name: 氏名
    job: 職種
    team: 部署
    country: 出身国
    grade: 等級

    And there are the following definitions.

    リーダー: grade is 'G5' or 'G6' or 'G7'
    外国籍: country is not '日本'

    Write a SQL that achieve the following instruction.
    The instruction is written in Japanese.

    {instruction}

    Output only SQL in raw text.
    Remove any information except for SQL.
    If you cannot write SQL, write 'null'.
    """

    print(content)

    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": content}],
        temperature=0.0,
    )

    print(completion)

    sql = completion.choices[0].message.content

    return sql
