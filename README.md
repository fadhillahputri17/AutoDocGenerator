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
