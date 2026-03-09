"""
PDF Editor — Join PDF and image files into a single PDF.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Listbox
from pathlib import Path

from pdf_merge import merge_files_to_pdf, IMAGE_EXTENSIONS, PDF_EXTENSION

ALLOWED_EXTENSIONS = tuple(IMAGE_EXTENSIONS | {PDF_EXTENSION})


def get_file_types() -> list[tuple[str, str]]:
    return [
        ("PDF and images", " ".join(f"*{e}" for e in sorted(ALLOWED_EXTENSIONS))),
        ("PDF files", "*.pdf"),
        ("JPEG files", "*.jpg *.jpeg"),
        ("PNG files", "*.png"),
        ("All supported", "*.pdf *.jpg *.jpeg *.png"),
    ]


class PdfEditorApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("PDF Editor — Join PDFs & Images")
        self.root.minsize(480, 420)
        self.root.geometry("560x480")

        self.file_list: list[str] = []
        self.output_folder = tk.StringVar(value="")
        self.output_filename = tk.StringVar(value="merged.pdf")

        self._build_ui()

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill=tk.BOTH, expand=True)

        # Files section
        ttk.Label(main, text="Files to join (PDF, JPEG, PNG):").pack(anchor=tk.W)
        list_frame = ttk.Frame(main)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        scrollbar = ttk.Scrollbar(list_frame)
        self.listbox = Listbox(
            list_frame,
            height=8,
            selectmode=tk.EXTENDED,
            yscrollcommand=scrollbar.set,
            font=("Segoe UI", 10),
        )
        scrollbar.config(command=self.listbox.yview)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=6)
        ttk.Button(btn_frame, text="Add files…", command=self._add_files).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Remove selected", command=self._remove_selected).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_frame, text="Clear all", command=self._clear_list).pack(side=tk.LEFT)

        # Output path
        out_frame = ttk.LabelFrame(main, text="Output", padding=8)
        out_frame.pack(fill=tk.X, pady=(12, 0))

        row1 = ttk.Frame(out_frame)
        row1.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(row1, text="Folder:").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Entry(row1, textvariable=self.output_folder, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        ttk.Button(row1, text="Browse…", command=self._choose_output_folder).pack(side=tk.LEFT)

        row2 = ttk.Frame(out_frame)
        row2.pack(fill=tk.X)
        ttk.Label(row2, text="File name:").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Entry(row2, textvariable=self.output_filename, width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Merge button
        ttk.Button(main, text="Merge to PDF", command=self._merge).pack(pady=16)

    def _add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="Select PDF or image files",
            filetypes=get_file_types(),
        )
        for p in paths:
            if p and p not in self.file_list:
                self.file_list.append(p)
                self.listbox.insert(tk.END, Path(p).name)

    def _remove_selected(self) -> None:
        indices = list(self.listbox.curselection())
        for i in reversed(indices):
            self.listbox.delete(i)
            del self.file_list[i]

    def _clear_list(self) -> None:
        self.listbox.delete(0, tk.END)
        self.file_list.clear()

    def _choose_output_folder(self) -> None:
        path = filedialog.askdirectory(title="Select output folder")
        if path:
            self.output_folder.set(path)

    def _merge(self) -> None:
        if not self.file_list:
            messagebox.showwarning("No files", "Add at least one file to join.")
            return
        folder = self.output_folder.get().strip()
        if not folder:
            messagebox.showwarning("No folder", "Choose an output folder.")
            return
        name = self.output_filename.get().strip()
        if not name:
            messagebox.showwarning("No file name", "Enter an output file name.")
            return
        if not name.lower().endswith(".pdf"):
            name += ".pdf"
        out_path = Path(folder) / name
        try:
            merge_files_to_pdf([Path(p) for p in self.file_list], out_path)
            messagebox.showinfo("Done", f"Saved to:\n{out_path}")
        except FileNotFoundError as e:
            messagebox.showerror("File error", str(e))
        except ValueError as e:
            messagebox.showerror("Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Merge failed:\n{e}")

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    app = PdfEditorApp()
    app.run()


if __name__ == "__main__":
    main()
