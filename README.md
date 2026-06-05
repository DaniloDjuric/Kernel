# Evidencija radnog vremena


## Zaposleni i rasporedi

Uredi `employees.py` — dodaj ili ukloni zaposlene u `EMPLOYEES_CONFIG`, zatim ponovo pokreni aplikaciju. Broj radnika nije fiksan (4, 5, 6, …). Svaki mora imati dnevni raspored:

Part time: 4h dnevno
6 dana nedeljno: 6h 40 min dnevno
5 dana nedeljno: 8h dnevno

Novi radnik: dodaj red u `EMPLOYEES_CONFIG`, npr. `("Ime Prezime", DailySchedule.EIGHT_HOURS),`.  
Uklonjeni radnik: obriši red i restartuj aplikaciju — više se ne prikazuje, ali stari JSON arhivi i dalje sadrže njegove podatke.

Prekovremeni sati = stvarno radno vrijeme − očekivano za taj raspored. Sačuvano u arhivi kao `prekovremene_minute`.

## Tok rada

Za svakog zaposlenog redom:

1. **Dolazak** — dolazak na posao  
2. **Početak pauze** — odlazak na pauzu  
3. **Kraj pauze** — povratak s pauze  
4. **Kraj smjene** — odlazak s posla  

Samo je sljedeće dugme u nizu je aktivno. Vremena se prikazuju kao **samo za čitanje** — nema ručnog unosa.

Svaki dan se **jednom** automatski sačuva u `data/archive/DD-MM-YYYY.json` (npr. `31-12-2025.json`):
- kad **svi radnici koji su danas došli na posao** završe smjenu (ranije u danu), ili
- u **23:59** ako taj dan još nije sačuvan (samo oni koji su kliknuli Dolazak).

Nakon što je dan sačuvan, aplikacija se resetuje, spremna za sledeći dan.

## Admin mod

1. Kliknite **Admin** (gore desno) i unesite lozinku.  
2. Lozinka je definirana u `admin_auth.py` (`ADMIN_PASSWORD`, zadano: `admin`).  
3. U admin modu:
   - polja vremena postaju **ručno promjenjiva** (format `HH:MM`);
   - dugmad za zaposlene su onemogućena;
   - Omogućeno je biranje i izmjena današnjeg ili prethodnih arhiviranih dana;
   - **Sačuvaj promjene** — zapis u memoriju (danas) ili u JSON arhivu (prošli dani).

Prazno polje znači da taj korak nije zabilježen (npr. poništite krivo pritisnuti odlazak).

