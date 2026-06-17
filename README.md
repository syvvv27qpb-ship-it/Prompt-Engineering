# File Profiling Pipeline

Dieses Skript verknüpft Dateizugriffsprotokolle mit LDAP-Verzeichnisdaten und erzeugt pro Datei ein strukturiertes Profil (`file_profiles.csv`). Ziel ist die KI-gestützte Sicherheitsklassifizierung – die Einschätzung von **Vertraulichkeit**, **Integrität** und **Verfügbarkeit** einer Datei anhand von Zugriffsmustern und Inhaltsignalen.

---

## Datenquellen

| Quelle | Beschreibung |
|---|---|
| `Data/r4.2/LDAP/*.csv` | Mitarbeiterverzeichnis: Benutzer-IDs, Abteilungen und Rollen |
| `Data/r4.2/file.csv` | Zugriffsprotokolle: wer hat wann auf welche Datei zugegriffen |

---

## Ausgabe: `file_profiles.csv`

Jede Zeile repräsentiert eine Datei. Die Attribute sind so gestaltet, dass ein KI-Modell ohne manuelle Beschriftung auf die Sensitivität einer Datei schließen kann.

### Identifikation

**`filename`** — Name und Pfad der Datei. Über die reine Identifikation hinaus liefert der Dateiname semantische Hinweise: Namen wie `salary_2024_Q1.xlsx` oder `contract_final.docx` signalisieren mögliche Sensitivität, noch bevor der Inhalt betrachtet wird.

**`file_extension`** — Aus dem Dateinamen abgeleitete Endung. Hilft bei der Unterscheidung von Dokumenttypen (z. B. `.docx`, `.pdf`, `.csv`), die mit bestimmten Inhaltskategorien korrelieren können.

---

### Inhalt

**`content_snippet`** — Das stärkste Attribut. Ein bereinigter Auszug aus dem Dateiinhalt (bis zu 800 Zeichen). Ein KI-Modell kann daraus direkt ableiten, ob eine Datei personenbezogene Daten, Finanzzahlen, strategische Pläne oder öffentliche Informationen enthält – und Vertraulichkeit, Integrität sowie Verfügbarkeit unabhängig von allen anderen Attributen einschätzen. Hex-Artefakte aus Binärdateien werden automatisch entfernt.

---

### Zugriffsbreite (Need-to-Know)

Diese Attribute operationalisieren das **Need-to-Know-Prinzip**: Je weniger Personen und Organisationseinheiten auf eine Datei zugreifen, desto wahrscheinlicher wurde der Zugang bewusst eingeschränkt.

**`unique_user_count`** — Anzahl der verschiedenen Personen, die auf die Datei zugegriffen haben.

**`total_employees`** — Gesamtanzahl aller Mitarbeiter im Datensatz. Dient als Nenner für `access_ratio`.

**`access_ratio`** — `unique_user_count / total_employees`. Die entscheidende Kennzahl: 3 Zugreifende von 1.000 (0,3 %) signalisieren eine stark eingeschränkte Datei; 3 von 5 (60 %) deuten auf breite Verfügbarkeit hin. Absolute Zahlen sind ohne diesen organisatorischen Kontext nicht aussagekräftig.

**`unique_dept_count`** — Anzahl der verschiedenen Abteilungen mit Zugriff. Eine Datei, die nur von einer Abteilung genutzt wird, ist wahrscheinlich fachspezifisch und nicht für die gesamte Organisation bestimmt.

**`total_departments`** — Gesamtanzahl aller Abteilungen in der Organisation. Nenner für `dept_ratio`.

**`dept_ratio`** — `unique_dept_count / total_departments`. Ein hoher Wert zeigt abteilungsübergreifende Relevanz (→ hohe Verfügbarkeitskritikalität); ein niedriger Wert deutet auf fachspezifischen Einsatz hin (→ höhere Vertraulichkeit).

**`unique_role_count`** — Anzahl der verschiedenen Rollen unter den Zugreifenden.

**`total_roles`** — Gesamtanzahl aller Rollen in der Organisation. Nenner für `role_ratio`.

**`role_ratio`** — `unique_role_count / total_roles`. Gibt an, wie rollendivers die Nutzergruppe ist. Eine Datei, auf die ausschließlich Führungsebenen (z. B. Directors, VPs) zugreifen, signalisiert strategisch sensible Inhalte.

---

### Zugriffskomposition (Semantischer Kontext)

**`accessing_roles`** — Sortierte Liste aller Rollen, die auf die Datei zugegriffen haben (z. B. `[Manager, Senior Analyst, Director]`). Rollenhierarchien sind ein starkes Proxy-Signal für Inhaltssensitivität – ausschließlicher Führungszugriff deutet auf strategisches oder vertrauliches Material hin.

**`accessing_departments`** — Sortierte Liste der Abteilungsnamen (z. B. `[Finance, Legal]`). Ergänzt `unique_dept_count` um semantischen Gehalt. Die KI kann aus der Kombination von Abteilungen auf den wahrscheinlichen Inhalt schließen: Finance allein → Finanzdaten; Finance + Legal → Verträge oder Compliance-Dokumente.

---

### Zugriffsvolumen & Konzentration

**`access_frequency`** — Gesamtanzahl aller Zugriffe über den Beobachtungszeitraum. Hohe Frequenz zeigt betriebliche Abhängigkeit: Fällt die Datei aus, bemerkt die Organisation dies sofort. Dies ist der primäre **Verfügbarkeits**-Indikator im Sinne des NIST.

**`top_user_access_ratio`** — Anteil aller Zugriffe, der auf den aktivsten einzelnen Nutzer entfällt. Ein hoher Wert (z. B. 0,95) deutet darauf hin, dass die Datei faktisch von einer Person kontrolliert wird; ein niedriger Wert zeigt verteilte Nutzung.

**`single_department_file`** — Binäres Flag (`1`/`0`): ob alle Zugriffe aus genau einer Abteilung stammen. Schneller Indikator für abteilungsspezifische vs. organisationsweite Dateien.

---

### Zeitliche Merkmale

**`first_access`** — Datum des frühesten aufgezeichneten Zugriffs.

**`last_access`** — Datum des jüngsten Zugriffs.

**`access_span_days`** — `last_access - first_access` in Tagen. Lange Zeitspannen deuten auf dauerhafte Relevanz hin; kurze Spannen können auf einmalige oder projektbezogene Nutzung hinweisen.
