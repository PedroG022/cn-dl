from genericpath import exists, isfile
from os.path import join
import os
import shutil
from zipfile import ZipFile

from PyPDF2 import PdfFileReader, PdfMerger
from bs4 import BeautifulSoup
from natsort import natsorted
from book import Series, Chapter, Volume

from utils import write, read, read_bytes, convert_document, mkdir, mkdirs

def save_as_html(chapter: Chapter, out: str):
    print("Saving chapter...")
    write(out, chapter.content)

def merge_htmls(folder: str, out: str):
    print("Merging htmls...")
    content = ""

    for path in os.listdir(folder):
        file_path = join(folder, path)

        if isfile(file_path) and path.endswith(".html"):
            content += f"{read(file_path)}\n"

    write(out, content)

def merge_to_pdf(folder: str, out: str):
    print("Merging to pdf...")
    pdf_merger = PdfMerger()

    chapter_files = list()

    for path in os.listdir(folder):
        if isfile(join(folder, path)):
            chapter_files.append(join(folder, path))

    chapter_files = natsorted(chapter_files)

    for chapter in chapter_files:
        chapter_title = chapter[chapter.rfind("/") + 1: chapter.rfind(".")]
        inserted_at = len(pdf_merger.pages)
        pdf_merger.add_outline_item(pagenum=inserted_at, title=chapter_title)
        pdf_merger.append(PdfFileReader(read_bytes(chapter)))

    pdf_merger.write(out)
    pdf_merger.close()

def compile_volume(series: Series, volume: Volume):
    print("Compiling volume...")
    folder_series = f"{series.title}/"
    mkdir(folder_series)

    folder_volume = f"{folder_series}{volume.title}/"
    folder_html = f"{folder_volume}html/"
    folder_pdf = f"{folder_volume}pdf/"
    folder_epub = f"{folder_volume}epub/"

    mkdirs([folder_volume, folder_html, folder_pdf, folder_epub])

    output_pdf = f"{folder_volume}{volume.complete_title}.pdf"
    output_epub = f"{folder_volume}{volume.complete_title}.epub"

    for chapter in volume.chapters:
        chapter_output_html = f"{folder_html}{chapter.complete_title}.html"
        chapter_output_pdf = f"{folder_pdf}{chapter.complete_title}.pdf"

        if not exists(chapter_output_html):
            save_as_html(chapter, chapter_output_html)

        if not exists(chapter_output_pdf):
            convert_document(chapter_output_html, chapter_output_pdf)

    merge_to_pdf(folder_pdf, output_pdf)
    
    convert_document(output_pdf, output_epub, ["--no-default-epub-cover", "--toc-title", "Sumário", "--pretty-print", 
                        "--epub-inline-toc", "--change-justification", "justify", "--extract-to", folder_epub, "--flow-size", "0"])

    os.remove(output_epub)
    beautify_epub(series, volume)

def beautify_epub(series: Series, volume: Volume):
    print("Modifiying the volume...")
    
    folder_series = f"{series.title}/"
    folder_volume = f"{folder_series}{volume.title}/"
    folder_epub = f"{folder_volume}epub/"

    output_epub_old = f"{folder_volume}{volume.complete_title}.old.epub"
    output_epub = f"{folder_volume}{volume.complete_title}.epub"

    anchors = list()

    contents_xhtml = read(join(folder_epub, "contents.xhtml"))
    chapter_header_template = read("chapter-title.html")

    soup = BeautifulSoup(contents_xhtml, "html.parser")
    links = soup.find_all("a")

    for link in links:
        href = link.get("href")
        anchor = href[href.index("#") + 1: ]
        anchors.append(anchor)

    soup = BeautifulSoup(read(join(folder_epub, "index_split_000.html")), "html.parser")
    
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

    write(join(folder_epub, "index_split_000.html"), str(soup))

    os.remove(join(folder_epub, "index_split_001.html"))

    print("Compressing epub...")
    zip = ZipFile(output_epub_old, "w")

    for path in os.listdir(folder_epub):
        f = join(folder_epub, path)
        zip.write(f, arcname=os.path.relpath(f, folder_epub))

    zip.close()

    print("Re-converting output...")
    convert_document(output_epub_old, output_epub)

    shutil.rmtree(folder_epub)
    os.remove(output_epub_old)

def ProccessSeries(series: Series):
    for volume in series.volumes:
        compile_volume(volume)