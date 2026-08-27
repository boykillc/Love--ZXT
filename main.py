import argparse
import ast
import json
import os
import random
import sys
from datetime import date, datetime
from pathlib import Path

import requests
from jinja2 import Environment, FileSystemLoader, select_autoescape
from zhdate import ZhDate


REPO_PAGE_URL = "https://boykillc.github.io/Love--ZXT/"
DATA_CACHE_FILE = Path(".daily_data.json")
SITE_DIR = Path("_site")
TEMPLATE_DIR = Path("templates")

FALLBACK_LOVE_LINES = [
    "今天也要记得，我一直都超级喜欢你。",
    "希望今天的天气和你的心情一样明亮。",
    "每天都有一点点想你，今天也不例外。",
    "愿你今天顺顺利利，也一直被温柔包围。",
    "天气会变化，但喜欢你的心情不会。",
]


def load_config():
    """优先从 GitHub Secret APP_CONFIG_JSON 读取，未配置时兼容旧 config.txt。"""
    raw_json = os.getenv("APP_CONFIG_JSON", "").strip()
    if raw_json:
        try:
            return json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise RuntimeError("APP_CONFIG_JSON 不是合法 JSON，请检查 GitHub Secret。") from exc

    config_file = Path("config.txt")
    if config_file.exists():
        try:
            return ast.literal_eval(config_file.read_text(encoding="utf-8-sig"))
        except (SyntaxError, ValueError) as exc:
            raise RuntimeError("config.txt 格式不正确。") from exc

    raise RuntimeError(
        "没有找到配置。请在 GitHub Actions Secrets 中添加 APP_CONFIG_JSON，"
        "或在本地保留 config.txt。"
    )


config = load_config()


def request_json(method, url, *, timeout=20, **kwargs):
    response = requests.request(method, url, timeout=timeout, **kwargs)
    response.raise_for_status()
    return response.json()


def get_access_token():
    app_id = config["app_id"]
    app_secret = config["app_secret"]
    url = (
        "https://api.weixin.qq.com/cgi-bin/token"
        f"?grant_type=client_credential&appid={app_id}&secret={app_secret}"
    )
    data = request_json("GET", url)
    token = data.get("access_token")
    if not token:
        raise RuntimeError(f"获取微信 access_token 失败：{data}")
    return token


def get_weather(region):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/120 Safari/537.36"
        )
    }
    key = config["weather_key"]

    region_url = (
        "https://geoapi.qweather.com/v2/city/lookup"
        f"?location={region}&key={key}"
    )
    response = request_json("GET", region_url, headers=headers)
    if response.get("code") != "200" or not response.get("location"):
        raise RuntimeError(f"获取地区信息失败：{response}")

    location_id = response["location"][0]["id"]

    now_url = (
        "https://devapi.qweather.com/v7/weather/now"
        f"?location={location_id}&key={key}"
    )
    now_data = request_json("GET", now_url, headers=headers)
    if now_data.get("code") != "200":
        raise RuntimeError(f"获取实时天气失败：{now_data}")

    now = now_data["now"]
    weather = now.get("text", "未知")
    temp = f'{now.get("temp", "--")}°C'
    wind_dir = now.get("windDir", "--")

    daily_url = (
        "https://devapi.qweather.com/v7/weather/3d"
        f"?location={location_id}&key={key}"
    )
    daily_data = request_json("GET", daily_url, headers=headers)
    if daily_data.get("code") != "200" or not daily_data.get("daily"):
        raise RuntimeError(f"获取天气预报失败：{daily_data}")

    today_weather = daily_data["daily"][0]
    max_temp = f'{today_weather.get("tempMax", "--")}°C'
    min_temp = f'{today_weather.get("tempMin", "--")}°C'
    sunrise = today_weather.get("sunrise", "--:--")
    sunset = today_weather.get("sunset", "--:--")

    category = "暂无"
    pm2p5 = "暂无"
    try:
        air_url = (
            "https://devapi.qweather.com/v7/air/now"
            f"?location={location_id}&key={key}"
        )
        air_data = request_json("GET", air_url, headers=headers)
        if air_data.get("code") == "200":
            category = air_data.get("now", {}).get("category", "暂无")
            pm2p5 = air_data.get("now", {}).get("pm2p5", "暂无")
    except Exception as exc:
        print("空气质量获取失败，使用兜底值：", repr(exc))

    proposal = "今天也要照顾好自己，出门前记得看看天气呀。"
    try:
        index_type = random.randint(1, 16)
        proposal_url = (
            "https://devapi.qweather.com/v7/indices/1d"
            f"?location={location_id}&key={key}&type={index_type}"
        )
        proposal_data = request_json("GET", proposal_url, headers=headers)
        if proposal_data.get("code") == "200" and proposal_data.get("daily"):
            proposal = proposal_data["daily"][0].get("text", proposal) or proposal
    except Exception as exc:
        print("生活指数获取失败，使用兜底建议：", repr(exc))

    return {
        "region": region,
        "weather": weather,
        "temp": temp,
        "max_temp": max_temp,
        "min_temp": min_temp,
        "wind_dir": wind_dir,
        "sunrise": sunrise,
        "sunset": sunset,
        "category": category,
        "pm2p5": pm2p5,
        "proposal": proposal,
    }


def get_tianhang():
    fallback = random.choice(FALLBACK_LOVE_LINES)
    key = str(config.get("tian_api", "")).strip()
    if not key:
        return fallback

    try:
        url = f"https://apis.tianapi.com/caihongpi/index?key={key}"
        response = request_json(
            "GET",
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        if response.get("code") == 200:
            content = str(response.get("result", {}).get("content", "")).strip()
            if content:
                return content
        print("彩虹屁 API 返回异常，使用兜底文案：", response)
    except Exception as exc:
        print("彩虹屁 API 请求失败，使用兜底文案：", repr(exc))

    return fallback


def get_ciba():
    custom_ch = str(config.get("note_ch", "")).strip()
    custom_en = str(config.get("note_en", "")).strip()
    if custom_ch or custom_en:
        return custom_ch, custom_en

    try:
        data = request_json(
            "GET",
            "https://open.iciba.com/dsapi/",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        return data.get("note", ""), data.get("content", "")
    except Exception as exc:
        print("每日金句获取失败：", repr(exc))
        return "愿今天的你，也被这个世界温柔以待。", "Have a lovely day."


def get_birthday(birthday, year, today):
    birthday_year = birthday.split("-")[0]

    if birthday_year.startswith("r"):
        lunar_month = int(birthday.split("-")[1])
        lunar_day = int(birthday.split("-")[2])
        year_date = ZhDate(year, lunar_month, lunar_day).to_datetime().date()
    else:
        birthday_month = int(birthday.split("-")[1])
        birthday_day = int(birthday.split("-")[2])
        year_date = date(year, birthday_month, birthday_day)

    if today > year_date:
        if birthday_year.startswith("r"):
            next_lunar = ZhDate(year + 1, lunar_month, lunar_day).to_datetime().date()
            birth_date = next_lunar
        else:
            birth_date = date(year + 1, birthday_month, birthday_day)
        return (birth_date - today).days

    if today == year_date:
        return 0

    return (year_date - today).days


def weather_icon(weather_text):
    text = weather_text or ""
    if "雷" in text:
        return "⛈️"
    if "雪" in text:
        return "❄️"
    if "雨" in text:
        return "🌧️"
    if "雾" in text or "霾" in text:
        return "🌫️"
    if "阴" in text:
        return "☁️"
    if "云" in text:
        return "⛅"
    if "晴" in text:
        return "☀️"
    return "🌤️"


def collect_daily_data():
    today = date.today()
    week_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    week = week_names[today.weekday()]

    weather = get_weather(config["region"])
    note_ch, note_en = get_ciba()
    chp = get_tianhang()

    love_date_value = str(config.get("love_date", "")).strip()
    love_days = ""
    if love_date_value:
        love_date = datetime.strptime(love_date_value, "%Y-%m-%d").date()
        love_days = str((today - love_date).days)

    birthdays = []
    for key, value in config.items():
        if not key.startswith("birth") or not isinstance(value, dict):
            continue
        days = get_birthday(value["birthday"], today.year, today)
        birthdays.append(
            {
                "key": key,
                "name": value.get("name", "生日"),
                "days": days,
                "display": "今天生日啦" if days == 0 else f"还有 {days} 天",
                "short": "今天生日" if days == 0 else f"还有{days}天",
            }
        )

    data = {
        "date": today.isoformat(),
        "date_cn": today.strftime("%Y年%m月%d日"),
        "week": week,
        "page_title": config.get("page_title", "小小洁的今日天气"),
        "page_subtitle": config.get("page_subtitle", "今天也要开开心心呀 ♡"),
        "love_days": love_days,
        "note_ch": note_ch,
        "note_en": note_en,
        "chp": chp,
        "birthdays": birthdays,
        **weather,
    }
    data["weather_icon"] = weather_icon(data["weather"])
    return data


def render_page(data):
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("index.html")
    output = template.render(**data)
    (SITE_DIR / "index.html").write_text(output, encoding="utf-8")

    (SITE_DIR / "weather.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"网页已生成：{SITE_DIR / 'index.html'}")


def save_daily_data(data):
    DATA_CACHE_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_daily_data():
    if DATA_CACHE_FILE.exists():
        return json.loads(DATA_CACHE_FILE.read_text(encoding="utf-8"))
    return collect_daily_data()


def legacy_template_data(data):
    birthday_map = {item["key"]: item for item in data.get("birthdays", [])}
    payload = {
        "date": {"value": f'{data["date"]} {data["week"]}'},
        "region": {"value": data["region"]},
        "weather": {"value": data["weather"]},
        "temp": {"value": data["temp"]},
        "wind_dir": {"value": data["wind_dir"]},
        "love_day": {"value": data.get("love_days", "")},
        "note_en": {"value": "点击网页查看每日一句"},
        "note_ch": {"value": "点击网页查看每日一句"},
        "max_temp": {"value": data["max_temp"]},
        "min_temp": {"value": data["min_temp"]},
        "sunrise": {"value": data["sunrise"]},
        "sunset": {"value": data["sunset"]},
        "category": {"value": data["category"]},
        "pm2p5": {"value": str(data["pm2p5"])},
        "proposal": {"value": "点击查看完整建议"},
        "chp": {"value": "点击查看今日彩虹屁"},
    }
    for key, item in birthday_map.items():
        payload[key] = {"value": item["short"]}
    return payload


def minimal_template_data(data):
    return {
        "date": {"value": f'{data["date"]} {data["week"]}'},
        "message": {"value": "今日天气和小惊喜已准备好，点击查看"},
    }


def send_message(to_user, access_token, data, page_url):
    url = (
        "https://api.weixin.qq.com/cgi-bin/message/template/send"
        f"?access_token={access_token}"
    )

    mode = str(config.get("wechat_template_mode", "legacy")).lower()
    if mode == "minimal":
        message_data = minimal_template_data(data)
    else:
        message_data = legacy_template_data(data)

    payload = {
        "touser": to_user,
        "template_id": config["template_id"],
        "url": page_url,
        "data": message_data,
    }

    response = request_json(
        "POST",
        url,
        headers={"Content-Type": "application/json"},
        json=payload,
    )

    if response.get("errcode") != 0:
        raise RuntimeError(f"微信推送失败：{response}")

    print(f"微信推送成功：{to_user[:6]}***")


def notify_wechat(data, page_url):
    users = config.get("user", [])
    if isinstance(users, str):
        users = [users]
    if not users:
        raise RuntimeError("config 中没有配置 user。")

    access_token = get_access_token()
    for user in users:
        send_message(user, access_token, data, page_url)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-only", action="store_true")
    parser.add_argument("--notify-only", action="store_true")
    args = parser.parse_args()

    if args.build_only and args.notify_only:
        raise RuntimeError("--build-only 与 --notify-only 不能同时使用。")

    if args.notify_only:
        data = load_daily_data()
        page_url = os.getenv("PAGE_URL", "").strip() or config.get("page_url", REPO_PAGE_URL)
        notify_wechat(data, page_url)
        return

    data = collect_daily_data()
    render_page(data)
    save_daily_data(data)

    if args.build_only:
        return

    page_url = os.getenv("PAGE_URL", "").strip() or config.get("page_url", REPO_PAGE_URL)
    notify_wechat(data, page_url)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("运行失败：", repr(exc))
        sys.exit(1)
