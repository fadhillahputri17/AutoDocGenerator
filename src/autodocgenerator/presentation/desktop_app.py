from __future__ import annotations

import inspect
import os
import subprocess
import sys
import threading
import tkinter as tk
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from autodocgenerator.application.factory import (
    ApplicationSettings,
    build_workflow,
)


@dataclass(frozen=True, slots=True)
class FormValues:
    """Nilai form yang dikumpulkan sebelum worker thread dijalankan."""

    input_directory: Path
    output_directory: Path
    company_name: str
    bank_name: str
    document_date: datetime | None
    tesseract_path: Path | None
    open_after_finish: bool


class ScrollableFrame(ttk.Frame):
    """Area utama yang dapat digulir secara vertikal."""

    def __init__(self, master: tk.Misc, **kwargs: Any) -> None:
        super().__init__(master, **kwargs)

        self._canvas = tk.Canvas(
            self,
            highlightthickness=0,
            borderwidth=0,
        )
        self._scrollbar = ttk.Scrollbar(
            self,
            orient="vertical",
            command=self._canvas.yview,
        )
        self.content = ttk.Frame(self._canvas)

        self._canvas_window = self._canvas.create_window(
            (0, 0),
            window=self.content,
            anchor="nw",
        )

        self.content.bind(
            "<Configure>",
            self._update_scroll_region,
        )
        self._canvas.bind(
            "<Configure>",
            self._resize_content_width,
        )
        self._canvas.bind(
            "<Enter>",
            self._enable_mousewheel,
        )
        self._canvas.bind(
            "<Leave>",
            self._disable_mousewheel,
        )

        self._canvas.configure(
            yscrollcommand=self._scrollbar.set,
        )

        self._canvas.grid(
            row=0,
            column=0,
            sticky="nsew",
        )
        self._scrollbar.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

    def _update_scroll_region(
        self,
        _event: tk.Event[tk.Misc],
    ) -> None:
        bounding_box = self._canvas.bbox("all")

        if bounding_box is not None:
            self._canvas.configure(
                scrollregion=bounding_box,
            )

    def _resize_content_width(
        self,
        event: tk.Event[tk.Misc],
    ) -> None:
        self._canvas.itemconfigure(
            self._canvas_window,
            width=event.width,
        )

    def _enable_mousewheel(
        self,
        _event: tk.Event[tk.Misc],
    ) -> None:
        self._canvas.bind_all(
            "<MouseWheel>",
            self._on_mousewheel,
        )
        self._canvas.bind_all(
            "<Button-4>",
            self._on_mousewheel_linux,
        )
        self._canvas.bind_all(
            "<Button-5>",
            self._on_mousewheel_linux,
        )

    def _disable_mousewheel(
        self,
        _event: tk.Event[tk.Misc],
    ) -> None:
        self._canvas.unbind_all("<MouseWheel>")
        self._canvas.unbind_all("<Button-4>")
        self._canvas.unbind_all("<Button-5>")

    def _on_mousewheel(
        self,
        event: tk.Event[tk.Misc],
    ) -> None:
        if event.delta:
            self._canvas.yview_scroll(
                int(-event.delta / 120),
                "units",
            )

    def _on_mousewheel_linux(
        self,
        event: tk.Event[tk.Misc],
    ) -> None:
        if event.num == 4:
            self._canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self._canvas.yview_scroll(1, "units")

    def scroll_to_top(self) -> None:
        self._canvas.yview_moveto(0.0)


class DesktopApp:
    """Antarmuka desktop AutoDocGenerator."""

    def __init__(self, root: tk.Tk) -> None:
        self._root = root

        self._root.title("AutoDocGenerator")
        self._root.geometry("1280x820")
        self._root.minsize(900, 650)

        with suppress(tk.TclError):
            self._root.state("zoomed")

        self._input_var = tk.StringVar(value="")
        self._output_var = tk.StringVar(
            value=str(self._default_output_directory())
        )
        self._company_var = tk.StringVar(
            value="PT. XXXXXXX XXXXXX XXXXXXX"
        )
        self._bank_var = tk.StringVar(value="BCA")
        self._document_date_var = tk.StringVar(
            value=datetime.now().strftime("%d/%m/%Y")
        )
        self._tesseract_var = tk.StringVar(
            value=self._default_tesseract_path()
        )
        self._status_var = tk.StringVar(value="Siap.")
        self._progress_text_var = tk.StringVar(value="0%")
        self._open_after_finish_var = tk.BooleanVar(value=False)

        self._progress_value = 0
        self._last_document_path: Path | None = None
        self._last_output_directory: Path | None = None

        self._scrollable: ScrollableFrame
        self._run_button: ttk.Button
        self._open_document_button: ttk.Button
        self._open_folder_button: ttk.Button
        self._log_text: tk.Text
        self._progress_bar: ttk.Progressbar

        self._build_ui()

    @staticmethod
    def _default_output_directory() -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent / "output"

        return Path("output").resolve()

    @staticmethod
    def _default_tesseract_path() -> str:
        common_path = Path(
            r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        )

        if common_path.is_file():
            return str(common_path)

        return ""

    def _build_ui(self) -> None:
        self._configure_styles()

        self._root.columnconfigure(0, weight=1)
        self._root.rowconfigure(0, weight=1)

        self._scrollable = ScrollableFrame(self._root)
        self._scrollable.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        page = self._scrollable.content
        page.columnconfigure(0, weight=1)

        ttk.Label(
            page,
            text="AutoDocGenerator",
            style="Header.TLabel",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            padx=22,
            pady=(18, 6),
        )

        ttk.Label(
            page,
            text=(
                "Susun bukti transfer, nota real, dan PDF menjadi "
                "dokumen Word secara otomatis."
            ),
            style="SubHeader.TLabel",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=22,
            pady=(0, 14),
        )

        settings_frame = ttk.LabelFrame(
            page,
            text="Pengaturan Dokumen",
            padding=14,
        )
        settings_frame.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=22,
            pady=(0, 14),
        )
        settings_frame.columnconfigure(1, weight=1)

        self._add_labeled_entry(
            settings_frame,
            row=0,
            label="Nama perusahaan",
            textvariable=self._company_var,
        )
        self._add_labeled_combobox(
            settings_frame,
            row=1,
            label="Nama bank",
            textvariable=self._bank_var,
            values=("BCA", "BRI"),
        )
        self._add_document_date_row(
            settings_frame,
            row=2,
        )

        folder_frame = ttk.LabelFrame(
            page,
            text="Folder dan Program",
            padding=14,
        )
        folder_frame.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=22,
            pady=(0, 14),
        )
        folder_frame.columnconfigure(1, weight=1)

        self._add_path_selector_row(
            folder_frame,
            row=0,
            label="Folder input",
            variable=self._input_var,
            command=self._choose_input,
            button_text="Pilih Folder",
        )
        self._add_path_selector_row(
            folder_frame,
            row=1,
            label="Folder output",
            variable=self._output_var,
            command=self._choose_output,
            button_text="Pilih Folder",
        )
        self._add_path_selector_row(
            folder_frame,
            row=2,
            label="Tesseract",
            variable=self._tesseract_var,
            command=self._choose_tesseract,
            button_text="Pilih File",
        )

        ttk.Label(
            folder_frame,
            text=(
                'Simpan seluruh nota fisik dan PDF di subfolder "NOTA REAL". '
                "File di folder tersebut diletakkan paling akhir dan "
                "tidak dibaca tanggal transaksinya."
            ),
            wraplength=1150,
            justify="left",
        ).grid(
            row=3,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(12, 4),
        )

        process_frame = ttk.LabelFrame(
            page,
            text="Proses",
            padding=14,
        )
        process_frame.grid(
            row=4,
            column=0,
            sticky="ew",
            padx=22,
            pady=(0, 14),
        )
        process_frame.columnconfigure(0, weight=1)

        ttk.Label(
            process_frame,
            textvariable=self._status_var,
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 10),
        )

        ttk.Label(
            process_frame,
            textvariable=self._progress_text_var,
        ).grid(
            row=0,
            column=1,
            sticky="e",
            pady=(0, 10),
        )

        self._progress_bar = ttk.Progressbar(
            process_frame,
            orient="horizontal",
            mode="determinate",
            maximum=100,
        )
        self._progress_bar.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(0, 10),
        )

        ttk.Checkbutton(
            process_frame,
            text="Buka dokumen Word otomatis setelah selesai",
            variable=self._open_after_finish_var,
        ).grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="w",
        )

        log_frame = ttk.LabelFrame(
            page,
            text="Catatan Proses",
            padding=14,
        )
        log_frame.grid(
            row=5,
            column=0,
            sticky="ew",
            padx=22,
            pady=(0, 20),
        )
        log_frame.columnconfigure(0, weight=1)

        self._log_text = tk.Text(
            log_frame,
            height=12,
            wrap="word",
            state="disabled",
            font=("Consolas", 10),
        )
        self._log_text.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        log_scrollbar = ttk.Scrollbar(
            log_frame,
            orient="vertical",
            command=self._log_text.yview,
        )
        log_scrollbar.grid(
            row=0,
            column=1,
            sticky="ns",
        )
        self._log_text.configure(
            yscrollcommand=log_scrollbar.set,
        )

        self._build_fixed_action_bar()

    def _build_fixed_action_bar(self) -> None:
        action_bar = ttk.Frame(
            self._root,
            padding=(22, 12),
        )
        action_bar.grid(
            row=1,
            column=0,
            sticky="ew",
        )
        action_bar.columnconfigure(3, weight=1)

        self._run_button = ttk.Button(
            action_bar,
            text="Buat Dokumen",
            command=self._start,
            style="Primary.TButton",
        )
        self._run_button.grid(
            row=0,
            column=0,
            padx=(0, 12),
            ipadx=10,
            ipady=8,
        )

        self._open_document_button = ttk.Button(
            action_bar,
            text="Buka Dokumen",
            command=self._open_document,
            state="disabled",
        )
        self._open_document_button.grid(
            row=0,
            column=1,
            padx=(0, 12),
        )

        self._open_folder_button = ttk.Button(
            action_bar,
            text="Buka Folder Hasil",
            command=self._open_output_folder,
            state="disabled",
        )
        self._open_folder_button.grid(
            row=0,
            column=2,
            padx=(0, 12),
        )

        ttk.Button(
            action_bar,
            text="Keluar",
            command=self._root.destroy,
        ).grid(
            row=0,
            column=4,
            ipadx=12,
            sticky="e",
        )

    def _configure_styles(self) -> None:
        style = ttk.Style()

        with suppress(tk.TclError):
            style.theme_use("vista")

        style.configure(
            "Header.TLabel",
            font=("Segoe UI", 20, "bold"),
        )
        style.configure(
            "SubHeader.TLabel",
            font=("Segoe UI", 10),
        )
        style.configure(
            "Primary.TButton",
            font=("Segoe UI", 10, "bold"),
        )

    def _add_labeled_entry(
        self,
        parent: ttk.LabelFrame,
        row: int,
        label: str,
        textvariable: tk.StringVar,
    ) -> None:
        ttk.Label(
            parent,
            text=label,
        ).grid(
            row=row,
            column=0,
            sticky="w",
            pady=8,
            padx=(0, 12),
        )

        ttk.Entry(
            parent,
            textvariable=textvariable,
        ).grid(
            row=row,
            column=1,
            sticky="ew",
            pady=8,
        )

    def _add_labeled_combobox(
        self,
        parent: ttk.LabelFrame,
        row: int,
        label: str,
        textvariable: tk.StringVar,
        values: tuple[str, ...],
    ) -> None:
        ttk.Label(
            parent,
            text=label,
        ).grid(
            row=row,
            column=0,
            sticky="w",
            pady=8,
            padx=(0, 12),
        )

        ttk.Combobox(
            parent,
            textvariable=textvariable,
            values=values,
            state="readonly",
        ).grid(
            row=row,
            column=1,
            sticky="ew",
            pady=8,
        )

    def _add_document_date_row(
        self,
        parent: ttk.LabelFrame,
        row: int,
    ) -> None:
        ttk.Label(
            parent,
            text="Tanggal dokumen",
        ).grid(
            row=row,
            column=0,
            sticky="w",
            pady=8,
            padx=(0, 12),
        )

        ttk.Entry(
            parent,
            textvariable=self._document_date_var,
        ).grid(
            row=row,
            column=1,
            sticky="ew",
            pady=8,
        )

        ttk.Label(
            parent,
            text="Format: DD/MM/YYYY",
        ).grid(
            row=row,
            column=2,
            sticky="w",
            padx=(14, 0),
            pady=8,
        )

    def _add_path_selector_row(
        self,
        parent: ttk.LabelFrame,
        row: int,
        label: str,
        variable: tk.StringVar,
        command: Any,
        button_text: str,
    ) -> None:
        ttk.Label(
            parent,
            text=label,
        ).grid(
            row=row,
            column=0,
            sticky="w",
            pady=8,
            padx=(0, 12),
        )

        ttk.Entry(
            parent,
            textvariable=variable,
        ).grid(
            row=row,
            column=1,
            sticky="ew",
            pady=8,
        )

        ttk.Button(
            parent,
            text=button_text,
            command=command,
        ).grid(
            row=row,
            column=2,
            sticky="w",
            padx=(12, 0),
            pady=8,
        )

    def _choose_input(self) -> None:
        selected = filedialog.askdirectory(
            parent=self._root,
            title="Pilih folder input",
        )

        if selected:
            self._input_var.set(selected)

    def _choose_output(self) -> None:
        selected = filedialog.askdirectory(
            parent=self._root,
            title="Pilih folder output",
        )

        if selected:
            self._output_var.set(selected)

    def _choose_tesseract(self) -> None:
        selected = filedialog.askopenfilename(
            parent=self._root,
            title="Pilih file tesseract.exe",
            filetypes=[
                ("Executable files", "*.exe"),
                ("All files", "*.*"),
            ],
        )

        if selected:
            self._tesseract_var.set(selected)

    def _collect_form_values(self) -> FormValues:
        input_directory_raw = self._input_var.get().strip()
        output_directory_raw = self._output_var.get().strip()
        company_name = self._company_var.get().strip()
        bank_name = self._bank_var.get().strip().upper()
        document_date_raw = self._document_date_var.get().strip()
        tesseract_raw = self._tesseract_var.get().strip()
        open_after_finish = self._open_after_finish_var.get()

        if not input_directory_raw:
            raise ValueError("Folder input belum dipilih.")

        if not output_directory_raw:
            raise ValueError("Folder output belum dipilih.")

        if not company_name:
            raise ValueError("Nama perusahaan belum diisi.")

        if not bank_name:
            raise ValueError("Nama bank belum dipilih.")

        input_directory = Path(
            input_directory_raw
        ).expanduser().resolve()
        output_directory = Path(
            output_directory_raw
        ).expanduser().resolve()

        if not input_directory.is_dir():
            raise ValueError(
                "Folder input tidak ditemukan:\n"
                f"{input_directory}"
            )

        document_date: datetime | None = None

        if document_date_raw:
            try:
                document_date = datetime.strptime(
                    document_date_raw,
                    "%d/%m/%Y",
                )
            except ValueError as error:
                raise ValueError(
                    "Tanggal dokumen harus memakai format DD/MM/YYYY."
                ) from error

        tesseract_path: Path | None = None

        if tesseract_raw:
            tesseract_path = Path(
                tesseract_raw
            ).expanduser().resolve()

            if not tesseract_path.is_file():
                raise ValueError(
                    "File Tesseract tidak ditemukan:\n"
                    f"{tesseract_path}"
                )

        return FormValues(
            input_directory=input_directory,
            output_directory=output_directory,
            company_name=company_name,
            bank_name=bank_name,
            document_date=document_date,
            tesseract_path=tesseract_path,
            open_after_finish=open_after_finish,
        )

    def _start(self) -> None:
        try:
            form_values = self._collect_form_values()
        except Exception as error:
            messagebox.showerror(
                "Data belum lengkap",
                str(error),
                parent=self._root,
            )
            return

        self._last_document_path = None
        self._last_output_directory = None

        self._open_document_button.configure(state="disabled")
        self._open_folder_button.configure(state="disabled")

        self._clear_log()
        self._set_progress(0)
        self._status_var.set("Sedang memulai proses...")

        self._write_log("Memulai AutoDocGenerator...")
        self._write_log(
            f"Folder input: {form_values.input_directory}"
        )
        self._write_log(
            f"Folder output: {form_values.output_directory}"
        )
        self._write_log(
            f"Nama perusahaan: {form_values.company_name}"
        )
        self._write_log(
            f"Nama bank: {form_values.bank_name}"
        )
        self._write_log(
            "Tanggal dokumen: "
            + (
                form_values.document_date.strftime("%d/%m/%Y")
                if form_values.document_date is not None
                else "-"
            )
        )

        self._run_button.configure(state="disabled")

        worker = threading.Thread(
            target=self._run_workflow,
            args=(form_values,),
            daemon=True,
            name="autodocgenerator-worker",
        )
        worker.start()

    def _run_workflow(
        self,
        form_values: FormValues,
    ) -> None:
        try:
            self._root.after(
                0,
                self._status_var.set,
                "Membangun workflow...",
            )
            self._root.after(
                0,
                self._set_progress,
                10,
            )

            workflow = build_workflow(
                ApplicationSettings(
                    company_name=form_values.company_name,
                    bank_name=form_values.bank_name,
                    tesseract_executable_path=(
                        form_values.tesseract_path
                    ),
                )
            )

            self._root.after(
                0,
                self._status_var.set,
                "Memproses file...",
            )
            self._root.after(
                0,
                self._set_progress,
                20,
            )

            def progress_callback(message: str) -> None:
                self._append_log(message)
                self._advance_progress_softly()

            run_kwargs: dict[str, object] = {
                "input_directory": form_values.input_directory,
                "output_directory": form_values.output_directory,
                "progress": progress_callback,
            }

            run_signature = inspect.signature(workflow.run)

            if "document_date" in run_signature.parameters:
                run_kwargs["document_date"] = (
                    form_values.document_date
                )

            result = workflow.run(**run_kwargs)

            document_path = Path(
                result.document_path
            ).resolve()

            run_directory = getattr(
                result,
                "run_directory",
                None,
            )

            if run_directory is not None:
                output_directory = Path(
                    run_directory
                ).resolve()
            else:
                output_directory = (
                    form_values.output_directory.resolve()
                )

            self._root.after(
                0,
                self._finish_success,
                document_path,
                output_directory,
                form_values.open_after_finish,
            )

        except Exception as error:
            error_message = str(error)

            self._root.after(
                0,
                self._finish_failure,
                error_message,
            )

    def _advance_progress_softly(self) -> None:
        self._root.after(
            0,
            self._advance_progress_softly_ui,
        )

    def _advance_progress_softly_ui(self) -> None:
        if self._progress_value < 90:
            self._set_progress(
                self._progress_value + 5
            )

    def _finish_success(
        self,
        document_path: Path,
        output_directory: Path,
        open_after_finish: bool,
    ) -> None:
        self._last_document_path = document_path
        self._last_output_directory = output_directory

        self._set_progress(100)
        self._status_var.set("Selesai.")
        self._run_button.configure(state="normal")
        self._open_document_button.configure(state="normal")
        self._open_folder_button.configure(state="normal")

        self._write_log("")
        self._write_log("Dokumen berhasil dibuat.")
        self._write_log(f"Dokumen: {document_path}")
        self._write_log(
            f"Folder hasil: {output_directory}"
        )

        messagebox.showinfo(
            "Selesai",
            "Dokumen berhasil dibuat:\n\n"
            f"{document_path}",
            parent=self._root,
        )

        if open_after_finish:
            self._open_path(document_path)

    def _finish_failure(
        self,
        error_message: str,
    ) -> None:
        self._status_var.set("Gagal.")
        self._run_button.configure(state="normal")
        self._set_progress(0)

        self._write_log("")
        self._write_log("PROSES GAGAL")
        self._write_log(error_message)

        messagebox.showerror(
            "Gagal",
            error_message,
            parent=self._root,
        )

    def _set_progress(
        self,
        value: int,
    ) -> None:
        self._progress_value = max(
            0,
            min(100, value),
        )
        self._progress_bar["value"] = (
            self._progress_value
        )
        self._progress_text_var.set(
            f"{self._progress_value}%"
        )

    def _append_log(
        self,
        message: str,
    ) -> None:
        self._root.after(
            0,
            self._write_log,
            message,
        )

    def _write_log(
        self,
        message: str,
    ) -> None:
        self._log_text.configure(state="normal")
        self._log_text.insert(
            "end",
            message + "\n",
        )
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    def _clear_log(self) -> None:
        self._log_text.configure(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.configure(state="disabled")

    def _open_document(self) -> None:
        document_path = self._last_document_path

        if document_path is None or not document_path.exists():
            messagebox.showwarning(
                "Belum tersedia",
                "Dokumen hasil belum tersedia.",
                parent=self._root,
            )
            return

        self._open_path(document_path)

    def _open_output_folder(self) -> None:
        output_directory = self._last_output_directory

        if (
            output_directory is None
            or not output_directory.exists()
        ):
            messagebox.showwarning(
                "Belum tersedia",
                "Folder hasil belum tersedia.",
                parent=self._root,
            )
            return

        self._open_path(output_directory)

    def _open_path(
        self,
        path: Path,
    ) -> None:
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.run(
                    ["open", str(path)],
                    check=False,
                )
            else:
                subprocess.run(
                    ["xdg-open", str(path)],
                    check=False,
                )
        except Exception as error:
            messagebox.showerror(
                "Gagal membuka",
                str(error),
                parent=self._root,
            )


def launch_desktop_app() -> None:
    root = tk.Tk()
    DesktopApp(root)
    root.mainloop()
