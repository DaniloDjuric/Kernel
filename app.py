from __future__ import annotations

from datetime import date, datetime, time

import customtkinter as ctk

from admin_auth import change_password, verify_password
from app_records import STEP_LABELS, DayRecord, ShiftStep, Workday
from archive_io import is_day_saved, list_archived_dates, load_day, save_day
from employees import EMPLOYEES, expected_minutes
from paths import data_dir, load_ctk_image, load_logo_image

STEPS_UI = (
    ShiftStep.DOLAZAK,
    ShiftStep.POCETAK_PAUZE,
    ShiftStep.KRAJ_PAUZE,
    ShiftStep.KRAJ_SMJENE,
)


class AttendanceApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Evidencija radnog vremena")
        self.geometry("1280x580")
        self.minsize(1050, 450)

        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.workday = Workday()
        self.workday.ensure_employees(EMPLOYEES)

        self.admin_mode = False
        self.admin_view_date: date = date.today()
        self._admin_records: dict[str, DayRecord] | None = None
        self._row_widgets: dict[str, dict] = {}

        self._build_ui()
        self._refresh_all_rows()
        self._check_new_calendar_day()
        self.after(60_000, self._periodic_checks)

    # --- Data access ---------------------------------------------------------

    def _is_viewing_today(self) -> bool:
        return self.admin_view_date == date.today()

    def _active_records(self) -> dict[str, DayRecord]:
        if self.admin_mode and not self._is_viewing_today() and self._admin_records:
            return self._admin_records
        return self.workday.records

    def _record_for(self, name: str) -> DayRecord:
        return self._active_records()[name]

    # --- UI ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self._header_row_height = 40
        self._header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._header_frame.pack(fill="x", padx=24, pady=(16, 4))
        header = self._header_frame
        header.grid_columnconfigure(1, weight=1)
        header.grid_rowconfigure(0, minsize=self._header_row_height)

        self._logo_image = load_ctk_image("icons", "kernel-png.png", size=(32, 32))
        if self._logo_image is None:
            self._logo_image = load_logo_image()

        self._settings_menu_popup: ctk.CTkToplevel | None = None
        self.settings_btn = ctk.CTkButton(
            header,
            text="" if self._logo_image else "K",
            image=self._logo_image,
            width=36,
            height=36,
            fg_color="transparent",
            hover_color=("gray85", "gray30"),
            command=self._toggle_settings_menu,
        )
        self.settings_btn.grid(row=0, column=0, padx=(0, 12))

        self.title_label = ctk.CTkLabel(
            header,
            text="Evidencija radnog vremena",
            font=ctk.CTkFont(size=20, weight="bold"),
            height=36,
        )
        self.title_label.grid(row=0, column=1, sticky="w")

        self.admin_banner = ctk.CTkLabel(
            header,
            text="",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("#b45309", "#fbbf24"),
        )
        self.admin_banner.grid(row=1, column=1, sticky="w", padx=(48, 0))
        self.admin_banner.grid_remove()

        self.admin_btn = ctk.CTkButton(
            header,
            text="Admin",
            width=100,
            height=32,
            fg_color=("gray75", "gray30"),
            hover_color=("gray65", "gray40"),
            command=self._toggle_admin_request,
        )
        self.admin_btn.grid(row=0, column=2, padx=(0, 12))

        self.date_label = ctk.CTkLabel(
            header,
            text="",
            font=ctk.CTkFont(size=14),
            text_color="gray",
            height=36,
            anchor="e",
        )
        self.date_label.grid(row=0, column=3, sticky="e")

        self.admin_bar = ctk.CTkFrame(self, fg_color=("gray88", "gray20"))
        self.admin_bar.pack(fill="x", padx=24, pady=(0, 4))
        self.admin_bar.pack_forget()

        admin_inner = ctk.CTkFrame(self.admin_bar, fg_color="transparent")
        admin_inner.pack(fill="x", padx=12, pady=10)

        ctk.CTkLabel(admin_inner, text="Dan:").pack(side="left", padx=(0, 8))
        self.day_combo = ctk.CTkComboBox(
            admin_inner,
            width=200,
            state="readonly",
            command=self._on_admin_day_changed,
        )
        self.day_combo.pack(side="left")

        self.save_admin_btn = ctk.CTkButton(
            admin_inner,
            text="Sačuvaj promjene",
            command=self._save_admin_edits,
        )
        self.save_admin_btn.pack(side="left", padx=12)

        ctk.CTkLabel(
            admin_inner,
            text="Ručno uređivanje vremena (HH:MM). Prazno polje = nije zabilježeno.",
            text_color="gray",
        ).pack(side="left", padx=(20, 0))

        col_header = ctk.CTkFrame(self, fg_color="transparent")
        col_header.pack(fill="x", padx=24, pady=(4, 0))

        ctk.CTkLabel(col_header, text="Radnici", width=150, anchor="w").grid(
            row=0, column=0, padx=(0, 6), sticky="w"
        )
        col = 1
        for step in STEPS_UI:
            ctk.CTkLabel(col_header, text="Vrijeme", width=72, anchor="center").grid(
                row=0, column=col, padx=2
            )
            ctk.CTkLabel(
                col_header, text=STEP_LABELS[step], width=118, anchor="center"
            ).grid(row=0, column=col + 1, padx=2)
            col += 2

        ctk.CTkLabel(col_header, text="Status", width=190, anchor="w").grid(
            row=0, column=col, padx=(10, 0), sticky="w"
        )

        rows_frame = ctk.CTkScrollableFrame(self)
        rows_frame.pack(fill="both", expand=True, padx=24, pady=10)

        for name in EMPLOYEES:
            row = ctk.CTkFrame(rows_frame, fg_color=("gray92", "gray17"))
            row.pack(fill="x", pady=5, ipady=6)

            ctk.CTkLabel(
                row,
                text=name,
                width=150,
                anchor="w",
                font=ctk.CTkFont(size=14, weight="bold"),
            ).grid(row=0, column=0, padx=12, pady=8, sticky="w")

            time_labels: dict[ShiftStep, ctk.CTkLabel] = {}
            time_entries: dict[ShiftStep, ctk.CTkEntry] = {}
            buttons: dict[ShiftStep, ctk.CTkButton] = {}

            col = 1
            for step in STEPS_UI:
                lbl = ctk.CTkLabel(
                    row,
                    text="—",
                    width=72,
                    anchor="center",
                    fg_color=("gray85", "gray25"),
                    corner_radius=6,
                )
                lbl.grid(row=0, column=col, padx=2, pady=8)

                ent = ctk.CTkEntry(row, width=72, placeholder_text="HH:MM")
                ent.grid(row=0, column=col, padx=2, pady=8)
                ent.grid_remove()

                btn = ctk.CTkButton(
                    row,
                    text=STEP_LABELS[step],
                    width=110,
                    command=lambda n=name, s=step: self._on_action(n, s),
                    border_width=3,
                    border_color=("gray85", "gray25"),
                )
                btn.grid(row=0, column=col + 1, padx=2, pady=8)

                time_labels[step] = lbl
                time_entries[step] = ent
                buttons[step] = btn
                col += 2

            status = ctk.CTkLabel(row, text="", width=190, anchor="w", text_color="gray")
            status.grid(row=0, column=col, padx=10, pady=8, sticky="w")

            self._row_widgets[name] = {
                "time_labels": time_labels,
                "time_entries": time_entries,
                "buttons": buttons,
                "status": status,
            }

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=24, pady=(0, 14))

        self.footer_label = ctk.CTkLabel(
            footer,
            text="",
            font=ctk.CTkFont(size=13),
            text_color="gray",
        )
        self.footer_label.pack(side="left")

        self.hint_label = ctk.CTkLabel(
            footer,
            text="Vremena se unose isključivo pritiskom na dugme.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        self.hint_label.pack(side="right")

    # --- Settings -------------------------------------------------------------

    def _toggle_settings_menu(self) -> None:
        if self._settings_menu_popup is not None and self._settings_menu_popup.winfo_exists():
            self._settings_menu_popup.destroy()
            self._settings_menu_popup = None
            return

        menu = ctk.CTkToplevel(self)
        menu.overrideredirect(True)
        menu.attributes("-topmost", True)
        self._settings_menu_popup = menu

        frame = ctk.CTkFrame(menu, corner_radius=8)
        frame.pack(fill="both", expand=True)

        options = [
            ("Promijeni admin lozinku", self._show_change_password_dialog),
            ("Upravljanje radnicima", self._show_workers_settings_placeholder),
        ]

        for label, action in options:
            ctk.CTkButton(
                frame,
                text=label,
                anchor="w",
                width=220,
                fg_color="transparent",
                hover_color=("gray85", "gray30"),
                command=lambda a=action: self._run_settings_action(a),
            ).pack(fill="x", padx=6, pady=3)

        self.update_idletasks()
        x = self.settings_btn.winfo_rootx()
        y = self.settings_btn.winfo_rooty() + self.settings_btn.winfo_height() + 4
        menu.geometry(f"232x{len(options) * 44 + 16}+{x}+{y}")

        menu.bind("<Escape>", lambda _e: self._close_settings_menu())

    def _close_settings_menu(self) -> None:
        if self._settings_menu_popup is not None and self._settings_menu_popup.winfo_exists():
            self._settings_menu_popup.destroy()
        self._settings_menu_popup = None

    def _run_settings_action(self, action) -> None:
        self._close_settings_menu()
        action()

    def _show_change_password_dialog(self) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title("Promjena admin lozinke")
        dialog.geometry("400x340")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="Promjena admin lozinke",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(pady=(20, 16))

        fields: dict[str, ctk.CTkEntry] = {}
        for label, key in (
            ("Trenutna lozinka:", "current"),
            ("Nova lozinka:", "new"),
            ("Potvrdi novu lozinku:", "confirm"),
        ):
            ctk.CTkLabel(dialog, text=label, anchor="w").pack(padx=32, fill="x")
            ent = ctk.CTkEntry(dialog, width=280, show="*")
            ent.pack(padx=32, pady=(4, 10))
            fields[key] = ent

        fields["current"].focus_set()
        err = ctk.CTkLabel(dialog, text="", text_color="#ef4444")

        def submit() -> None:
            if fields["new"].get() != fields["confirm"].get():
                err.configure(text="Nove lozinke se ne podudaraju.")
                err.pack(pady=(0, 8))
                return
            if change_password(fields["current"].get(), fields["new"].get()):
                dialog.destroy()
                self._show_message("Sačuvano", "Admin lozinka je promijenjena.")
            else:
                err.configure(text="Trenutna lozinka nije ispravna.")
                err.pack(pady=(0, 8))

        btns = ctk.CTkFrame(dialog, fg_color="transparent")
        btns.pack(pady=(8, 20))
        ctk.CTkButton(btns, text="Odustani", fg_color="gray40", command=dialog.destroy).pack(
            side="left", padx=8
        )
        ctk.CTkButton(btns, text="Sačuvaj", command=submit).pack(side="left", padx=8)
        dialog.bind("<Return>", lambda _e: submit())

    def _show_workers_settings_placeholder(self) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title("Upravljanje radnicima")
        dialog.geometry("420x160")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        ctk.CTkLabel(
            dialog,
            text="Upravljanje radnicima\n(dodavanje i uklanjanje)\n\nUskoro dostupno.",
            justify="center",
        ).pack(expand=True, padx=20, pady=20)
        ctk.CTkButton(dialog, text="U redu", command=dialog.destroy).pack(pady=(0, 16))

    # --- Admin ----------------------------------------------------------------

    def _toggle_admin_request(self) -> None:
        if self.admin_mode:
            self._exit_admin()
            return
        self._show_login_dialog()

    def _show_login_dialog(self) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title("Admin prijava")
        dialog.geometry("360x200")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Unesite admin lozinku:", font=ctk.CTkFont(size=14)).pack(
            pady=(24, 8)
        )
        pwd = ctk.CTkEntry(dialog, width=220, show="*")
        pwd.pack()
        pwd.focus_set()

        err = ctk.CTkLabel(dialog, text="", text_color="#ef4444")

        def submit() -> None:
            if verify_password(pwd.get()):
                dialog.destroy()
                self._enter_admin()
            else:
                err.configure(text="Pogrešna lozinka.")
                err.pack(pady=(6, 0))

        ctk.CTkButton(dialog, text="Prijava", command=submit).pack(pady=16)
        dialog.bind("<Return>", lambda _e: submit())

    def _enter_admin(self) -> None:
        self.admin_mode = True
        self.admin_view_date = date.today()
        self._admin_records = None
        self.admin_bar.pack(fill="x", padx=24, pady=(0, 4), after=self.winfo_children()[0])
        self._refresh_day_combo()
        self.admin_btn.configure(text="Zatvori admin mod")
        self.admin_banner.configure(text="ADMIN MOD")
        self.admin_banner.grid(row=1, column=1, sticky="w", padx=(48, 0))
        self.hint_label.configure(
            text="Admin: Ručno uređivanje vremena"
        )
        self._refresh_all_rows()

    def _exit_admin(self) -> None:
        self.admin_mode = False
        self._admin_records = None
        self.admin_view_date = date.today()
        self.admin_bar.pack_forget()
        self.admin_btn.configure(text="Admin")
        self.admin_banner.configure(text="")
        self.admin_banner.grid_remove()
        self.hint_label.configure(text="Vremena se unose isključivo pritiskom na dugme.")
        self._refresh_all_rows()

    def _refresh_day_combo(self) -> None:
        today = date.today()
        options = [f"Danas ({today.strftime('%d.%m.%Y.')})"]
        for d in list_archived_dates():
            if d == today:
                continue
            options.append(d.strftime("%d.%m.%Y."))
        self.day_combo.configure(values=options)
        self.day_combo.set(options[0])

    def _on_admin_day_changed(self, choice: str) -> None:
        if choice.startswith("Danas"):
            self.admin_view_date = date.today()
            self._admin_records = None
        else:
            self.admin_view_date = datetime.strptime(choice, "%d.%m.%Y.").date()
            self._admin_records = load_day(self.admin_view_date, EMPLOYEES)
        self._refresh_all_rows()

    def _read_admin_entries(self, name: str) -> DayRecord | None:
        record = DayRecord()
        widgets = self._row_widgets[name]
        try:
            for step in STEPS_UI:
                text = widgets["time_entries"][step].get()
                record.set(step, DayRecord.parse_time(text, self.admin_view_date))
        except ValueError as exc:
            self._show_message("Greška", str(exc))
            return None
        return record

    def _save_admin_edits(self) -> None:
        if not self.admin_mode:
            return

        new_records: dict[str, DayRecord] = {}
        all_warnings: list[str] = []

        for name in EMPLOYEES:
            parsed = self._read_admin_entries(name)
            if parsed is None:
                return
            warnings = parsed.validation_warnings()
            for w in warnings:
                all_warnings.append(f"{name}: {w}")
            new_records[name] = parsed

        if all_warnings:
            if not self._confirm_warnings(all_warnings):
                return

        if self._is_viewing_today():
            self.workday.records = new_records
            self.workday.work_date = date.today()
            self._show_message("Sačuvano", "Podaci za današnji dan su ažurirani.")
        else:
            save_day(self.admin_view_date, new_records, EMPLOYEES)
            self._admin_records = new_records
            self._show_message(
                "Sačuvano",
                f"Arhiva za {self.admin_view_date.strftime('%d.%m.%Y.')} je ažurirana.",
            )

        self._refresh_all_rows()

    def _confirm_warnings(self, warnings: list[str]) -> bool:
        dialog = ctk.CTkToplevel(self)
        dialog.title("Upozorenje")
        dialog.geometry("480x280")
        dialog.transient(self)
        dialog.grab_set()
        result = {"ok": False}

        text = "Pronađena su upozorenja:\n\n" + "\n".join(f"• {w}" for w in warnings)
        text += "\n\nŽelite li ipak sačuvati?"

        ctk.CTkLabel(dialog, text=text, justify="left", wraplength=440).pack(
            padx=20, pady=20, anchor="w"
        )

        btns = ctk.CTkFrame(dialog, fg_color="transparent")
        btns.pack(pady=(0, 16))

        ctk.CTkButton(
            btns, text="Odustani", fg_color="gray40", command=dialog.destroy
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            btns,
            text="Ipak sačuvaj",
            command=lambda: (result.update(ok=True), dialog.destroy()),
        ).pack(side="left", padx=8)

        dialog.wait_window()
        return result["ok"]

    def _show_message(self, title: str, message: str) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("400x140")
        dialog.transient(self)
        dialog.grab_set()
        ctk.CTkLabel(dialog, text=message, wraplength=360).pack(expand=True, padx=20, pady=20)
        ctk.CTkButton(dialog, text="U redu", command=dialog.destroy).pack(pady=(0, 14))

    # --- Display / actions ----------------------------------------------------

    def _format_status(self, name: str, record: DayRecord) -> str:
        step = record.next_step()
        if step == ShiftStep.DONE:
            mins = record.worked_minutes()
            if mins is None:
                return "Smjena završena"
            text = f"Smjena završena ({DayRecord.format_duration(mins)})"
            overtime = record.overtime_minutes(expected_minutes(name))
            if overtime and overtime > 0:
                text += f", +{DayRecord.format_duration(overtime)} preko"
            return text
        if step == ShiftStep.DOLAZAK:
            return "Nije na poslu"
        if step == ShiftStep.POCETAK_PAUZE:
            t = record.dolazak.strftime("%H:%M") if record.dolazak else ""
            return f"Na poslu od {t}"
        if step == ShiftStep.KRAJ_PAUZE:
            t = record.pocetak_pauze.strftime("%H:%M") if record.pocetak_pauze else ""
            return f"Na pauzi od {t}"
        if step == ShiftStep.KRAJ_SMJENE:
            t = record.kraj_pauze.strftime("%H:%M") if record.kraj_pauze else ""
            return f"Radi (pauza {t})"
        return ""

    def _refresh_row(self, name: str) -> None:
        record = self._record_for(name)
        widgets = self._row_widgets[name]
        next_step = record.next_step()

        if self.admin_mode:
            for step in STEPS_UI:
                widgets["time_labels"][step].grid_remove()
                ent = widgets["time_entries"][step]
                ent.grid()
                ent.delete(0, "end")
                ent.insert(0, DayRecord.format_time(record.get(step)).replace("—", ""))
                widgets["buttons"][step].configure(state="disabled")
        else:
            for step in STEPS_UI:
                widgets["time_entries"][step].grid_remove()
                lbl = widgets["time_labels"][step]
                lbl.grid()
                lbl.configure(text=DayRecord.format_time(record.get(step)))

                btn = widgets["buttons"][step]
                if next_step == ShiftStep.DONE:
                    btn.configure(state="disabled")
                elif step == next_step:
                    btn.configure(state="normal", border_color=("gray85", "gray35"), text_color=("gray10", "gray90"))
                else:
                    btn.configure(state="disabled", border_color=("gray65", "gray15"), text_color=("gray50", "gray60"))

        widgets["status"].configure(text=self._format_status(name, record))

    def _refresh_all_rows(self) -> None:
        view = self.admin_view_date if self.admin_mode else self.workday.work_date
        self.date_label.configure(text=view.strftime("%A, %d.%m.%Y."))

        if not self.admin_mode:
            self._refresh_footer_count()
        else:
            self.footer_label.configure(text="Admin način aktivan")

        for name in EMPLOYEES:
            self._refresh_row(name)

    def _on_action(self, name: str, step: ShiftStep) -> None:
        if self.admin_mode:
            return
        record = self.workday.records[name]
        if record.next_step() != step:
            return
        record.apply(step, datetime.now())
        self._refresh_row(name)
        self._refresh_footer_count()
        if self.workday.all_active_finished(EMPLOYEES):
            self._try_finalize_day(show_message=True)

    def _refresh_footer_count(self) -> None:
        active = self.workday.active_employees(EMPLOYEES)
        if not active:
            saved = is_day_saved(self.workday.work_date)
            self.footer_label.configure(
                text="Danas nema evidentiranih radnika"
                if not saved
                else "Dan je već sačuvan"
            )
            return
        finished = sum(
            1 for n in active if self.workday.records[n].next_step() == ShiftStep.DONE
        )
        self.footer_label.configure(
            text=f"Završilo smjenu: {finished} / {len(active)} radnika danas"
        )

    def _try_finalize_day(self, *, show_message: bool) -> bool:
        """Save the workday once. Only workers who checked in are included."""
        if self.admin_mode:
            return False

        work_date = self.workday.work_date
        if is_day_saved(work_date):
            return False

        active = self.workday.active_employees(EMPLOYEES)
        if not active:
            return False

        path = save_day(work_date, self.workday.records, EMPLOYEES)

        if work_date == date.today():
            self.workday.records = {name: DayRecord() for name in EMPLOYEES}
            self._refresh_all_rows()

        if show_message:
            self._show_message(
                "Dan sačuvan",
                f"Evidencija za {work_date.strftime('%d.%m.%Y.')} je sačuvana "
                f"({len(active)} radnika).\nDatoteka: {path.name}",
            )
        return True

    def _should_auto_finalize_now(self) -> bool:
        now = datetime.now()
        if now.date() != self.workday.work_date:
            return False
        if is_day_saved(self.workday.work_date):
            return False
        return now.time() >= time(23, 59)

    def _check_new_calendar_day(self) -> None:
        if self.admin_mode:
            return
        today = date.today()
        if today != self.workday.work_date:
            self.workday.work_date = today
            self.workday.records = {name: DayRecord() for name in EMPLOYEES}
            self._refresh_all_rows()

    def _periodic_checks(self) -> None:
        if not self.admin_mode and self._should_auto_finalize_now():
            self._try_finalize_day(show_message=True)
        self._check_new_calendar_day()
        self.after(30_000, self._periodic_checks)


def main() -> None:
    data_dir().mkdir(parents=True, exist_ok=True)
    app = AttendanceApp()
    app.mainloop()


if __name__ == "__main__":
    main()
