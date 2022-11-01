from genericpath import exists
import os
import subprocess

DEFAULT_ENCODING = "utf-8"

def write(file_path: str, content: str):
    file = open(file_path, "w", encoding=DEFAULT_ENCODING)
    file.write(content)
    file.close()

def read(file_path: str) -> str: 
    file = open(file_path, "r", encoding=DEFAULT_ENCODING)
    content = file.read()
    file.close()
    return content

def read_bytes(file_path: str):
    file = open(file_path, "rb")
    return file

def convert_document(document: str, output: str, options: list() = []) -> str:
    return subprocess.run(['ebook-convert', document, output] + options,  stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT).stdout

def mkdir(path: str):
    if not exists(path):
        os.mkdir(path)

def mkdirs(paths: list):
    for path in paths:
        mkdir(path)
