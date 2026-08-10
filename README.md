# AutoDocGenerator

AutoDocGenerator is a Python-based desktop application that automates the preparation of transaction evidence documents.

The project was created after identifying a repetitive workflow during finance-related work: transaction screenshots and receipts had to be manually checked, ordered, formatted, and inserted into Microsoft Word documents.

A process that previously could take hours can be reduced to only a few minutes using AutoDocGenerator.

## Problem

Preparing transaction evidence manually involves several repetitive steps:

* checking transaction screenshots
* identifying transaction dates and times
* arranging files chronologically
* cropping and resizing images
* inserting evidence into a standardized Word document
* attaching receipts at the end of the document

When dealing with dozens of files and hundreds of transactions, this process becomes time-consuming and prone to human error.

## Solution

AutoDocGenerator automates this workflow by:

* reading transaction screenshots from a folder
* extracting transaction date and time using OCR
* sorting transfer evidence chronologically
* processing screenshots automatically
* inserting images into a standardized Word document
* appending receipt images after transfer evidence
* generating a ready-to-review `.docx` file

## Key Features

* OCR-based transaction date detection
* Automatic chronological sorting
* Support for multiple image formats
* Duplicate image detection
* Automatic screenshot cropping
* Image resizing and formatting
* Automatic Word document generation
* Receipt handling
* Desktop GUI
* Windows executable support

## Tech Stack

* Python
* Tesseract OCR
* pytesseract
* Pillow
* OpenCV
* python-docx
* Tkinter
* PyInstaller
* pytest
* Ruff

## How It Works

```text
Input Files
     ↓
File Loader
     ↓
OCR Transaction Detection
     ↓
Chronological Sorting
     ↓
Image Processing
     ↓
Word Document Generator
     ↓
Final Evidence Document
```

Transfer screenshots are sorted based on the transaction date and time detected inside the image rather than the file creation date.

Receipt images are processed separately and appended after the transfer evidence.

## Privacy

This repository does not contain real transaction documents, bank account information, company records, or confidential financial data.

Any screenshots used for demonstration purposes are dummy data.

## Status

Completed MVP.

The application has been tested locally on Windows and can generate formatted transaction evidence documents automatically.

## Motivation

This project was built as a practical solution to a repetitive finance workflow.

It is also part of my personal exploration of using AI and automation to solve real-world operational problems.




AUTODOCGENERATOR — INSTALLER BUILD GUIDE
Package Files

The installer build package contains the following files:

AutoDocGenerator.iss
build_installer.bat
build_release.bat
File Location

Copy all three files directly into:

D:\Project\AutoDocGenerator
Final Project Structure
D:\Project\AutoDocGenerator
│
├── AutoDocGenerator.iss
├── build_installer.bat
├── build_release.bat
├── build_windows.bat
├── AutoDocGenerator.spec
├── launcher.py
│
├── dist
│   └── AutoDocGenerator
│       ├── AutoDocGenerator.exe
│       └── other required files and folders
│
└── installer_output
    └── AutoDocGenerator_Setup_0.1.0.exe
Build Instructions
Make sure Inno Setup is installed.
Make sure the Python application passes the following checks:
ruff check src tests launcher.py
pytest -q
Run:
build_release.bat
Alternative: Build Separately

Instead of running the complete release build, you can run the build process separately in the following order:

build_windows.bat
build_installer.bat
Final Output

The completed installer will be generated at:

installer_output\AutoDocGenerator_Setup_0.1.0.exe

The setup file can be distributed as a single installer file.

The installer copies the entire contents of:

dist\AutoDocGenerator

rather than only copying AutoDocGenerator.exe. This ensures that all supporting files and dependencies generated during the build process are included.

Tesseract OCR Requirement

Tesseract OCR is not currently bundled with the AutoDocGenerator installer.

Therefore, the destination computer must either:

have Tesseract OCR installed, or
allow the user to manually select the location of tesseract.exe through the AutoDocGenerator application.

This is a current limitation of version 0.1.0 and may be improved in a future release.
