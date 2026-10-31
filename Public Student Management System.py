"""
Student Management System
Python + MySQL command-line application

Fields: Admission No., Name, Class, Gender, Date of Birth, Age (auto),
        Address, Stream Opted, Percentage Scored.

Requires: pip install mysql-connector-python
"""

import os
from datetime import date, datetime
from getpass import getpass
import mysql.connector
from mysql.connector import Error

# ---------- Configuration ----------
# Use environment variables or update these placeholders with your generic configurations
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "your_username")
DB_NAME = os.getenv("DB_NAME", "school_database")
TABLE = "student_records"

STREAMS = ["Science", "Commerce", "Humanities"]
MIN_AGE, MAX_AGE = 3, 30  # sanity check for the date of birth entered

# Age is never stored. MySQL works it out from the DOB every time we read.
SELECT_COLS = (
    "admn_no, name, class_name, gender, dob, "
    "TIMESTAMPDIFF(YEAR, dob, CURDATE()) AS age, "
    "stream, percentage, address"
)


# ---------- Database setup ----------
def connect(password, database=None):
  """Open a connection to MySQL (optionally to a specific database)."""
  return mysql.connector.connect(
      host=DB_HOST,
      port=DB_PORT,
      user=DB_USER,
      password=password,
      database=database,
  )


def setup_database(password):
  """Create the database and table if they don't exist yet."""
  conn = connect(password)
  cur = conn.cursor()
  cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
  cur.execute(f"USE {DB_NAME}")
  cur.execute(
      f"""
        CREATE TABLE IF NOT EXISTS {TABLE} (
            admn_no     VARCHAR(20)  PRIMARY KEY,
            name        VARCHAR(100) NOT NULL,
            class_name  VARCHAR(20)  NOT NULL,
            gender      VARCHAR(10)  NOT NULL,
            dob         DATE         NOT NULL,
            address     VARCHAR(255) NOT NULL,
            stream      VARCHAR(20)  NOT NULL,
            percentage  DECIMAL(5,2) NOT NULL
        )
        """
  )
  conn.commit()
  cur.close()
  conn.close()


# ---------- Helpers ----------
def calculate_age(dob, today=None):
  """Age in completed years as of today."""
  today = today or date.today()
  return (
      today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
  )


def format_dob(d):
  return d.strftime("%d-%m-%Y")


def truncate(text, length):
  return text if len(text) <= length else text[: length - 3] + "..."


# ---------- Input helpers ----------
def ask_text(prompt, max_len=255, current=None):
  """Required text. If 'current' is given, pressing Enter keeps the old value."""
  while True:
    hint = f" [{current}]" if current is not None else ""
    value = input(f"{prompt}{hint}: ").strip()
    if not value and current is not None:
      return current
    if not value:
      print("  This field cannot be empty.")
    elif len(value) > max_len:
      print(f"  Too long (maximum {max_len} characters).")
    else:
      return value


def ask_admn_no(prompt="Admission number"):
  """Admission number, stored in capitals so 'a101' and 'A101' match."""
  while True:
    value = ask_text(prompt, max_len=20).upper()
    if " " in value:
      print("  Admission number cannot contain spaces.")
    else:
      return value


def ask_gender(current=None):
  options = {"m": "Male", "f": "Female", "o": "Other"}
  while True:
    hint = f" [{current}]" if current is not None else ""
    value = input(f"Gender (M/F/O){hint}: ").strip().lower()
    if not value and current is not None:
      return current
    if value in options:
      return options[value]
    print("  Please enter M, F or O.")


def ask_date(prompt, current=None):
  """Date of birth in DD-MM-YYYY format."""
  while True:
    hint = f" [{format_dob(current)}]" if current is not None else ""
    value = input(f"{prompt} (DD-MM-YYYY){hint}: ").strip().replace("/", "-")
    if not value and current is not None:
      return current
    try:
      dob = datetime.strptime(value, "%d-%m-%Y").date()
    except ValueError:
      print("  Invalid date. Use DD-MM-YYYY, for example 15-08-2008.")
      continue
    if dob > date.today():
      print("  Date of birth cannot be in the future.")
      continue
    age = calculate_age(dob)
    if not MIN_AGE <= age <= MAX_AGE:
      print(f"  That gives an age of {age}. Expected {MIN_AGE} to {MAX_AGE}.")
      continue
    return dob


def ask_stream(current=None):
  """Stream chosen by number or name."""
  print("Stream opted:")
  for i, s in enumerate(STREAMS, 1):
    print(f"  {i}. {s}")
  while True:
    hint = f" [{current}]" if current is not None else ""
    value = input(f"Choose stream (1-3){hint}: ").strip().lower()
    if not value and current is not None:
      return current
    if value.isdigit() and 1 <= int(value) <= len(STREAMS):
      return STREAMS[int(value) - 1]
    for s in STREAMS:
      if value == s.lower():
        return s
    print("  Please choose 1, 2 or 3 (Science, Commerce, Humanities).")


def ask_percentage(current=None):
  """Percentage between 0 and 100 (up to 2 decimal places)."""
  while True:
    hint = f" [{float(current):.2f}]" if current is not None else ""
    value = input(f"Percentage scored{hint}: ").strip().rstrip("%")
    if not value and current is not None:
      return current
    try:
      number = float(value)
    except ValueError:
      print("  Please enter a number, for example 87.5")
      continue
    if 0 <= number <= 100:
      return round(number, 2)
    print("  Percentage must be between 0 and 100.")


# ---------- Display ----------
def print_students(rows):
  """Print rows as a neat table (long addresses are shortened)."""
  if not rows:
    print("\nNo students found.")
    return

  headers = [
      "Admn No",
      "Name",
      "Class",
      "Gender",
      "DOB",
      "Age",
      "Stream",
      "Percentage",
      "Address",
  ]
  table = [
      [
          r[0],
          r[1],
          r[2],
          r[3],
          format_dob(r[4]),
          str(r[5]),
          r[6],
          f"{float(r[7]):.2f}%",
          truncate(r[8], 25),
      ]
      for r in rows
  ]
  widths = [
      max(len(headers[i]), *(len(r[i]) for r in table))
      for i in range(len(headers))
  ]

  line = "+-" + "-+-".join("-" * w for w in widths) + "-+"
  print()
  print(line)
  print("| " + " | ".join(h.ljust(w) for h, w in zip(headers, widths)) + " |")
  print(line)
  for r in table:
    print("| " + " | ".join(c.ljust(w) for c, w in zip(r, widths)) + " |")
  print(line)
  print(f"{len(table)} record(s)")


def print_detail(row):
  """Full details of one student, including the complete address."""
  print("\n------------------------------")
  print(f"Admission No. : {row[0]}")
  print(f"Name          : {row[1]}")
  print(f"Class         : {row[2]}")
  print(f"Gender        : {row[3]}")
  print(f"Date of Birth : {format_dob(row[4])}")
  print(f"Age           : {row[5]} years")
  print(f"Stream        : {row[6]}")
  print(f"Percentage    : {float(row[7]):.2f}%")
  print(f"Address       : {row[8]}")
  print("------------------------------")


def fetch_student(cur, admn_no):
  cur.execute(f"SELECT {SELECT_COLS} FROM {TABLE} WHERE admn_no = %s", (admn_no,))
  return cur.fetchone()


# ---------- Features ----------
def add_student(conn):
  print("\n--- Add New Student ---")
  cur = conn.cursor()

  while True:
    admn_no = ask_admn_no()
    if fetch_student(cur, admn_no) is None:
      break
    print("  A student with this admission number already exists.")

  name = ask_text("Name", max_len=100)
  class_name = ask_text("Class (e.g. 12-A)", max_len=20).upper()
  gender = ask_gender()
  dob = ask_date("Date of birth")
  print(f"Age (auto-calculated): {calculate_age(dob)} years")
  address = ask_text("Address", max_len=255)
  stream = ask_stream()
  percentage = ask_percentage()

  cur.execute(
      f"INSERT INTO {TABLE} "
      "(admn_no, name, class_name, gender, dob, address, stream, percentage) "
      "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
      (admn_no, name, class_name, gender, dob, address, stream, percentage),
  )
  conn.commit()
  print(f"\nStudent {name} (Admn. No. {admn_no}) added successfully.")
  cur.close()


def view_students(conn):
  print("\n--- All Students ---")
  cur = conn.cursor()
  cur.execute(
      f"SELECT {SELECT_COLS} FROM {TABLE} "
      "ORDER BY class_name, LENGTH(admn_no), admn_no"
  )
  print_students(cur.fetchall())
  cur.close()


def search_students(conn):
  print("\n--- Search Student ---")
  print("1. By admission number")
  print("2. By name")
  print("3. By class")
  print("4. By stream")
  choice = input("Choose (1-4): ").strip()
  cur = conn.cursor()

  if choice == "1":
    admn_no = ask_admn_no()
    row = fetch_student(cur, admn_no)
    if row is None:
      print("\nNo student found with that admission number.")
    else:
      print_detail(row)
    cur.close()
    return
  elif choice == "2":
    name = ask_text("Enter name (or part of it)", max_len=100)
    cur.execute(
        f"SELECT {SELECT_COLS} FROM {TABLE} WHERE name LIKE %s ORDER BY name",
        (f"%{name}%",),
    )
  elif choice == "3":
    class_name = ask_text("Enter class (e.g. 12-A)", max_len=20).upper()
    cur.execute(
        f"SELECT {SELECT_COLS} FROM {TABLE} WHERE class_name = %s "
        "ORDER BY LENGTH(admn_no), admn_no",
        (class_name,),
    )
  elif choice == "4":
    stream = ask_stream()
    cur.execute(
        f"SELECT {SELECT_COLS} FROM {TABLE} WHERE stream = %s ORDER BY name",
        (stream,),
    )
  else:
    print("Invalid choice.")
    cur.close()
    return

  print_students(cur.fetchall())
  cur.close()


def update_student(conn):
  print("\n--- Update Student ---")
  admn_no = ask_admn_no("Enter admission number to update")
  cur = conn.cursor()
  row = fetch_student(cur, admn_no)
  if row is None:
    print("No student found with that admission number.")
    cur.close()
    return

  print("\nCurrent details:")
  print_detail(row)
  print("\nPress Enter to keep the current value.")
  print(
      "(Admission number and age cannot be edited. Age follows the date of"
      " birth.)"
  )

  _, name, class_name, gender, dob, _, stream, percentage, address = row
  name = ask_text("Name", max_len=100, current=name)
  class_name = ask_text("Class", max_len=20, current=class_name).upper()
  gender = ask_gender(current=gender)
  dob = ask_date("Date of birth", current=dob)
  print(f"Age (auto-calculated): {calculate_age(dob)} years")
  address = ask_text("Address", max_len=255, current=address)
  stream = ask_stream(current=stream)
  percentage = ask_percentage(current=percentage)

  cur.execute(
      f"UPDATE {TABLE} SET name=%s, class_name=%s, gender=%s, dob=%s, "
      "address=%s, stream=%s, percentage=%s WHERE admn_no=%s",
      (name, class_name, gender, dob, address, stream, percentage, admn_no),
  )
  conn.commit()
  print("\nStudent updated successfully.")
  cur.close()


def delete_student(conn):
  print("\n--- Delete Student ---")
  admn_no = ask_admn_no("Enter admission number to delete")
  cur = conn.cursor()
  row = fetch_student(cur, admn_no)
  if row is None:
    print("No student found with that admission number.")
    cur.close()
    return

  print_detail(row)
  confirm = (
      input("\nAre you sure you want to delete this student? (y/n): ")
      .strip()
      .lower()
  )
  if confirm == "y":
    cur.execute(f"DELETE FROM {TABLE} WHERE admn_no = %s", (admn_no,))
    conn.commit()
    print("Student deleted.")
  else:
    print("Deletion cancelled.")
  cur.close()


# ---------- Main menu ----------
def show_menu():
  print("\n==============================")
  print("   STUDENT MANAGEMENT SYSTEM")
  print("==============================")
  print("1. Add student")
  print("2. View all students")
  print("3. Search student")
  print("4. Update student")
  print("5. Delete student")
  print("6. Exit")


def main():
  password = getpass(f"Enter MySQL password for user '{DB_USER}': ")

  try:
    setup_database(password)
    conn = connect(password, DB_NAME)
  except Error as e:
    print(f"\nCould not connect to MySQL: {e}")
    print("Check that the MySQL service is running,")
    print("and that your password and port are correct.")
    return

  actions = {
      "1": add_student,
      "2": view_students,
      "3": search_students,
      "4": update_student,
      "5": delete_student,
  }

  try:
    while True:
      show_menu()
      choice = input("Enter your choice (1-6): ").strip()
      if choice == "6":
        print("\nGoodbye!")
        break
      action = actions.get(choice)
      if action is None:
        print("Invalid choice. Please enter a number from 1 to 6.")
        continue
      try:
        action(conn)
      except Error as e:
        conn.rollback()
        print(f"\nDatabase error: {e}")
  except KeyboardInterrupt:
    print("\n\nProgram interrupted. Goodbye!")
  finally:
    if conn.is_connected():
      conn.close()


if __name__ == "__main__":
  main()