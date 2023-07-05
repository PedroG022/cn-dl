from numbers import Number
from utils import read


class Series:
    def __init__(self, title: str, volumes: list, author="Unknown") -> None:
        self.title = title
        self.volumes = volumes
        self.author = author


class Volume:
    def __init__(self, number: Number, title: str, series: str, chapters: list, cover_file="none") -> None:
        self.number = number
        self.title = title
        self.series = series
        self.chapters = chapters
        self.complete_title = f"{series} - {title}"
        self.cover_file = cover_file

    def __str__(self) -> str:
        return self.complete_title


class Chapter:
    def __init__(self, number: Number, title: str, url: str) -> None:

        if float(number) < 10:
            self.number = f"0{number}"
        else:
            self.number = number

        self.title: str = title
        self.url: str = url
        self.complete_title = f"Ch. {number} - {title}"
        self.content: str

    def setContent(self, content):
        header = read("chapter-title.html")
        header = header.replace("chapter_name", self.title)
        header = header.replace("chapter_number", self.number)
        self.content = f"{header}\n{content}"

    def __str__(self) -> str:
        return f"{self.number} - {self.title}"
