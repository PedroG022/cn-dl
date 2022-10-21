import subprocess
import os
from os import system
from os.path import isfile, join
import requests
from bs4 import BeautifulSoup
from PyPDF2 import PdfFileMerger, PdfFileReader
from natsort import natsorted
from sanitize_filename import sanitize

base_url = ""

class Chapter():
    def __init__(self, details: str, title: str, url: str) -> None:
        self.title: str = title
        self.url: str = url
        self.number: str = details[details.index("Cap.") + 4:].strip()
        self.volume_name: str = "Volume " + details[5: details.index(" Cap.")]

    def __str__(self) -> str:
        return f"{self.number} - {self.title}"

    def save(self):
        volume_folder = self.volume_name
        volume_html_folder = f"{self.volume_name}/html"
        volume_pdf_folder =  f"{self.volume_name}/pdf"

        folders = [volume_folder, volume_html_folder, volume_pdf_folder]

        for folder in folders:
            if not (os.path.exists(folder)):
                os.mkdir(folder)

        # Number standardization, also a bug
        # were chapters would order incorrectly
        if (float(self.number.strip()) < 10):
            self.number = f"0{self.number}"

        chapter_name = sanitize(f"Capítulo {self.number} - {self.title}")

        content_output = f"""<h3 style="text-align: center;"><strong><em>{chapter_name}</em></strong></h1>\n"""
        html_out_name = f"{volume_html_folder}/{chapter_name}.html"
        pdf_out_name = f"{volume_pdf_folder}/{chapter_name}.pdf"

        chapter_file = open(html_out_name, "w", encoding="utf-8")
        chapter_file.write(content_output)
        chapter_file.write(self.get_content())
        chapter_file.close()

        print(f"Starting html to pdf creation for chapter {self.number}...")

        convert_document(html_out_name, pdf_out_name)

        print("Document conversion done!")

    def get_content(self):
        request = requests.get(self.url)
        soup = BeautifulSoup(request.text, "html.parser")
        
        out = ""

        for paragraph in soup.select("div.epcontent.entry-content p"):
            out += f"{paragraph}\n"

        return out

class Volume():
    def __init__(self, series: str, chapters: list) -> None:
        self.series = series
        self.chapters = chapters
        pass

    def download(self):
        for chapter in self.chapters:
            pass

def merge(volume_name: str):
    pdf_merger = PdfFileMerger()

    pdf_path = volume_name + "/pdf/"
    chapter_files = list()

    print(f"Merging {volume_name}")

    for file in os.listdir(pdf_path):
        if isfile(join(pdf_path, file)):
            chapter_files.append(join(pdf_path, file))

    chapter_files = natsorted(chapter_files)

    for chapter in chapter_files:
        chapter_title = chapter[chapter.rfind("/") + 1: chapter.rfind(".")]
        inserted_at = len(pdf_merger.pages)
        pdf_merger.add_outline_item(pagenum=inserted_at, title=chapter_title)
        pdf_merger.append(PdfFileReader(open(chapter, "rb")))
        
    output_pdf = f"{volume_name}/{volume_name}.pdf"
    output_epub = f"{volume_name}/{volume_name}.epub"

    print("Creating PDF...")
    pdf_merger.write(output_pdf)
    pdf_merger.close()

    print("PDF output is done!")

    print("Converting to EPUB...")
    convert_document(output_pdf, output_epub,
        ["--no-default-epub-cover", "--toc-title", "Sumário", "--pretty-print", "--epub-inline-toc"])

    print("EPUB output is done!")

def convert_document(document: str, output: str, options: list() = []) -> str:
    return subprocess.run(['ebook-convert', document, output] + options,  stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT).stdout

def parse_page(series_slug: str):
    req = requests.get(base_url + series_slug)
    return BeautifulSoup(req.text, "html.parser")

def main():
    soup = parse_page("")
    
    series_title = soup.title.text
    series_title = series_title[0:series_title.index("|")]

    system("clear")

    print(f"Title: {series_title}")
    print("Available volumes:")

    vol_names = list()
    volume = Volume(series_title, list())

    for item in soup.select(".ts-chl-collapsible"):
        vol_names.append(item.text)

    vol_names.reverse()

    for vol in vol_names:
        print(f"{vol_names.index(vol)}: {vol}")

    selected_vol = int(input("Select the desired volume: "))

    volumes = soup.select("div.ts-chl-collapsible-content")
    volumes.reverse()
    
    for item in volumes[selected_vol].select("ul li"):
        base = item.select_one("a")

        link = base.attrs['href']
        number = base.select_one("div.epl-num").text
        title = base.select_one("div.epl-title").text

        chapter = Chapter(number, title, link)
        volume.chapters.append(chapter)

    print(f"{len(volume.chapters)} chapter(s) were found.")
    print("Starting downloads...")

    for chapter in volume.chapters:
        chapter.save()

    merge(volume.chapters[0].volume_name)

if __name__ == "__main__":
    main()