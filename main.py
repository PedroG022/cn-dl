import subprocess
import os
from os import system
from os.path import isfile, join
import requests
from bs4 import BeautifulSoup
from PyPDF2 import PdfFileMerger, PdfFileReader
from natsort import natsorted
from sanitize_filename import sanitize
from zipfile import ZipFile
import shutil

base_url = ""

class Chapter():
    def __init__(self, details: str, title: str, url: str) -> None:
        self.title: str = title
        self.url: str = url
        self.number: str = details[details.index("Cap.") + 4:].strip()
        self.volume_name: str = "Volume " + details[5: details.index(" Cap.")]

    def __str__(self) -> str:
        return f"{self.number} - {self.title}"

    def get_content(self) -> str:
        request = requests.get(self.url)
        soup = BeautifulSoup(request.text, "html.parser")
        
        out = ""

        for paragraph in soup.select("div.epcontent.entry-content p"):
            out += f"{paragraph}\n"

        return out

class Volume():
    def __init__(self, name: str, series: str, chapters: list) -> None:
        self.name = name
        self.series = series
        self.chapters = chapters
        self.complete_name = f"{series} - {name}"
        print(self.complete_name)

    def save_chapter(self, chapter: Chapter):
        volume_folder = self.complete_name
        volume_html_folder = f"{volume_folder}/html"
        volume_pdf_folder =  f"{volume_folder}/pdf"

        chapter_name = sanitize(f"Capítulo {chapter.number} - {chapter.title}")

        html_out_name = f"{volume_html_folder}/{chapter_name}.html"
        pdf_out_name = f"{volume_pdf_folder}/{chapter_name}.pdf"

        if os.path.exists(html_out_name):
            print("Chapter already downloaded, skipping!")
            return

        print(f"Downloading chapter {chapter.number}")

        folders = [volume_folder, volume_html_folder, volume_pdf_folder]

        for folder in folders:
            if not (os.path.exists(folder)):
                os.mkdir(folder)

        # Number standardization
        if (float(chapter.number.strip()) < 10):
            chapter.number = f"0{chapter.number}"

        content_output = ""

        with open("chapter-title.html", "r", encoding="utf-8") as file:
            content = file.read()
            content = content.replace("chapter_name", chapter.title)
            content = content.replace("chapter_number", chapter.number)
            content_output = join(content_output, content)

        chapter_file = open(html_out_name, "w", encoding="utf-8")
        chapter_file.write(content_output)
        chapter_file.write(chapter.get_content())
        chapter_file.close()

        print("Converting to pdf...")
        convert_document(html_out_name, pdf_out_name)

    def download(self):
        for chapter in self.chapters:
            self.save_chapter(chapter)
        
        merge(self)

def merge(volume: Volume):
    pdf_merger = PdfFileMerger()

    pdf_path = volume.complete_name + "/pdf/"
    chapter_files = list()

    output_epub = f"{volume.complete_name}/{volume.complete_name}.epub"
    output_epub_old = f"{volume.complete_name}/{volume.complete_name}.old.epub"
    output_pdf = f"{volume.complete_name}/{volume.complete_name}.pdf"
    output_epub_folder = f"{os.getcwd()}\{volume.complete_name}\epub-output\\"

    print(f"Compiling {volume.complete_name}...")

    for path in os.listdir(pdf_path):
        if isfile(join(pdf_path, path)):
            chapter_files.append(join(pdf_path, path))

    chapter_files = natsorted(chapter_files)

    print("Merging pdfs...")
    
    for chapter in chapter_files:
        chapter_title = chapter[chapter.rfind("/") + 1: chapter.rfind(".")]
        inserted_at = len(pdf_merger.pages)
        pdf_merger.add_outline_item(pagenum=inserted_at, title=chapter_title)
        pdf_merger.append(PdfFileReader(open(chapter, "rb")))

    pdf_merger.write(f"{volume.complete_name}/{volume.complete_name}.pdf")

    print("Converting to EPUB...")
    convert_document(output_pdf, output_epub,
        ["--no-default-epub-cover", "--toc-title", "Sumário", "--pretty-print", "--epub-inline-toc", "--change-justification", "justify", "--extract-to", output_epub_folder])

    print("Deleting old epub...")
    os.remove(output_epub)

    print("Merge complete! Now modifiying the volume...")

    htmls = list()
    anchors = list()

    contents_file = open(join(output_epub_folder, "contents.xhtml"), encoding="utf-8")
    contents_xhtml = contents_file.read()
    contents_file.close()

    chapter_header_template_file = open("chapter-title.html", "r", encoding="utf-8")
    chapter_header_template = chapter_header_template_file.read()
    chapter_header_template_file.close()

    soup = BeautifulSoup(contents_xhtml, "html.parser")
    links = soup.find_all("a")

    for link in links:
        href = link.get("href")
        anchor = href[href.index("#") + 1: ]
        anchors.append(anchor)

    for path in os.listdir(output_epub_folder):
        if path.endswith(".html"):
            htmls.append(join(output_epub_folder, path))

    for path in htmls:
        file = open(path, "r", encoding="utf-8")
        soup = BeautifulSoup(file, "html.parser")
        
        for anchor in anchors:
            objects = soup.select(f"a[id='{anchor}']")
            if len(objects) > 0:
                for obj in objects:
                    number_holder = obj.parent 
                    title_holder = obj.parent.find_next_sibling('p')

                    number = number_holder.find('b').text
                    title = title_holder.find('b').text

                    header_copy = chapter_header_template
                    header_copy = header_copy.replace("chapter_name", title)
                    header_copy = header_copy.replace("chapter_number", number)
                    header_copy = header_copy.replace("anchor", anchor)

                    number_holder.replace_with('')
                    title_holder.replace_with(BeautifulSoup(header_copy, "html.parser"))

        file.close()
        file = open(path, "w", encoding="utf-8")
        file.write(str(soup))
        file.close()

    print("Compressing epub...")
    zip = ZipFile(output_epub_old, "w")

    for path in os.listdir(output_epub_folder):
        f = join(output_epub_folder, path)
        zip.write(f, arcname=os.path.relpath(f, output_epub_folder))

    zip.close()

    print("Re-converting the output file due to cover issues...")
    convert_document(output_epub_old, output_epub)

    shutil.rmtree(output_epub_folder)
    os.remove(output_epub_old)

def convert_document(document: str, output: str, options: list() = []) -> str:
    return subprocess.run(['ebook-convert', document, output] + options,  stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT).stdout

def parse_page(series_slug: str):
    req = requests.get(base_url + series_slug)
    return BeautifulSoup(req.text, "html.parser")

def main():
    soup = parse_page("")
    
    series_title = soup.title.text
    series_title = series_title[0:series_title.index("|") - 1]

    system("clear")

    print(f"Title: {series_title}")
    print("Available volumes:")

    vol_names = list()

    for item in soup.select(".ts-chl-collapsible"):
        vol_names.append(item.text)

    vol_names.reverse()

    for vol in vol_names:
        print(f"{vol_names.index(vol)}: {vol}")

    selected_vol = int(input("Select the desired volume: "))

    volume = Volume(vol_names[selected_vol], series_title, list())

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

    volume.download()

if __name__ == "__main__":
    main()