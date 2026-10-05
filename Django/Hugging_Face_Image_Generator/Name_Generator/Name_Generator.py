import json
import random
from faker import Faker

fake = Faker()

INPUT_FILE = "users.json"
OUTPUT_FILE = "users_with_names.json"

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    users = json.load(f)

used_emails = set()

for user in users:

    gender = random.choice(["Male", "Female"])

    if gender == "Male":
        first_name = fake.first_name_male()
    else:
        first_name = fake.first_name_female()

    last_name = fake.last_name()

    email = f"{first_name}.{last_name}{random.randint(100,9999)}@gmail.com".lower()

    while email in used_emails:
        email = f"{first_name}.{last_name}{random.randint(100,9999)}@gmail.com".lower()

    used_emails.add(email)

    user["first_name"] = first_name
    user["last_name"] = last_name
    user["full_name"] = f"{first_name} {last_name}"
    user["gender"] = gender
    user["email"] = email
    user["phone"] = fake.phone_number()

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(users, f, indent=4)

print(f"Saved {len(users)} users to {OUTPUT_FILE}")
